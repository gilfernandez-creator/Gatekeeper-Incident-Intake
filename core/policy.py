# core/policy.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from core.types import PolicyDecision, ReasonCode, Decision
from policies.v1.rules import eval_when_block


def load_policy(policy_version: str) -> Tuple[Dict[str, Any], str]:
    """
    Returns (policy_doc, policy_text) so we can snapshot the exact YAML used.
    """
    path = Path("policies") / policy_version / "policy.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")

    policy_text = path.read_text(encoding="utf-8")
    policy_doc = yaml.safe_load(policy_text)
    return policy_doc, policy_text


def decide(
    policy_doc: Dict[str, Any],
    raw_text: str,
    normalized_bundle,
) -> PolicyDecision:
    """
    Deterministic policy evaluation: first match wins.
    """
    rules = policy_doc.get("rules", [])
    for rule in rules:
        rule_id = rule.get("id", "UNKNOWN_RULE")
        when = rule.get("when", {})
        if eval_when_block(when, raw_text=raw_text, normalized=normalized_bundle):
            then = rule.get("then", {})
            decision: Decision = then.get("decision", "ESCALATED")

            rc = then.get("reason_codes", []) or []
            reason_codes = []
            for r in rc:
                try:
                    reason_codes.append(ReasonCode(r))
                except Exception:
                    # Unknown reason codes get ignored to keep engine resilient
                    pass

            return PolicyDecision(
                decision=decision,
                reason_codes=reason_codes,
                rule_ids_fired=[rule_id],
                required_next_actions=then.get("required_next_actions", []) or [],
                confidence_bound=0.75,
            )

    # If somehow no rules matched, fail-safe escalate
    return PolicyDecision(
        decision="ESCALATED",
        reason_codes=[ReasonCode.POLICY_BLOCKED],
        rule_ids_fired=["NO_RULE_MATCH"],
        required_next_actions=["Review input and policy configuration."],
        confidence_bound=0.5,
    )
