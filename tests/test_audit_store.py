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
from sentinel.orchestrator import (
    STATUS_AWAITING,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_REJECTED,
    STATUS_RUNNING,
)
from sentinel.platform.audit_store import (
    OUTCOME_AWAITING,
    OUTCOME_OK,
    OUTCOME_REFUSED,
    audit_runs,
    normalize_status,
    summary,
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
