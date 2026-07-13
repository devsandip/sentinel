"""Adoption and utilization metrics (ideas.md lead ask A).

Who uses what agent, how often, and with what outcome. Aggregated over the model
registry (each registered run implies its agent invocations) plus the template
reuse metric and a small seeded weekly series so the trend is not empty. Live
session runs are counted alongside the seeded history, and the UI labels which is
which. This is the platform-stage signal from the PRODUCT_BRIEF metric tree.
"""

from __future__ import annotations

from .registry import STATUS_PROMOTED, STATUS_REJECTED, model_versions
from .templates import reuse_metrics

# Seeded weekly run counts (labeled as demo history in the UI).
SEEDED_WEEKLY: list[tuple[str, int]] = [
    ("2026-W26", 6),
    ("2026-W27", 9),
    ("2026-W28", 14),
]


def adoption_metrics() -> dict:
    mv = model_versions()
    total = len(mv)
    promoted = sum(1 for m in mv if m.status == STATUS_PROMOTED)
    rejected = sum(1 for m in mv if m.status == STATUS_REJECTED)
    live = sum(1 for m in mv if not m.seeded)

    # Each run invokes profiler, eda, modeler; validator runs unless rejected.
    per_agent = {
        "profiler": total,
        "eda": total,
        "modeler": total,
        "validator": total - rejected,
    }

    reuse = reuse_metrics()
    return {
        "total_runs": total,
        "live_session_runs": live,
        "seeded_runs": total - live,
        "promoted": promoted,
        "rejected": rejected,
        "promotion_rate": round(promoted / total, 3) if total else 0.0,
        "override_rate": round(rejected / total, 3) if total else 0.0,
        "per_agent_invocations": per_agent,
        "template_coverage": reuse["coverage_rate"],
        "est_hours_saved": reuse["est_hours_saved"],
        "weekly": list(SEEDED_WEEKLY),
    }
