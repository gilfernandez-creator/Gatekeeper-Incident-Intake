# evals/invariants.py
from __future__ import annotations

from core.types import DecisionArtifact, QualityFlag, ReasonCode


def invariant_missing_required_never_accept(artifact: DecisionArtifact):
    if artifact.normalized.report.missing_required:
        assert artifact.decision != "ACCEPTED", (
            "Invariant violated: ACCEPTED despite missing required fields"
        )


def invariant_relative_time_never_accept(artifact: DecisionArtifact):
    flags = artifact.normalized.report.flags
    if QualityFlag.RELATIVE_TIME_UNRESOLVED in flags:
        assert artifact.decision != "ACCEPTED", (
            "Invariant violated: ACCEPTED with unresolved relative time"
        )


def invariant_rejected_has_reason(artifact: DecisionArtifact):
    if artifact.decision == "REJECTED":
        assert artifact.policy.reason_codes, (
            "Invariant violated: REJECTED without reason codes"
        )


def invariant_accepted_schema_complete(artifact: DecisionArtifact):
    if artifact.decision == "ACCEPTED":
        missing = artifact.normalized.report.missing_required
        assert not missing, (
            f"Invariant violated: ACCEPTED with missing fields {missing}"
        )


INVARIANTS = [
    invariant_missing_required_never_accept,
    invariant_relative_time_never_accept,
    invariant_rejected_has_reason,
    invariant_accepted_schema_complete,
]
