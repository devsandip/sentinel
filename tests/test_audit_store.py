"""Tests for the cross-run audit reader (docs/features/audit-log.md).

Most of these run against the committed seed corpus rather than fixtures. That
is deliberate: the Audit Log's whole claim is that it renders a real record, so
a test that passes on a synthetic corpus while the shipped one is empty or
malformed would be worse than no test.
"""

from __future__ import annotations

import json

from sentinel.analyses.engine import STATUS_BLOCKED as ANALYSIS_BLOCKED
from sentinel.analyses.engine import STATUS_COMPLETED as ANALYSIS_COMPLETED
from sentinel.govflow.flow import STATUS_BLOCKED as GOVFLOW_BLOCKED
from sentinel.govflow.flow import STATUS_COMPLETED as GOVFLOW_COMPLETED
from sentinel.govflow.flow import STATUS_ERROR as GOVFLOW_ERROR
from sentinel.harness.identity import get_persona
from sentinel.orchestrator import (
    STATUS_AWAITING,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_REJECTED,
    STATUS_RUNNING,
)
from sentinel.platform.audit_stages import CANONICAL_STAGES
from sentinel.platform.audit_store import (
    OUTCOME_AWAITING,
    OUTCOME_OK,
    OUTCOME_REFUSED,
    audit_runs,
    normalize_status,
    summary,
    visible_runs,
)
from sentinel.platform.run_history import load_seed_audit, load_seed_runs

# -- the store itself -------------------------------------------------------


def test_every_seeded_run_has_a_committed_event_stream():
    """The gap this feature exists to close.

    runtime/ is gitignored and excluded from the deploy bundle, so unless the
    events are committed the screen is empty on a fresh instance. If this fails,
    re-run scripts/seed_runs.py.
    """
    events = load_seed_audit()
    missing = [r.run_id for r in load_seed_runs() if not events.get(r.run_id)]
    assert not missing, f"seeded runs with no committed events: {missing}"


def test_every_seeded_run_names_its_actor():
    """The 'who ran it' column cannot be populated from an empty field."""
    without = [r.run_id for r in load_seed_runs() if not r.actor]
    assert not without, f"seeded runs with no actor: {without}"


def test_seeded_actors_are_personas_not_modules():
    """AuditEvent.actor defaults to the agent name when a call site omits it.

    A module id in the 'who' column is worse than a blank one, so assert the
    run-level actor is always a real persona.
    """
    from sentinel.harness.identity import all_personas

    ids = {p.id for p in all_personas()}
    bad = [(r.run_id, r.actor) for r in load_seed_runs() if r.actor not in ids]
    assert not bad, f"run actors that are not personas: {bad}"


def test_sequence_is_continuous_within_every_run():
    """The only tamper evidence available before a hash chain exists."""
    gapped = [(r.run_id, r.seq_gaps) for r in audit_runs() if r.seq_gaps]
    assert not gapped, f"runs with missing audit sequence numbers: {gapped}"


def test_seeded_audit_lines_carry_the_full_event_shape():
    from sentinel.harness.audit import AuditEvent

    expected = set(AuditEvent.__dataclass_fields__)
    for run_id, events in load_seed_audit().items():
        for ev in events:
            assert set(ev) == expected, f"{run_id} seq {ev.get('seq')} shape drifted"


def test_every_step_carries_what_actually_happened():
    """A status word alone is a claim with the evidence removed.

    The first cut of the store kept only name/status/agent, so the screen could
    say "ok" and nothing else. Each run kind records the substance somewhere
    different (StepRun.summary, StepRecord.narration, StageRecord.detail) and
    all three land in `detail`.
    """
    thin = []
    for r in load_seed_runs():
        for s in r.steps:
            # A skipped stage legitimately has little to say, but every step
            # the run actually reached must account for itself.
            if s.get("status") not in ("skipped",) and not (s.get("detail") or "").strip():
                thin.append((r.run_id, s.get("name")))
    assert not thin, f"steps with no detail: {thin[:5]}"


def test_step_event_attribution_is_declared_not_guessed():
    """`attributable` must be true only where the agent identifies the step.

    analysis and credit_risk name one agent per step. govflow and L3 do not:
    flow.py records agent="govflow" from Ask, Plan and Access alike, so
    grouping by agent there would file events under the wrong stage.
    """
    for r in load_seed_runs():
        for s in r.steps:
            if s.get("attributable"):
                assert s.get("agent"), f"{r.run_id}: attributable step with no agent"
        if r.run_kind in ("govflow", "l3"):
            assert not any(s.get("attributable") for s in r.steps), (
                f"{r.run_id}: nine-stage runs cannot attribute events by agent"
            )


def test_attributable_steps_actually_match_events():
    """The claim has to hold on the real corpus, not just in principle."""
    for r in audit_runs():
        agents = {e["agent"] for e in r.events}
        for s in r.steps:
            if s.get("attributable") and s.get("status") != "skipped":
                assert s["agent"] in agents, (
                    f"{r.run_id}: step {s['name']} claims agent {s['agent']}, "
                    f"which emitted no events"
                )


def test_govflow_stages_carry_the_controls_that_fired_there():
    """The stage's own control list is exact even though its events are not."""
    gov = [
        r
        for r in load_seed_runs()
        if r.run_kind == "govflow" and "CTL-DISC-01" in r.controls_fired
    ]
    assert gov, "expected a seeded govflow run with suppression"
    for r in gov:
        screen = next(s for s in r.steps if s["name"] == "Screen")
        assert "CTL-DISC-01" in screen["controls"]


# -- the nine-stage shape ---------------------------------------------------


def test_every_run_reads_as_the_nine_stages_in_order():
    """One vocabulary for every run kind, matching the Run screen's spine."""
    from sentinel.govflow.flow import STAGES
    from sentinel.platform.audit_stages import CANONICAL_STAGES, canonical_steps

    # The canonical list must BE the flow's list, or the Audit Log and the Run
    # screen teach two different spines.
    assert CANONICAL_STAGES == STAGES

    for r in audit_runs():
        got = [c["stage"] for c in canonical_steps(r)]
        assert got == CANONICAL_STAGES, f"{r.run_id} rendered {got}"


def test_absent_stages_are_not_reported_as_skipped_or_ok():
    """Three different facts, and collapsing them is how normalization lies.

    ok ran. skipped was reached and declined. not_in_route means the route has
    no such stage: a linear analysis generates no code, so its Generate stage
    is absent, not skipped.
    """
    from sentinel.platform.audit_stages import NOT_IN_ROUTE, canonical_steps

    analysis = next(r for r in audit_runs() if r.run_kind == "analysis")
    by_stage = {c["stage"]: c for c in canonical_steps(analysis)}
    assert by_stage["Generate"]["status"] == NOT_IN_ROUTE
    assert by_stage["Gate"]["status"] == NOT_IN_ROUTE
    # And a real govflow stage that was reached and declined stays 'skipped'.
    blocked = next(
        r for r in audit_runs() if r.run_kind in ("govflow", "l3") and r.stopped_run
    )
    stages = {c["stage"]: c["status"] for c in canonical_steps(blocked)}
    assert "skipped" in stages.values()
    assert NOT_IN_ROUTE not in stages.values(), "the nine-stage route has all nine"


def test_a_stage_folding_several_steps_takes_the_worst_outcome():
    """Two of three steps passing does not make a stage green."""
    from sentinel.platform.audit_stages import _fold_status

    assert _fold_status(["ok", "ok", "blocked"]) == "blocked"
    assert _fold_status(["ok", "awaiting_approval"]) == "awaiting_approval"
    assert _fold_status(["skipped", "skipped"]) == "skipped"
    assert _fold_status(["ok", "done"]) == "ok"


def test_native_step_names_survive_the_normalization():
    """The mapping is additive: nothing is renamed away."""
    from sentinel.platform.audit_stages import canonical_steps

    cr = next(r for r in audit_runs() if r.run_kind == "credit_risk" and not r.stopped_run)
    execute = next(c for c in canonical_steps(cr) if c["stage"] == "Execute")
    names = {s["name"] for s in execute["native"]}
    assert {"Data Profiler", "EDA / Feature", "Modeler"} <= names


def test_nine_stage_routes_take_their_engine_from_the_run_screen():
    """Audit Log and Run screen must not drift on what a stage is built with."""
    from sentinel.platform.audit_stages import stage_engine
    from sentinel.ui.govflow import _ENGINE

    for stage, (libs, ctls) in _ENGINE.items():
        assert stage_engine("govflow", stage) == (list(libs), list(ctls))
        assert stage_engine("l3", stage) == (list(libs), list(ctls))


def test_other_routes_do_not_borrow_govflow_libraries():
    """credit_risk trains a scikit-learn model; it does not run duckdb."""
    from sentinel.platform.audit_stages import stage_engine

    libs, _ = stage_engine("credit_risk", "Execute")
    assert "scikit-learn" in libs
    assert "duckdb" not in libs and "subprocess" not in libs


def test_fired_controls_at_a_stage_are_a_subset_of_those_armed():
    """A control cannot fire at a stage that never armed it."""
    from sentinel.platform.audit_stages import canonical_steps

    for r in audit_runs():
        if r.run_kind not in ("govflow", "l3"):
            continue
        for c in canonical_steps(r):
            unarmed = set(c["fired"]) - set(c["controls"])
            assert not unarmed, f"{r.run_id} {c['stage']}: fired but not armed: {unarmed}"


# -- status normalization ---------------------------------------------------


def test_every_status_constant_in_the_codebase_is_mapped():
    """Four run kinds, four vocabularies, no shared base class.

    An unmapped status silently becomes 'refused', so this asserts the map
    covers every constant the code can actually produce. Adding a status
    without adding it here fails the build rather than mislabeling a run.
    """
    from sentinel.platform.audit_store import _STATUS_MAP

    produced = {
        ANALYSIS_COMPLETED,
        ANALYSIS_BLOCKED,
        STATUS_RUNNING,
        STATUS_AWAITING,
        STATUS_COMPLETED,
        STATUS_REJECTED,
        STATUS_BLOCKED,
        GOVFLOW_COMPLETED,
        GOVFLOW_BLOCKED,
        GOVFLOW_ERROR,
        "promoted",  # the seeder's rename of a completed credit_risk run
    }
    assert produced <= set(_STATUS_MAP), f"unmapped statuses: {produced - set(_STATUS_MAP)}"


def test_unknown_status_is_refused_not_ok():
    """An unrecognized status is not evidence of success."""
    assert normalize_status("something_new") == OUTCOME_REFUSED


def test_normalization_covers_the_three_outcomes():
    assert normalize_status(STATUS_COMPLETED) == OUTCOME_OK
    assert normalize_status(STATUS_AWAITING) == OUTCOME_AWAITING
    assert normalize_status(GOVFLOW_BLOCKED) == OUTCOME_REFUSED


def test_every_seeded_status_normalizes_without_falling_through():
    from sentinel.platform.audit_store import _STATUS_MAP

    for r in load_seed_runs():
        assert r.status in _STATUS_MAP, f"{r.run_id} has unmapped status {r.status!r}"


# -- refusal accounting -----------------------------------------------------


def test_refusal_split_is_exhaustive():
    """stopped + withheld must equal the refusal count, or a tile lies."""
    s = summary(audit_runs())
    assert s["stopped"] + s["withheld"] == s["refused"]


def test_the_corpus_actually_contains_refusals():
    """A ledger whose refusal column is empty argues against the platform."""
    s = summary(audit_runs())
    assert s["stopped"] >= 1, "no run was stopped by a control"
    assert s["withheld"] >= 1, "no run completed with something withheld"


def test_a_refused_run_always_names_what_refused_it():
    """The Caught column must never be blank on a run that was refused.

    govflow only accumulates CTL- ids from Gate and Screen, so a run refused at
    Ask by the tier gate has an empty controls_fired; refusal_controls reads the
    event stream instead.
    """
    blank = [
        r.run_id
        for r in audit_runs()
        if r.has_refusal and not r.refusal_controls
    ]
    assert not blank, f"refused runs with nothing in Caught: {blank}"


def test_a_run_refused_at_ask_still_names_its_control():
    """The specific case the fallback exists for."""
    refused_early = [r for r in audit_runs() if r.stopped_at == "Ask"]
    assert refused_early, "expected a seeded run refused at Ask (the tier gate)"
    for r in refused_early:
        assert r.refusal_controls, f"{r.run_id} refused at Ask names no control"


def test_a_gate_that_passed_is_not_counted_as_a_refusal():
    """The bug this pins: gate-level events mean 'consulted', not 'refused'.

    `eval_gate` at 6/6 passed and `approval_decision` APPROVED are gate level
    and both mean the run proceeded. The seeder's controls_fired mixes them in,
    so reading that list directly inflates every refusal number and credits
    controls with stopping things they waved through.
    """
    passes = {"approval_requested", "approval_decision", "approval_auto", "eval_gate"}
    for r in audit_runs():
        if not r.events:
            continue
        leaked = passes & set(r.refusal_controls)
        assert not leaked, f"{r.run_id} counts gate passes as refusals: {leaked}"


def test_a_promoted_run_is_not_reported_as_refused_for_its_gate():
    """A run that was approved and promoted still withheld things (RBAC, PII),
    but its approval must not be among them."""
    promoted = [r for r in audit_runs() if r.status == "promoted"]
    assert promoted, "expected promoted runs in the corpus"
    for r in promoted:
        assert "approval_decision" not in r.refusal_controls
        assert "eval_gate" not in r.refusal_controls
        # It did withhold: a column was denied and a value redacted.
        assert "rbac_access_denied" in r.refusal_controls
        assert not r.stopped_run


def test_govflow_suppression_control_survives_the_event_filter():
    """CTL-DISC-01 is in controls_fired but its event stamps CTL-DISC-02.

    Reading events alone would drop a control that genuinely fired, so CTL-
    ids from controls_fired are unioned back in.
    """
    gov = [r for r in audit_runs() if r.run_kind == "govflow" and "CTL-DISC-01" in r.controls_fired]
    assert gov, "expected a seeded govflow run with small-cell suppression"
    for r in gov:
        assert "CTL-DISC-01" in r.refusal_controls
        assert "CTL-DISC-02" in r.refusal_controls


def test_clean_runs_report_no_refusal():
    clean = [r for r in audit_runs() if r.run_kind == "analysis" and r.outcome == OUTCOME_OK]
    assert clean, "expected clean analysis runs in the corpus"
    for r in clean:
        assert not r.has_refusal
        assert not r.refusal_controls


def test_no_events_is_distinct_from_no_refusal():
    """Two different statements the screen must not conflate.

    A run with no persisted trail must not fall through has_refusal as clean,
    so the property reads controls_fired when the event stream is absent.
    """
    from sentinel.platform.audit_store import AuditRun

    silent = AuditRun(
        run_id="x", run_kind="govflow", ref_id="r", dataset_id="d", status="blocked_at_gate",
        outcome=OUTCOME_REFUSED, actor="analyst", approver="", origin="seeded", when="",
        controls_fired=["CTL-EGRESS-01"], events=[],
    )
    assert not silent.has_events
    assert silent.has_refusal


# -- four eyes --------------------------------------------------------------


def test_four_eyes_counts_only_a_different_approver():
    s = summary(audit_runs())
    assert s["four_eyes"] <= s["gated"]
    for r in audit_runs():
        if r.four_eyes:
            assert r.approver and r.approver != r.actor


def test_a_self_approval_is_a_refusal_not_coverage():
    """CTL-SOD-01 leaves the run awaiting and writes no decision event.

    So the run reaches a gate, counts in the denominator, and must not count as
    four-eyes coverage.
    """
    selfies = [
        r
        for r in audit_runs()
        if any(e.get("action") == "approval_denied" for e in r.events)
    ]
    assert selfies, "expected a seeded self-approval refusal"
    for r in selfies:
        assert not r.four_eyes, f"{r.run_id} counted a refused self-approval as coverage"
        assert not r.approver, f"{r.run_id} recorded an approver for a refused approval"
        assert r.outcome == OUTCOME_AWAITING


def test_the_corpus_holds_both_approval_refusals_and_they_are_different():
    """Orchestrator.approve tests promotion authority before segregation of duties.

    So an Analyst self-approving is refused for lacking authority and never
    reaches CTL-SOD-01; only an author who does hold promotion authority
    exercises four-eyes itself. The two are different findings and the ledger
    must be able to tell them apart, otherwise the screen credits CTL-SOD-01
    with a refusal it did not make.
    """
    denials = [
        e
        for r in audit_runs()
        for e in r.events
        if e.get("action") == "approval_denied"
    ]
    assert len(denials) >= 2, "expected both an authority refusal and an SoD refusal"

    sod = [e for e in denials if (e.get("extra") or {}).get("control") == "CTL-SOD-01"]
    authority = [e for e in denials if not (e.get("extra") or {}).get("control")]

    assert sod, "no CTL-SOD-01 refusal in the corpus"
    assert authority, "no promotion-authority refusal in the corpus"

    for e in sod:
        assert "CTL-SOD-01" in e["output_summary"]
        assert "segregation of duties" in e["output_summary"]
    for e in authority:
        assert "lacks promotion authority" in e["output_summary"]
        assert "CTL-SOD-01" not in e["output_summary"], (
            "an authority refusal must not be attributed to CTL-SOD-01"
        )


# -- the reader -------------------------------------------------------------


def test_runs_are_newest_first():
    whens = [r.when for r in audit_runs()]
    assert whens == sorted(whens, reverse=True)


def test_seeded_runs_are_labelled_seeded():
    assert all(r.origin == "seeded" for r in audit_runs())


def test_events_round_trip_as_jsonl():
    """The export writes back byte-comparable lines."""
    for r in audit_runs():
        for ev in r.events:
            assert json.loads(json.dumps(ev)) == ev


def test_summary_totals_match_the_corpus():
    runs = audit_runs()
    s = summary(runs)
    assert s["runs"] == len(runs)
    assert s["events"] == sum(len(r.events) for r in runs)
    assert s["runs_without_events"] == 0


# -- per-stage attribution ---------------------------------------------------


def test_nine_stage_runs_stamp_every_event_with_its_stage():
    """The fix for the caveat the screen used to print.

    An event's agent cannot identify its stage: flow.py records agent="govflow"
    from Ask, Plan and Access alike. So the call site stamps the stage, and
    every event a nine-stage route emits must carry one. A new audit.record in
    flow.py or l3.py that forgets it fails here rather than quietly landing in
    the run-level stream.
    """
    nine = [r for r in audit_runs() if r.run_kind in ("govflow", "l3")]
    assert nine, "corpus needs nine-stage runs for this to mean anything"
    for r in nine:
        for e in r.events:
            assert e.get("stage"), (
                f"{r.run_id} seq {e.get('seq')} ({e.get('action')}) carries no stage"
            )
            assert e["stage"] in CANONICAL_STAGES, (
                f"{r.run_id} seq {e['seq']} names stage {e['stage']!r}, "
                "which is not one of the nine"
            )


def test_a_stamped_stage_agrees_with_the_run_own_stage_record():
    """The stamp must not name a stage the run never reached.

    Both the events and the StageRecord list are written by the same function
    side by side; this asserts they still describe the same run.
    """
    for r in audit_runs():
        if r.run_kind not in ("govflow", "l3"):
            continue
        recorded = {str(s.get("name", "")) for s in r.steps}
        for e in r.events:
            assert e["stage"] in recorded, (
                f"{r.run_id}: event at {e['stage']} but the run records no such stage"
            )


def test_other_routes_leave_the_stage_empty_rather_than_guessing():
    """analysis and credit_risk have no stage spine, and say so by omission."""
    for r in audit_runs():
        if r.run_kind in ("govflow", "l3"):
            continue
        for e in r.events:
            assert not e.get("stage"), (
                f"{r.run_id}: {e['action']} claims stage {e['stage']!r} on a "
                "route that has no stages of its own"
            )


# -- who may read the ledger -------------------------------------------------


def test_oversight_roles_read_the_whole_ledger():
    runs = audit_runs()
    for pid in ("auditor", "admin", "model_validator", "mrm_approver"):
        assert len(visible_runs(runs, get_persona(pid))) == len(runs), pid


def test_the_first_line_reads_only_its_own_runs():
    runs = audit_runs()
    analyst = get_persona("analyst")
    seen = visible_runs(runs, analyst)
    assert seen, "the analyst authored seeded runs, so this must not be empty"
    assert len(seen) < len(runs), "the corpus needs runs by someone else too"
    assert all(r.actor == "analyst" for r in seen)


def test_an_unidentified_viewer_reads_nothing():
    """Default deny. An access check that fails open is not a check."""
    assert visible_runs(audit_runs(), None) == []
