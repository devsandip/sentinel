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


def onboard_ulb_fraud(nonfraud_sample: int = 19508) -> Path:
    """ULB credit-card fraud via OpenML 1597 (no account, DbCL 1.0, not Kaggle).

    284,807 rows at 0.17% fraud is too big and too skewed to ship whole. Keep
    every fraud row (the rare positive class is the whole point) and sample the
    negatives, so the local file stays lean but the imbalance stays real.
    """
    from sklearn.datasets import fetch_openml

    d = fetch_openml(data_id=1597, as_frame=True, parser="auto")
    df = d.frame
    if "Class" not in df.columns and d.target is not None:
        df = df.copy()
        df["Class"] = d.target
    df["Class"] = df["Class"].astype(int)
    fraud = df[df["Class"] == 1]
    legit = df[df["Class"] == 0].sample(
        n=min(nonfraud_sample, (df["Class"] == 0).sum()), random_state=42
    )
    out = (
        pd.concat([fraud, legit])
        .sample(frac=1.0, random_state=42)  # shuffle so fraud is not clustered
        .reset_index(drop=True)
    )
    # The V1..V28 PCA components ship at full float precision (~10 MB); round the
    # floats to 5 decimals to roughly halve the repo file with no visible loss.
    float_cols = out.select_dtypes("float").columns
    out[float_cols] = out[float_cols].round(5)
    return _write("ulb_fraud", out)


def onboard_lendingclub(sample: int = 20000) -> Path:
    """LendingClub messy loan table via the DePaul econdata mirror (no account).

    The canonical messy-finance table: many columns, mixed types, missingness.
    Data-quality triage is the point, so keep the columns intact and only
    subsample rows for repo leanness.
    """
    url = (
        "https://bigblue.depaul.edu/jlee141/econdata/LendingClub_LoanData/"
        "LC_Loan_sample_2016.csv"
    )
    df = pd.read_csv(url, low_memory=False)
    df = df.sample(n=min(sample, len(df)), random_state=42).reset_index(drop=True)
    return _write("lendingclub", df)


def _write(dataset_id: str, df: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{dataset_id}.csv"
    df.to_csv(path, index=False)
    print(f"  onboarded {dataset_id}: {df.shape[0]} rows x {df.shape[1]} cols -> {path.name}")
    return path


# --- Berka (relational): the faithful jlacko mirror, not the Teradata demo ---
_BERKA_BASE = "https://raw.githubusercontent.com/jlacko/berka-dataset/master"
_BERKA_TABLES = ["account", "client", "disp", "order", "trans", "loan", "card", "district"]
_BERKA_DATE_COLS = {"account": ["date"], "trans": ["date"], "loan": ["date"], "card": ["issued"]}
_BERKA_NUM_COLS = {
    "trans": ["amount", "balance"],
    "loan": ["amount", "duration", "payments"],
    "order": ["amount"],
}


def _yymmdd_to_iso(v: str) -> str:
    s = str(v).split(".")[0].zfill(6)  # 930101 -> 1993-01-01 (all clients 1900s)
    return f"19{s[:2]}-{s[2:4]}-{s[4:6]}"


def _derive_client(client: pd.DataFrame) -> pd.DataFrame:
    """Decode birth_number: Czech YYMMDD where women have month + 50."""

    def decode(bn: str) -> tuple[int, str]:
        s = str(bn).zfill(6)
        yy, mm = int(s[:2]), int(s[2:4])
        female = mm > 50
        return 1900 + yy, ("female" if female else "male")

    decoded = client["birth_number"].map(decode)
    client = client.copy()
    client["birth_year"] = [d[0] for d in decoded]
    client["gender"] = [d[1] for d in decoded]
    client["age_1999"] = 1999 - client["birth_year"]
    client["age_band"] = pd.cut(
        client["age_1999"],
        bins=[0, 25, 40, 60, 200],
        labels=["<=25", "26-40", "41-60", "60+"],
    ).astype(str)
    return client


def onboard_berka(n_accounts: int = 300) -> Path:
    t = {n: pd.read_csv(f"{_BERKA_BASE}/{n}.asc", sep=";", dtype=str) for n in _BERKA_TABLES}

    # Credit-default target from loan quality (B = finished defaulted, D = in debt).
    loan = t["loan"]
    loan["default"] = loan["status"].isin(["B", "D"]).astype(int)

    # Relational sample: keep a subset of loan-holding accounts + all their rows,
    # so the FK graph and per-account transaction depth stay intact for DFS.
    loan_accts = loan["account_id"].drop_duplicates()
    keep = set(loan_accts.sample(n=min(n_accounts, len(loan_accts)), random_state=42))

    t["account"] = t["account"][t["account"]["account_id"].isin(keep)]
    t["trans"] = t["trans"][t["trans"]["account_id"].isin(keep)]
    t["order"] = t["order"][t["order"]["account_id"].isin(keep)]
    t["loan"] = loan[loan["account_id"].isin(keep)]
    t["disp"] = t["disp"][t["disp"]["account_id"].isin(keep)]
    keep_disp = set(t["disp"]["disp_id"])
    keep_clients = set(t["disp"]["client_id"])
    t["card"] = t["card"][t["card"]["disp_id"].isin(keep_disp)]
    t["client"] = _derive_client(t["client"][t["client"]["client_id"].isin(keep_clients)])
    # district is small (77 rows); keep it whole as the demographic lookup.

    # Type-cast dates + numerics so downstream tools get clean columns.
    for name, cols in _BERKA_DATE_COLS.items():
        for c in cols:
            if c in t[name].columns:
                t[name] = t[name].copy()
                t[name][c] = t[name][c].map(
                    lambda v: _yymmdd_to_iso(v) if pd.notna(v) and str(v).strip() else v
                )
    for name, cols in _BERKA_NUM_COLS.items():
        for c in cols:
            if c in t[name].columns:
                t[name][c] = pd.to_numeric(t[name][c], errors="coerce")

    out_dir = DATA_DIR / "berka"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for name in _BERKA_TABLES:
        t[name].to_csv(out_dir / f"{name}.csv", index=False)
        total += len(t[name])
    print(
        f"  onboarded berka: {len(keep)} accounts, {total} rows across "
        f"{len(_BERKA_TABLES)} tables -> berka/"
    )
    return out_dir


def onboard_synthetic_its(
    days: int = 365, intervention_day: int = 250, effect: float = 12.0
) -> Path:
    """Generate the semi-synthetic interrupted time series (fully synthetic).

    Nothing here is real: a daily metric with a trend, weekly seasonality, a
    correlated control series, and a known additive effect injected after the
    intervention date. Because the effect is injected, the ground truth is known,
    which is the point: it is a validation fixture for causal-impact analysis, and
    the only Public-class dataset, so the only legal home for the L3 sandbox. The
    generation is seeded, so re-running reproduces the same file.
    """
    import numpy as np

    rng = np.random.default_rng(42)
    t = np.arange(days)
    dates = pd.date_range("2025-01-01", periods=days, freq="D")
    trend = 100.0 + 0.05 * t
    season = 6.0 * np.sin(2 * np.pi * t / 7)  # weekly seasonality
    control = trend + season + rng.normal(0, 2.0, days)  # a covariate, no effect
    intervention = (t >= intervention_day).astype(int)
    metric = control + intervention * effect + rng.normal(0, 1.5, days)
    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "intervention": intervention,
            "control": control.round(3),
            "metric": metric.round(3),
        }
    )
    path = _write("synthetic_its", df)
    print(
        f"    ground truth: +{effect} additive effect from day {intervention_day} "
        f"({dates[intervention_day].date()})"
    )
    return path


ONBOARDERS = {
    "uci_taiwan_credit": onboard_uci_taiwan,
    "hillstrom": onboard_hillstrom,
    "berka": onboard_berka,
    "ulb_fraud": onboard_ulb_fraud,
    "lendingclub": onboard_lendingclub,
    "synthetic_its": onboard_synthetic_its,
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
