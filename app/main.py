# app/main.py
from __future__ import annotations
import hashlib
import os

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv()
    

from core.ids import new_run_id
from core.clock import Stopwatch, now_iso_utc
from core.ingest import ingest
from core.extract_ai import extract_ai
from core.normalize import normalize
from core.policy import load_policy, decide
from core.artifacts import write_outbox_artifact
from core.audit import write_run_bundle
from core.types import DecisionArtifact


def run_gatekeeper(raw_text: str, metadata: dict | None = None):
    stopwatch = Stopwatch()
    run_id = new_run_id()

    model = os.getenv("GATEKEEPER_MODEL", "mock")
    if not model:
        raise RuntimeError("GATEKEEPER_MODEL is not set in the environment.")
    policy_version = os.getenv("GATEKEEPER_POLICY_VERSION", "v1")

    # 1. Ingest
    intake = ingest(raw_text, metadata)

    # 2. Extract (AI sensor)
    extraction = extract_ai(intake.raw_text, model=model)

    # 3. Normalize
    normalized = normalize(intake.raw_text, extraction)

    # 4. Policy gate
    policy_doc, policy_text = load_policy(policy_version)
    decision = decide(policy_doc, intake.raw_text, normalized)
    
    policy_hash = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()


    # 5. Build artifact
    artifact = DecisionArtifact(
        run_id=run_id,
        decision=decision.decision,
        policy_version=policy_version,
        model=model,
        received_at=intake.metadata.received_at,
        decided_at=now_iso_utc(),
        duration_ms=stopwatch.ms(),
        input=intake,
        extraction=extraction,
        normalized=normalized,
        policy=decision,
        build={
            "system": "Gatekeeper",
            "policy_version": policy_version,
            "policy_hash": policy_hash,
        },
    )

    # 6. Persist outputs
    outbox_path = write_outbox_artifact(artifact)
    run_dir = write_run_bundle(
        run_id=run_id,
        config={
            "model": model,
            "policy_version": policy_version,
        },
        intake=intake,
        extraction=extraction,
        normalized=normalized,
        decision=decision,
        policy_text=policy_text,
    )

    return artifact, outbox_path, run_dir


if __name__ == "__main__":
    print("\nGatekeeper — CLI Test\n")
    raw = input("Paste intake text:\n> ")

    artifact, outbox, run_dir = run_gatekeeper(raw)

    print("\nDecision:", artifact.decision)
    print("Outbox file:", outbox)
    print("Run bundle:", run_dir)
