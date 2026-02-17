"""SQL compiler – translate DSL plans into validated SQL using sqlglot."""

from __future__ import annotations

from typing import Any

import sqlglot

# Map metric IDs to their SQL expressions and source tables
METRIC_SQL: dict[str, dict[str, str]] = {
    "net_income": {
        "table": "dp_call_reports",
        "expression": "SUM(net_income)",
        "alias": "total_net_income",
    },
    "complaint_volume": {
        "table": "dp_complaints",
        "expression": "COUNT(*)",
        "alias": "complaint_count",
    },
    "total_assets": {
        "table": "dp_call_reports",
        "expression": "SUM(assets)",
        "alias": "total_assets",
    },
    "total_deposits": {
        "table": "dp_call_reports",
        "expression": "SUM(deposits)",
        "alias": "total_deposits",
    },
    "npa_ratio": {
        "table": "dp_call_reports",
        "expression": "AVG(npa)",
        "alias": "avg_npa",
    },
    "tier1_ratio": {
        "table": "dp_call_reports",
        "expression": "AVG(tier1_ratio)",
        "alias": "avg_tier1_ratio",
    },
    "complaint_narrative": {
        "table": "dp_complaints",
        "expression": "consumer_complaint_narrative",
        "alias": "narrative",
    },
}

# Map dimension names to actual column references per table
DIMENSION_COL: dict[str, str] = {
    "quarter": "quarter",
    "state": "state",
    "product": "product",
    "bank_name": "bank_name",
    "date_received": "date_received",
    "company": "company",
    "channel": "channel",
}

# Dimension overrides for tables that lack certain columns
DIMENSION_TABLE_OVERRIDE: dict[str, dict[str, str]] = {
    "dp_complaints": {
        "quarter": "CONCAT(EXTRACT(YEAR FROM date_received), '-Q', EXTRACT(QUARTER FROM date_received))",
    },
}


def compile_dsl_to_sql(dsl: dict[str, Any], constraints: dict[str, Any] | None = None) -> str:
    """Compile a DSL plan dict into a SQL string, validated via sqlglot."""
    plan = dsl.get("dsl", dsl)
    metrics = plan.get("metric_ids", [])
    dims = plan.get("dimensions", [])
    filters = plan.get("filters", [])
    time_range = plan.get("time_range", {})
    limit = plan.get("limit", 200)
    sort = plan.get("sort", [])
    min_group = (constraints or {}).get("min_group_size", plan.get("privacy", {}).get("min_group_size", 10))

    if not metrics:
        raise ValueError("No metrics specified in DSL plan")

    # Determine source table from first metric
    first_metric = metrics[0]
    meta = METRIC_SQL.get(first_metric)
    if not meta:
        raise ValueError(f"Unknown metric: {first_metric}")
    table = meta["table"]
    overrides = DIMENSION_TABLE_OVERRIDE.get(table, {})

    def _dim_expr(d: str) -> str:
        """Return the SQL expression for a dimension, respecting table overrides."""
        if d in overrides:
            return overrides[d]
        return DIMENSION_COL.get(d, d)

    def _dim_alias(d: str) -> str:
        """Return an alias-safe column reference for GROUP BY / ORDER BY."""
        if d in overrides:
            return d  # use the alias name
        return DIMENSION_COL.get(d, d)

    # SELECT clause
    select_parts: list[str] = []
    for d in dims:
        expr = _dim_expr(d)
        if d in overrides:
            select_parts.append(f"{expr} AS {d}")
        else:
            select_parts.append(expr)
    for m in metrics:
        info = METRIC_SQL.get(m)
        if info:
            select_parts.append(f"{info['expression']} AS {info['alias']}")

    # WHERE clause
    where_parts: list[str] = []
    if time_range.get("start"):
        date_col = "quarter" if table == "dp_call_reports" else "date_received"
        where_parts.append(f"{date_col} >= '{time_range['start']}'")
    if time_range.get("end"):
        date_col = "quarter" if table == "dp_call_reports" else "date_received"
        where_parts.append(f"{date_col} <= '{time_range['end']}'")
    for f in filters:
        where_parts.append(f"{f['field']} {f['op']} '{f['value']}'")

    # GROUP BY / HAVING
    group_exprs = [_dim_expr(d) for d in dims] if dims else []
    group_by = ", ".join(group_exprs) if group_exprs else ""
    # Only apply HAVING privacy threshold for tables with individual-level records
    needs_having = group_by and min_group and table == "dp_complaints"
    having = f"HAVING COUNT(*) >= {min_group}" if needs_having else ""

    # ORDER BY
    order_parts: list[str] = []
    for s in sort:
        col = _dim_alias(s["field"])
        order_parts.append(f"{col} {s.get('direction', 'asc').upper()}")
    order_by = ", ".join(order_parts) if order_parts else ""

    # Assemble
    sql = f"SELECT {', '.join(select_parts)} FROM {table}"
    if where_parts:
        sql += f" WHERE {' AND '.join(where_parts)}"
    if group_by:
        sql += f" GROUP BY {group_by}"
    if having:
        sql += f" {having}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {limit}"

    # Validate via sqlglot
    try:
        parsed = sqlglot.parse(sql, read="duckdb")
        if not parsed:
            raise ValueError("sqlglot returned empty parse")
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Generated SQL failed validation: {exc}") from exc

    return sql
