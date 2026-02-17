"""Tests for the DSL parser."""

from src.dsl.parser import parse_nl_to_dsl


def test_net_income_trend():
    plan = parse_nl_to_dsl("Show quarterly net income trend for US banks since 2020 and highlight outliers.")
    dsl = plan["dsl"]
    assert dsl["intent"] == "chart"
    assert "net_income" in dsl["metric_ids"]
    assert "quarter" in dsl["dimensions"]
    assert dsl["time_range"]["start"] == "2020-01-01"


def test_complaint_breakdown():
    plan = parse_nl_to_dsl("Break down complaint volumes by product and state for the last 12 months.")
    dsl = plan["dsl"]
    assert dsl["intent"] == "table"
    assert "complaint_volume" in dsl["metric_ids"]
    assert "product" in dsl["dimensions"]
    assert "state" in dsl["dimensions"]


def test_narrative_detected():
    plan = parse_nl_to_dsl("Can I see complaint narratives?")
    assert len(plan["fields_requested"]) > 0
    assert plan["fields_requested"][0]["sensitivity"] == "HIGH"


def test_export_detected():
    plan = parse_nl_to_dsl("Export the table and give me an evidence pack for audit.")
    assert plan["dsl"]["export"]["format"] == "csv"
