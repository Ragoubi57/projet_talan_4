"""Tests for the policy engine."""

import pytest
from src.policy.engine import policy_eval


def test_allow_normal_request():
    req = {
        "user_attributes": {"role": "analyst"},
        "fields_requested": [],
        "privacy": {"min_group_size": 10},
    }
    result = policy_eval(req)
    assert result["decision"] == "ALLOW"


def test_deny_narrative_for_analyst():
    req = {
        "user_attributes": {"role": "analyst"},
        "fields_requested": [{"field": "consumer_complaint_narrative", "sensitivity": "HIGH"}],
        "privacy": {"min_group_size": 10},
    }
    result = policy_eval(req)
    assert result["decision"] == "DENY"
    assert "narrative" in result["rationale"].lower() or "sensitivity" in result["rationale"].lower()


def test_allow_narrative_for_compliance():
    req = {
        "user_attributes": {"role": "compliance_officer"},
        "fields_requested": [{"field": "consumer_complaint_narrative", "sensitivity": "HIGH"}],
        "privacy": {"min_group_size": 10},
    }
    result = policy_eval(req)
    assert result["decision"] == "ALLOW"


def test_enforce_min_group_size():
    req = {
        "user_attributes": {"role": "analyst"},
        "fields_requested": [],
        "privacy": {"min_group_size": 5},
    }
    result = policy_eval(req)
    assert result["decision"] == "ALLOW_WITH_CONSTRAINTS"
    assert result["constraints"]["min_group_size"] == 10
