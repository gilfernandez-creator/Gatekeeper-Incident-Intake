# core/artifacts.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.types import DecisionArtifact


OUTBOX_DIR = Path("outbox")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_outbox_artifact(artifact: DecisionArtifact) -> Path:
    """
    Writes the durable, API-agnostic artifact to:
      outbox/accepted/<run_id>.json
      outbox/escalated/<run_id>.json
      outbox/rejected/<run_id>.json
    """
    decision = artifact.decision.lower()
    folder = OUTBOX_DIR / decision
    _ensure_dir(folder)

    path = folder / f"{artifact.run_id}.json"
    payload: Any = artifact.model_dump(mode="json", exclude_none=False)

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
