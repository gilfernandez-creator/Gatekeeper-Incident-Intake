# core/normalize.py
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from core.types import (
    ExtractionResult,
    NormalizedRecord,
    NormalizationReport,
    NormalizedBundle,
    QualityFlag,
)

# Gatekeeper v1 required fields for ACCEPT
REQUIRED_FOR_ACCEPT = ("summary", "category", "location", "event_time")

# Heuristic patterns for relative time
RELATIVE_TIME_PATTERNS = [
    r"\btoday\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\blast\s+(night|week|month|year)\b",
    r"\bthis\s+(morning|afternoon|evening|week|month)\b",
    r"\bnext\s+(week|month|year)\b",
    r"\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
]

INJECTION_PATTERNS = [
    r"\bignore (all|any)?\s*(previous|prior)\s+instructions\b",
    r"\baccept this\b",
    r"\bdo not escalate\b",
    r"\bforce accept\b",
    r"\bbypass\b",
    r"\bpolicy override\b",
]

def _has_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)



def _has_relative_time(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in RELATIVE_TIME_PATTERNS)


def _pick_best(extraction: ExtractionResult, field: str) -> Tuple[Optional[object], bool]:
    """
    Returns (value, has_evidence)
    """
    f = extraction.fields.get(field)
    if not f:
        return None, False
    best = f.best()
    if not best:
        return None, False
    has_evidence = best.evidence is not None and bool(best.evidence.text.strip())
    return best.value, has_evidence


def normalize(intake_text: str, extraction: ExtractionResult) -> NormalizedBundle:
    """
    Deterministic normalization. Converts AI candidates into canonical record,
    generates missing-required list and quality flags. Never guesses.
    """

    # Pull best candidates
    summary, summary_ev = _pick_best(extraction, "summary")
    category, category_ev = _pick_best(extraction, "category")
    location, location_ev = _pick_best(extraction, "location")

    event_time, _ = _pick_best(extraction, "event_time")
    severity, sev_ev = _pick_best(extraction, "severity")
    people_involved, _ = _pick_best(extraction, "people_involved")
    requested_action, _ = _pick_best(extraction, "requested_action")

    # Canonicalize types safely
    record = NormalizedRecord(
        summary=str(summary).strip() if isinstance(summary, str) and summary.strip() else None,
        category=str(category).strip() if isinstance(category, str) and category.strip() else None,
        location=str(location).strip() if isinstance(location, str) and location.strip() else None,
        event_time=str(event_time).strip() if isinstance(event_time, str) and event_time.strip() else None,
        severity=str(severity).strip() if isinstance(severity, str) and severity.strip() else None,
        people_involved=people_involved if isinstance(people_involved, list) else [],
        requested_action=str(requested_action).strip()
        if isinstance(requested_action, str) and requested_action.strip()
        else None,
    )


    flags = []

    # Summary quality
    if record.summary is not None and len(record.summary) < 12:
        flags.append(QualityFlag.SUMMARY_TOO_SHORT)
    if record.summary is not None and not summary_ev:
        flags.append(QualityFlag.NO_EVIDENCE_FOR_SUMMARY)

    # Evidence flags for critical fields
    if record.category is not None and not category_ev:
        flags.append(QualityFlag.NO_EVIDENCE_FOR_CATEGORY)
    if record.location is not None and not location_ev:
        flags.append(QualityFlag.NO_EVIDENCE_FOR_LOCATION)
    if record.severity is not None and not sev_ev:
        flags.append(QualityFlag.NO_EVIDENCE_FOR_SEVERITY)

    # Time ambiguity
    if _has_relative_time(intake_text) and not record.event_time:
        flags.append(QualityFlag.RELATIVE_TIME_UNRESOLVED)

    # Missing required fields for ACCEPT
    missing_required = [f for f in REQUIRED_FOR_ACCEPT if getattr(record, f) is None]
    
    if _has_injection(intake_text):
        flags.append(QualityFlag.PROMPT_INJECTION_ATTEMPT)


    report = NormalizationReport(
        missing_required=missing_required,
        flags=flags,
        canonical=record,
    )

    return NormalizedBundle(record=record, report=report)
