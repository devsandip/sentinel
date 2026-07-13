"""Relational feature engineering over the Berka bank tables.

Builds one feature row per loan-holding account from the transaction, account,
disposition, client, and card tables. The governance point is the pre-decision
window: transaction features are aggregated only from transactions dated on or
before the loan date (optionally within a lookback window), so no post-outcome
information leaks into a default-risk feature set. A separate leakage scan then
verifies that independently and flags any feature that correlates with the
target too tightly to be legitimate.

Hand-rolled with pandas rather than Featuretools/DFS (deferred, heavier): the
aggregations are explicit and their lineage is recorded, which is what a model-
risk reviewer needs to see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

ENTITY = "account_id"
TARGET = "default"
PROTECTED = ("gender", "age_band")

# Transaction features derived from PRE-LOAN transactions only.
_TXN_FEATURES = [
    "txn_count",
    "txn_amount_sum",
    "txn_amount_mean",
    "txn_amount_std",
    "txn_amount_max",
    "balance_mean",
    "balance_min",
    "balance_last",
    "credit_count",
    "debit_count",
    "credit_debit_ratio",
]
_RFM_FEATURES = ["rfm_recency_days", "rfm_frequency", "rfm_monetary"]
_ACCOUNT_FEATURES = ["account_tenure_days", "n_dispositions", "has_card"]
# Known at origination -> legitimate decision-time features (not leakage).
_LOAN_FEATURES = ["loan_amount", "loan_duration", "loan_payments"]

# feature -> (source tables, transform) for the lineage record.
_LINEAGE: dict[str, tuple[str, str]] = {
    "txn_count": ("trans", "count of pre-loan transactions"),
    "txn_amount_sum": ("trans", "sum(amount) over pre-loan window"),
    "txn_amount_mean": ("trans", "mean(amount) over pre-loan window"),
    "txn_amount_std": ("trans", "std(amount) over pre-loan window"),
    "txn_amount_max": ("trans", "max(amount) over pre-loan window"),
    "balance_mean": ("trans", "mean(balance) over pre-loan window"),
    "balance_min": ("trans", "min(balance) over pre-loan window"),
    "balance_last": ("trans", "balance of last pre-loan transaction"),
    "credit_count": ("trans", "count where type=PRIJEM (credit)"),
    "debit_count": ("trans", "count where type!=PRIJEM (debit)"),
    "credit_debit_ratio": ("trans", "credit_count / debit_count"),
    "rfm_recency_days": ("trans", "loan_date - last pre-loan txn date"),
    "rfm_frequency": ("trans", "pre-loan transaction count"),
    "rfm_monetary": ("trans", "sum(|amount|) over pre-loan window"),
    "account_tenure_days": ("account", "loan_date - account open date"),
    "n_dispositions": ("disp", "count of dispositions on the account"),
    "has_card": ("card, disp", "1 if any card issued to the account"),
    "loan_amount": ("loan", "origination amount (decision-time)"),
    "loan_duration": ("loan", "origination term (decision-time)"),
    "loan_payments": ("loan", "scheduled payment (decision-time)"),
}


@dataclass
class FeatureResult:
    entity: str
    n_entities: int
    feature_names: list[str]
    target: str
    protected: list[str]
    window_days: int
    include_rfm: bool
    top_k: int
    frame: pd.DataFrame = field(repr=False)
    lineage: list[dict[str, Any]] = field(default_factory=list)
    leakage_notes: list[dict[str, Any]] = field(default_factory=list)

    @property
    def headline(self) -> str:
        return (
            f"{self.n_entities} accounts x {len(self.feature_names)} features "
            f"(pre-loan window {self.window_days}d); target '{self.target}'"
        )

    def head(self, n: int = 10) -> list[dict[str, Any]]:
        cols = [self.entity, *self.feature_names, *self.protected, self.target]
        cols = [c for c in cols if c in self.frame.columns]
        return self.frame[cols].head(n).round(3).to_dict("records")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "n_entities": self.n_entities,
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "target": self.target,
            "protected": self.protected,
            "window_days": self.window_days,
            "include_rfm": self.include_rfm,
            "top_k": self.top_k,
            "headline": self.headline,
            "lineage": self.lineage,
            "leakage_notes": self.leakage_notes,
            "sample": self.head(10),
        }


def _to_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def build_entity_features(
    tables: dict[str, pd.DataFrame],
    *,
    window_days: int = 365,
    include_rfm: bool = True,
    top_k: int = 0,
) -> FeatureResult:
    """Build per-account features from the relational tables.

    window_days > 0 restricts transaction aggregation to that many days before
    the loan date (0 = all pre-loan history). top_k > 0 keeps only the top_k
    features by absolute correlation with the target (id/target/protected are
    always retained).
    """
    loan = tables["loan"].copy()
    trans = tables["trans"].copy()
    account = tables["account"].copy()
    disp = tables["disp"].copy()
    client = tables["client"].copy()
    card = tables.get("card")

    loan["date"] = _to_dt(loan["date"])
    trans["date"] = _to_dt(trans["date"])
    account["date"] = _to_dt(account["date"])

    base = loan[
        ["account_id", "date", "amount", "duration", "payments", "status", TARGET]
    ].rename(
        columns={
            "date": "loan_date",
            "amount": "loan_amount",
            "duration": "loan_duration",
            "payments": "loan_payments",
            "status": "loan_status",
        }
    )
    base = base.merge(
        account[["account_id", "date", "frequency"]].rename(
            columns={"date": "account_open_date"}
        ),
        on="account_id",
        how="left",
    )

    # Pre-decision transaction window (the leakage guard).
    tl = trans.merge(base[["account_id", "loan_date"]], on="account_id", how="inner")
    pre = tl[tl["date"] <= tl["loan_date"]].copy()
    if window_days and window_days > 0:
        cutoff = pre["loan_date"] - pd.to_timedelta(window_days, unit="D")
        pre = pre[pre["date"] >= cutoff]
    pre["is_credit"] = (pre["type"] == "PRIJEM").astype(int)
    pre["abs_amount"] = pre["amount"].abs()

    g = pre.groupby("account_id")
    agg = pd.DataFrame(
        {
            "txn_count": g.size(),
            "txn_amount_sum": g["amount"].sum(),
            "txn_amount_mean": g["amount"].mean(),
            "txn_amount_std": g["amount"].std(),
            "txn_amount_max": g["amount"].max(),
            "balance_mean": g["balance"].mean(),
            "balance_min": g["balance"].min(),
            "credit_count": g["is_credit"].sum(),
            "rfm_monetary": g["abs_amount"].sum(),
        }
    )
    agg["debit_count"] = agg["txn_count"] - agg["credit_count"]
    agg["credit_debit_ratio"] = agg["credit_count"] / agg["debit_count"].replace(0, np.nan)
    last = pre.sort_values("date").groupby("account_id").tail(1).set_index("account_id")
    agg["balance_last"] = last["balance"]
    last_date = g["date"].max()
    agg = agg.reset_index()

    feat = base.merge(agg, on="account_id", how="left")
    feat["account_tenure_days"] = (
        feat["loan_date"] - feat["account_open_date"]
    ).dt.days
    feat = feat.merge(last_date.rename("last_txn_date").reset_index(), on="account_id", how="left")
    feat["rfm_recency_days"] = (feat["loan_date"] - feat["last_txn_date"]).dt.days
    feat["rfm_frequency"] = feat["txn_count"]

    # Dispositions + owner protected attributes.
    ndisp = disp.groupby("account_id").size().rename("n_dispositions").reset_index()
    feat = feat.merge(ndisp, on="account_id", how="left")
    owners = disp[disp["type"] == "OWNER"][["account_id", "client_id"]].merge(
        client[["client_id", "gender", "age_band"]], on="client_id", how="left"
    )
    owners = owners.drop_duplicates("account_id")
    feat = feat.merge(owners[["account_id", "gender", "age_band"]], on="account_id", how="left")

    # Cards (via disposition).
    if card is not None and len(card):
        card_acct = card.merge(disp[["disp_id", "account_id"]], on="disp_id", how="left")
        with_card = set(card_acct["account_id"].dropna().astype(int))
        feat["has_card"] = feat["account_id"].isin(with_card).astype(int)
    else:
        feat["has_card"] = 0

    candidates = (
        _TXN_FEATURES
        + (_RFM_FEATURES if include_rfm else [])
        + _ACCOUNT_FEATURES
        + _LOAN_FEATURES
    )
    feature_names = [c for c in candidates if c in feat.columns]
    # Accounts with no pre-loan transactions get zeros, not NaN.
    feat[feature_names] = feat[feature_names].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if top_k and top_k > 0 and top_k < len(feature_names):
        corrs = {
            c: abs(float(np.corrcoef(feat[c], feat[TARGET])[0, 1]))
            if feat[c].std() > 0
            else 0.0
            for c in feature_names
        }
        feature_names = sorted(feature_names, key=lambda c: corrs[c], reverse=True)[:top_k]

    lineage = [
        {
            "feature": f,
            "source": _LINEAGE[f][0],
            "transform": _LINEAGE[f][1],
        }
        for f in feature_names
        if f in _LINEAGE
    ]

    leakage_notes = [
        {
            "item": "loan_status",
            "verdict": "excluded",
            "reason": "target 'default' is derived from loan.status; the status "
            "column is a direct target proxy and is excluded from features.",
        },
        {
            "item": "transaction features",
            "verdict": "guarded",
            "reason": f"aggregated only from transactions dated <= loan_date "
            f"(pre-decision window {window_days}d); no post-outcome leakage.",
        },
        {
            "item": ", ".join(PROTECTED),
            "verdict": "retained-for-audit",
            "reason": "protected attributes joined for the fairness audit; excluded "
            "from the model feature set.",
        },
        {
            "item": ", ".join(_LOAN_FEATURES),
            "verdict": "decision-time",
            "reason": "known at origination; legitimate features, retained.",
        },
    ]

    keep = [ENTITY, "loan_date", *feature_names, *PROTECTED, TARGET]
    keep = [c for c in dict.fromkeys(keep) if c in feat.columns]
    return FeatureResult(
        entity=ENTITY,
        n_entities=len(feat),
        feature_names=feature_names,
        target=TARGET,
        protected=list(PROTECTED),
        window_days=window_days,
        include_rfm=include_rfm,
        top_k=top_k,
        frame=feat[keep],
        lineage=lineage,
        leakage_notes=leakage_notes,
    )


@dataclass
class LeakageReport:
    structural_ok: bool
    corr_threshold: float
    suspects: list[dict[str, Any]]
    max_corr: dict[str, Any]
    findings: list[dict[str, Any]]

    @property
    def passed(self) -> bool:
        return self.structural_ok and not self.suspects

    @property
    def headline(self) -> str:
        v = "clean" if self.passed else f"{len(self.suspects)} suspect feature(s)"
        return f"leakage scan: {v} (structural {'ok' if self.structural_ok else 'FAIL'})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "structural_ok": self.structural_ok,
            "corr_threshold": self.corr_threshold,
            "suspects": self.suspects,
            "max_corr": self.max_corr,
            "findings": self.findings,
            "headline": self.headline,
        }


def leakage_scan(
    frame: pd.DataFrame,
    feature_names: list[str],
    target: str,
    *,
    corr_threshold: float = 0.98,
) -> LeakageReport:
    """Independently verify a feature set for target leakage.

    Two checks: (1) structural - the target and the loan_status proxy must not
    appear among features; (2) statistical - no feature may correlate with the
    target above `corr_threshold`, which would signal a leak the window guard
    missed.
    """
    structural_ok = target not in feature_names and "loan_status" not in feature_names

    corrs: list[tuple[str, float]] = []
    y = frame[target].to_numpy(dtype=float)
    for c in feature_names:
        x = frame[c].to_numpy(dtype=float)
        if x.std() == 0 or y.std() == 0:
            corrs.append((c, 0.0))
            continue
        corrs.append((c, abs(float(np.corrcoef(x, y)[0, 1]))))
    corrs.sort(key=lambda kv: kv[1], reverse=True)

    suspects = [
        {"feature": c, "abs_corr": round(v, 4)} for c, v in corrs if v >= corr_threshold
    ]
    top = corrs[0] if corrs else ("", 0.0)
    findings = [
        {
            "check": "no_target_or_proxy_in_features",
            "status": "pass" if structural_ok else "fail",
            "detail": "target and loan_status excluded"
            if structural_ok
            else "target/proxy present in features",
        },
        {
            "check": "no_feature_correlates_above_threshold",
            "status": "pass" if not suspects else "fail",
            "detail": f"max |corr| = {round(top[1], 4)} on '{top[0]}' "
            f"(threshold {corr_threshold})",
        },
    ]
    return LeakageReport(
        structural_ok=structural_ok,
        corr_threshold=corr_threshold,
        suspects=suspects,
        max_corr={"feature": top[0], "abs_corr": round(top[1], 4)},
        findings=findings,
    )
