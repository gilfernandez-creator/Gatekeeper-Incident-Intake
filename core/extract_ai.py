# core/extract_ai.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from core.types import (
    ExtractionResult,
    ExtractedField,
    ExtractedCandidate,
    EvidenceSpan,
)

FIELDS = [
    "summary",
    "category",
    "location",
    "event_time",
    "severity",
    "people_involved",
    "requested_action",
]


SYSTEM_PROMPT = """You are Gatekeeper's Extraction Sensor.

Rules:
- You only extract information.
- You NEVER decide outcomes.
- You NEVER invent missing data.
- If a field is not explicitly supported, return UNKNOWN or empty.
- Evidence must be verbatim from the input text.
- Max 2 candidates per field.
"""


# ---------- Structured Output Schema ----------

class Candidate(BaseModel):
    value: str = Field(
        ...,
        description="Extracted value as a string. Use 'UNKNOWN' if not supported."
    )
    evidence: str = Field(
        ...,
        description="Verbatim excerpt from the input text supporting the value."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence the value is explicitly supported by the text."
    )



class Fields(BaseModel):
    summary: List[Candidate] = []
    category: List[Candidate] = []
    location: List[Candidate] = []
    event_time: List[Candidate] = []
    severity: List[Candidate] = []
    people_involved: List[Candidate] = []
    requested_action: List[Candidate] = []


class ExtractionPayload(BaseModel):
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    fields: Fields
    notes: str = ""


# ---------- Helpers ----------

def _find_span(raw: str, snippet: str) -> EvidenceSpan:
    if not snippet:
        return EvidenceSpan(text="", start=None, end=None)

    idx = raw.find(snippet)
    if idx == -1:
        return EvidenceSpan(text=snippet, start=None, end=None)

    return EvidenceSpan(text=snippet, start=idx, end=idx + len(snippet))


def _convert_field(raw_text: str, name: str, candidates: List[Candidate]) -> ExtractedField:
    ef = ExtractedField(field=name, candidates=[])

    for c in candidates[:2]:
        if isinstance(c.value, str) and c.value.upper() == "UNKNOWN":
            continue

        evidence = _find_span(raw_text, c.evidence)

        ef.candidates.append(
            ExtractedCandidate(
                value=c.value,
                evidence=evidence if evidence.text else None,
                confidence=c.confidence,
            )
        )

    return ef


# ---------- Main extractor ----------

def extract_ai(raw_text: str, model: str) -> ExtractionResult:
    client = OpenAI()

    resp = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""Raw intake text:
\"\"\"{raw_text}\"\"\"

Extract candidates for:
- summary
- category: one of ["Injury/Illness", "Near Miss", "Property Damage", "Motor Vehicle Accident", "Environmental Incident"] if explicitly supported, otherwise UNKNOWN
- location
- event_time (ISO or UNKNOWN)
- severity (Low/Medium/High/Critical or UNKNOWN)
- people_involved
- requested_action
""",
            },
        ],
        text_format=ExtractionPayload,
    )

    parsed: Optional[ExtractionPayload] = resp.output_parsed
    if not parsed:
        return ExtractionResult(
            model=model,
            extraction_confidence=0.0,
            fields={f: ExtractedField(field=f) for f in FIELDS},
            notes="No structured output returned.",
        )

    fields: Dict[str, ExtractedField] = {}
    for f in FIELDS:
        fields[f] = _convert_field(raw_text, f, getattr(parsed.fields, f))

    return ExtractionResult(
        model=model,
        extraction_confidence=parsed.extraction_confidence,
        fields=fields,
        notes=parsed.notes,
    )
