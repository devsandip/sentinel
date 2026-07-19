"""Adoption and utilization metrics (ideas.md lead ask A).

Who uses what agent, how often, and with what outcome. Totals and the weekly
trend derive from the executed seed-run history (sentinel/data/seed_runs.jsonl,
labeled seeded in the UI) plus live-session model runs on top. Model-pipeline
figures (promotion, per-agent invocations) are scoped to credit_risk runs, the
only kind that produces registry models. This is the platform-stage signal from
the PRODUCT_BRIEF metric tree.
"""

from __future__ import annotations

from .registry import STATUS_PROMOTED, STATUS_REJECTED, model_versions
from .run_history import load_seed_runs, seeded_by_dataset, seeded_weekly
from .templates import reuse_metrics


def adoption_metrics() -> dict:
    seeds = load_seed_runs()
    mv = model_versions()
    live_models = [m for m in mv if not m.seeded]
    seeded_credit = sum(1 for s in seeds if s.run_kind == "credit_risk")

    total = len(seeds) + len(live_models)
    credit_total = seeded_credit + len(live_models)
    promoted = sum(1 for m in mv if m.status == STATUS_PROMOTED)
    rejected = sum(1 for m in mv if m.status == STATUS_REJECTED)

    # The 4-agent credit pipeline: profiler/eda/modeler run on every credit_risk
    # run; validator runs unless the run was rejected at the human gate.
    per_agent = {
        "profiler": credit_total,
        "eda": credit_total,
        "modeler": credit_total,
        "validator": credit_total - rejected,
    }

    reuse = reuse_metrics()
    return {
        "total_runs": total,
        "live_session_runs": len(live_models),
        "seeded_runs": len(seeds),
        "credit_risk_runs": credit_total,
        "promoted": promoted,
        "rejected": rejected,
        "promotion_rate": round(promoted / credit_total, 3) if credit_total else 0.0,
        "override_rate": round(rejected / credit_total, 3) if credit_total else 0.0,
        "per_agent_invocations": per_agent,
        "template_coverage": reuse["coverage_rate"],
        "est_hours_saved": reuse["est_hours_saved"],
        "weekly": seeded_weekly(),
        "per_dataset": seeded_by_dataset(),
    }
