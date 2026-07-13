"""Sentinel MCP server (ideas.md item 5).

Exposes Sentinel's governed tools over the Model Context Protocol, so an external
agent (Claude, Gemini, any MCP client) that connects inherits the controls: every
tool call runs through the same audit log, RBAC, and guardrail allow-list the
in-app agents use. The governance travels with the tools.

Run it (needs the optional extra: `uv sync --extra mcp`):

    uv run python -m sentinel.mcp_server        # stdio transport

Tools:
  profile_dataset   - profile the credit dataset under RBAC (a denial is logged)
  retrieve_policy   - retrieve governing policy passages with citations (RAG)
  compute_fairness  - fairness across a protected attribute (four-fifths ratio)
  get_audit_log     - the audit trail accumulated by this session's tool calls

The tool bodies are plain functions registered on the server, so they are unit
testable without a running transport.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .harness.audit import AuditLog
from .harness.guardrails import Guardrails
from .harness.identity import policy_version
from .harness.rbac import RBAC
from .ml.data import load_dataset
from .ml.fairness import compute_fairness as _compute_fairness
from .ml.pipeline import profile_dataset as _profile_dataset
from .rag.retriever import retrieve_policy as _retrieve_policy

# One governed session for the server: a shared audit log every tool writes to,
# with RBAC and guardrails wired in. This is what makes the controls travel.
_audit = AuditLog("mcp-session", persist=False, policy_version=policy_version())
_rbac = RBAC(_audit)
_guardrails = Guardrails(_audit)

_dataset_cache: dict[str, Any] = {}


def _dataset(protected: str = "age_band"):
    if protected not in _dataset_cache:
        _dataset_cache[protected] = load_dataset(protected)
    return _dataset_cache[protected]


def profile_dataset() -> dict[str, Any]:
    """Profile the credit dataset. Runs under RBAC as the profiler role: the
    sex-proxy column is denied and the denial is logged."""
    ds = _dataset()
    requested = [*ds.feature_columns, "credit_risk"]
    allowed = _guardrails.call(
        "profiler", "read_columns", _rbac.enforce, "profiler", requested
    )
    profile = _guardrails.call("profiler", "profile_dataset", _profile_dataset, ds)
    _audit.record(
        agent="profiler",
        action="profiled",
        inputs_summary=f"{len(allowed)}/{len(requested)} columns readable",
        data_touched=allowed,
        output_summary=f"{profile.n_rows} rows, default rate {profile.positive_rate:.3f}",
    )
    return {
        "n_rows": profile.n_rows,
        "n_features": profile.n_features,
        "default_rate": round(profile.positive_rate, 3),
        "columns_allowed": allowed,
        "columns_denied": [c for c in requested if c not in allowed],
        "governed": True,
    }


def retrieve_policy(query: str, k: int = 3) -> dict[str, Any]:
    """Retrieve governing policy passages for a query, with citations (RAG)."""
    result = _retrieve_policy(query, _audit, "validator", k)
    return result.to_dict()


def compute_fairness(protected_attribute: str = "age_band", seed: int = 42) -> dict[str, Any]:
    """Fairness across a protected attribute: the four-fifths disparity ratio."""
    ds = _dataset(protected_attribute)
    report = _guardrails.call(
        "validator",
        "compute_fairness",
        _compute_fairness,
        protected_attribute=protected_attribute,
        seed=seed,
        dataset=ds,
    )
    _audit.record(
        agent="validator",
        action="validated",
        output_summary=(
            f"disparity {report.disparity_ratio} "
            + ("within tolerance" if report.passes else "FLAGGED")
        ),
    )
    return {
        "protected_attribute": report.protected_attribute,
        "disparity_ratio": report.disparity_ratio,
        "threshold": report.threshold,
        "passes": report.passes,
    }


def get_audit_log() -> list[dict[str, Any]]:
    """The audit trail this session's tool calls have produced."""
    return _audit.as_dicts()


def build_server() -> FastMCP:
    server = FastMCP("sentinel")
    server.tool()(profile_dataset)
    server.tool()(retrieve_policy)
    server.tool()(compute_fairness)
    server.tool()(get_audit_log)
    return server


def main() -> None:
    build_server().run()  # stdio transport


if __name__ == "__main__":
    main()
