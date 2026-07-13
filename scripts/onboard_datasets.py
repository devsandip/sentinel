"""Onboard datasets into the registry (analysis-platform.md, first-slice step 2).

Downloads, samples, and normalizes datasets into sentinel/data/<id>.csv so they
ship with the repo (lean, reproducible, work offline in prod). Tabular sets come
from OpenML (clean CSV, no account, no Excel engine); Hillstrom from its S3
mirror. Idempotent: re-running refreshes the files.

Run: uv run python scripts/onboard_datasets.py [dataset_id ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "sentinel" / "data"

# UCI Taiwan default-of-credit-card-clients columns (OpenML 42477 uses x1..x23).
_TAIWAN_RENAME = {
    "x1": "LIMIT_BAL", "x2": "SEX", "x3": "EDUCATION", "x4": "MARRIAGE", "x5": "AGE",
    "x6": "PAY_0", "x7": "PAY_2", "x8": "PAY_3", "x9": "PAY_4", "x10": "PAY_5",
    "x11": "PAY_6", "x12": "BILL_AMT1", "x13": "BILL_AMT2", "x14": "BILL_AMT3",
    "x15": "BILL_AMT4", "x16": "BILL_AMT5", "x17": "BILL_AMT6", "x18": "PAY_AMT1",
    "x19": "PAY_AMT2", "x20": "PAY_AMT3", "x21": "PAY_AMT4", "x22": "PAY_AMT5",
    "x23": "PAY_AMT6", "y": "default_payment_next_month",
}


def onboard_uci_taiwan(sample: int = 10000) -> Path:
    from sklearn.datasets import fetch_openml

    d = fetch_openml(data_id=42477, as_frame=True, parser="auto")
    df = d.frame.rename(columns=_TAIWAN_RENAME)
    if "default_payment_next_month" not in df.columns and d.target is not None:
        df["default_payment_next_month"] = d.target.astype(int)
    df = df.sample(n=min(sample, len(df)), random_state=42).reset_index(drop=True)
    return _write("uci_taiwan_credit", df)


def onboard_hillstrom(sample: int = 20000) -> Path:
    url = "https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz"
    df = pd.read_csv(url, compression="gzip")
    df = df.sample(n=min(sample, len(df)), random_state=42).reset_index(drop=True)
    return _write("hillstrom", df)


def _write(dataset_id: str, df: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{dataset_id}.csv"
    df.to_csv(path, index=False)
    print(f"  onboarded {dataset_id}: {df.shape[0]} rows x {df.shape[1]} cols -> {path.name}")
    return path


ONBOARDERS = {
    "uci_taiwan_credit": onboard_uci_taiwan,
    "hillstrom": onboard_hillstrom,
}


def main(argv: list[str]) -> None:
    wanted = argv or list(ONBOARDERS)
    for did in wanted:
        fn = ONBOARDERS.get(did)
        if fn is None:
            print(f"  (no onboarder for {did}; skipping)")
            continue
        print(f"onboarding {did} ...")
        fn()


if __name__ == "__main__":
    main(sys.argv[1:])
