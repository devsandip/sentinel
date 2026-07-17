"""The Access stage: resolve the grant and build a policy-scoped table (Stage 3).

Enforcement by construction: the scoped table has only the columns the purpose
grants, so a column the analyst may not see does not exist on the object the
generated code receives. For v1 this is one purpose (fair_lending_review) on one
dataset (german_credit).

Two demo-honest constructions, both disclosed:
  - A fine age band, so the fair-lending analysis produces a genuinely small top
    cell (71-75, n=6) for the Screen to suppress. Nothing staged: the cell is
    small in the real data.
  - A synthetic proxy column, digital_engagement_score, built to correlate with
    age (the real german_credit features do not, max ~0.35). This mirrors the
    existing pattern in ml/data.py, where synthetic PII columns exist "only to
    demonstrate the redaction control." CTL-PROXY-01 then computes a real
    association on honestly-synthetic data.
"""

from __future__ import annotations

import pandas as pd

from ..ml.data import load_dataset
from ..ml.pipeline import run_pipeline

DATASET_ID = "german_credit"
PROTECTED_ATTRIBUTE = "age_band"

# The column grant for fair_lending_review. age_band + y + pred drive the
# analysis; credit_amount, duration_months, and the synthetic proxy are granted
# so proxy discovery (CTL-PROXY-01) has features to test.
FAIR_LENDING_GRANT = [
    "age_band",
    "y",
    "pred",
    "credit_amount",
    "duration_months",
    "digital_engagement_score",
]

# Features (not the protected attribute, not the target/prediction) that proxy
# discovery evaluates at Screen.
PROXY_CANDIDATES = ["credit_amount", "duration_months", "digital_engagement_score"]


def _fine_age_band(age: int) -> str:
    """A finer banding than ml.data._age_band, so the oldest band is small enough
    to trip the disclosure floor on the real data (71-75 has 6 applicants)."""
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    if age <= 55:
        return "46-55"
    if age <= 65:
        return "56-65"
    if age <= 70:
        return "66-70"
    return "71-75"


def _digital_engagement_score(age: int, i: int) -> float:
    """A synthetic, disclosed proxy for age. Anti-correlated with age with a
    small deterministic spread, so CTL-PROXY-01 finds a real (~0.8) association
    on data that is honestly synthetic. Deterministic per row (no RNG), like the
    synthetic PII columns in ml/data.py."""
    noise = ((i * 37) % 13) - 6  # -6..6, deterministic
    return round(max(0.0, 95.0 - age + noise), 1)


def build_scoped_table(seed: int = 42) -> pd.DataFrame:
    """The fair_lending_review scoped view of german_credit.

    Trains the same logistic pipeline the hero flow uses to produce `pred`, then
    projects to the granted columns with a fine age band and the synthetic proxy.
    """
    ds = load_dataset(PROTECTED_ATTRIBUTE)
    result = run_pipeline(protected_attribute=PROTECTED_ATTRIBUTE, seed=seed, dataset=ds)
    pipe = result._pipeline
    assert pipe is not None
    pred = (pipe.predict_proba(ds.X)[:, 1] >= 0.5).astype(int)

    ages = ds.frame["age_years"].tolist()
    return pd.DataFrame(
        {
            "age_band": [_fine_age_band(a) for a in ages],
            "y": ds.frame["y"].to_numpy(),
            "pred": pred,
            "credit_amount": ds.frame["credit_amount"].to_numpy(),
            "duration_months": ds.frame["duration_months"].to_numpy(),
            "digital_engagement_score": [
                _digital_engagement_score(a, i) for i, a in enumerate(ages)
            ],
        }
    )
