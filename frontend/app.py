"""
Demo UI. Calls backend.ingestion + backend.agent.runner directly,
in-process -- no FastAPI layer yet. That split (Gradio -> HTTP ->
FastAPI -> agent) is real architecture for later, once the core loop is
proven; for a fast demo it's pure overhead with no visible payoff, since
there's exactly one caller (this UI) and one user (you).

Run from the project root:
    uv run python frontend/app.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from backend import ingestion
from backend.agent import runner

VERDICT_LABELS = {
    "compliant": "✅ Compliant",
    "fallback_acceptable": "🟡 Fallback acceptable",
    "violation": "🔴 Violation",
    "missing_required": "🔴 Missing (required)",
    "needs_escalation": "🟠 Needs escalation",
}


def format_report(contract_id: str, verdicts: list[dict]) -> str:
    lines = [f"# Compliance report: {contract_id}\n"]
    for v in verdicts:
        label = VERDICT_LABELS.get(v["verdict"], v["verdict"])
        lines.append(f"## {v['display_name']} -- {label}")
        lines.append(v["explanation"])
        if v.get("quoted_text"):
            quote = v["quoted_text"].replace("\n", " ")
            if v.get("grounded", True):
                lines.append(f"\n> {quote}")
            else:
                lines.append(f"\n> ⚠️ UNVERIFIED, do not trust -- not found in retrieved text: {quote}")
        lines.append("")
    return "\n".join(lines)


async def run_report(contract_id: str, progress=gr.Progress()):
    if not contract_id:
        return "Pick a contract first."
    progress(0, desc="Ingesting contract...")
    ingestion.ensure_ingested(contract_id)
    progress(0.2, desc="Calling MCP tools + reviewing all 7 clause types (one Gemini call, ~20-30s)...")
    verdicts = await runner.generate_report(contract_id)
    progress(1.0, desc="Done")
    return format_report(contract_id, verdicts)


with gr.Blocks(title="Vendor Contract Review") as demo:
    gr.Markdown("# Vendor Contract Intelligence -- Demo\nPick a contract, generate a playbook-compliance report.")
    with gr.Row():
        contract_dropdown = gr.Dropdown(
            choices=ingestion.get_demo_contract_ids(),
            label="Contract",
        )
        generate_btn = gr.Button("Generate Report", variant="primary")
    report_output = gr.Markdown()

    generate_btn.click(fn=run_report, inputs=[contract_dropdown], outputs=[report_output])


if __name__ == "__main__":
    demo.launch()
