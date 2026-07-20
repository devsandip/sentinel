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


@dataclass(frozen=True)
class PurposeScope:
    """What a declared purpose covers, and what it does not.

    Purpose limitation only means something if a purpose has edges. A user
    picking one off a dropdown cannot see those edges, so they are written down
    here, in the same module as the matrix that enforces them, rather than in
    the UI where they would drift away from the policy they describe.
    """

    covers: str
    excludes: str


PURPOSE_SCOPE: dict[str, PurposeScope] = {
    "fair_lending": PurposeScope(
        covers=(
            "Testing whether a lending decision falls differently on a protected "
            "group. Selection rates, approval gaps and disparity ratios, measured "
            "on the decision the model already makes."
        ),
        excludes=(
            "Not a licence to build or tune the model, and not a route to an "
            "individual applicant. It measures outcomes across groups; it does "
            "not score a person."
        ),
    ),
    "credit_risk": PurposeScope(
        covers=(
            "Developing, validating or monitoring a model that estimates whether a "
            "borrower defaults. Development samples, discrimination and calibration "
            "metrics, drift against a benchmark."
        ),
        excludes=(
            "Not fairness testing, which is its own purpose and its own review. A "
            "risk score produced here may not be turned around and used to pick who "
            "gets an offer."
        ),
    ),
    "fraud": PurposeScope(
        covers=(
            "Detecting or investigating fraudulent transactions and accounts: "
            "anomaly rates, rule and model performance, case triage."
        ),
        excludes=(
            "Not general behavioural profiling, and refused on credit-decision "
            "data, where a fraud purpose would be a pretext for looking at "
            "applicants."
        ),
    ),
    "marketing": PurposeScope(
        covers=(
            "Campaign design, targeting, uplift measurement and channel attribution, "
            "on data that was collected for marketing in the first place."
        ),
        excludes=(
            "Refused on credit-decision data. Credit data is collected to decide "
            "credit; reusing it to sell is the textbook purpose-limitation breach, "
            "and CTL-PURP-01 stops it at Access before any code is generated."
        ),
    ),
    "quality": PurposeScope(
        covers=(
            "Profiling the data itself: completeness, ranges, duplicate and null "
            "rates, drift against the data contract."
        ),
        excludes=(
            "Not an analysis of people. It looks at columns and distributions, not "
            "at what a decision does to a group, which is why it is permitted on "
            "every dataset here."
        ),
    ),
    "causal": PurposeScope(
        covers=(
            "Estimating what an intervention caused: difference-in-differences, "
            "interrupted time series, and the like, where the question is the "
            "effect of a change rather than an association."
        ),
        excludes=(
            "Not correlational reporting relabelled. Refused on credit-decision "
            "data in this build, where a causal claim about applicants would need "
            "a model review this platform does not pretend to model."
        ),
    ),
    # The L3 route declares its purpose as `causal_impact` rather than `causal`
    # (govflow/l3.py). It never reaches the matrix, but it does reach the UI, so
    # it needs an entry here or the L3 user is told nothing.
    "causal_impact": PurposeScope(
        covers=(
            "The L3 route's fixed purpose: estimating the effect of one "
            "intervention on one metric, on Public synthetic data with a known "
            "injected effect to check the answer against."
        ),
        excludes=(
            "Not a general licence that comes with the L3 tier. L3 widens what "
            "code may be written, not what the data may be used for; the purpose "
            "is pinned to the route and cannot be switched here."
        ),
    ),
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
