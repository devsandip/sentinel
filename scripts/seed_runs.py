"""Seed the run-history store by actually executing runs (unified-app-build H1).

Executes the per-dataset seed plan from docs/features/unified-app-build.md H2
headlessly, all scripted/free (no LLM, no keys), and writes one JSONL record
per run to sentinel/data/seed_runs.jsonl. Honesty rule: every record's status,
metrics, and controls are the run's real outputs; nothing is invented. Each
record stores executed_at (real wall clock) plus demo_date (its assigned spot
on the demo timeline the UI renders); see run_history.py for the convention.

Idempotent: re-running replaces the store. ~19 runs, a couple of minutes.

Run: uv run python scripts/seed_runs.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel.analyses.engine import AnalysisEngine  # noqa: E402
from sentinel.analyses.registry import get_analysis  # noqa: E402
from sentinel.govflow.flow import run_governed_analysis  # noqa: E402
from sentinel.govflow.l3 import run_l3_analysis  # noqa: E402
from sentinel.harness.identity import get_persona  # noqa: E402
from sentinel.orchestrator import Orchestrator  # noqa: E402
from sentinel.platform.run_history import (  # noqa: E402
    KIND_ANALYSIS,
    KIND_CREDIT_RISK,
    KIND_GOVFLOW,
    KIND_L3,
    SEED_RUNS_PATH,
    SeedRun,
    write_seed_runs,
)

GOVFLOW_Q = "Does the model decline older applicants more often, holding income constant?"
L3_Q = "Estimate the effect of the intervention on the metric."

# The plan: (kind, ref_id, dataset_id, params, demo_date). Weeks W26-W29 of the
# demo timeline; ~19 runs, at least 2 per dataset, 5 on the hero dataset.
PLAN: list[tuple[str, str, str, dict, str]] = [
    (KIND_ANALYSIS, "data_profiling", "german_credit", {}, "2026-06-23T10:15:00+00:00"),
    (KIND_CREDIT_RISK, "build_model", "german_credit", {"approved": True},
     "2026-06-24T14:40:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "uci_taiwan_credit", {}, "2026-06-25T09:20:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "ulb_fraud", {}, "2026-06-26T16:05:00+00:00"),
    (KIND_CREDIT_RISK, "fairness_age", "german_credit", {"approved": True},
     "2026-06-30T11:10:00+00:00"),
    (KIND_ANALYSIS, "feature_engineering", "berka", {"window_days": 365},
     "2026-07-01T10:45:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "hillstrom", {}, "2026-07-02T13:30:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "lendingclub", {}, "2026-07-03T15:55:00+00:00"),
    (KIND_CREDIT_RISK, "profile_risks", "german_credit", {"approved": False},
     "2026-07-07T09:50:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "uci_taiwan_credit", {"sample_rows": 5000},
     "2026-07-08T10:25:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "lendingclub", {"missing_threshold": 0.4},
     "2026-07-09T11:35:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "uci_bank_marketing", {}, "2026-07-09T16:20:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "synthetic_its", {}, "2026-07-10T09:05:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "ulb_fraud", {"outlier_z": 6.0},
     "2026-07-10T14:15:00+00:00"),
    (KIND_ANALYSIS, "feature_engineering", "berka", {"window_days": 180},
     "2026-07-14T10:40:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "hillstrom", {"max_cardinality": 20},
     "2026-07-15T13:00:00+00:00"),
    (KIND_ANALYSIS, "data_profiling", "uci_bank_marketing", {"sample_rows": 10000},
     "2026-07-16T11:30:00+00:00"),
    (KIND_GOVFLOW, "fair_lending", "german_credit", {}, "2026-07-17T10:10:00+00:00"),
    (KIND_L3, "causal_impact", "synthetic_its", {}, "2026-07-17T15:45:00+00:00"),
]

_ORCH_STATUS = {"completed": "promoted", "blocked": "blocked", "rejected": "rejected"}


def _controls_from_audit(events: list[dict]) -> list[str]:
    """Actions of control-level audit events (blocked / redaction / gate)."""
    fired = [e["action"] for e in events if e.get("level") in ("blocked", "redaction", "gate")]
    return sorted(set(fired))


def _run_analysis(ref_id: str, dataset_id: str, params: dict, actor) -> SeedRun:
    run = AnalysisEngine().run(get_analysis(ref_id), dataset_id, params or None, actor=actor)
    metrics: dict = {"steps": len(run.steps)}
    quality = run.results.get("quality")
    if quality:
        metrics["quality_fail"] = quality.get("n_fail")
        metrics["quality_warn"] = quality.get("n_warn")
        metrics["quality_verdict"] = quality.get("verdict")
    features = run.results.get("features")
    if features:
        metrics["features"] = features.get("n_features")
    leakage = run.results.get("leakage")
    if leakage:
        metrics["leakage_flags"] = len(leakage.get("flags", []))
    return SeedRun(
        run_kind=KIND_ANALYSIS,
        run_id=run.run_id,
        ref_id=ref_id,
        dataset_id=dataset_id,
        params=params,
        status=run.status,
        metrics=metrics,
        controls_fired=_controls_from_audit(run.audit),
        cost=run.cost,
    )


def _run_credit_risk(orch: Orchestrator, question_id: str, params: dict) -> SeedRun:
    analyst = get_persona("analyst")
    approver = get_persona("mrm_approver")
    state = orch.start_run(question_id, narration_mode="scripted", actor=analyst)
    state = orch.approve(state.run_id, approved=params["approved"], actor=approver)
    pub = state.to_public_dict()
    model = pub.get("model") or {}
    fairness = pub.get("fairness") or {}
    evals = pub.get("evals") or {}
    metrics = {
        "auc": (model.get("metrics") or {}).get("auc"),
        "disparity_ratio": fairness.get("disparity_ratio"),
        "fairness_pass": fairness.get("passes"),
        "evals_passed": evals.get("passed"),
        "evals_failed": evals.get("failed"),
    }
    return SeedRun(
        run_kind=KIND_CREDIT_RISK,
        run_id=state.run_id,
        ref_id=question_id,
        dataset_id="german_credit",
        params={"narration_mode": "scripted", "approved": params["approved"]},
        status=_ORCH_STATUS.get(state.status, state.status),
        metrics=metrics,
        controls_fired=_controls_from_audit(pub.get("audit", [])),
        cost=pub.get("cost"),
    )


def _run_govflow() -> SeedRun:
    r = run_governed_analysis(GOVFLOW_Q, persona=get_persona("analyst"), intent="fair_lending")
    metrics = {
        "tier": r.tier,
        "stages": len(r.stages),
        "suppressed": len(r.screen.suppressed) if r.screen else 0,
        "proxy_flags": len(r.screen.proxy_flags) if r.screen else 0,
    }
    return SeedRun(
        run_kind=KIND_GOVFLOW,
        run_id=r.run_id,
        ref_id="fair_lending",
        dataset_id=r.dataset,
        params={"intent": "fair_lending"},
        status=r.status,
        metrics=metrics,
        controls_fired=list(r.controls_fired),
        cost=None,
    )


def _run_l3() -> SeedRun:
    r = run_l3_analysis(L3_Q, persona=get_persona("admin"), intent="causal_impact")
    emitted = r.execution.emitted if (r.execution and r.execution.has_emitted) else {}
    metrics = {
        "tier": r.tier,
        "stages": len(r.stages),
        "effect": emitted.get("effect"),
        "ci_low": emitted.get("ci_low"),
        "ci_high": emitted.get("ci_high"),
    }
    return SeedRun(
        run_kind=KIND_L3,
        run_id=r.run_id,
        ref_id="causal_impact",
        dataset_id=r.dataset,
        params={"intent": "causal_impact"},
        status=r.status,
        metrics=metrics,
        controls_fired=list(r.controls_fired),
        cost=None,
    )


def main() -> None:
    analyst = get_persona("analyst")
    orch = Orchestrator()
    records: list[SeedRun] = []
    for kind, ref_id, dataset_id, params, demo_date in PLAN:
        print(f"executing {kind}:{ref_id} on {dataset_id} {params or ''} ...")
        if kind == KIND_ANALYSIS:
            rec = _run_analysis(ref_id, dataset_id, params, analyst)
        elif kind == KIND_CREDIT_RISK:
            rec = _run_credit_risk(orch, ref_id, params)
        elif kind == KIND_GOVFLOW:
            rec = _run_govflow()
        else:
            rec = _run_l3()
        rec = SeedRun(
            **{
                **rec.to_dict(),
                "executed_at": datetime.now(UTC).isoformat(),
                "demo_date": demo_date,
            }
        )
        print(f"  -> {rec.status} {rec.metrics}")
        records.append(rec)

    path = write_seed_runs(records, SEED_RUNS_PATH)
    print(f"\nwrote {len(records)} records -> {path}")


if __name__ == "__main__":
    main()
