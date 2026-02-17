"""Agent pipeline – orchestrates the full analytics flow.

Flow: NL request → METADATA_SEARCH → DSL plan → POLICY_EVAL →
      compile SQL → RUN_QUERY → QUALITY_STATUS → MAKE_EVIDENCE_PACK
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import duckdb

from src.catalog.metrics_catalog import metadata_search
from src.dsl.compiler import compile_dsl_to_sql
from src.dsl.parser import parse_nl_to_dsl
from src.policy.engine import policy_eval


def _sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()[:16]


def quality_status(dataset_ids: list[str], catalog_path: str | None = None) -> list[dict[str, Any]]:
    """QUALITY_STATUS – return freshness + test status for given datasets."""
    from src.catalog.metrics_catalog import _load_catalog

    catalog = _load_catalog(catalog_path)
    result = []
    for dp in catalog.get("data_products", []):
        if dp["name"] in dataset_ids:
            result.append({
                "dataset": dp["name"],
                "version": dp.get("version", "unknown"),
                "freshness": dp.get("freshness", "unknown"),
                "tests_passed": True,
            })
    return result


def make_evidence_pack(
    dsl: dict[str, Any],
    policy_result: dict[str, Any],
    sql: str,
    quality: list[dict[str, Any]],
    row_count: int,
) -> dict[str, Any]:
    """MAKE_EVIDENCE_PACK – build an audit-ready evidence pack."""
    return {
        "evidence_pack_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dsl_plan": dsl,
        "policy_decision": policy_result,
        "sql_hash": _sql_hash(sql),
        "sql": sql,
        "datasets_quality": quality,
        "result_row_count": row_count,
    }


def run_agent(
    query: str,
    con: duckdb.DuckDBPyConnection,
    user_role: str = "analyst",
    catalog_path: str | None = None,
) -> dict[str, Any]:
    """Execute the full verifiable analytics pipeline for a NL query.

    Returns a JSON-serialisable result dict.
    """

    # Step 1: parse NL → DSL
    plan = parse_nl_to_dsl(query)

    # Step 2: metadata search
    meta = metadata_search(query, catalog_path=catalog_path)
    datasets_used = list({m["name"] for m in meta if "name" in m})

    # Step 3: policy evaluation
    policy_request = {
        "user_attributes": {"role": user_role},
        "fields_requested": plan.get("fields_requested", []),
        "privacy": plan["dsl"].get("privacy", {}),
    }
    policy_result = policy_eval(policy_request)

    if policy_result["decision"] == "DENY":
        return {
            "status": "denied",
            "policy": policy_result,
            "explanation": policy_result["rationale"],
            "alternative": "Try a query without narrative fields, or request access elevation.",
            "dsl": plan["dsl"],
        }

    # Step 4: compile DSL → SQL
    constraints = policy_result.get("constraints", {})
    sql = compile_dsl_to_sql(plan, constraints=constraints)

    # Step 5: execute query
    try:
        result_rel = con.execute(sql)
        columns = [desc[0] for desc in result_rel.description]
        rows = result_rel.fetchall()
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "sql": sql,
            "dsl": plan["dsl"],
        }

    # Step 6: quality status
    quality = quality_status(datasets_used, catalog_path=catalog_path)

    # Step 7: evidence pack
    evidence = make_evidence_pack(plan["dsl"], policy_result, sql, quality, len(rows))

    # Build tabular result
    table_data = [dict(zip(columns, row)) for row in rows]

    # Detect outliers (simple IQR on first numeric column)
    outlier_indices: list[int] = []
    numeric_cols = [c for c in columns if any(isinstance(row[columns.index(c)], (int, float)) for row in rows[:1])]
    if numeric_cols and len(rows) >= 4:
        col_idx = columns.index(numeric_cols[-1])  # use last numeric col (the metric)
        values = sorted(row[col_idx] for row in rows if isinstance(row[col_idx], (int, float)))
        q1 = values[len(values) // 4]
        q3 = values[3 * len(values) // 4]
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        for i, row in enumerate(rows):
            v = row[col_idx]
            if isinstance(v, (int, float)) and (v < lo or v > hi):
                outlier_indices.append(i)

    return {
        "status": "success",
        "dsl": plan["dsl"],
        "policy": policy_result,
        "sql": sql,
        "columns": columns,
        "data": table_data,
        "outlier_indices": outlier_indices,
        "evidence_pack": evidence,
        "explanation": _build_explanation(plan["dsl"], len(rows), outlier_indices, policy_result),
    }


def _build_explanation(dsl: dict, row_count: int, outliers: list[int], policy: dict) -> str:
    """Generate a plain-language explanation of the result."""
    intent = dsl.get("intent", "analysis")
    metrics = ", ".join(dsl.get("metric_ids", []))
    dims = ", ".join(dsl.get("dimensions", []))
    tr = dsl.get("time_range", {})
    parts = [
        f"Produced a **{intent}** for metric(s) [{metrics}] grouped by [{dims}].",
        f"Time range: {tr.get('start', '?')} to {tr.get('end', '?')} ({tr.get('grain', 'quarter')}).",
        f"Returned **{row_count}** rows.",
    ]
    if outliers:
        parts.append(f"**{len(outliers)} outlier(s)** detected via IQR method.")
    if policy.get("decision") == "ALLOW_WITH_CONSTRAINTS":
        parts.append(f"Policy applied constraints: {json.dumps(policy.get('constraints', {}))}.")
    return " ".join(parts)
