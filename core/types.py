# core/types.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# -----------------------------
# Enums / constants
# -----------------------------

Decision = Literal["ACCEPTED", "ESCALATED", "REJECTED"]


class ReasonCode(str, Enum):
    EMPTY_INPUT = "EMPTY_INPUT"
    SUMMARY_TOO_SHORT = "SUMMARY_TOO_SHORT"
    MISSING_REQUIRED_FIELDS = "MISSING_REQUIRED_FIELDS"
    NO_EVIDENCE_FOR_CRITICAL_FIELD = "NO_EVIDENCE_FOR_CRITICAL_FIELD"
    RELATIVE_TIME_UNRESOLVED = "RELATIVE_TIME_UNRESOLVED"
    LOCATION_AMBIGUOUS = "LOCATION_AMBIGUOUS"
    LOW_CONFIDENCE_CRITICAL = "LOW_CONFIDENCE_CRITICAL"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    MISSING_LOCATION = "MISSING_LOCATION"


class QualityFlag(str, Enum):
    SUMMARY_TOO_SHORT = "SUMMARY_TOO_SHORT"
    LOCATION_AMBIGUOUS = "LOCATION_AMBIGUOUS"
    RELATIVE_TIME_UNRESOLVED = "RELATIVE_TIME_UNRESOLVED"
    NO_EVIDENCE_FOR_SEVERITY = "NO_EVIDENCE_FOR_SEVERITY"
    NO_EVIDENCE_FOR_CATEGORY = "NO_EVIDENCE_FOR_CATEGORY"
    NO_EVIDENCE_FOR_LOCATION = "NO_EVIDENCE_FOR_LOCATION"
    NO_EVIDENCE_FOR_SUMMARY = "NO_EVIDENCE_FOR_SUMMARY"
    PROMPT_INJECTION_ATTEMPT = "PROMPT_INJECTION_ATTEMPT"



# -----------------------------
# Input
# -----------------------------

class IntakeMetadata(BaseModel):
    source: Optional[str] = None          # email, form, chat, etc.
    submitted_by: Optional[str] = None
    business_unit: Optional[str] = None
    received_at: Optional[str] = None     # ISO-8601 string (set by ingest if missing)
    extra: Dict[str, Any] = Field(default_factory=dict)


class IntakeEnvelope(BaseModel):
    raw_text: str = Field(..., description="Raw unstructured input exactly as received")
    metadata: IntakeMetadata = Field(default_factory=IntakeMetadata)


# -----------------------------
# Extraction (AI as sensor)
# -----------------------------

class EvidenceSpan(BaseModel):
    text: str = Field(..., description="Evidence excerpt from the raw input")
    start: Optional[int] = Field(default=None, description="Start char index in raw_text")
    end: Optional[int] = Field(default=None, description="End char index in raw_text")


class ExtractedCandidate(BaseModel):
    value: Any
    evidence: Optional[EvidenceSpan] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class ExtractedField(BaseModel):
    field: str
    candidates: List[ExtractedCandidate] = Field(default_factory=list)

    def best(self) -> Optional[ExtractedCandidate]:
        if not self.candidates:
            return None
        return sorted(self.candidates, key=lambda c: c.confidence, reverse=True)[0]


class ExtractionResult(BaseModel):
    model: str
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    notes: Optional[str] = None


# -----------------------------
# Normalized record (deterministic)
# -----------------------------

class NormalizedRecord(BaseModel):
    # Generic intake record (v1)
    summary: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None

    event_time: Optional[str] = None      # ISO if resolvable, else None
    severity: Optional[str] = None
    people_involved: List[str] = Field(default_factory=list)
    requested_action: Optional[str] = None


class NormalizationReport(BaseModel):
    missing_required: List[str] = Field(default_factory=list)
    flags: List[QualityFlag] = Field(default_factory=list)
    canonical: NormalizedRecord = Field(default_factory=NormalizedRecord)


class NormalizedBundle(BaseModel):
    record: NormalizedRecord
    report: NormalizationReport


# -----------------------------
# Policy output (system authority)
# -----------------------------

class PolicyDecision(BaseModel):
    decision: Decision
    reason_codes: List[ReasonCode] = Field(default_factory=list)
    rule_ids_fired: List[str] = Field(default_factory=list)
    required_next_actions: List[str] = Field(default_factory=list)
    confidence_bound: float = Field(ge=0.0, le=1.0, default=0.75)


# -----------------------------
# Final artifact (durable output)
# -----------------------------

class DecisionArtifact(BaseModel):
    run_id: str
    decision: Decision

    policy_version: str
    model: str

    received_at: str
    decided_at: str
    duration_ms: int

    input: IntakeEnvelope
    extraction: ExtractionResult
    normalized: NormalizedBundle
    policy: PolicyDecision

    # Helpful for debugging / “enterprise-ness”
    build: Dict[str, Any] = Field(default_factory=dict)
