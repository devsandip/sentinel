"""Shape + invariant tests on fairness metrics."""

from __future__ import annotations

import pytest

from sentinel.ml.data import PROTECTED_SOURCE_COLUMNS
from sentinel.ml.fairness import DISPARITY_THRESHOLD, compute_fairness


@pytest.mark.parametrize("protected", list(PROTECTED_SOURCE_COLUMNS))
def test_fairness_shapes(protected):
    rep = compute_fairness(protected_attribute=protected, seed=42)
    assert rep.protected_attribute == protected
    assert len(rep.groups) >= 2
    total_n = sum(g.n for g in rep.groups)
    assert total_n == 250  # 25% of 1000
    for g in rep.groups:
        for rate in (g.selection_rate, g.tpr, g.fpr, g.base_rate):
            assert 0.0 <= rate <= 1.0


def test_disparity_ratio_bounds_and_verdict():
    rep = compute_fairness(protected_attribute="age_band", seed=42)
    assert 0.0 <= rep.disparity_ratio <= 1.0
    assert rep.passes == (rep.disparity_ratio >= DISPARITY_THRESHOLD)
    assert rep.threshold == DISPARITY_THRESHOLD


def test_note_mentions_exclusion():
    rep = compute_fairness(protected_attribute="age_band", seed=42)
    assert "excluded from model features" in rep.note
    assert "age_years" in rep.note
