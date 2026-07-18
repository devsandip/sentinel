"""Autonomy tier resolution (sections 4.5-4.6): tier is computed, never chosen.

    tier = min(ceiling_for(classification), ceiling_for(role, attestations))

Both ceilings bind. These tests pin the PRD's worked examples and the ceiling
tables, so a change that quietly lets a permissive dataset elevate a person, or
a person elevate a dataset, fails here.
"""

from __future__ import annotations

import pytest

from sentinel.govflow import resolve_tier, resolve_tier_for_dataset
from sentinel.govflow.tiers import (
    CLASSIFICATION_CEILING,
    UnknownClassification,
    person_ceiling,
)

# -- the five worked examples from PRD 4.6 ---------------------------------


@pytest.mark.parametrize(
    "classification,role,attestations,expected",
    [
        ("Restricted", "data_scientist", ["certified_analyst"], "L2"),  # Priya x german_credit
        ("Confidential", "data_scientist", ["certified_analyst"], "L1"),  # Priya x ulb_fraud
        ("Public", "data_scientist", ["certified_analyst"], "L2"),  # Priya x synthetic (no waiver)
        ("Restricted", "data_scientist", [], "L1"),  # Junior uncertified x german_credit
        ("Public", "model_validator", [], "L0"),  # Rahul validator x anything
    ],
)
def test_prd_worked_examples(classification, role, attestations, expected):
    assert resolve_tier(classification, role, attestations).tier == expected


def test_full_ladder_needs_public_data_and_a_waiver():
    d = resolve_tier("Public", "data_scientist", ["certified_analyst", "sandbox_waiver"])
    assert d.tier == "L3"
    assert d.classification_ceiling == "L3"
    assert d.person_ceiling == "L3"


# -- both ceilings bind -----------------------------------------------------


def test_a_permissive_dataset_does_not_elevate_a_person():
    # Public data would allow L3, but a certified analyst without a waiver is
    # capped at L2. The person ceiling binds.
    d = resolve_tier("Public", "data_scientist", ["certified_analyst"])
    assert d.tier == "L2"
    assert d.person_ceiling == "L2"
    assert d.classification_ceiling == "L3"
    assert "person" in d.rationale


def test_a_trusted_person_does_not_elevate_a_dataset():
    # A waivered analyst could reach L3, but confidential data caps at L1. The
    # data ceiling binds.
    d = resolve_tier("Confidential", "data_scientist", ["certified_analyst", "sandbox_waiver"])
    assert d.tier == "L1"
    assert d.classification_ceiling == "L1"
    assert d.person_ceiling == "L3"
    assert "data classification" in d.rationale


# -- person ceilings by role/attestation -----------------------------------


def test_non_data_science_roles_cap_at_l0():
    for role in ("model_validator", "compliance_officer", "executive"):
        assert person_ceiling(role, []) == "L0"
        # Attestations cannot lift a non data-science role off L0.
        assert person_ceiling(role, ["certified_analyst", "sandbox_waiver"]) == "L0"


def test_data_scientist_ladder_by_attestation():
    assert person_ceiling("data_scientist", []) == "L1"
    assert person_ceiling("data_scientist", ["certified_analyst"]) == "L2"
    assert person_ceiling("data_scientist", ["certified_analyst", "sandbox_waiver"]) == "L3"
    # A waiver without certification does not skip the L2 rung.
    assert person_ceiling("data_scientist", ["sandbox_waiver"]) == "L1"


# -- classification ceilings match the PRD ---------------------------------


def test_classification_ceilings():
    assert CLASSIFICATION_CEILING == {
        "Public": "L3",
        "Internal": "L2",
        "Restricted": "L2",
        "Confidential": "L1",
    }


def test_unknown_classification_raises():
    with pytest.raises(UnknownClassification):
        resolve_tier("Top Secret", "data_scientist", ["certified_analyst"])


# -- dataset convenience ties to the classification map --------------------


def test_resolve_for_dataset_uses_simulated_classification():
    certified = ["certified_analyst"]
    # german_credit is Restricted; a certified analyst resolves to L2.
    assert resolve_tier_for_dataset("german_credit", "data_scientist", certified).tier == "L2"
    # ulb_fraud is Confidential; the same analyst is capped at L1.
    assert resolve_tier_for_dataset("ulb_fraud", "data_scientist", certified).tier == "L1"


def test_decision_to_dict_is_public_safe():
    d = resolve_tier("Restricted", "data_scientist", ["certified_analyst"])
    pub = d.to_dict()
    assert pub["tier"] == "L2"
    assert pub["classification_ceiling"] == "L2"
    assert pub["attestations"] == ["certified_analyst"]
