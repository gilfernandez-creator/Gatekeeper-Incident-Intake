# core/audit.py
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict

from core.types import IntakeEnvelope, ExtractionResult, NormalizedBundle, PolicyDecision



def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

RUNS_DIR = Path("runs")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_run_bundle(
    run_id: str,
    config: Dict[str, Any],
    intake: IntakeEnvelope,
    extraction: ExtractionResult,
    normalized: NormalizedBundle,
    decision: PolicyDecision,
    policy_text: str,
) -> Path:
    """
    Writes a replayable audit bundle:
      runs/<run_id>/raw.json
      runs/<run_id>/extraction.json
      runs/<run_id>/normalized.json
      runs/<run_id>/policy.json
      runs/<run_id>/config.json
      runs/<run_id>/policy.yaml
    """
    run_dir = RUNS_DIR / run_id
    _ensure_dir(run_dir)

    (run_dir / "raw.json").write_text(
        json.dumps(intake.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "extraction.json").write_text(
        json.dumps(extraction.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "normalized.json").write_text(
        json.dumps(normalized.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "policy.json").write_text(
        json.dumps(decision.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ✅ Snapshot the exact policy YAML used
    (run_dir / "policy.yaml").write_text(policy_text, encoding="utf-8")

    # ✅ Record a hash of the exact policy snapshot
    config = dict(config)
    config["policy_hash"] = _sha256(policy_text)

    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return run_dir
