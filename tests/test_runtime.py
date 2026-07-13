"""Tests for the agent runtime lifecycle boundary (item 4)."""

from __future__ import annotations

from sentinel.orchestrator import Orchestrator


def test_runtime_records_lifecycle_for_every_agent():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    events = state.deps.audit.events()
    started = [e for e in events if e.action == "agent_started"]
    finished = [e for e in events if e.action == "agent_finished"]
    ran = {e.agent for e in started}
    # Every pipeline agent went through the runtime.
    assert ran == {"profiler", "eda", "modeler", "validator"}
    assert len(started) == len(finished) == 4
    # Lifecycle records carry the scope in effect.
    prof_start = next(e for e in started if e.agent == "profiler")
    assert "template=data_analysis" in prof_start.output_summary
    assert "rbac=" in prof_start.output_summary


def test_lifecycle_ordering_start_before_finish():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    seq = [
        (e.action, e.agent)
        for e in state.deps.audit.events()
        if e.action in ("agent_started", "agent_finished") and e.agent == "profiler"
    ]
    assert seq == [("agent_started", "profiler"), ("agent_finished", "profiler")]
