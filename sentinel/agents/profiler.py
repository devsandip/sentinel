"""Data Profiler agent.

Profiles the dataset and flags class imbalance. Its RBAC allow-list omits
personal_status_sex (a sex proxy), so profiling the full feature set produces
a real "access denied" event in the audit trail.
"""

from __future__ import annotations

from ..ml.pipeline import profile_dataset
from .base import Agent


class ProfilerAgent(Agent):
    id = "profiler"
    title = "Data Profiler"

    def run(self, state) -> None:  # noqa: ANN001
        ds = self.deps.dataset
        requested = [*ds.feature_columns, "credit_risk"]
        allowed = self.read_columns(requested)

        profile = self.use_tool("profile_dataset", profile_dataset, ds)
        state.shared["profile"] = profile

        imbalance = (
            "class imbalance present" if profile.positive_rate < 0.35 else "balanced"
        )
        self.log(
            "profiled",
            inputs_summary=f"{len(allowed)}/{len(requested)} columns readable",
            data_touched=allowed,
            output_summary=(
                f"{profile.n_rows} rows, default rate {profile.positive_rate:.3f} "
                f"({imbalance})"
            ),
        )
        gen = self.narrate(
            "profiler",
            {
                "n_rows": profile.n_rows,
                "n_features": profile.n_features,
                "class_balance": profile.class_balance,
                "default_rate": round(profile.positive_rate, 3),
            },
        )
        state.add_step(self, "done", gen)
