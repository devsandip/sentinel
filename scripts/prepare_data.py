"""Convert the raw UCI Statlog German Credit file into a named CSV.

Source: german.data (space-separated, no header, 20 features + target).
Target coding in source: 1 = good credit, 2 = bad credit (default).

We keep the raw categorical codes (A11, A34, ...) as-is so the CSV stays
faithful to the source. Human-readable derivations (sex, age band) are
computed at load time in sentinel/ml/data.py, not baked in here.
"""

from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "sentinel" / "data" / "german.data"
OUT = Path(__file__).resolve().parents[1] / "sentinel" / "data" / "german_credit.csv"

# Column order per the UCI Statlog German Credit documentation.
COLUMNS = [
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
    "target_raw",
]


def main() -> None:
    df = pd.read_csv(RAW, sep=r"\s+", header=None, names=COLUMNS)
    # 1 = good, 2 = bad(default) -> readable label; y is derived downstream.
    df["credit_risk"] = df["target_raw"].map({1: "good", 2: "bad"})
    df = df.drop(columns=["target_raw"])
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} ({len(df)} rows, {df.shape[1]} columns)")
    print("Class balance:")
    print(df["credit_risk"].value_counts())


if __name__ == "__main__":
    main()
