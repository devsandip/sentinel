"""Data-quality expectation suite.

A declarative set of expectations checked against a frame: each returns a
pass/warn/fail status with the count affected and a human-readable detail. This
is the pandera-style "expectations as data" idea, hand-rolled to avoid a heavy
dependency: the checks live as a list, the runner evaluates them, and the report
aggregates a verdict. Data-quality triage is the governance gate before any
modeling: a fail here should stop a pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"

SEV_INFO = "info"
SEV_WARN = "warning"
SEV_BLOCK = "blocking"


@dataclass
class Expectation:
    id: str
    description: str
    severity: str
    status: str
    n_affected: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.id,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "n_affected": self.n_affected,
            "detail": self.detail,
        }


@dataclass
class QualityReport:
    expectations: list[Expectation]
    n_rows: int
    passed: bool = field(init=False)
    n_fail: int = field(init=False)
    n_warn: int = field(init=False)

    def __post_init__(self) -> None:
        self.n_fail = sum(1 for e in self.expectations if e.status == STATUS_FAIL)
        self.n_warn = sum(1 for e in self.expectations if e.status == STATUS_WARN)
        self.passed = self.n_fail == 0

    @property
    def verdict(self) -> str:
        if self.n_fail:
            return STATUS_FAIL
        if self.n_warn:
            return STATUS_WARN
        return STATUS_PASS

    @property
    def headline(self) -> str:
        n = len(self.expectations)
        return (
            f"{n - self.n_fail - self.n_warn}/{n} passed, "
            f"{self.n_warn} warnings, {self.n_fail} failures"
        )

    def table(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.expectations]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "passed": self.passed,
            "n_fail": self.n_fail,
            "n_warn": self.n_warn,
            "headline": self.headline,
            "expectations": self.table(),
        }


def run_quality_checks(
    df: pd.DataFrame,
    *,
    missing_threshold: float = 0.2,
    outlier_z: float = 4.0,
    key_columns: Sequence[str] = (),
    target: str | None = None,
) -> QualityReport:
    """Evaluate the expectation suite against `df` and return a report."""
    n_rows = len(df)
    checks: list[Expectation] = []

    def add(id_, desc, sev, ok, n, detail):  # noqa: ANN001, PLR0913
        checks.append(
            Expectation(
                id=id_,
                description=desc,
                severity=sev,
                status=STATUS_PASS if ok else (STATUS_WARN if sev != SEV_BLOCK else STATUS_FAIL),
                n_affected=int(n),
                detail=detail,
            )
        )

    # 1. Duplicate rows.
    dups = int(df.duplicated().sum())
    add(
        "no_duplicate_rows",
        "No fully-duplicate rows",
        SEV_WARN,
        dups == 0,
        dups,
        "clean" if dups == 0 else f"{dups} duplicate rows",
    )

    # 2. Missingness under threshold (blocking).
    miss = {
        c: df[c].isna().mean()
        for c in df.columns
        if n_rows and df[c].isna().mean() > missing_threshold
    }
    add(
        "missingness_under_threshold",
        f"No column exceeds {int(missing_threshold * 100)}% missing",
        SEV_BLOCK,
        not miss,
        len(miss),
        "clean"
        if not miss
        else ", ".join(f"{c} {round(v * 100, 1)}%" for c, v in miss.items()),
    )

    # 3. Constant columns.
    const = [c for c in df.columns if df[c].dropna().nunique() <= 1]
    add(
        "no_constant_columns",
        "No zero-variance (constant) columns",
        SEV_WARN,
        not const,
        len(const),
        "clean" if not const else ", ".join(const),
    )

    # 4. Key columns not null (blocking).
    key_nulls = {c: int(df[c].isna().sum()) for c in key_columns if c in df.columns}
    bad_keys = {c: n for c, n in key_nulls.items() if n > 0}
    if key_columns:
        add(
            "key_columns_not_null",
            f"Key columns non-null: {', '.join(key_columns)}",
            SEV_BLOCK,
            not bad_keys,
            sum(bad_keys.values()),
            "clean" if not bad_keys else ", ".join(f"{c}={n}" for c, n in bad_keys.items()),
        )

    # 5. Numeric outliers by z-score.
    numeric = df.select_dtypes(include=[np.number])
    outlier_counts: dict[str, int] = {}
    for c in numeric.columns:
        col = numeric[c].dropna().to_numpy(dtype=float)
        if len(col) < 3:
            continue
        std = col.std(ddof=1)
        if std == 0:
            continue
        z = np.abs((col - col.mean()) / std)
        n_out = int((z > outlier_z).sum())
        if n_out:
            outlier_counts[c] = n_out
    add(
        "numeric_outliers",
        f"Few |z| > {outlier_z} outliers in numeric columns",
        SEV_INFO,
        not outlier_counts,
        sum(outlier_counts.values()),
        "clean"
        if not outlier_counts
        else ", ".join(f"{c}={n}" for c, n in outlier_counts.items()),
    )

    # 6. Id-like high-cardinality categoricals.
    id_like = [
        c
        for c in df.select_dtypes(exclude=[np.number]).columns
        if n_rows and df[c].dropna().nunique() > 0.9 * n_rows
    ]
    add(
        "no_id_like_categoricals",
        "No id-like categorical (near-unique) columns among features",
        SEV_INFO,
        not id_like,
        len(id_like),
        "clean" if not id_like else ", ".join(id_like),
    )

    # 7. Target not degenerate (blocking) + imbalance (warn).
    if target and target in df.columns:
        vc = df[target].value_counts()
        n_classes = int(vc.shape[0])
        add(
            "target_has_two_classes",
            "Target has at least two classes",
            SEV_BLOCK,
            n_classes >= 2,
            n_classes,
            f"{n_classes} distinct values",
        )
        if n_classes >= 2:
            minority = int(vc.min()) / max(int(vc.sum()), 1)
            add(
                "target_not_severely_imbalanced",
                "Target minority class >= 1%",
                SEV_WARN,
                minority >= 0.01,
                0 if minority >= 0.01 else 1,
                f"minority class {round(minority * 100, 2)}%",
            )

    return QualityReport(expectations=checks, n_rows=n_rows)
