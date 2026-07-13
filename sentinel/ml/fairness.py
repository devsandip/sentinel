"""Group fairness metrics for the credit model.

Implemented directly (no fairlearn dependency) so every number is auditable
in a few lines. Computed on the held-out test split using the same seed as
the model, so model performance and fairness reference the same predictions.

Convention: positive prediction (1) = flagged as default risk. A higher
selection rate means a group is flagged as risky more often.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.model_selection import train_test_split

from .data import Dataset, load_dataset
from .pipeline import run_pipeline

# Four-fifths rule: disparity ratio below this is conventionally a flag.
DISPARITY_THRESHOLD = 0.8


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


def _rate(mask: np.ndarray, condition: np.ndarray) -> float:
    denom = int(mask.sum())
    if denom == 0:
        return 0.0
    return float((mask & condition).sum() / denom)


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

    group_metrics: list[GroupMetrics] = []
    for g in sorted(set(groups_series.tolist())):
        gmask = groups_series == g
        actual_pos = y_test == 1
        actual_neg = y_test == 0
        pred_pos = preds == 1
        group_metrics.append(
            GroupMetrics(
                group=str(g),
                n=int(gmask.sum()),
                selection_rate=_rate(gmask, pred_pos),
                tpr=_rate(gmask & actual_pos, pred_pos),
                fpr=_rate(gmask & actual_neg, pred_pos),
                base_rate=_rate(gmask, actual_pos),
            )
        )

    rates = [g.selection_rate for g in group_metrics if g.n > 0]
    max_rate = max(rates) if rates else 0.0
    disparity = (min(rates) / max_rate) if max_rate > 0 else 1.0
    passes = disparity >= DISPARITY_THRESHOLD

    note = (
        f"Protected attribute '{protected_attribute}' was excluded from model "
        f"features ({', '.join(result.excluded_features)}). Disparity ratio is "
        f"min/max selection rate across groups. "
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
