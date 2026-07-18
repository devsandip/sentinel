"""Purpose limitation: the purpose-by-dataset matrix at Access (sections 4.3-4.4).

The heart of purpose limitation, and the one governance idea a banker recognises
instantly: **you may not use credit data for marketing.** Not because the role
lacks permission, but because the reason is wrong. A generic AI-governance demo
gates on who you are; this one also gates on why you are asking.

An `x` in the matrix (PRD 4.4) means the request is refused at Access with
`CTL-PURP-01`, before a single line of code is generated. The refusal is a
purpose limitation, not a permissions gap: the same analyst, same role, same
data, a different purpose, would be allowed.

The data classification (PRD 4.3) is **simulated** because every dataset here is
genuinely public. The UI says so. Pretending otherwise would be exactly the kind
of dishonesty this project argues against.
"""

from __future__ import annotations

from dataclasses import dataclass

CTL_PURP_01 = "CTL-PURP-01"

# -- classification (PRD 4.3), simulated because every dataset is really public --

CLASS_PUBLIC = "Public"
CLASS_INTERNAL = "Internal"
CLASS_RESTRICTED = "Restricted"
CLASS_CONFIDENTIAL = "Confidential"

DATA_CLASSIFICATION: dict[str, str] = {
    "synthetic_its": CLASS_PUBLIC,
    "hillstrom": CLASS_INTERNAL,
    "lendingclub": CLASS_INTERNAL,
    "uci_bank_marketing": CLASS_INTERNAL,
    "uci_taiwan_credit": CLASS_RESTRICTED,
    "german_credit": CLASS_RESTRICTED,
    "berka": CLASS_CONFIDENTIAL,
    "ulb_fraud": CLASS_CONFIDENTIAL,
}

# What each dataset is, in a phrase, so a refusal can name the reason concretely.
_DATASET_NATURE: dict[str, str] = {
    "german_credit": "credit-decision data",
    "uci_taiwan_credit": "credit-decision data",
    "ulb_fraud": "transaction fraud data",
    "berka": "account-level relational bank data",
    "hillstrom": "marketing campaign history",
    "lendingclub": "consumer-loan data",
    "uci_bank_marketing": "marketing campaign contact history",
    "synthetic_its": "synthetic, public data",
}

# -- purposes (PRD 4.4 columns) --------------------------------------------

PURPOSES: list[str] = [
    "fair_lending",
    "credit_risk",
    "fraud",
    "marketing",
    "quality",
    "causal",
]

PURPOSE_LABEL: dict[str, str] = {
    "fair_lending": "fair lending review",
    "credit_risk": "credit risk modeling",
    "fraud": "fraud detection",
    "marketing": "marketing",
    "quality": "data quality",
    "causal": "causal inference",
}

# The matrix (PRD 4.4). True = permitted, False = refused at Access (CTL-PURP-01).
# Transcribed cell for cell from the PRD; the bolded marketing column is the demo.
_Y, _X = True, False
PURPOSE_MATRIX: dict[str, dict[str, bool]] = {
    #                fair_lending credit_risk fraud marketing quality causal
    "german_credit":     dict(zip(PURPOSES, [_Y, _Y, _X, _X, _Y, _X], strict=True)),
    "uci_taiwan_credit": dict(zip(PURPOSES, [_Y, _Y, _X, _X, _Y, _X], strict=True)),
    "ulb_fraud":         dict(zip(PURPOSES, [_X, _X, _Y, _X, _Y, _X], strict=True)),
    "berka":             dict(zip(PURPOSES, [_X, _Y, _Y, _X, _Y, _Y], strict=True)),
    "hillstrom":         dict(zip(PURPOSES, [_X, _X, _X, _Y, _Y, _Y], strict=True)),
    "lendingclub":       dict(zip(PURPOSES, [_Y, _Y, _X, _X, _Y, _X], strict=True)),
    "uci_bank_marketing": dict(zip(PURPOSES, [_X, _X, _X, _Y, _Y, _Y], strict=True)),
    "synthetic_its":     dict(zip(PURPOSES, [_Y, _Y, _Y, _Y, _Y, _Y], strict=True)),
}

# The showpiece cell: credit data asked for a marketing purpose.
SHOWPIECE = ("german_credit", "marketing")


class UnknownCell(KeyError):
    """Raised when a (dataset, purpose) pair is not in the matrix."""


@dataclass(frozen=True)
class PurposeDecision:
    """The Access-stage verdict for one (dataset, purpose) pair."""

    dataset: str
    purpose: str
    permitted: bool
    classification: str
    control: str | None  # CTL-PURP-01 when refused, else None
    reason: str

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "purpose": self.purpose,
            "permitted": self.permitted,
            "classification": self.classification,
            "control": self.control,
            "reason": self.reason,
        }


def is_known(dataset: str, purpose: str) -> bool:
    return dataset in PURPOSE_MATRIX and purpose in PURPOSE_MATRIX[dataset]


def evaluate_purpose(dataset: str, purpose: str) -> PurposeDecision:
    """The Access-stage purpose gate. Returns permitted or a CTL-PURP-01 refusal
    with a reason that names why the *purpose* is wrong, not the role."""
    if not is_known(dataset, purpose):
        raise UnknownCell(f"no matrix cell for dataset={dataset!r}, purpose={purpose!r}")

    classification = DATA_CLASSIFICATION[dataset]
    permitted = PURPOSE_MATRIX[dataset][purpose]
    label = PURPOSE_LABEL.get(purpose, purpose)

    if permitted:
        reason = (
            f"{label} is a permitted purpose for {dataset} "
            f"({classification}, simulated). Access granted."
        )
        return PurposeDecision(dataset, purpose, True, classification, None, reason)

    nature = _DATASET_NATURE.get(dataset, "this data")
    reason = (
        f"{dataset} is {nature}; {label} is not a permitted purpose for it. "
        f"This is purpose limitation, not a permissions gap: the reason is wrong, "
        f"not the role. The same analyst on a permitted purpose would be allowed."
    )
    return PurposeDecision(dataset, purpose, False, classification, CTL_PURP_01, reason)


def matrix_rows() -> list[dict]:
    """The full matrix as rows for display: one dict per dataset with its
    classification and a permitted flag per purpose."""
    rows = []
    for dataset, cells in PURPOSE_MATRIX.items():
        row = {"dataset": dataset, "classification": DATA_CLASSIFICATION[dataset]}
        row.update({p: cells[p] for p in PURPOSES})
        rows.append(row)
    return rows
