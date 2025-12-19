# policies/v1/rules.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.types import NormalizedBundle, QualityFlag


def is_empty_input(raw_text: str) -> bool:
    return raw_text is None or not raw_text.strip()

def field_missing(*, normalized, field: str, **_) -> bool:
    v = getattr(normalized.record, field, None)
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    return False

def field_not_in(*, normalized, field: str, values: List[str], **_) -> bool:
    v = getattr(normalized.record, field, None)
    # If missing, let the missing-category rule handle it (don’t call it invalid)
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    return str(v).strip() not in set(values or [])


def flag_present(normalized: NormalizedBundle, flag: str) -> bool:
    try:
        qf = QualityFlag(flag)
    except Exception:
        return False
    return qf in normalized.report.flags


def missing_required(normalized: NormalizedBundle) -> bool:
    return len(normalized.report.missing_required) > 0


def no_blockers(normalized: NormalizedBundle) -> bool:
    """
    "No blockers" means:
      - required fields present
      - no RELATIVE_TIME_UNRESOLVED flag
    (We keep this conservative.)
    """
    if missing_required(normalized):
        return False
    if QualityFlag.RELATIVE_TIME_UNRESOLVED in normalized.report.flags:
        return False
    return True


def eval_condition(
    condition: str,
    raw_text: str,
    normalized: NormalizedBundle,
    value: Optional[str] = None,
    field: Optional[str] = None,
    values: Optional[List[str]] = None,
) -> bool:
    if condition == "empty_input":
        return is_empty_input(raw_text)

    if condition == "flag_present":
        return bool(value) and flag_present(normalized, value)

    if condition == "field_missing":
        return bool(field) and field_missing(normalized=normalized, field=field)

    if condition == "field_not_in":
        return bool(field) and field_not_in(normalized=normalized, field=field, values=values)
    
    if condition == "missing_required":
        return missing_required(normalized)

    if condition == "no_blockers":
        return no_blockers(normalized)

    return False


def eval_when_block(
    when: Dict[str, Any],
    raw_text: str,
    normalized: NormalizedBundle,
) -> bool:
    """
    Supports:
      when:
        any: [ {condition: ...}, ... ]
      when:
        all: [ {condition: ...}, ... ]
    """
    if "any" in when:
        checks: List[Dict[str, Any]] = when["any"]
        return any(
           eval_condition(
                c["condition"],
                raw_text,
                normalized,
                c.get("value"),
                c.get("field"),
                c.get("values"),
            )
            for c in checks
        )

    if "all" in when:
        checks: List[Dict[str, Any]] = when["all"]
        return all(
           eval_condition(
                c["condition"],
                raw_text,
                normalized,
                c.get("value"),
                c.get("field"),
                c.get("values"),
            )            
            for c in checks
        )

    return False
