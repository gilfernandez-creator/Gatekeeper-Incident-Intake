# evals/run_evals.py
from __future__ import annotations

import json
from pathlib import Path

from app.main import run_gatekeeper
from evals.invariants import INVARIANTS


CASES_PATH = Path("evals/cases.jsonl")


def load_cases():
    cases = []
    with CASES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def run():
    cases = load_cases()
    failures = 0

    print("\nGatekeeper — Evaluation Run\n")

    for case in cases:
        cid = case["id"]
        raw = case["raw_text"]
        expected = case.get("expected_decision")

        artifact, _, _ = run_gatekeeper(raw)

        print(f"[{cid}] decision={artifact.decision}", end="")

        # Expected decision check (soft assertion)
        if expected and artifact.decision != expected:
            print(f"  ❌ expected={expected}", end="")
            failures += 1
        else:
            print("  ✅", end="")

        # Invariant checks (hard assertions)
        try:
            for inv in INVARIANTS:
                inv(artifact)
            print("  invariants=PASS")
        except AssertionError as e:
            print(f"\n    🔥 INVARIANT FAILED: {e}")
            failures += 1
        must_not_be = case.get("must_not_be")
        if must_not_be and artifact.decision == must_not_be:
            print(f"  🔥 must_not_be violated: {must_not_be}")
            failures += 1


    print("\n----------------------------")
    if failures:
        print(f"❌ FAILURES: {failures}")
        raise SystemExit(1)
    else:
        print("✅ ALL EVALS PASSED")
        return True


if __name__ == "__main__":
    run()
