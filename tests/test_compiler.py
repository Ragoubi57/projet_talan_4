"""Tests for the SQL compiler."""

import pytest
from src.dsl.compiler import compile_dsl_to_sql


def test_compile_net_income():
    plan = {
        "dsl": {
            "metric_ids": ["net_income"],
            "dimensions": ["quarter"],
            "filters": [],
            "time_range": {"start": "2020-01-01", "end": "2025-06-30", "grain": "quarter"},
            "sort": [{"field": "quarter", "direction": "asc"}],
            "limit": 200,
            "privacy": {"min_group_size": 10},
        }
    }
    sql = compile_dsl_to_sql(plan)
    assert "dp_call_reports" in sql
    assert "SUM(net_income)" in sql
    assert "GROUP BY" in sql


def test_compile_complaints():
    plan = {
        "dsl": {
            "metric_ids": ["complaint_volume"],
            "dimensions": ["product", "state"],
            "filters": [],
            "time_range": {"start": "2024-01-01", "end": "2025-01-01", "grain": "month"},
            "sort": [{"field": "product", "direction": "asc"}],
            "limit": 200,
            "privacy": {"min_group_size": 10},
        }
    }
    sql = compile_dsl_to_sql(plan)
    assert "dp_complaints" in sql
    assert "COUNT(*)" in sql
    assert "HAVING COUNT(*) >= 10" in sql


def test_no_metrics_raises():
    plan = {"dsl": {"metric_ids": [], "dimensions": [], "filters": [], "time_range": {}}}
    with pytest.raises(ValueError, match="No metrics"):
        compile_dsl_to_sql(plan)
