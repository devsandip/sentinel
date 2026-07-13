"""Shape + sanity tests on the real ML core. No hard-coded metric values."""

from __future__ import annotations

import pytest

from sentinel.ml.data import PROTECTED_SOURCE_COLUMNS, load_dataset
from sentinel.ml.pipeline import run_pipeline


def test_dataset_loads_and_excludes_protected():
    ds = load_dataset("age_band")
    assert len(ds.frame) == 1000
    # Protected source column is excluded from model features.
    assert "age_years" not in ds.feature_columns
    assert set(ds.y.unique()) == {0, 1}
    assert ds.protected.notna().all()


@pytest.mark.parametrize("protected", list(PROTECTED_SOURCE_COLUMNS))
def test_protected_source_excluded(protected):
    ds = load_dataset(protected)
    for col in PROTECTED_SOURCE_COLUMNS[protected]:
        assert col not in ds.feature_columns


def test_unknown_protected_raises():
    with pytest.raises(ValueError):
        load_dataset("income")


def test_pipeline_metric_shapes():
    r = run_pipeline(seed=42)
    assert r.model_type == "logistic_regression"
    assert r.n_train + r.n_test == 1000
    for key in ("auc", "accuracy", "precision", "recall", "f1"):
        assert 0.0 <= r.metrics[key] <= 1.0
    # A logistic baseline on this dataset should clear random.
    assert r.metrics["auc"] > 0.65
    c = r.confusion
    assert c["tn"] + c["fp"] + c["fn"] + c["tp"] == r.n_test
    assert len(r.top_features) == 10
    assert r.roc_curve["fpr"][0] == 0.0
    assert "age_years" in r.excluded_features


def test_pipeline_reproducible_with_seed():
    a = run_pipeline(seed=42).metrics["auc"]
    b = run_pipeline(seed=42).metrics["auc"]
    assert a == b


def test_seed_changes_results():
    a = run_pipeline(seed=1).metrics
    b = run_pipeline(seed=2).metrics
    # Different splits should generally move at least one metric.
    assert a != b
