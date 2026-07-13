"""P4 tests: the agent pipeline, the approval pause, and end-to-end payload."""

from __future__ import annotations

import pytest

from sentinel.orchestrator import (
    STATUS_AWAITING,
    STATUS_COMPLETED,
    STATUS_REJECTED,
    Orchestrator,
)


def test_pipeline_pauses_at_approval_gate():
    orch = Orchestrator()
    state = orch.start_run("build_model", narration_mode="scripted")
    assert state.status == STATUS_AWAITING
    # Profiler, EDA, Modeler have run; Validator has not.
    agents_run = [s.agent for s in state.steps]
    assert agents_run == ["profiler", "eda", "modeler"]
    assert state.shared.get("payload") is None  # not assembled pre-approval


def test_scripted_mode_makes_no_external_calls_and_zero_cost():
    orch = Orchestrator()
    state = orch.start_run("build_model", narration_mode="scripted")
    orch.approve(state.run_id, approved=True)
    cost = state.deps.cost.snapshot()
    assert cost["tokens"] == 0
    assert cost["cost_usd"] == 0.0
    assert cost["narration_mode"] == "templated"
    # No step claims live reasoning.
    assert all(not s.live for s in state.steps)


def test_full_run_completes_and_assembles_payload():
    orch = Orchestrator()
    state = orch.start_run("build_model", narration_mode="scripted")
    orch.approve(state.run_id, approved=True)
    assert state.status == STATUS_COMPLETED
    pub = state.to_public_dict()
    assert pub["model"]["metrics"]["auc"] > 0.65
    assert pub["fairness"]["disparity_ratio"] <= 1.0
    assert pub["model_card"]["purpose"]
    assert pub["evals"]["promoted"] is True


def test_audit_contains_rbac_denial_and_pii_redaction():
    orch = Orchestrator()
    state = orch.start_run("build_model", narration_mode="scripted")
    orch.approve(state.run_id, approved=True)
    audit = state.deps.audit
    levels = [e.level for e in audit.events()]
    assert "blocked" in levels  # RBAC denied personal_status_sex for profiler
    assert "redaction" in levels  # EDA scrubbed the applicant email
    # Find the specific RBAC denial.
    denials = [e for e in audit.events() if e.action == "rbac_access_denied"]
    assert denials
    assert "personal_status_sex" in denials[0].data_touched


def test_rejection_stops_the_run():
    orch = Orchestrator()
    state = orch.start_run("build_model", narration_mode="scripted")
    orch.approve(state.run_id, approved=False)
    assert state.status == STATUS_REJECTED
    assert state.shared.get("payload") is None
    assert state.deps.cost.snapshot()["rejections"] == 1


def test_human_override_counted():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    assert state.deps.cost.snapshot()["human_overrides"] == 1
    assert state.deps.cost.snapshot()["approvals"] == 1


def test_unknown_question_raises():
    orch = Orchestrator()
    with pytest.raises(ValueError):
        orch.start_run("does_not_exist")
