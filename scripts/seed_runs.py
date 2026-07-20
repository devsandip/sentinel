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
    SEED_AUDIT_PATH,
    SEED_RUNS_PATH,
    SeedRun,
    write_seed_audit,
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
    # Refusal runs (docs/features/audit-log.md 5b). Every one is an existing
    # code path executed for real: no sample is written by hand, and the events
    # below are whatever the controls actually emitted. They are here because a
    # ledger whose refusal column is empty on every row argues the opposite of
    # what this platform claims. Refusal density is a seeding choice and the
    # Audit Log screen says so on its face.
    (KIND_GOVFLOW, "fair_lending", "german_credit", {"intent": "exfiltrate"},
     "2026-07-18T09:50:00+00:00"),
    (KIND_GOVFLOW, "fair_lending", "german_credit", {"persona": "auditor"},
     "2026-07-18T15:35:00+00:00"),
    # An Analyst tries to promote their own model: refused for lacking
    # promotion authority, before segregation of duties is even reached.
    (KIND_CREDIT_RISK, "build_model", "german_credit", {"approved": True, "self_approve": True},
     "2026-07-19T11:05:00+00:00"),
    # The four-eyes control itself. This run is authored by the MRM Approver,
    # which is already the wrong thing for an approver to do; the record exists
    # because CTL-SOD-01 is what catches the consequence. Nothing enforces
    # can_run at the entrypoint, so the platform has to catch it at the gate.
    (KIND_CREDIT_RISK, "build_model", "german_credit",
     {"approved": True, "self_approve": True, "run_as": "mrm_approver"},
     "2026-07-19T14:30:00+00:00"),
    (KIND_L3, "causal_impact", "synthetic_its", {"intent": "exfiltrate"},
     "2026-07-19T16:20:00+00:00"),
]

_ORCH_STATUS = {"completed": "promoted", "blocked": "blocked", "rejected": "rejected"}


def _controls_from_audit(events: list[dict]) -> list[str]:
    """Actions of control-level audit events (blocked / redaction / gate)."""
    fired = [e["action"] for e in events if e.get("level") in ("blocked", "redaction", "gate")]
    return sorted(set(fired))


# Each run kind records the substance of a step somewhere different, and the
# first cut of this store kept only name/status/agent, which is why the screen
# could say "ok" and nothing else. `detail` is the field that actually says
# what happened; it is StepRun.summary, StepRecord.narration, StageRecord.detail
# respectively. `attributable` records whether the step's agent identifies its
# events uniquely, so the screen knows when it may group events under a step
# and when it must not pretend to.


def _steps_from_analysis(run) -> list[dict]:  # noqa: ANN001
    return [
        {
            "name": s.title or s.id,
            "status": s.status,
            "agent": s.agent,
            "controls": [],
            "detail": s.summary,
            "tool": s.tool,
            "produced": list(s.produced),
            "attributable": True,
        }
        for s in run.steps
    ]


def _steps_from_orchestrator(pub: dict) -> list[dict]:
    return [
        {
            "name": s["title"],
            "status": s["status"],
            "agent": s["agent"],
            "controls": [],
            # The agent's own account of what it did on this run. Scripted by
            # default and labeled as such in the UI; real either way.
            "detail": s.get("narration", ""),
            "attributable": True,
        }
        for s in pub.get("steps", [])
    ]


def _steps_from_stages(result) -> list[dict]:  # noqa: ANN001
    """govflow / L3 stages: the StageRecord already carries detail + controls.

    attributable is False because the emitting agent does not identify the
    stage: flow.py records agent="govflow" from Ask, Plan and Access alike, so
    grouping events by agent here would file them under the wrong stage. The
    stage's own detail and control list are exact; the events stay in the
    run-level stream until an event carries its stage.
    """
    return [
        {
            "name": s.stage,
            "status": s.status,
            "agent": "",
            "controls": list(s.controls),
            "detail": s.detail,
            "attributable": False,
        }
        for s in result.stages
    ]


def _approver_from_audit(events: list[dict]) -> str:
    """The actor that decided at a human gate, if the run reached one.

    Reads the decision event rather than assuming the persona we passed in:
    an approval can be refused (CTL-SOD-01) and never taken, and the record
    should say what happened, not what was intended.
    """
    for e in events:
        if e.get("action") in ("approval_decision", "approval_auto"):
            return str(e.get("actor", ""))
    return ""


def _run_analysis(
    ref_id: str, dataset_id: str, params: dict, actor
) -> tuple[SeedRun, list[dict]]:
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
        actor=actor.id if actor else "",
        approver="",  # a linear analysis produces no model, so nothing to sign
        steps=_steps_from_analysis(run),
    ), run.audit


def _run_credit_risk(
    orch: Orchestrator, question_id: str, params: dict
) -> tuple[SeedRun, list[dict]]:
    author = get_persona(params.get("run_as", "analyst"))
    # self_approve drives the run's own author at the gate. Which control
    # refuses depends on who that author is, and the two are not the same
    # finding: Orchestrator.approve tests promotion authority BEFORE it tests
    # segregation of duties, so an Analyst self-approving is refused for
    # lacking authority and never reaches CTL-SOD-01. Only an author who does
    # hold promotion authority exercises the four-eyes control itself. Both are
    # seeded, because a ledger that shows only one of them misstates which
    # control is load-bearing.
    approver = author if params.get("self_approve") else get_persona("mrm_approver")
    state = orch.start_run(question_id, narration_mode="scripted", actor=author)
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
    events = pub.get("audit", [])
    return SeedRun(
        run_kind=KIND_CREDIT_RISK,
        run_id=state.run_id,
        ref_id=question_id,
        dataset_id="german_credit",
        params={
            "narration_mode": "scripted",
            "approved": params["approved"],
            **({"self_approve": True} if params.get("self_approve") else {}),
        },
        status=_ORCH_STATUS.get(state.status, state.status),
        metrics=metrics,
        controls_fired=_controls_from_audit(events),
        cost=pub.get("cost"),
        actor=state.started_by,
        approver=_approver_from_audit(events),
        steps=_steps_from_orchestrator(pub),
    ), events


def _run_govflow(params: dict) -> tuple[SeedRun, list[dict]]:
    persona = get_persona(params.get("persona", "analyst"))
    intent = params.get("intent", "fair_lending")
    r = run_governed_analysis(GOVFLOW_Q, persona=persona, intent=intent)
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
        params={"intent": intent, "persona": persona.id},
        status=r.status,
        metrics=metrics,
        controls_fired=list(r.controls_fired),
        cost=None,
        actor=persona.id,
        # The nine-stage route has no human promotion gate. Left empty rather
        # than filled with the author, which would read as a signature.
        approver="",
        steps=_steps_from_stages(r),
    ), r.audit


def _run_l3(params: dict) -> tuple[SeedRun, list[dict]]:
    persona = get_persona("admin")
    intent = params.get("intent", "causal_impact")
    r = run_l3_analysis(L3_Q, persona=persona, intent=intent)
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
        params={"intent": intent},
        status=r.status,
        metrics=metrics,
        controls_fired=list(r.controls_fired),
        cost=None,
        actor=persona.id,
        approver="",
        steps=_steps_from_stages(r),
    ), r.audit


def main() -> None:
    analyst = get_persona("analyst")
    orch = Orchestrator()
    records: list[SeedRun] = []
    events_by_run: dict[str, list[dict]] = {}
    for kind, ref_id, dataset_id, params, demo_date in PLAN:
        print(f"executing {kind}:{ref_id} on {dataset_id} {params or ''} ...")
        if kind == KIND_ANALYSIS:
            rec, events = _run_analysis(ref_id, dataset_id, params, analyst)
        elif kind == KIND_CREDIT_RISK:
            rec, events = _run_credit_risk(orch, ref_id, params)
        elif kind == KIND_GOVFLOW:
            rec, events = _run_govflow(params)
        else:
            rec, events = _run_l3(params)
        rec = SeedRun(
            **{
                **rec.to_dict(),
                "executed_at": datetime.now(UTC).isoformat(),
                "demo_date": demo_date,
            }
        )
        print(f"  -> {rec.status} {len(events)} events {rec.metrics}")
        records.append(rec)
        events_by_run[rec.run_id] = events

    path = write_seed_runs(records, SEED_RUNS_PATH)
    print(f"\nwrote {len(records)} records -> {path}")
    n_events = sum(len(v) for v in events_by_run.values())
    apath = write_seed_audit(events_by_run, SEED_AUDIT_PATH)
    print(f"wrote {n_events} events -> {apath}")
    empty = [rid for rid, evs in events_by_run.items() if not evs]
    if empty:
        print(f"WARNING: {len(empty)} run(s) emitted no events: {', '.join(empty)}")


if __name__ == "__main__":
    main()
