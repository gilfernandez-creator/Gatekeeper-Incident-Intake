# core/ingest.py
from __future__ import annotations

from typing import Dict, Any

from core.clock import now_iso_utc
from core.types import IntakeEnvelope, IntakeMetadata


def ingest(raw_text: str, metadata: Dict[str, Any] | None = None) -> IntakeEnvelope:
    """
    Ingest captures raw input exactly as received and ensures minimal metadata defaults.
    No interpretation happens here.
    """
    md = metadata or {}

    meta = IntakeMetadata(
        source=md.get("source"),
        submitted_by=md.get("submitted_by"),
        business_unit=md.get("business_unit"),
        received_at=md.get("received_at") or now_iso_utc(),
        extra={k: v for k, v in md.items() if k not in {"source", "submitted_by", "business_unit", "received_at"}},
    )

    return IntakeEnvelope(raw_text=raw_text, metadata=meta)
