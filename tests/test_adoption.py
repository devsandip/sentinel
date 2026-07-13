"""Tests for adoption / utilization metrics (lead ask A)."""

from __future__ import annotations

from sentinel.orchestrator import Orchestrator
from sentinel.platform import adoption_metrics


def test_adoption_metrics_shape_and_bounds():
    m = adoption_metrics()
    assert m["total_runs"] >= 0
    assert 0.0 <= m["promotion_rate"] <= 1.0
    assert 0.0 <= m["override_rate"] <= 1.0
    # Profiler/EDA/Modeler run on every run; Validator only on non-rejected ones.
    pa = m["per_agent_invocations"]
    assert pa["profiler"] == pa["eda"] == pa["modeler"] == m["total_runs"]
    assert pa["validator"] == m["total_runs"] - m["rejected"]
    assert m["weekly"]  # seeded history present


def test_completed_run_increments_utilization():
    before = adoption_metrics()["total_runs"]
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    after = adoption_metrics()
    assert after["total_runs"] == before + 1
    assert after["live_session_runs"] >= 1
