"""Tests for the model/agent registry (item 13)."""

from __future__ import annotations

from sentinel.orchestrator import Orchestrator
from sentinel.platform import agent_registry, model_versions
from sentinel.platform.registry import STATUS_PROMOTED, STATUS_REJECTED
from sentinel.platform.templates import AGENT_LINEAGE


def test_registry_seeded_and_agent_inventory():
    mv = model_versions()
    assert mv  # seeded history is present
    assert any(m.seeded for m in mv)
    # Agent registry mirrors the live lineage.
    ar = agent_registry()
    assert {a.agent_id for a in ar} == set(AGENT_LINEAGE)
    for a in ar:
        assert a.template and a.tools and a.rbac_scope


def test_completed_run_registers_a_promoted_model():
    before = len(model_versions())
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    after = model_versions()
    assert len(after) == before + 1
    newest = after[0]  # newest first
    assert newest.version.endswith(state.run_id[:6])
    assert newest.status == STATUS_PROMOTED
    assert newest.auc is not None
    assert "model_registered" in [e.action for e in state.deps.audit.events()]


def test_rejected_run_registers_as_rejected():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=False)
    newest = model_versions()[0]
    assert newest.status == STATUS_REJECTED
    # No fairness ran on a rejected model.
    assert newest.fairness_pass is None
