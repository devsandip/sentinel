"""Tests for the Sentinel MCP server's governed tools (item 5)."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from sentinel import mcp_server  # noqa: E402


def test_profile_tool_runs_under_rbac():
    out = mcp_server.profile_dataset()
    assert out["governed"] is True
    assert out["n_rows"] == 1000
    # The sex-proxy column is denied even to an external MCP caller.
    assert "personal_status_sex" in out["columns_denied"]


def test_retrieve_policy_tool_returns_citations():
    out = mcp_server.retrieve_policy("four-fifths rule adverse impact", k=2)
    assert out["backend"] == "local"
    assert out["citations"]
    assert any("Four-Fifths" in c["citation"] for c in out["citations"])


def test_compute_fairness_tool():
    out = mcp_server.compute_fairness("age_band", seed=42)
    assert out["protected_attribute"] == "age_band"
    assert 0.0 <= out["disparity_ratio"] <= 1.0
    assert isinstance(out["passes"], bool)


def test_audit_log_accumulates_across_tool_calls():
    mcp_server.profile_dataset()
    mcp_server.compute_fairness("age_band")
    log = mcp_server.get_audit_log()
    actions = {e["action"] for e in log}
    # The external calls left a governed trail, including an RBAC denial.
    assert "profiled" in actions
    assert "rbac_access_denied" in actions
    assert all(e["policy_version"] for e in log)


def test_build_server_registers_tools():
    server = mcp_server.build_server()
    assert server.name == "sentinel"
