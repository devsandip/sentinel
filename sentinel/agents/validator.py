"""Validator agent.

Runs after human approval. Performs the fairness review, generates the model
card, assembles the run payload, and runs the eval gate. Flags a disparity
breach or a blocked promotion.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..harness.eval_gate import run_eval_gate
from ..harness.model_card import build_model_card
from ..ml.fairness import compute_fairness
from .base import Agent


def assemble_payload(result, fairness, card) -> dict[str, Any]:  # noqa: ANN001
    return {
        "model": result.to_dict(),
        "fairness": fairness.to_dict(),
        "model_card": card.to_dict(),
    }


class ValidatorAgent(Agent):
    id = "validator"
    title = "Validator"

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
        card = build_model_card(
            result,
            fairness,
            question=state.question_label,
            generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        )
        payload = assemble_payload(result, fairness, card)
        eval_report = self.use_tool(
            "run_eval_gate", run_eval_gate, payload, self.deps.audit, self.id
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
