"""Data profiling tool.

A lightweight, dependency-free profiler: per-column type, missingness,
cardinality, and summary statistics, plus dataset-level shape, duplicates, and
memory. It intentionally does not pull ydata-profiling (heavy); the profile is
computed with pandas/numpy so it runs on the small prod instance. Everything is
derived from the actual frame, nothing is hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    is_numeric: bool
    n_missing: int
    pct_missing: float
    n_unique: int
    top_value: str
    top_freq: int
    stats: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        row = {
            "column": self.name,
            "dtype": self.dtype,
            "missing_%": round(self.pct_missing * 100, 2),
            "n_unique": self.n_unique,
            "top_value": self.top_value,
        }
        for k in ("min", "max", "mean", "std", "median"):
            row[k] = round(self.stats[k], 4) if k in self.stats else None
        return row


@dataclass
class ProfileResult:
    n_rows: int
    n_cols: int
    memory_mb: float
    duplicate_rows: int
    columns: list[ColumnProfile]
    fully_null_columns: list[str]
    constant_columns: list[str]
    high_cardinality_columns: list[str]
    class_balance: dict[str, int] = field(default_factory=dict)
    sampled_rows: int = 0

    @property
    def headline(self) -> str:
        bits = [f"{self.n_rows:,} rows x {self.n_cols} cols"]
        if self.duplicate_rows:
            bits.append(f"{self.duplicate_rows} duplicate rows")
        if self.fully_null_columns:
            bits.append(f"{len(self.fully_null_columns)} fully-null")
        if self.high_cardinality_columns:
            bits.append(f"{len(self.high_cardinality_columns)} high-cardinality")
        if self.class_balance:
            total = sum(self.class_balance.values()) or 1
            minority = min(self.class_balance.values())
            bits.append(f"target minority {round(100 * minority / total, 1)}%")
        return "; ".join(bits)

    def table(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.columns]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "memory_mb": round(self.memory_mb, 3),
            "duplicate_rows": self.duplicate_rows,
            "fully_null_columns": self.fully_null_columns,
            "constant_columns": self.constant_columns,
            "high_cardinality_columns": self.high_cardinality_columns,
            "class_balance": self.class_balance,
            "sampled_rows": self.sampled_rows,
            "headline": self.headline,
            "columns": self.table(),
        }


def profile_frame(
    df: pd.DataFrame,
    *,
    max_cardinality: int = 50,
    sample_rows: int = 0,
    target: str | None = None,
) -> ProfileResult:
    """Profile a DataFrame. `sample_rows` (>0) profiles a deterministic sample.

    `max_cardinality` sets the threshold above which a categorical column is
    flagged as high-cardinality. `target`, if given and present, yields a class
    balance.
    """
    sampled = 0
    if 0 < sample_rows < len(df):
        df = df.sample(n=sample_rows, random_state=0)
        sampled = sample_rows

    n_rows = len(df)
    columns: list[ColumnProfile] = []
    fully_null: list[str] = []
    constant: list[str] = []
    high_card: list[str] = []

    for col in df.columns:
        s = df[col]
        n_missing = int(s.isna().sum())
        pct_missing = (n_missing / n_rows) if n_rows else 0.0
        non_null = s.dropna()
        n_unique = int(non_null.nunique())
        is_numeric = bool(pd.api.types.is_numeric_dtype(s))

        if n_missing == n_rows:
            fully_null.append(col)
        if n_unique <= 1:
            constant.append(col)
        if not is_numeric and n_unique > max_cardinality:
            high_card.append(col)

        top_value, top_freq = "", 0
        if not non_null.empty:
            vc = non_null.value_counts()
            top_value = str(vc.index[0])
            top_freq = int(vc.iloc[0])

        stats: dict[str, float] = {}
        if is_numeric and not non_null.empty:
            arr = non_null.to_numpy(dtype=float)
            stats = {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                "median": float(np.median(arr)),
            }

        columns.append(
            ColumnProfile(
                name=str(col),
                dtype=str(s.dtype),
                is_numeric=is_numeric,
                n_missing=n_missing,
                pct_missing=pct_missing,
                n_unique=n_unique,
                top_value=top_value,
                top_freq=top_freq,
                stats=stats,
            )
        )

    class_balance: dict[str, int] = {}
    if target and target in df.columns:
        class_balance = {
            str(k): int(v) for k, v in df[target].value_counts().items()
        }

    return ProfileResult(
        n_rows=n_rows,
        n_cols=df.shape[1],
        memory_mb=float(df.memory_usage(deep=True).sum()) / 1e6,
        duplicate_rows=int(df.duplicated().sum()),
        columns=columns,
        fully_null_columns=fully_null,
        constant_columns=constant,
        high_cardinality_columns=high_card,
        class_balance=class_balance,
        sampled_rows=sampled,
    )
