"""Autonomy tier resolution: how much rope the model gets (sections 4.5-4.6).

The autonomy ladder has four rungs (PRD 4.5):

  L0  the model explains finished numbers, writes no code;
  L1  it picks a certified analysis and fills typed params, writes no code;
  L2  it writes code against a fenced API, reviewed before it runs;
  L3  it writes near-arbitrary code in a sandbox, reviewed before it runs.

The tier is **computed, never chosen** (PRD 4.6):

    tier = min(ceiling_for(classification), ceiling_for(role, attestations))

Both ceilings bind. A permissive dataset must not silently elevate a person, and
a trusted person must not silently elevate a dataset. That is the whole point of
taking the minimum: the request lands at the lower of what the data allows and
what the person has earned.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .purpose_matrix import DATA_CLASSIFICATION

# The four rungs, ordered. min() over these picks the lower autonomy.
TIERS = ["L0", "L1", "L2", "L3"]
_RANK = {t: i for i, t in enumerate(TIERS)}

# Attestations a person can hold (PRD 4.6).
ATT_CERTIFIED = "certified_analyst"
ATT_SANDBOX_WAIVER = "sandbox_waiver"

# Ceiling by data classification (PRD 4.6). Nothing public is worth stealing;
# account-level data forbids generated code entirely.
CLASSIFICATION_CEILING: dict[str, str] = {
    "Public": "L3",
    "Internal": "L2",
    "Restricted": "L2",
    "Confidential": "L1",
}

# Tier roles (distinct from the display personas). Non data-science roles cap at
# L0: they read finished numbers, they do not run analyses.
ROLE_DATA_SCIENTIST = "data_scientist"
ROLE_MODEL_VALIDATOR = "model_validator"
ROLE_COMPLIANCE = "compliance_officer"
ROLE_EXECUTIVE = "executive"


class UnknownClassification(KeyError):
    """Raised when a classification has no ceiling."""


@dataclass(frozen=True)
class TierDecision:
    """The resolved tier and the two ceilings it was the minimum of."""

    classification: str
    role: str
    attestations: tuple[str, ...]
    classification_ceiling: str
    person_ceiling: str
    tier: str
    rationale: str = field(default="")

    def to_dict(self) -> dict:
        return {
            "classification": self.classification,
            "role": self.role,
            "attestations": list(self.attestations),
            "classification_ceiling": self.classification_ceiling,
            "person_ceiling": self.person_ceiling,
            "tier": self.tier,
        }


def _min_tier(a: str, b: str) -> str:
    return a if _RANK[a] <= _RANK[b] else b


def person_ceiling(role: str, attestations: tuple[str, ...] | list[str]) -> str:
    """The most autonomy a person may ever have, before the data is considered.

    Only a data scientist can rise above L0, and only by earning attestations:
    certified_analyst lifts L1 to L2, and a sandbox_waiver lifts L2 to L3. Every
    other role reads finished numbers at L0."""
    atts = set(attestations)
    if role != ROLE_DATA_SCIENTIST:
        return "L0"
    if ATT_SANDBOX_WAIVER in atts and ATT_CERTIFIED in atts:
        return "L3"
    if ATT_CERTIFIED in atts:
        return "L2"
    return "L1"


def resolve_tier(
    classification: str,
    role: str,
    attestations: tuple[str, ...] | list[str] = (),
) -> TierDecision:
    """Resolve the autonomy tier as the minimum of the two ceilings (PRD 4.6)."""
    if classification not in CLASSIFICATION_CEILING:
        raise UnknownClassification(f"no ceiling for classification {classification!r}")

    atts = tuple(attestations)
    class_ceiling = CLASSIFICATION_CEILING[classification]
    pers_ceiling = person_ceiling(role, atts)
    tier = _min_tier(class_ceiling, pers_ceiling)

    binding = (
        "data classification"
        if _RANK[class_ceiling] < _RANK[pers_ceiling]
        else ("person" if _RANK[pers_ceiling] < _RANK[class_ceiling] else "both, equally")
    )
    rationale = (
        f"{classification} data allows up to {class_ceiling}; {role} with "
        f"{sorted(atts) or 'no attestations'} allows up to {pers_ceiling}. "
        f"The request lands at {tier} (bound by {binding})."
    )
    return TierDecision(
        classification=classification,
        role=role,
        attestations=atts,
        classification_ceiling=class_ceiling,
        person_ceiling=pers_ceiling,
        tier=tier,
        rationale=rationale,
    )


def resolve_tier_for_dataset(
    dataset: str, role: str, attestations: tuple[str, ...] | list[str] = ()
) -> TierDecision:
    """Convenience: resolve the tier from a dataset id, using its simulated
    classification (PRD 4.3)."""
    return resolve_tier(DATA_CLASSIFICATION[dataset], role, attestations)
