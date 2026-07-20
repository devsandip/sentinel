"""Modeler agent.

Trains the baseline and proposes it, then triggers the human-in-the-loop
approval gate: the run pauses here until a person approves or rejects.
"""

from __future__ import annotations

from ..ml.pipeline import run_pipeline
from .base import Agent


class ModelerAgent(Agent):
    id = "modeler"
    title = "Modeler"
    template = "modeling"
    does = (
        "Trains the baseline model on permitted features and proposes it, then "
        "stops: the run pauses at the human approval gate until a person decides."
    )

    def run(self, state) -> None:  # noqa: ANN001
        ds = self.deps.dataset
        result = self.use_tool(
            "train_model",
            run_pipeline,
            protected_attribute=ds.protected_attribute,
            seed=state.seed,
            dataset=ds,
        )
        state.shared["model_result"] = result

        self.log(
            "model_trained",
            inputs_summary=f"{result.n_train} train / {result.n_test} test",
            output_summary=(
                f"AUC {result.metrics['auc']}, accuracy {result.metrics['accuracy']}"
            ),
            extra={"metrics": result.metrics},
        )
        gen = self.narrate(
            "modeler",
            {
                "n_train": result.n_train,
                "n_test": result.n_test,
                "auc": result.metrics["auc"],
                "accuracy": result.metrics["accuracy"],
            },
        )
        # Pause for approval. The step is recorded as awaiting_approval.
        state.add_step(self, "awaiting_approval", gen)
        state.status = "awaiting_approval"
        self.log(
            "approval_requested",
            level="gate",
            output_summary="Model proposed; awaiting human approval before promotion.",
        )
