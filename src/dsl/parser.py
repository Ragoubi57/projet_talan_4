"""Analytics DSL – parse natural-language intents into structured DSL plans."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any


def _detect_intent(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["chart", "trend", "plot", "graph", "visuali"]):
        return "chart"
    if any(w in q for w in ["table", "list", "export", "break down", "breakdown"]):
        return "table"
    return "analysis"


def _detect_metrics(query: str) -> list[str]:
    q = query.lower()
    metrics: list[str] = []
    if "net income" in q:
        metrics.append("net_income")
    if "complaint" in q:
        metrics.append("complaint_volume")
    if "asset" in q:
        metrics.append("total_assets")
    if "deposit" in q:
        metrics.append("total_deposits")
    if "npa" in q or "non-performing" in q:
        metrics.append("npa_ratio")
    if "tier" in q or "capital" in q:
        metrics.append("tier1_ratio")
    if "narrative" in q:
        metrics.append("complaint_narrative")
    if not metrics:
        metrics.append("complaint_volume")
    return metrics


def _detect_dimensions(query: str) -> list[str]:
    q = query.lower()
    dims: list[str] = []
    if "state" in q:
        dims.append("state")
    if "product" in q:
        dims.append("product")
    if "company" in q or "bank" in q:
        dims.append("bank_name")
    if "quarter" in q or "quarterly" in q:
        dims.append("quarter")
    if not dims:
        dims.append("quarter")
    return dims


def _detect_time_range(query: str) -> dict[str, str]:
    q = query.lower()
    today = date.today()
    # "since YYYY"
    m = re.search(r"since (\d{4})", q)
    if m:
        return {"start": f"{m.group(1)}-01-01", "end": today.isoformat(), "grain": "quarter"}
    # "last N months"
    m = re.search(r"last (\d+) months?", q)
    if m:
        months = int(m.group(1))
        start = today - timedelta(days=months * 30)
        return {"start": start.isoformat(), "end": today.isoformat(), "grain": "month"}
    return {"start": "2020-01-01", "end": today.isoformat(), "grain": "quarter"}


def _detect_filters(query: str) -> list[dict[str, str]]:
    """Detect explicit column-level filters from the query.

    Note: "US banks" is treated as context (all data products already
    represent US institutions) rather than an explicit column filter.
    """
    q = query.lower()
    filters: list[dict[str, str]] = []
    # Add state-level filters only if a specific two-letter state is mentioned
    state_match = re.search(r"\b([A-Z]{2})\b", query)
    if state_match and state_match.group(1) in {
        "CA", "TX", "NY", "FL", "IL", "OH", "PA", "GA", "NC", "MI",
    }:
        filters.append({"field": "state", "op": "=", "value": state_match.group(1)})
    return filters


def _detect_export(query: str) -> dict[str, str]:
    q = query.lower()
    if "export" in q or "csv" in q:
        return {"format": "csv"}
    return {"format": "none"}


def _needs_narrative(query: str) -> list[dict[str, Any]]:
    q = query.lower()
    if "narrative" in q:
        return [{"field": "consumer_complaint_narrative", "sensitivity": "HIGH"}]
    return []


def parse_nl_to_dsl(query: str) -> dict[str, Any]:
    """Convert a natural-language analytics request into a structured DSL plan."""
    return {
        "dsl": {
            "intent": _detect_intent(query),
            "metric_ids": _detect_metrics(query),
            "dimensions": _detect_dimensions(query),
            "filters": _detect_filters(query),
            "time_range": _detect_time_range(query),
            "sort": [{"field": _detect_dimensions(query)[0], "direction": "asc"}],
            "limit": 200,
            "privacy": {"min_group_size": 10},
            "export": _detect_export(query),
        },
        "fields_requested": _needs_narrative(query),
    }
