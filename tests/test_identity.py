"""Tests for identity personas and the role-aware approval gate (item 9)."""

from __future__ import annotations

from sentinel.harness.identity import (
    all_personas,
    default_persona,
    get_persona,
    policy_version,
)
from sentinel.orchestrator import STATUS_AWAITING, STATUS_COMPLETED, Orchestrator


def test_personas_load_with_capabilities():
    personas = all_personas()
    ids = {p.id for p in personas}
    assert ids == {
        "analyst",
        "junior_analyst",
        "model_validator",
        "mrm_approver",
        "auditor",
        "admin",
    }
    # Only the MRM Approver holds promotion authority (admin dropped can_approve).
    approvers = {p.id for p in personas if p.can_approve}
    assert approvers == {"mrm_approver"}
    # Run authority and promotion authority are held by disjoint personas: the
    # approver can never be the author of the run (segregation of duties). Both
    # the certified Analyst and the uncertified Junior Analyst can run.
    runners = {p.id for p in personas if p.can_run}
    assert runners == {"analyst", "junior_analyst", "admin"}
    assert runners.isdisjoint(approvers)
    # Only the Admin may toggle controls.
    togglers = {p.id for p in personas if p.can_toggle_controls}
    assert togglers == {"admin"}
    # The Auditor is read-only and cannot run.
    auditor = get_persona("auditor")
    assert auditor.read_only and not auditor.can_run


def test_default_persona_can_run():
    dp = default_persona()
    assert dp.can_run and not dp.read_only


def test_policy_version_is_set():
    assert policy_version()
    # And it is stamped onto audit events.
    orch = Orchestrator()
    state = orch.start_run("build_model")
    assert all(e.policy_version == policy_version() for e in state.deps.audit.events())


def test_non_approver_is_denied_at_the_gate():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    analyst = get_persona("analyst")
    orch.approve(state.run_id, approved=True, actor=analyst)
    # The run stays at the gate; nothing promoted.
    assert state.status == STATUS_AWAITING
    assert state.shared.get("payload") is None
    denials = [e for e in state.deps.audit.events() if e.action == "approval_denied"]
    assert denials and denials[0].actor == "analyst"


def test_mrm_approver_can_promote():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    approver = get_persona("mrm_approver")
    orch.approve(state.run_id, approved=True, actor=approver)
    assert state.status == STATUS_COMPLETED
    # The approval event is attributed to the approver's role.
    gate = [e for e in state.deps.audit.events() if e.action == "approval_decision"]
    assert gate and gate[0].actor == "mrm_approver"


def test_backward_compatible_approve_without_actor():
    # Existing callers pass no actor; approval still works.
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    assert state.status == STATUS_COMPLETED


def test_self_approval_is_refused_by_ctl_sod_01():
    # CTL-SOD-01: an approver may not promote a run it authored. This is the
    # backstop that fires even when the same identity both starts and approves
    # (the persona model already denies the second line can_run; this catches
    # the case regardless). mrm_approver holds can_approve, so it clears the role
    # check and is refused purely on segregation of duties.
    orch = Orchestrator()
    approver = get_persona("mrm_approver")
    state = orch.start_run("build_model", actor=approver)
    assert state.started_by == "mrm_approver"
    orch.approve(state.run_id, approved=True, actor=approver)
    # The run stays at the gate; nothing promoted.
    assert state.status == STATUS_AWAITING
    assert state.shared.get("payload") is None
    denials = [e for e in state.deps.audit.events() if e.action == "approval_denied"]
    assert denials
    sod = denials[-1]
    assert sod.actor == "mrm_approver"
    assert "CTL-SOD-01" in sod.output_summary
    assert sod.extra.get("control") == "CTL-SOD-01"


def test_cross_actor_approval_passes():
    # Independent approver (author is the analyst, approver is the MRM Approver):
    # different identities, so CTL-SOD-01 does not fire and the model promotes.
    orch = Orchestrator()
    analyst = get_persona("analyst")
    approver = get_persona("mrm_approver")
    state = orch.start_run("build_model", actor=analyst)
    assert state.started_by == "analyst"
    orch.approve(state.run_id, approved=True, actor=approver)
    assert state.status == STATUS_COMPLETED
