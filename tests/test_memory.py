"""Tests for governed memory: short-term context and long-term precedent (item 6)."""

from __future__ import annotations

from sentinel.harness.memory import precedents_for, short_term_context
from sentinel.orchestrator import Orchestrator


def test_short_term_context_reflects_run_state():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    keys = short_term_context(state.shared)
    # Pre-approval working context holds the model result and the profile.
    assert "model_result" in keys
    assert "profile" in keys


def test_completed_run_records_long_term_precedent():
    before = len(precedents_for("build_model"))
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    after = precedents_for("build_model")
    assert len(after) == before + 1
    newest = after[0]  # newest first
    assert newest.status == "promoted"
    assert newest.disparity_ratio is not None
    assert not newest.seeded


def test_public_dict_exposes_both_memory_tiers():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    mem = state.to_public_dict()["memory"]
    assert mem["short_term"]  # working context keys
    assert mem["long_term"]  # precedent for this question (seeded + this run)
