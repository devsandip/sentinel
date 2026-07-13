"""Real logistic-regression baseline for German Credit default risk.

Deliberately simple (per the build spec: governance is the star, not the ML).
Everything here runs live on each call and returns structured, JSON-friendly
numbers. Nothing is hard-coded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data import NUMERIC_FEATURES, Dataset, load_dataset


@dataclass
class ProfileSummary:
    n_rows: int
    n_features: int
    numeric_features: list[str]
    categorical_features: list[str]
    missing_by_column: dict[str, int]
    class_balance: dict[str, int]  # label -> count on the raw target
    positive_rate: float  # share of defaults ("bad")


@dataclass
class ModelResult:
    model_type: str
    protected_attribute: str
    excluded_features: list[str]
    feature_columns: list[str]
    n_train: int
    n_test: int
    seed: int
    metrics: dict[str, float]
    confusion: dict[str, int]  # tn, fp, fn, tp
    roc_curve: dict[str, list[float]]  # fpr, tpr
    top_features: list[dict[str, Any]]  # name, coefficient, direction
    profile: ProfileSummary
    _pipeline: Pipeline | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("_pipeline", None)
        return d


def profile_dataset(ds: Dataset) -> ProfileSummary:
    frame = ds.frame
    categorical = [c for c in ds.feature_columns if c not in NUMERIC_FEATURES]
    numeric = [c for c in ds.feature_columns if c in NUMERIC_FEATURES]
    counts = frame["credit_risk"].value_counts().to_dict()
    return ProfileSummary(
        n_rows=int(len(frame)),
        n_features=len(ds.feature_columns),
        numeric_features=numeric,
        categorical_features=categorical,
        missing_by_column={
            c: int(frame[c].isna().sum()) for c in ds.feature_columns
        },
        class_balance={str(k): int(v) for k, v in counts.items()},
        positive_rate=float(ds.y.mean()),
    )


def _build_estimator(numeric: list[str], categorical: list[str], seed: int) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ]
    )
    clf = LogisticRegression(max_iter=1000, random_state=seed)
    return Pipeline([("pre", pre), ("clf", clf)])


def _coefficient_importances(
    pipe: Pipeline, top_n: int = 10
) -> list[dict[str, Any]]:
    names = pipe.named_steps["pre"].get_feature_names_out()
    coefs = pipe.named_steps["clf"].coef_[0]
    order = np.argsort(np.abs(coefs))[::-1][:top_n]
    out = []
    for i in order:
        out.append(
            {
                "name": str(names[i]),
                "coefficient": float(coefs[i]),
                "direction": "increases default risk"
                if coefs[i] > 0
                else "decreases default risk",
            }
        )
    return out


def run_pipeline(
    protected_attribute: str = "age_band",
    seed: int = 42,
    test_size: float = 0.25,
    dataset: Dataset | None = None,
) -> ModelResult:
    """Train the baseline and compute performance metrics live."""
    ds = dataset if dataset is not None else load_dataset(protected_attribute)
    profile = profile_dataset(ds)

    numeric = [c for c in ds.feature_columns if c in NUMERIC_FEATURES]
    categorical = [c for c in ds.feature_columns if c not in NUMERIC_FEATURES]

    X_train, X_test, y_train, y_test = train_test_split(
        ds.X,
        ds.y,
        test_size=test_size,
        random_state=seed,
        stratify=ds.y,
    )

    pipe = _build_estimator(numeric, categorical, seed)
    pipe.fit(X_train, y_train)
    proba = pipe.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    auc = float(roc_auc_score(y_test, proba))
    acc = float(accuracy_score(y_test, preds))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, preds, average="binary", zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    fpr, tpr, _ = roc_curve(y_test, proba)

    return ModelResult(
        model_type="logistic_regression",
        protected_attribute=ds.protected_attribute,
        excluded_features=_excluded_source(ds),
        feature_columns=list(ds.feature_columns),
        n_train=int(len(X_train)),
        n_test=int(len(X_test)),
        seed=seed,
        metrics={
            "auc": round(auc, 4),
            "accuracy": round(acc, 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
        },
        confusion={"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        roc_curve={
            "fpr": [round(float(x), 4) for x in fpr],
            "tpr": [round(float(x), 4) for x in tpr],
        },
        top_features=_coefficient_importances(pipe),
        profile=profile,
        _pipeline=pipe,
    )


def _excluded_source(ds: Dataset) -> list[str]:
    from .data import PROTECTED_SOURCE_COLUMNS

    return list(PROTECTED_SOURCE_COLUMNS[ds.protected_attribute])
