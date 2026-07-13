"""Validator agent.

Runs after human approval. Performs the fairness review, generates the model
card, assembles the run payload, and runs the eval gate. Flags a disparity
breach or a blocked promotion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..harness.controls import CONTROL_EVAL_GATE
from ..harness.eval_gate import EvalReport, run_eval_gate
from ..harness.model_card import build_model_card
from ..ml.fairness import compute_fairness
from ..rag.retriever import retrieve_policy
from .base import Agent


def assemble_payload(result, fairness, card, citations=None) -> dict[str, Any]:  # noqa: ANN001
    return {
        "model": result.to_dict(),
        "fairness": fairness.to_dict(),
        "model_card": card.to_dict(),
        "citations": citations or [],
    }


class ValidatorAgent(Agent):
    id = "validator"
    title = "Validator"
    template = "validation"

    def run(self, state) -> None:  # noqa: ANN001
        ds = self.deps.dataset
        result = state.shared["model_result"]

        fairness = self.use_tool(
            "compute_fairness",
            compute_fairness,
            protected_attribute=ds.protected_attribute,
            seed=state.seed,
            dataset=ds,
        )

        # Ground the fairness finding in policy: retrieve and cite the governing
        # passages instead of asserting the four-fifths rule from a constant.
        verdict_word = "adverse impact" if not fairness.passes else "within tolerance"
        query = (
            f"four-fifths rule disparate impact fairness {verdict_word} across "
            f"{ds.protected_attribute} in a credit decision"
        )
        retrieval = self.use_tool(
            "retrieve_policy", retrieve_policy, query, self.deps.audit, self.id
        )
        citations = [c.to_dict() for c in retrieval.citations]
        state.shared["retrieval"] = retrieval

        card = build_model_card(
            result,
            fairness,
            question=state.question_label,
            generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        )
        payload = assemble_payload(result, fairness, card, citations)
        if self.deps.controls.is_enabled(CONTROL_EVAL_GATE):
            eval_report = self.use_tool(
                "run_eval_gate", run_eval_gate, payload, self.deps.audit, self.id
            )
        else:
            # Eval gate disabled (demo toggle): no golden checks run; the model
            # is allowed to promote unchecked. The disabling is audited at start.
            eval_report = EvalReport(results=[], passed=0, failed=0, promoted=True)
            self.log(
                "eval_gate_skipped",
                level="gate",
                output_summary="Eval gate DISABLED; promotion allowed unchecked.",
            )

        payload["evals"] = eval_report.to_dict()
        state.shared["fairness"] = fairness
        state.shared["model_card"] = card
        state.shared["eval_report"] = eval_report
        state.shared["payload"] = payload
        self.deps.cost.set_eval_pass_rate(eval_report.to_dict()["pass_rate"])

        verdict = "within tolerance" if fairness.passes else "FLAGGED for review"
        self.log(
            "validated",
            inputs_summary="fairness review + eval gate",
            output_summary=(
                f"Disparity {fairness.disparity_ratio} ({verdict}); "
                f"eval gate {eval_report.passed}/{eval_report.passed + eval_report.failed}"
            ),
        )
        gen = self.narrate(
            "validator",
            {
                "protected_attribute": fairness.protected_attribute,
                "disparity_ratio": fairness.disparity_ratio,
                "threshold": fairness.threshold,
                "fairness_verdict": verdict,
                "eval_summary": (
                    "promotion allowed"
                    if eval_report.promoted
                    else "BLOCKED from promotion"
                ),
            },
        )
        state.add_step(self, "done", gen)
