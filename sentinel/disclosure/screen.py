"""The Screen stage: disclosure control before anything downstream (Stage 7).

Runs on the result object after execution and before the model narrates.
Suppressed cells are removed, not masked: the number is gone from the object the
model receives, so the model cannot leak or reason about what it never saw.

Controls:
  CTL-DISC-02  small-cell suppression, n < floor (default 10). The action.
  CTL-DISC-01  k-anonymity floor across grouped output. The guarantee: every
               surviving group has at least `floor` members. Fires when the raw
               output breached the floor (so screening had to enforce it).
  CTL-DISC-03  PII detected in output text (via harness.pii).
  CTL-PROXY-01 a granted feature proxies the protected attribute (section 5.1).
               Flags and records; does not refuse. The business-necessity call
               is Legal's, not the platform's.

CTL-DISC-04 (target leakage) is deferred past the v1 slice; it belongs with a
richer feature-set result than the single grouped table v1 produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..harness import pii
from .association import association

CTL_DISC_01 = "CTL-DISC-01"
CTL_DISC_02 = "CTL-DISC-02"
CTL_DISC_03 = "CTL-DISC-03"
CTL_PROXY_01 = "CTL-PROXY-01"

DEFAULT_CELL_FLOOR = 10
DEFAULT_PROXY_THRESHOLD = 0.5


@dataclass(frozen=True)
class SuppressedCell:
    """A grouped-output cell removed for being below the k-anonymity floor."""

    group: dict[str, Any]
    n: int

    def label(self) -> str:
        return ", ".join(f"{k}={v}" for k, v in self.group.items())


@dataclass(frozen=True)
class ProxyFlag:
    """A granted feature whose association with the protected attribute is high."""

    feature: str
    protected: str
    strength: float
    method: str

    def message(self) -> str:
        return (
            f"CTL-PROXY-01: '{self.feature}' is a candidate proxy for "
            f"'{self.protected}' ({self.method}={self.strength:.2f}). Flagged, "
            "not refused: business necessity is Legal's call."
        )


@dataclass(frozen=True)
class PiiFinding:
    """PII detected in a result's output text (CTL-DISC-03)."""

    location: str
    kinds: dict[str, int]


@dataclass
class ScreenResult:
    """The screened result and everything the Screen stage did to it."""

    screened: pd.DataFrame
    suppressed: list[SuppressedCell] = field(default_factory=list)
    proxy_flags: list[ProxyFlag] = field(default_factory=list)
    pii_findings: list[PiiFinding] = field(default_factory=list)
    cell_floor: int = DEFAULT_CELL_FLOOR
    min_cell_before: int | None = None
    min_cell_after: int | None = None

    @property
    def controls_fired(self) -> list[str]:
        fired: list[str] = []
        if self.min_cell_before is not None and self.min_cell_before < self.cell_floor:
            fired.append(CTL_DISC_01)
        if self.suppressed:
            fired.append(CTL_DISC_02)
        if self.pii_findings:
            fired.append(CTL_DISC_03)
        if self.proxy_flags:
            fired.append(CTL_PROXY_01)
        return fired

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_floor": self.cell_floor,
            "min_cell_before": self.min_cell_before,
            "min_cell_after": self.min_cell_after,
            "controls_fired": self.controls_fired,
            "suppressed": [
                {"group": c.group, "n": c.n, "label": c.label()}
                for c in self.suppressed
            ],
            "proxy_flags": [
                {
                    "feature": p.feature,
                    "protected": p.protected,
                    "strength": round(p.strength, 4),
                    "method": p.method,
                }
                for p in self.proxy_flags
            ],
            "pii_findings": [
                {"location": f.location, "kinds": f.kinds} for f in self.pii_findings
            ],
        }


def suppress_small_cells(
    grouped: pd.DataFrame,
    *,
    count_col: str = "n",
    floor: int = DEFAULT_CELL_FLOOR,
    group_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, list[SuppressedCell], int | None, int | None]:
    """Remove rows whose count is below the floor (CTL-DISC-02).

    Returns the screened frame, the removed cells, and the min cell count before
    and after. The group label for each suppressed cell is taken from
    `group_cols` (defaulting to every column that is not the count column).
    """
    if count_col not in grouped.columns:
        raise ValueError(f"count column {count_col!r} not in grouped output")
    if group_cols is None:
        group_cols = [c for c in grouped.columns if c != count_col]

    counts = grouped[count_col]
    min_before = int(counts.min()) if len(counts) else None
    keep_mask = counts >= floor
    screened = grouped[keep_mask].reset_index(drop=True)

    suppressed: list[SuppressedCell] = []
    for _, row in grouped[~keep_mask].iterrows():
        group = {c: _scalar(row[c]) for c in group_cols}
        suppressed.append(SuppressedCell(group=group, n=int(row[count_col])))

    kept_counts = screened[count_col]
    min_after = int(kept_counts.min()) if len(kept_counts) else None
    return screened, suppressed, min_before, min_after


def find_proxies(
    df: pd.DataFrame,
    protected: str,
    features: list[str],
    *,
    threshold: float = DEFAULT_PROXY_THRESHOLD,
) -> list[ProxyFlag]:
    """Flag granted features that reconstruct the protected attribute (CTL-PROXY-01).

    Empirical and post-execution: for each granted feature actually present, it
    measures association with the protected column and flags any above the
    threshold. The protected attribute never proxies itself, so it is skipped.
    """
    if protected not in df.columns:
        return []
    flags: list[ProxyFlag] = []
    for feature in features:
        if feature == protected or feature not in df.columns:
            continue
        strength, method = association(df[feature], df[protected])
        if strength > threshold:
            flags.append(
                ProxyFlag(
                    feature=feature,
                    protected=protected,
                    strength=strength,
                    method=method,
                )
            )
    # Strongest first: the most dangerous proxy leads the evidence pack.
    flags.sort(key=lambda p: p.strength, reverse=True)
    return flags


def screen_output_text(texts: dict[str, str]) -> list[PiiFinding]:
    """Detect PII in named output text fields (CTL-DISC-03)."""
    findings: list[PiiFinding] = []
    for location, text in texts.items():
        result = pii.scan(text or "")
        if result.total:
            findings.append(PiiFinding(location=location, kinds=dict(result.findings)))
    return findings


def screen(
    grouped: pd.DataFrame,
    *,
    count_col: str = "n",
    floor: int = DEFAULT_CELL_FLOOR,
    group_cols: list[str] | None = None,
    scoped_table: pd.DataFrame | None = None,
    protected: str | None = None,
    granted_features: list[str] | None = None,
    proxy_threshold: float = DEFAULT_PROXY_THRESHOLD,
    output_texts: dict[str, str] | None = None,
) -> ScreenResult:
    """Run the full Screen stage on one grouped result.

    Suppression (DISC-02) is the only step that changes the data; proxy (PROXY-01)
    and PII (DISC-03) flag and record without mutating the screened frame. Pass
    `scoped_table` + `protected` + `granted_features` to enable proxy discovery,
    and `output_texts` to scan narration-bound strings for PII.
    """
    screened, suppressed, min_before, min_after = suppress_small_cells(
        grouped, count_col=count_col, floor=floor, group_cols=group_cols
    )

    proxy_flags: list[ProxyFlag] = []
    if scoped_table is not None and protected and granted_features:
        proxy_flags = find_proxies(
            scoped_table, protected, granted_features, threshold=proxy_threshold
        )

    pii_findings: list[PiiFinding] = []
    if output_texts:
        pii_findings = screen_output_text(output_texts)

    return ScreenResult(
        screened=screened,
        suppressed=suppressed,
        proxy_flags=proxy_flags,
        pii_findings=pii_findings,
        cell_floor=floor,
        min_cell_before=min_before,
        min_cell_after=min_after,
    )


def _scalar(value: Any) -> Any:
    """Convert a numpy scalar to a plain Python value for clean serialization."""
    item = getattr(value, "item", None)
    return item() if callable(item) else value
