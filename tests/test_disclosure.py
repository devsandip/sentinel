"""Tests for the Screen stage (docs/features/governed-codegen.md section 5, 5.1).

Headline test is the v1 done-when: the n=3 cell from the golden path (section
1.7) is suppressed, removed from the screened result, before the number could
reach the narration model. Plus proxy discovery (CTL-PROXY-01), which is the
first thing a fair lending reviewer asks about.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sentinel.disclosure import find_proxies, screen
from sentinel.disclosure.association import correlation_ratio, cramers_v


def _golden_bands() -> pd.DataFrame:
    # Section 1.6 result table: the 76+ band has n=3, below the floor of 10.
    return pd.DataFrame(
        {
            "band": ["18-25", "26-40", "41-60", "61-75", "76+"],
            "n": [142, 408, 331, 106, 3],
            "selection_rate": [0.31, 0.24, 0.27, 0.44, 0.67],
        }
    )


# -- the done-when ---------------------------------------------------------
def test_small_cell_is_suppressed_before_downstream():
    result = screen(_golden_bands(), count_col="n", group_cols=["band"])
    # The 76+ row is gone from the screened frame, not masked.
    assert "76+" not in result.screened["band"].tolist()
    assert 3 not in result.screened["n"].tolist()
    # And 0.67 (the value the suppressed cell carried) never survives.
    assert 0.67 not in result.screened["selection_rate"].tolist()
    # It was recorded as a CTL-DISC-02 suppression, with the k-anon floor breach.
    assert "CTL-DISC-02" in result.controls_fired
    assert "CTL-DISC-01" in result.controls_fired
    assert len(result.suppressed) == 1
    cell = result.suppressed[0]
    assert cell.group == {"band": "76+"} and cell.n == 3
    assert result.min_cell_before == 3
    assert result.min_cell_after == 106


def test_no_suppression_when_all_cells_meet_floor():
    grouped = pd.DataFrame({"band": ["a", "b"], "n": [50, 40]})
    result = screen(grouped, count_col="n", group_cols=["band"])
    assert result.suppressed == []
    assert result.controls_fired == []
    assert result.screened["n"].tolist() == [50, 40]


def test_custom_floor_is_respected():
    grouped = pd.DataFrame({"band": ["a", "b", "c"], "n": [3, 8, 40]})
    result = screen(grouped, count_col="n", group_cols=["band"], floor=5)
    # Only n=3 is below a floor of 5; n=8 survives.
    assert [c.n for c in result.suppressed] == [3]
    assert result.screened["n"].tolist() == [8, 40]


# -- proxy discovery (CTL-PROXY-01, section 5.1) ---------------------------
def _proxy_frame() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    band = np.array(["young"] * 100 + ["old"] * 100)
    # income tracks band almost perfectly -> a strong numeric proxy.
    income = np.where(band == "young", 20000.0, 60000.0) + rng.normal(0, 800, 200)
    # region reconstructs band exactly -> a strong categorical proxy.
    region = np.where(band == "young", "R1", "R2")
    # noise is independent of band -> not a proxy.
    noise = rng.normal(0, 1, 200)
    return pd.DataFrame(
        {"age_band": band, "income": income, "region": region, "noise": noise}
    )


def test_numeric_and_categorical_proxies_are_flagged():
    df = _proxy_frame()
    flags = find_proxies(
        df, "age_band", ["income", "region", "noise", "age_band"], threshold=0.5
    )
    flagged = {f.feature for f in flags}
    assert "income" in flagged  # correlation ratio near 1
    assert "region" in flagged  # cramers_v near 1
    assert "noise" not in flagged  # independent
    assert "age_band" not in flagged  # never proxies itself
    # It flags, it does not refuse: this is a signal for the evidence pack.
    strongest = flags[0]
    assert strongest.strength >= 0.9
    assert "flagged" in strongest.message().lower()


def test_proxy_flag_surfaces_in_screen_controls():
    df = _proxy_frame()
    grouped = pd.DataFrame({"age_band": ["young", "old"], "n": [100, 100]})
    result = screen(
        grouped,
        count_col="n",
        group_cols=["age_band"],
        scoped_table=df,
        protected="age_band",
        granted_features=["income", "region", "noise"],
    )
    assert "CTL-PROXY-01" in result.controls_fired
    assert result.suppressed == []  # proxy flagging does not suppress cells


def test_independent_feature_is_not_a_proxy():
    rng = np.random.default_rng(1)
    band = np.array(["young"] * 100 + ["old"] * 100)
    indep = rng.normal(0, 1, 200)
    df = pd.DataFrame({"age_band": band, "indep": indep})
    assert find_proxies(df, "age_band", ["indep"], threshold=0.5) == []


# -- association measure edges ---------------------------------------------
def test_cramers_v_bounds():
    a = pd.Series(["x", "x", "y", "y"])
    perfect = pd.Series(["p", "p", "q", "q"])
    assert cramers_v(a, perfect) == 1.0
    constant = pd.Series(["p", "p", "p", "p"])
    assert cramers_v(a, constant) == 0.0  # single-valued -> no association


def test_correlation_ratio_bounds():
    cats = pd.Series(["a", "a", "b", "b"])
    perfectly_separated = pd.Series([1.0, 1.0, 9.0, 9.0])
    assert correlation_ratio(cats, perfectly_separated) == 1.0
    flat = pd.Series([5.0, 5.0, 5.0, 5.0])
    assert correlation_ratio(cats, flat) == 0.0


# -- PII in output (CTL-DISC-03) -------------------------------------------
def test_pii_in_output_text_is_flagged():
    result = screen(
        _golden_bands(),
        count_col="n",
        group_cols=["band"],
        output_texts={"narration": "reach the applicant at john.doe@example.com"},
    )
    assert "CTL-DISC-03" in result.controls_fired
    assert result.pii_findings[0].location == "narration"
    assert result.pii_findings[0].kinds.get("email") == 1


def test_to_dict_is_serializable():
    result = screen(_golden_bands(), count_col="n", group_cols=["band"])
    d = result.to_dict()
    assert d["min_cell_before"] == 3
    assert d["suppressed"][0]["group"] == {"band": "76+"}
    assert "CTL-DISC-02" in d["controls_fired"]
