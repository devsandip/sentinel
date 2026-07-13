"""P3 harness tests: audit immutability, RBAC denial logged, PII redaction
logged, guardrails block, eval gate pass/fail, cost tracking."""

from __future__ import annotations

import dataclasses

import pytest

from sentinel.harness.audit import (
    LEVEL_BLOCKED,
    LEVEL_REDACTION,
    AuditLog,
)
from sentinel.harness.cost import CostTracker
from sentinel.harness.eval_gate import run_eval_gate
from sentinel.harness.guardrails import Guardrails, ToolNotAllowed
from sentinel.harness.pii import redact, scan
from sentinel.harness.rbac import RBAC


def _audit():
    return AuditLog(run_id="test-run", persist=False)


# --- Audit ---------------------------------------------------------------


def test_audit_appends_and_is_immutable():
    log = _audit()
    e1 = log.record("profiler", "profile", output_summary="ok")
    e2 = log.record("modeler", "train", output_summary="done")
    assert e1.seq == 0 and e2.seq == 1
    assert len(log.events()) == 2
    # Frozen dataclass: cannot mutate a past event.
    with pytest.raises(dataclasses.FrozenInstanceError):
        e1.output_summary = "tampered"  # type: ignore[misc]
    # events() returns a copy; clearing it does not affect the log.
    log.events().clear()
    assert len(log.events()) == 2


# --- RBAC ----------------------------------------------------------------


def test_rbac_denies_and_logs_restricted_column():
    log = _audit()
    rbac = RBAC(log)
    # Profiler is not allowed personal_status_sex, and no one may read SSN.
    allowed = rbac.enforce(
        "profiler", ["checking_status", "personal_status_sex", "applicant_ssn"]
    )
    assert "checking_status" in allowed
    assert "personal_status_sex" not in allowed
    assert "applicant_ssn" not in allowed
    denials = [e for e in log.events() if e.level == LEVEL_BLOCKED]
    assert len(denials) == 1
    assert set(denials[0].data_touched) == {"personal_status_sex", "applicant_ssn"}


def test_rbac_wildcard_allows_non_restricted():
    log = _audit()
    rbac = RBAC(log)
    allowed = rbac.enforce("validator", ["sex", "age_band", "applicant_email"])
    assert "sex" in allowed and "age_band" in allowed
    assert "applicant_email" not in allowed  # restricted globally
    assert log.count(LEVEL_BLOCKED) == 1


# --- PII -----------------------------------------------------------------


def test_pii_scan_detects_email_ssn_phone():
    r = scan("Contact applicant0001@example-bank.com SSN 123-45-6789 tel 415-555-0199")
    assert r.findings == {"email": 1, "ssn": 1, "phone": 1}
    assert "[REDACTED_EMAIL]" in r.redacted_text
    assert "[REDACTED_SSN]" in r.redacted_text
    assert "[REDACTED_PHONE]" in r.redacted_text


def test_pii_redact_logs_event():
    log = _audit()
    out = redact("email a@b.com and ssn 111-22-3333", "profiler", log)
    assert "a@b.com" not in out and "111-22-3333" not in out
    reds = [e for e in log.events() if e.level == LEVEL_REDACTION]
    assert len(reds) == 1
    assert reds[0].extra["findings"]["email"] == 1


def test_pii_no_findings_no_log():
    log = _audit()
    out = redact("no personal data here", "profiler", log)
    assert out == "no personal data here"
    assert log.count(LEVEL_REDACTION) == 0


# --- Guardrails ----------------------------------------------------------


def test_guardrails_allow_and_block():
    log = _audit()
    g = Guardrails(log)
    assert g.call("profiler", "profile_dataset", lambda: 42) == 42
    with pytest.raises(ToolNotAllowed):
        g.call("profiler", "train_model", lambda: None)
    assert log.count(LEVEL_BLOCKED) == 1


# --- Eval gate -----------------------------------------------------------


def _good_payload():
    return {
        "model": {
            "metrics": {"auc": 0.8, "accuracy": 0.75},
            "confusion": {"tn": 1, "fp": 1, "fn": 1, "tp": 1},
            "excluded_features": ["age_years"],
        },
        "fairness": {"disparity_ratio": 0.57},
        "model_card": {
            "purpose": "x",
            "data_lineage": {},
            "methodology": {},
            "performance": {},
            "fairness": {},
            "limitations": [],
            "governance": {},
        },
    }


def test_eval_gate_passes_on_complete_payload():
    report = run_eval_gate(_good_payload())
    assert report.promoted is True
    assert report.failed == 0


def test_eval_gate_blocks_on_low_auc_and_missing_section():
    payload = _good_payload()
    payload["model"]["metrics"]["auc"] = 0.4  # below floor
    del payload["fairness"]["disparity_ratio"]  # missing
    report = run_eval_gate(payload)
    assert report.promoted is False
    failed_ids = {r.id for r in report.results if not r.passed}
    assert "auc_computed" in failed_ids
    assert "fairness_section_present" in failed_ids


def test_eval_gate_logs_to_audit():
    log = _audit()
    run_eval_gate(_good_payload(), audit=log)
    gate_events = [e for e in log.events() if e.action == "eval_gate"]
    assert len(gate_events) == 1
    assert "passed" in gate_events[0].output_summary


# --- Cost ----------------------------------------------------------------


def test_cost_tracker_accumulates():
    ticks = iter([100.0, 102.5])  # start() then stop()
    ct = CostTracker(narration_mode="templated", _clock=lambda: next(ticks))
    ct.start()
    ct.add_usage(tokens=0, cost=0.0)
    ct.record_decision(approved=True)
    ct.set_eval_pass_rate(1.0)
    ct.stop()
    snap = ct.snapshot()
    assert snap["tokens"] == 0
    assert snap["cost_usd"] == 0.0
    assert snap["cycle_time_s"] == 2.5
    assert snap["human_overrides"] == 1
    assert snap["approvals"] == 1
    assert snap["eval_pass_rate"] == 1.0
