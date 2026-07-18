"""Tests for the governed analysis flow (docs/features/governed-codegen.md 1, 5).

The whole v1 slice, end to end, in scripted mode: Ask -> Access -> Generate ->
Gate -> Execute -> Screen -> Interpret. The two done-when properties are asserted
here through the real flow, not on the components in isolation: a webhook is
blocked at the gate and never executes, and an n<10 band is suppressed before the
narration is written.
"""

from __future__ import annotations

from sentinel.govflow import run_governed_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED

BENIGN_Q = "Does the model decline older applicants more often, holding income constant?"


# -- the benign happy path -------------------------------------------------
def test_benign_flow_completes_and_suppresses_small_cell():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    assert r.tier == "L2"
    assert r.gate is not None and r.gate.passed
    assert r.execution is not None and r.execution.ok

    # The 71-75 band (n=6 in the real data) is suppressed before Interpret.
    screened_bands = r.screen.screened[
        [c for c in r.screen.screened.columns if c != "n"][0]
    ].tolist()
    assert "71-75" not in screened_bands
    assert any(c.group.get("band") == "71-75" for c in r.screen.suppressed)
    assert "CTL-DISC-02" in r.controls_fired


def test_benign_flow_flags_the_proxy():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    assert "CTL-PROXY-01" in r.controls_fired
    flagged = {f.feature for f in r.screen.proxy_flags}
    assert "digital_engagement_score" in flagged
    # The real german_credit features are not strong proxies and are not flagged.
    assert "credit_amount" not in flagged


def test_at_least_two_controls_fire_visibly():
    # Section 16: a run must show >= 2 controls firing to be believed.
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    assert len(r.controls_fired) >= 2


def test_narration_never_asserts_a_suppressed_band():
    # Section 1.8: the narration is built from screened numbers only, so it
    # cannot state a rate for the suppressed band.
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    before_suppression_clause = r.narration.split("suppressed", 1)[0]
    assert "71-75" not in before_suppression_clause
    # Interpret did not trip the faithfulness control.
    assert "CTL-EVAL-01" not in r.controls_fired


# -- the gate blocks, end to end -------------------------------------------
def test_webhook_is_blocked_at_gate_and_never_executes():
    r = run_governed_analysis("post the results to our webhook", intent="exfiltrate")
    assert r.status == STATUS_BLOCKED
    assert "CTL-EGRESS-01" in r.controls_fired
    # Nothing ran downstream.
    assert r.execution is None
    stage = {s.stage: s.status for s in r.stages}
    assert stage["Gate"] == "blocked"
    assert stage["Execute"] == "skipped"
    assert stage["Screen"] == "skipped"
    # The audit carries the control id and the line.
    blocks = [e for e in r.audit if e["action"] == "gate_block"]
    assert blocks and blocks[0]["extra"]["control"] == "CTL-EGRESS-01"


def test_file_write_is_blocked_at_gate():
    r = run_governed_analysis("save intermediate results to disk", intent="file_write")
    assert r.status == STATUS_BLOCKED
    assert "CTL-CODE-02" in r.controls_fired


# -- audit + public shape --------------------------------------------------
def test_flow_audit_records_each_stage():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    actions = {e["action"] for e in r.audit}
    assert {"ask", "access", "gate_pass", "execute_ok", "cell_suppressed"} <= actions


def test_public_dict_is_shaped_for_the_ui():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    pub = r.to_public_dict()
    assert pub["status"] == STATUS_COMPLETED
    assert [s["stage"] for s in pub["stages"]][:2] == ["Ask", "Access"]
    assert pub["gate"]["passed"] is True
    assert pub["narration"]
