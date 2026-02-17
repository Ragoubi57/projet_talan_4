"""Policy engine – ABAC / PBAC evaluation inspired by OPA."""

from __future__ import annotations

from typing import Any

# ---------- default policies ----------

DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        "id": "deny_narrative_fields",
        "description": "Narrative / free-text fields are HIGH sensitivity and denied for most roles.",
        "match": lambda req: any(
            f.get("sensitivity", "").upper() == "HIGH"
            for f in req.get("fields_requested", [])
        ),
        "allowed_roles": ["compliance_officer", "admin"],
        "action": "DENY",
        "rationale": "High-sensitivity narrative fields are restricted. Only compliance_officer or admin roles may access them.",
    },
    {
        "id": "min_aggregation",
        "description": "Enforce minimum group size for privacy.",
        "match": lambda req: req.get("privacy", {}).get("min_group_size", 10) < 10,
        "allowed_roles": [],
        "action": "ALLOW_WITH_CONSTRAINTS",
        "constraints": {"min_group_size": 10},
        "rationale": "Minimum group size of 10 enforced for privacy.",
    },
]


def policy_eval(request_json: dict[str, Any], policies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """POLICY_EVAL – evaluate request against policies.

    Returns ``{decision, constraints, rationale}``.
    """
    policies = policies if policies is not None else DEFAULT_POLICIES
    user_role = request_json.get("user_attributes", {}).get("role", "analyst")

    for policy in policies:
        if policy["match"](request_json):
            if user_role in policy.get("allowed_roles", []):
                continue
            if policy["action"] == "DENY":
                return {
                    "decision": "DENY",
                    "constraints": {},
                    "rationale": policy["rationale"],
                }
            if policy["action"] == "ALLOW_WITH_CONSTRAINTS":
                return {
                    "decision": "ALLOW_WITH_CONSTRAINTS",
                    "constraints": policy.get("constraints", {}),
                    "rationale": policy["rationale"],
                }

    return {"decision": "ALLOW", "constraints": {}, "rationale": "Request complies with all policies."}
