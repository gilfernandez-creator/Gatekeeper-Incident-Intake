# app/ui_gradio.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import gradio as gr

from app.main import run_gatekeeper


def _safe_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _decision_badge(decision: str) -> str:
    # Minimal “enterprise” styling without custom CSS dependencies
    if decision == "ACCEPTED":
        return "✅ **ACCEPTED**"
    if decision == "ESCALATED":
        return "🟨 **ESCALATED**"
    return "🛑 **REJECTED**"


def _flatten_extraction(artifact) -> List[List[Any]]:
    """
    Returns rows: [field, best_value, confidence, evidence_excerpt]
    """
    rows: List[List[Any]] = []
    fields = artifact.extraction.fields or {}

    for field_name, ef in fields.items():
        best = ef.best() if ef else None
        if not best:
            rows.append([field_name, None, None, None])
            continue

        ev = best.evidence.text if best.evidence else None
        conf = best.confidence
        rows.append([field_name, best.value, conf, ev])

    # Sort: important fields first
    priority = {"summary": 0, "category": 1, "location": 2, "event_time": 3, "severity": 4}
    rows.sort(key=lambda r: priority.get(r[0], 99))
    return rows


def _make_policy_trace(artifact) -> str:
    p = artifact.policy
    lines = []
    lines.append(f"**Decision:** {artifact.decision}")
    lines.append(f"**Rule fired:** `{p.rule_ids_fired[0] if p.rule_ids_fired else 'NONE'}`")

    if p.reason_codes:
        lines.append("**Reason codes:** " + ", ".join([f"`{rc}`" for rc in p.reason_codes]))
    else:
        lines.append("**Reason codes:** *(none)*")

    if p.required_next_actions:
        lines.append("**Required next actions:**")
        for a in p.required_next_actions:
            lines.append(f"- {a}")
    else:
        lines.append("**Required next actions:** *(none)*")

    lines.append(f"**Confidence bound:** `{p.confidence_bound}`")
    return "\n".join(lines)


def _make_normalization_summary(artifact) -> str:
    rep = artifact.normalized.report
    missing = rep.missing_required or []
    flags = rep.flags or []

    out = []
    out.append("### Normalization Report")

    if missing:
        out.append("**Missing required fields:** " + ", ".join([f"`{m}`" for m in missing]))
    else:
        out.append("**Missing required fields:** *(none)*")

    if flags:
        out.append("**Quality flags:** " + ", ".join([f"`{f}`" for f in flags]))
    else:
        out.append("**Quality flags:** *(none)*")

    return "\n".join(out)


def _run_console(raw_text: str) -> Tuple[
    str, str, str, List[List[Any]], str, str, str, str
]:
    artifact, outbox_path, run_dir = run_gatekeeper(raw_text)

    # Top card
    policy_version = artifact.policy_version
    build = artifact.build or {}
    policy_hash = build.get("policy_hash", "unknown")

    header = "\n".join([
        f"{_decision_badge(artifact.decision)}",
        f"**Run ID:** `{artifact.run_id}`",
        f"**Policy:** `{policy_version}`  •  **Hash:** `{policy_hash[:12]}...`",
        f"**Model:** `{artifact.model}`",
        f"**Duration:** `{artifact.duration_ms} ms`",
        f"**Outbox:** `{outbox_path}`",
        f"**Run bundle:** `{run_dir}`",
    ])

    # Panels
    normalized_json = _safe_json(artifact.normalized.model_dump())
    policy_json = _safe_json(artifact.policy.model_dump())
    record_json = _safe_json(artifact.normalized.record.model_dump())
    extraction_rows = _flatten_extraction(artifact)
    policy_trace = _make_policy_trace(artifact)
    norm_summary = _make_normalization_summary(artifact)
    full_artifact = _safe_json(artifact.model_dump())

    return (
        header,
        norm_summary,
        policy_trace,
        extraction_rows,
        record_json,
        normalized_json,
        policy_json,
        full_artifact,
    )


with gr.Blocks(title="Gatekeeper Console") as demo:
    gr.Markdown(
        """
# Gatekeeper Console
**Policy-gated AI decision system**  
Unstructured intake → evidence-bound extraction → deterministic normalization → policy decision → auditable artifact
"""
    )

    with gr.Row():
        raw_input = gr.Textbox(
            label="Raw Intake Text",
            lines=7,
            placeholder="Paste an intake request, incident report, or ticket text…",
        )

    run_btn = gr.Button("Run Gatekeeper", variant="primary")

    # Decision card
    decision_card = gr.Markdown()

    with gr.Tabs():
        with gr.Tab("Overview"):
            norm_summary = gr.Markdown()
            policy_trace = gr.Markdown()

        with gr.Tab("Extraction"):
            gr.Markdown("### Best candidates (per field)")
            extraction_table = gr.Dataframe(
                headers=["field", "best_value", "confidence", "evidence_excerpt"],
                interactive=False,
                wrap=True,
            )

        with gr.Tab("Normalized Record"):
            record_json = gr.Code(label="Canonical record", language="json")

        with gr.Tab("Normalization Bundle"):
            normalized_json = gr.Code(label="Normalized bundle (record + report)", language="json")

        with gr.Tab("Policy Output"):
            policy_json = gr.Code(label="Policy decision", language="json")

        with gr.Tab("Full Artifact"):
            full_artifact = gr.Code(label="Decision artifact JSON", language="json")

    run_btn.click(
        fn=_run_console,
        inputs=[raw_input],
        outputs=[
            decision_card,
            norm_summary,
            policy_trace,
            extraction_table,
            record_json,
            normalized_json,
            policy_json,
            full_artifact,
        ],
    )

if __name__ == "__main__":
    demo.launch()
