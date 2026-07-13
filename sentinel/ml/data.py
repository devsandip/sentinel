"""Load German Credit and derive the columns fairness analysis needs.

The model target is default risk: y = 1 means "bad" (defaulted), the event
we want to flag. Derived protected attributes (sex, age_band) are computed
here so the logic is inspectable rather than hidden in a preprocessed file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "german_credit.csv"

# personal_status_sex codes -> sex (per UCI documentation).
# A91 male div/sep, A92 female div/sep/married, A93 male single,
# A94 male married/widowed, A95 female single.
_SEX_MAP = {
    "A91": "male",
    "A92": "female",
    "A93": "male",
    "A94": "male",
    "A95": "female",
}

# Raw feature columns (everything except the target label).
RAW_FEATURES = [
    "checking_status",
    "duration_months",
    "credit_history",
    "purpose",
    "credit_amount",
    "savings_status",
    "employment_since",
    "installment_rate",
    "personal_status_sex",
    "other_debtors",
    "residence_since",
    "property_type",
    "age_years",
    "other_installment_plans",
    "housing",
    "existing_credits",
    "job",
    "num_dependents",
    "telephone",
    "foreign_worker",
]

NUMERIC_FEATURES = [
    "duration_months",
    "credit_amount",
    "installment_rate",
    "residence_since",
    "age_years",
    "existing_credits",
    "num_dependents",
]

# Which raw column(s) back each protected attribute, so the pipeline can
# exclude them from model features (responsible-AI: don't model on the
# protected attribute directly).
PROTECTED_SOURCE_COLUMNS = {
    "age_band": ["age_years"],
    "sex": ["personal_status_sex"],
    "foreign_worker": ["foreign_worker"],
}


@dataclass
class Dataset:
    frame: pd.DataFrame  # full frame incl. derived + target columns
    feature_columns: list[str]  # columns used as model input
    target_column: str  # name of the 0/1 target
    protected_attribute: str  # name of the protected column for fairness

    @property
    def X(self) -> pd.DataFrame:
        return self.frame[self.feature_columns]

    @property
    def y(self) -> pd.Series:
        return self.frame[self.target_column]

    @property
    def protected(self) -> pd.Series:
        return self.frame[self.protected_attribute]


def _age_band(age: int) -> str:
    if age <= 25:
        return "<=25"
    if age <= 40:
        return "26-40"
    if age <= 60:
        return "41-60"
    return "60+"


def load_dataset(
    protected_attribute: str = "age_band",
    path: Path | None = None,
) -> Dataset:
    """Load the dataset and configure it for modeling + fairness.

    The protected attribute is excluded from model features by dropping its
    source column(s); this is the explicit responsible-AI control the demo
    is meant to surface.
    """
    if protected_attribute not in PROTECTED_SOURCE_COLUMNS:
        raise ValueError(
            f"Unknown protected attribute {protected_attribute!r}; "
            f"expected one of {sorted(PROTECTED_SOURCE_COLUMNS)}"
        )

    df = pd.read_csv(path or DATA_PATH)

    # Synthetic PII, deterministic per row. German Credit carries almost no
    # PII; these columns exist only to demonstrate the redaction control and
    # are never used as model features (and are RBAC-restricted).
    df["applicant_email"] = [
        f"applicant{i:04d}@example-bank.com" for i in range(len(df))
    ]
    df["applicant_ssn"] = [
        f"{100 + i % 900:03d}-{10 + i % 90:02d}-{1000 + i % 9000:04d}"
        for i in range(len(df))
    ]

    # Derived, human-readable columns.
    df["sex"] = df["personal_status_sex"].map(_SEX_MAP)
    df["age_band"] = df["age_years"].apply(_age_band)
    df["foreign_worker_label"] = df["foreign_worker"].map(
        {"A201": "yes", "A202": "no"}
    )
    # Target: 1 = default ("bad"), 0 = good.
    df["y"] = (df["credit_risk"] == "bad").astype(int)

    excluded = set(PROTECTED_SOURCE_COLUMNS[protected_attribute])
    feature_columns = [c for c in RAW_FEATURES if c not in excluded]

    return Dataset(
        frame=df,
        feature_columns=feature_columns,
        target_column="y",
        protected_attribute=protected_attribute,
    )
