"""Tests for the analysis platform: specs, engine, and tools."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel.analyses import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    AnalysisEngine,
    ParamError,
    all_analyses,
    get_analysis,
    linear_analyses,
)
from sentinel.analyses.spec import (
    ENGINE_LINEAR,
    AnalysisSpec,
    ParamSpec,
    StepSpec,
)
from sentinel.analyses.tools import (
    build_entity_features,
    leakage_scan,
    profile_frame,
    run_quality_checks,
)
from sentinel.config import load_agents
from sentinel.datasets import load_tables

# -- specs + params ---------------------------------------------------------


def test_catalog_seeded_and_unique():
    a = all_analyses()
    ids = [x.id for x in a]
    assert len(ids) == len(set(ids))
    assert {"data_profiling", "feature_engineering", "credit_risk"} <= set(ids)


def test_linear_steps_reference_scoped_tools():
    """Every non-gate step's tool is on its agent's guardrail allow-list."""
    allowed = {a["id"]: set(a.get("tools", [])) for a in load_agents()["agents"]}
    for spec in linear_analyses():
        for step in spec.steps:
            assert step.agent in allowed, f"{spec.id}: unknown agent {step.agent}"
            assert step.tool in allowed[step.agent], (
                f"{spec.id}/{step.id}: {step.agent} may not call {step.tool}"
            )


def test_param_coercion_and_bounds():
    p = ParamSpec("k", "K", "int", 5, minimum=0, maximum=10)
    assert p.coerce(None) == 5
    assert p.coerce("7") == 7
    with pytest.raises(ParamError):
        p.coerce(-1)
    with pytest.raises(ParamError):
        p.coerce(11)

    c = ParamSpec("mode", "Mode", "choice", "a", choices=("a", "b"))
    assert c.coerce("b") == "b"
    with pytest.raises(ParamError):
        c.coerce("z")


def test_resolve_params_rejects_unknown_key():
    spec = get_analysis("data_profiling")
    with pytest.raises(ParamError):
        spec.resolve_params({"not_a_param": 1})
    resolved = spec.resolve_params({"missing_threshold": 0.5})
    assert resolved["missing_threshold"] == 0.5
    assert resolved["max_cardinality"] == 50  # default preserved


def test_contract_build():
    spec = get_analysis("feature_engineering")
    c = spec.contract()
    assert "relational" in c.requires and "tabular" in c.requires


# -- engine -----------------------------------------------------------------


def test_engine_runs_profiling_governed():
    eng = AnalysisEngine()
    run = eng.run(get_analysis("data_profiling"), "german_credit")
    assert run.status == STATUS_COMPLETED
    assert run.contract["ok"]
    assert "profile" in run.results and "quality" in run.results
    actions = {e["action"] for e in run.audit}
    assert {"contract_check", "data_access", "run_started", "run_ended"} <= actions
    # profiled real rows.
    assert run.results["profile"]["n_rows"] > 0


def test_engine_runs_feature_engineering_relationally():
    eng = AnalysisEngine()
    run = eng.run(get_analysis("feature_engineering"), "berka", {"window_days": 0})
    assert run.status == STATUS_COMPLETED
    f = run.results["features"]
    # One feature row per loan-holding account.
    n_loans = len(load_tables("berka")["loan"])
    assert f["n_entities"] == n_loans
    assert f["n_features"] > 0 and f["lineage"]
    # The leakage scan is clean: the window guard kept post-outcome data out.
    assert run.results["leakage"]["passed"]


def test_engine_blocks_on_contract_violation():
    eng = AnalysisEngine()
    run = eng.run(get_analysis("feature_engineering"), "german_credit")
    assert run.status == STATUS_BLOCKED
    assert any("relational" in r for r in run.contract["reasons"])
    assert run.steps == []  # nothing executed


def test_engine_blocks_when_not_onboarded():
    eng = AnalysisEngine()
    # uci_bank_marketing is registered (satisfies the tabular contract) but has no
    # onboarder, so it stays un-onboarded and must be blocked before execution.
    run = eng.run(get_analysis("data_profiling"), "uci_bank_marketing")
    assert run.status == STATUS_BLOCKED
    assert any("onboard" in r for r in run.contract["reasons"])


def test_engine_guardrail_blocks_off_list_tool():
    """A step whose agent is not scoped for its tool is blocked and audited."""
    bad = AnalysisSpec(
        id="misscoped",
        name="mis-scoped",
        description="",
        engine=ENGINE_LINEAR,
        requires=frozenset({"tabular"}),
        min_rows=1,
        default_dataset_id="german_credit",
        steps=(
            StepSpec("load", "load", "data_connector", "load_dataset_frames", ""),
            # data_connector is NOT allowed to profile.
            StepSpec("p", "profile", "data_connector", "profile_dataset", ""),
        ),
    )
    run = AnalysisEngine().run(bad, "german_credit")
    assert run.status == STATUS_BLOCKED
    assert run.steps[-1].status == "blocked"
    assert any(e["action"] == "tool_blocked" for e in run.audit)


def test_engine_refuses_credit_risk_spec():
    with pytest.raises(ValueError, match="not run by AnalysisEngine"):
        AnalysisEngine().run(get_analysis("credit_risk"), "german_credit")


# -- tools ------------------------------------------------------------------


def test_profile_frame_flags_structure():
    df = pd.DataFrame(
        {
            "a": [1, 1, 2, 3, None],
            "const": [7, 7, 7, 7, 7],
            "cat": ["x", "y", "z", "w", "v"],
            "target": [0, 1, 0, 1, 0],
        }
    )
    res = profile_frame(df, max_cardinality=3, target="target")
    assert res.n_rows == 5
    assert "const" in res.constant_columns
    assert res.class_balance == {"0": 3, "1": 2}
    a = next(c for c in res.columns if c.name == "a")
    assert a.n_missing == 1 and a.is_numeric


def test_quality_checks_fail_on_missingness():
    df = pd.DataFrame({"x": [1, None, None, None], "y": [1, 2, 3, 4]})
    rep = run_quality_checks(df, missing_threshold=0.2)
    assert not rep.passed  # x is 75% missing -> blocking failure
    assert rep.verdict == "fail"


def test_feature_window_guard_limits_history():
    tables = load_tables("berka")
    wide = build_entity_features(tables, window_days=0)
    narrow = build_entity_features(tables, window_days=30)
    total_wide = wide.frame["txn_count"].sum()
    total_narrow = narrow.frame["txn_count"].sum()
    # A tighter pre-decision window can only include fewer transactions.
    assert total_narrow <= total_wide
    assert total_wide > total_narrow  # some accounts have older history


def test_leakage_scan_flags_injected_leak():
    frame = pd.DataFrame(
        {
            "account_id": range(20),
            "good_feature": np.arange(20) % 3,
            "leaky": [0] * 10 + [1] * 10,
            "default": [0] * 10 + [1] * 10,  # identical to leaky
        }
    )
    rep = leakage_scan(frame, ["good_feature", "leaky"], "default", corr_threshold=0.98)
    assert not rep.passed
    assert any(s["feature"] == "leaky" for s in rep.suspects)
