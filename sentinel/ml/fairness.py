"""Group fairness metrics for the credit model, computed with fairlearn.

Computed on the held-out test split using the same seed as the model, so model
performance and fairness reference the same predictions.

This governs fairlearn's MetricFrame rather than hand-rolling the metrics. The
earlier build reimplemented selection rate, TPR, and FPR "for auditability"; that
inverts under the platform thesis. If the pitch is "I govern off-the-shelf tools
inside a controlled fence," reimplementing the one metric a fair lending reviewer
cares most about undercuts it. Governing the standard library is the point; see
docs/features/governed-codegen.md section 15.2 and the journal entry for the
reversal.

Convention: positive prediction (1) = flagged as default risk. A higher
selection rate means a group is flagged as risky more often.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    count,
    false_positive_rate,
    selection_rate,
    true_positive_rate,
)
from sklearn.model_selection import train_test_split

from .data import Dataset, load_dataset
from .pipeline import run_pipeline

# Four-fifths rule: disparity ratio below this is conventionally a flag.
DISPARITY_THRESHOLD = 0.8


def _base_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:  # noqa: ARG001
    """Actual positive (default) rate in a group. A fairlearn-style metric:
    signature is (y_true, y_pred); it ignores predictions by design."""
    return float(np.mean(y_true)) if len(y_true) else 0.0


def _clean(value: Any) -> float:
    """Coerce a fairlearn metric to a plain float, mapping an empty-group NaN to
    0.0 so the report keeps the 0..1 invariant the UI and tests rely on."""
    return 0.0 if pd.isna(value) else float(value)


@dataclass
class GroupMetrics:
    group: str
    n: int
    selection_rate: float  # share predicted positive (flagged risky)
    tpr: float  # recall on actual defaulters in this group
    fpr: float  # false-positive rate on actual non-defaulters
    base_rate: float  # actual default rate in this group


@dataclass
class FairnessReport:
    protected_attribute: str
    groups: list[GroupMetrics]
    disparity_ratio: float  # min/max selection rate across groups
    disparity_metric: str
    threshold: float
    passes: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def compute_fairness(
    protected_attribute: str = "age_band",
    seed: int = 42,
    test_size: float = 0.25,
    dataset: Dataset | None = None,
) -> FairnessReport:
    ds = dataset if dataset is not None else load_dataset(protected_attribute)
    result = run_pipeline(
        protected_attribute=protected_attribute,
        seed=seed,
        test_size=test_size,
        dataset=ds,
    )
    pipe = result._pipeline
    assert pipe is not None

    # Reproduce the exact test split (same seed + stratify) to align the
    # protected attribute with the model's test-set predictions.
    idx = np.arange(len(ds.frame))
    _, test_idx = train_test_split(
        idx, test_size=test_size, random_state=seed, stratify=ds.y
    )
    X_test = ds.X.iloc[test_idx]
    y_test = ds.y.iloc[test_idx].to_numpy()
    groups_series = ds.protected.iloc[test_idx].to_numpy()
    preds = (pipe.predict_proba(X_test)[:, 1] >= 0.5).astype(int)

    # fairlearn does the group arithmetic. One MetricFrame, grouped by the
    # protected attribute, is the whole computation the earlier build hand-rolled.
    mf = MetricFrame(
        metrics={
            "selection_rate": selection_rate,
            "tpr": true_positive_rate,
            "fpr": false_positive_rate,
            "base_rate": _base_rate,
            "n": count,
        },
        y_true=y_test,
        y_pred=preds,
        sensitive_features=groups_series,
    )
    by_group = mf.by_group

    group_metrics: list[GroupMetrics] = []
    for g in sorted(by_group.index.tolist()):
        row = by_group.loc[g]
        group_metrics.append(
            GroupMetrics(
                group=str(g),
                n=int(row["n"]),
                selection_rate=_clean(row["selection_rate"]),
                tpr=_clean(row["tpr"]),
                fpr=_clean(row["fpr"]),
                base_rate=_clean(row["base_rate"]),
            )
        )

    rates = [g.selection_rate for g in group_metrics if g.n > 0]
    max_rate = max(rates) if rates else 0.0
    disparity = (min(rates) / max_rate) if max_rate > 0 else 1.0
    passes = disparity >= DISPARITY_THRESHOLD

    note = (
        f"Protected attribute '{protected_attribute}' was excluded from model "
        f"features ({', '.join(result.excluded_features)}). Group metrics via "
        f"fairlearn MetricFrame; disparity ratio is min/max selection rate across "
        f"groups. "
        + (
            "Within the four-fifths (0.8) threshold."
            if passes
            else f"Below the 0.8 threshold ({disparity:.2f}) — flag for review."
        )
    )

    return FairnessReport(
        protected_attribute=protected_attribute,
        groups=group_metrics,
        disparity_ratio=round(float(disparity), 4),
        disparity_metric="selection_rate_min_over_max",
        threshold=DISPARITY_THRESHOLD,
        passes=passes,
        note=note,
    )
