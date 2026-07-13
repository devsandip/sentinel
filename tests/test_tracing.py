"""Tests for OpenTelemetry tracing (item 8)."""

from __future__ import annotations

from sentinel.harness.tracing import span, spans_for
from sentinel.orchestrator import Orchestrator


def test_spans_captured_for_a_run():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    traces = spans_for(state.run_id)
    names = [t["name"] for t in traces]
    # Agent spans and gateway spans are both captured.
    assert "agent.profiler" in names
    assert "agent.validator" in names
    assert any(n.startswith("gateway.") for n in names)
    # Every span has a non-negative duration and is tagged to the run.
    for t in traces:
        assert t["duration_ms"] >= 0


def test_span_context_manager_records_attributes():
    with span("unit.test", "run-xyz", **{"k": "v"}):
        pass
    got = spans_for("run-xyz")
    assert got and got[-1]["name"] == "unit.test"
    assert got[-1]["attributes"].get("k") == "v"


def test_public_dict_exposes_traces():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    assert state.to_public_dict()["traces"]  # profiler/eda/modeler spans exist pre-approval
