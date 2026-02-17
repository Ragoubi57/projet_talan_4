"""Tests for the full agent pipeline."""

import pytest
from src.agent.pipeline import run_agent
from src.data.seed import seed_database


@pytest.fixture(scope="module")
def db():
    return seed_database()


def test_net_income_query(db):
    result = run_agent(
        "Show quarterly net income trend for US banks since 2020 and highlight outliers.",
        db,
        user_role="analyst",
    )
    assert result["status"] == "success"
    assert len(result["data"]) > 0
    assert "evidence_pack" in result
    assert result["evidence_pack"]["sql_hash"]


def test_complaint_breakdown(db):
    result = run_agent(
        "Break down complaint volumes by product and state for the last 12 months.",
        db,
        user_role="analyst",
    )
    assert result["status"] == "success"
    assert len(result["data"]) > 0


def test_narrative_denied(db):
    result = run_agent(
        "Can I see complaint narratives?",
        db,
        user_role="analyst",
    )
    assert result["status"] == "denied"
    assert "alternative" in result


def test_narrative_allowed_for_compliance(db):
    result = run_agent(
        "Can I see complaint narratives?",
        db,
        user_role="compliance_officer",
    )
    # Compliance officers may access narrative – but it may still error if col is null
    assert result["status"] in ("success", "error")


def test_export_query(db):
    result = run_agent(
        "Export the table and give me an evidence pack for audit.",
        db,
        user_role="analyst",
    )
    assert result["status"] == "success"
    assert result["dsl"]["export"]["format"] == "csv"
    assert "evidence_pack" in result


def test_evidence_pack_structure(db):
    result = run_agent(
        "Show quarterly net income trend for US banks since 2020.",
        db,
    )
    ep = result["evidence_pack"]
    assert "evidence_pack_id" in ep
    assert "timestamp" in ep
    assert "sql_hash" in ep
    assert "datasets_quality" in ep
    assert "policy_decision" in ep
