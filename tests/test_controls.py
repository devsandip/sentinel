"""Tests for the control on/off toggle (item 7).

Each toggle must actually change behavior (the control is load-bearing) and the
disabling must be audited.
"""

from __future__ import annotations

from sentinel.harness.controls import (
    CONTROL_EVAL_GATE,
    CONTROL_HUMAN_GATE,
    CONTROL_PII,
    CONTROL_RBAC,
    ControlSettings,
    from_disabled,
)
from sentinel.orchestrator import STATUS_COMPLETED, Orchestrator


def _audit_actions(state):
    return [e.action for e in state.deps.audit.events()]


def test_default_run_is_fully_governed():
    state = Orchestrator().start_run("build_model")
    assert not state.controls.any_disabled
    assert "control_disabled" not in _audit_actions(state)
    # RBAC fires normally: the proxy column is denied to the profiler.
    assert "rbac_access_denied" in _audit_actions(state)


def test_disabling_is_audited_and_marks_ungoverned():
    ctrls = from_disabled([CONTROL_RBAC])
    state = Orchestrator().start_run("build_model", controls=ctrls)
    assert state.controls.any_disabled
    disabled_events = [
        e for e in state.deps.audit.events() if e.action == "control_disabled"
    ]
    assert disabled_events and "RBAC" in disabled_events[0].output_summary
    assert state.to_public_dict()["ungoverned"] is True


def test_rbac_off_lets_the_proxy_column_through():
    ctrls = from_disabled([CONTROL_RBAC])
    state = Orchestrator().start_run("build_model", controls=ctrls)
    # No access denied, and the profiler now touches the sex-proxy column.
    assert "rbac_access_denied" not in _audit_actions(state)
    profiled = [e for e in state.deps.audit.events() if e.action == "profiled"]
    assert "personal_status_sex" in profiled[0].data_touched


def test_pii_off_leaks_the_email_into_the_audit():
    on = Orchestrator().start_run("build_model")
    off = Orchestrator().start_run("build_model", controls=from_disabled([CONTROL_PII]))
    assert "pii_redacted" in _audit_actions(on)
    assert "pii_redacted" not in _audit_actions(off)
    # With PII off, the raw email survives into the EDA event summary.
    eda_on = next(e for e in on.deps.audit.events() if e.action == "eda_reviewed")
    eda_off = next(e for e in off.deps.audit.events() if e.action == "eda_reviewed")
    assert "[REDACTED_EMAIL]" in eda_on.output_summary
    assert "@" in eda_off.output_summary and "[REDACTED_EMAIL]" not in eda_off.output_summary


def test_human_gate_off_auto_promotes_without_approval():
    ctrls = from_disabled([CONTROL_HUMAN_GATE])
    state = Orchestrator().start_run("build_model", controls=ctrls)
    # No pause: the run completes inside start_run.
    assert state.status == STATUS_COMPLETED
    assert "approval_auto" in _audit_actions(state)


def test_eval_gate_off_skips_the_checks():
    orch = Orchestrator()
    ctrls = from_disabled([CONTROL_EVAL_GATE])
    state = orch.start_run("build_model", controls=ctrls)
    orch.approve(state.run_id, approved=True)
    assert "eval_gate_skipped" in _audit_actions(state)
    assert state.shared["eval_report"].promoted is True
    assert state.shared["eval_report"].passed == 0  # no checks were run


def test_control_settings_helpers():
    assert not ControlSettings().any_disabled
    s = from_disabled([CONTROL_RBAC, "bogus"])  # unknown ids dropped
    assert s.disabled == frozenset({CONTROL_RBAC})
    assert s.disabled_names() == ["RBAC"]
