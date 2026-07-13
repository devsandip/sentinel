"""Data-contract vocabulary (analysis-platform.md, first-slice step 1).

The shared language between what a dataset *provides* and what an analysis
*requires*. An analysis declares a DataContract; a dataset declares the
capabilities it provides and a role for each column. The platform matches them,
so "applies to any dataset" is really "any dataset that satisfies the contract",
validated before a run. That check is itself a governance control.
"""

from __future__ import annotations

from dataclasses import dataclass

# Column roles (what a column IS, for contract matching + governance).
ROLE_TARGET = "target"  # the 0/1 label to model
ROLE_PROTECTED = "protected"  # a protected/demographic attribute (fairness)
ROLE_TREATMENT = "treatment"  # experiment arm assignment
ROLE_OUTCOME = "outcome"  # experiment outcome metric
ROLE_TIMESTAMP = "timestamp"  # time axis for a series
ROLE_ENTITY_ID = "entity_id"  # join/entity key (relational)
ROLE_FEATURE = "feature"  # ordinary model input
ROLE_PII = "pii"  # personally identifiable, must be redacted/restricted

ALL_ROLES = {
    ROLE_TARGET,
    ROLE_PROTECTED,
    ROLE_TREATMENT,
    ROLE_OUTCOME,
    ROLE_TIMESTAMP,
    ROLE_ENTITY_ID,
    ROLE_FEATURE,
    ROLE_PII,
}

# Capabilities a dataset PROVIDES and an analysis REQUIRES.
CAP_TABULAR = "tabular"
CAP_TARGET = "has_target"
CAP_PROTECTED = "has_protected_attr"
CAP_RELATIONAL = "relational"  # multiple tables + foreign keys
CAP_TREATMENT = "has_treatment"  # treatment/control arms
CAP_TIMESERIES = "timeseries"  # a time axis + (usually) an intervention

ALL_CAPABILITIES = {
    CAP_TABULAR,
    CAP_TARGET,
    CAP_PROTECTED,
    CAP_RELATIONAL,
    CAP_TREATMENT,
    CAP_TIMESERIES,
}


@dataclass(frozen=True)
class DataContract:
    """What an analysis needs from a dataset to run."""

    requires: frozenset[str] = frozenset()
    min_rows: int = 0

    def satisfied_by(self, provides: set[str], rows: int) -> tuple[bool, list[str]]:
        """Return (ok, reasons-it-fails). Empty reasons means it fits."""
        missing = sorted(self.requires - set(provides))
        reasons = [f"missing capability: {m}" for m in missing]
        if rows < self.min_rows:
            reasons.append(f"needs >= {self.min_rows} rows (has {rows})")
        return (not reasons), reasons


def contract(*capabilities: str, min_rows: int = 0) -> DataContract:
    for c in capabilities:
        if c not in ALL_CAPABILITIES:
            raise ValueError(f"unknown capability {c!r}")
    return DataContract(requires=frozenset(capabilities), min_rows=min_rows)
