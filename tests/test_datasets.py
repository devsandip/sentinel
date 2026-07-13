"""Tests for the dataset registry + data contracts."""

from __future__ import annotations

import pytest

from sentinel.datasets import (
    DATASETS,
    all_datasets,
    contract,
    get_dataset,
    onboarded_datasets,
)
from sentinel.datasets.contracts import (
    ALL_CAPABILITIES,
    ALL_ROLES,
    CAP_PROTECTED,
    CAP_RELATIONAL,
    CAP_TARGET,
)


def test_registry_seeded_and_ids_unique():
    ds = all_datasets()
    assert len(ds) >= 6
    ids = [d.id for d in ds]
    assert len(ids) == len(set(ids))
    # german_credit ships onboarded; it is the anchor.
    assert get_dataset("german_credit").onboarded is True


def test_every_spec_is_well_formed():
    for d in DATASETS:
        assert d.name and d.source_url and d.license
        assert d.provides <= ALL_CAPABILITIES
        for role in d.column_roles.values():
            assert role in ALL_ROLES
        assert isinstance(d.commercial_ok, bool)


def test_onboarded_subset():
    onboarded = {d.id for d in onboarded_datasets()}
    assert "german_credit" in onboarded
    # The rest register with metadata but are not onboarded until the script runs.
    assert "berka" not in onboarded


def test_contract_matching():
    fairness = contract(CAP_TARGET, CAP_PROTECTED, min_rows=500)
    gc = get_dataset("german_credit")
    ok, reasons = fairness.satisfied_by(set(gc.provides), gc.rows)
    assert ok and not reasons

    # Berka has no protected-attr capability declared -> fairness contract fails.
    berka = get_dataset("berka")
    ok2, reasons2 = fairness.satisfied_by(set(berka.provides), berka.rows)
    assert not ok2
    assert any("has_protected_attr" in r for r in reasons2)


def test_relational_contract_only_berka():
    rel = contract(CAP_RELATIONAL)
    matches = [d.id for d in DATASETS if rel.satisfied_by(set(d.provides), d.rows)[0]]
    assert matches == ["berka"]


def test_min_rows_enforced():
    c = contract(CAP_TARGET, min_rows=50000)
    gc = get_dataset("german_credit")  # 1000 rows
    ok, reasons = c.satisfied_by(set(gc.provides), gc.rows)
    assert not ok and any("rows" in r for r in reasons)


def test_unknown_capability_rejected():
    with pytest.raises(ValueError):
        contract("not_a_capability")
