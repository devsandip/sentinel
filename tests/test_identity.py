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
    assert ids == {"analyst", "model_validator", "mrm_approver", "auditor", "admin"}
    # Only the MRM Approver and Admin hold promotion authority.
    approvers = {p.id for p in personas if p.can_approve}
    assert approvers == {"mrm_approver", "admin"}
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
