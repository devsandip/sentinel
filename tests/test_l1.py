"""The L1 route: pick a certified analysis, fill typed params, write no code (4.5).

At L1 the model writes no code. The autonomy tier is computed from the persona:
the certified Analyst resolves to L2 (writes gated code), the uncertified Junior
Analyst resolves to L1 (fills typed params for a certified analysis) on the same
german_credit, and a second-line persona resolves to L0 (may not run).
"""

from __future__ import annotations

import ast

import pandas as pd
import pytest

from sentinel.evidence import to_marimo_notebook
from sentinel.govflow import run_governed_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED, STATUS_ERROR
from sentinel.govflow.l1 import (
    L1_ANALYSIS_ID,
    l1_code_descriptor,
    resolve_l1_params,
    run_l1_analysis,
)
from sentinel.harness.identity import get_persona

# -- the L1 analysis and its typed params ----------------------------------


def test_default_params_resolve():
    p = resolve_l1_params(None)
    assert p["min_band_size"] == 0
    assert p["sort_by"] == "age_band"


def test_params_are_typed_and_bounded():
    assert resolve_l1_params({"min_band_size": "40"})["min_band_size"] == 40
    with pytest.raises(ValueError):
        resolve_l1_params({"min_band_size": 9999})  # above maximum
    with pytest.raises(ValueError):
        resolve_l1_params({"sort_by": "nonsense"})  # not a choice
    with pytest.raises(ValueError):
        resolve_l1_params({"unknown_key": 1})


def _scoped():
    return pd.DataFrame(
        {
            "age_band": ["18-25", "18-25", "56-65", "56-65", "56-65"],
            "pred": [1, 0, 1, 1, 0],
        }
    )


def test_run_l1_analysis_groups_with_an_n_column():
    out = run_l1_analysis(_scoped(), resolve_l1_params(None))
    assert list(out.columns) == ["age_band", "selection_rate", "n"]
    assert set(out["age_band"]) == {"18-25", "56-65"}
    assert out["n"].sum() == 5


def test_min_band_size_filters_small_bands():
    out = run_l1_analysis(_scoped(), resolve_l1_params({"min_band_size": 3}))
    # 18-25 has n=2, dropped; 56-65 has n=3, kept.
    assert set(out["age_band"]) == {"56-65"}


def test_sort_by_selection_rate():
    out = run_l1_analysis(_scoped(), resolve_l1_params({"sort_by": "selection_rate"}))
    assert out["selection_rate"].is_monotonic_decreasing


# -- the flow computes the tier and routes by it ---------------------------


def test_certified_analyst_resolves_to_l2_and_writes_code():
    r = run_governed_analysis("older applicants declined more?", persona=get_persona("analyst"))
    assert r.tier == "L2"
    assert r.status == STATUS_COMPLETED
    assert r.generated_code  # the model wrote code
    assert next(s for s in r.stages if s.stage == "Gate").status == "ok"


def test_uncertified_junior_resolves_to_l1_and_writes_no_code():
    r = run_governed_analysis(
        "older applicants declined more?", persona=get_persona("junior_analyst")
    )
    assert r.tier == "L1"
    assert r.status == STATUS_COMPLETED
    # No code generated, and nothing to statically gate.
    assert r.generated_code == ""
    assert r.gate is None
    assert next(s for s in r.stages if s.stage == "Generate").status == "skipped"
    assert next(s for s in r.stages if s.stage == "Gate").status == "skipped"
    assert next(s for s in r.stages if s.stage == "Execute").status == "ok"
    # The L1 run still produces the finding and a signable evidence pack.
    assert r.evidence is not None
    assert "selection rate" in r.evidence.finding
    assert L1_ANALYSIS_ID in r.evidence.provenance.code


def test_l1_and_l2_reach_the_same_finding():
    # The certified analysis (L1) and the generated code (L2) compute the same
    # thing; the difference is who wrote it and whether a gate read it.
    l2 = run_governed_analysis("q", persona=get_persona("analyst"))
    l1 = run_governed_analysis("q", persona=get_persona("junior_analyst"))
    assert l1.evidence.finding == l2.evidence.finding


def test_second_line_persona_resolves_to_l0_and_may_not_run():
    r = run_governed_analysis("q", persona=get_persona("model_validator"))
    assert r.tier == "L0"
    assert r.status == STATUS_BLOCKED
    ask = next(s for s in r.stages if s.stage == "Ask")
    assert ask.status == "blocked"
    assert "may not run" in ask.detail
    assert r.evidence is None


def test_invalid_l1_params_error_out_cleanly():
    r = run_governed_analysis(
        "q", persona=get_persona("junior_analyst"), l1_params={"min_band_size": 100000}
    )
    assert r.status == STATUS_ERROR
    assert next(s for s in r.stages if s.stage == "Generate").status == "error"


def test_l1_params_flow_through_to_the_result():
    # A high min_band_size drops small bands, so the L1 run screens fewer/other bands.
    r = run_governed_analysis(
        "q", persona=get_persona("junior_analyst"), l1_params={"min_band_size": 50}
    )
    assert r.status == STATUS_COMPLETED
    assert r.tier == "L1"


def test_l1_evidence_makes_a_valid_marimo_notebook():
    r = run_governed_analysis("q", persona=get_persona("junior_analyst"))
    nb = to_marimo_notebook(r.evidence)
    ast.parse(nb)  # the L1 code descriptor embeds cleanly
    assert "L1 route" in nb


def test_l1_code_descriptor_names_the_params():
    d = l1_code_descriptor({"min_band_size": 25, "sort_by": "age_band"})
    assert "min_band_size=25" in d
    assert L1_ANALYSIS_ID in d
