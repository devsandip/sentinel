"""Purpose limitation: the purpose-by-dataset matrix at Access (sections 4.3-4.4).

The showpiece control: you may not use credit data for marketing. Not a
permissions gap, a purpose limitation. Refused at Access with CTL-PURP-01 before
any code is generated. This file pins the matrix to the PRD cell for cell, so a
later edit that quietly changes a policy cell fails a test.
"""

from __future__ import annotations

import pytest

from sentinel.govflow import evaluate_purpose, matrix_rows, run_governed_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED
from sentinel.govflow.purpose_matrix import (
    CTL_PURP_01,
    DATA_CLASSIFICATION,
    PURPOSES,
    SHOWPIECE,
    UnknownCell,
)
from sentinel.govflow.purpose_matrix import (
    evaluate_purpose as ep,
)

# The authoritative matrix, transcribed from PRD 4.4, kept independent of the
# module's own literal so the test genuinely checks it. Order: PURPOSES.
_EXPECTED = {
    "german_credit": [1, 1, 0, 0, 1, 0],
    "uci_taiwan_credit": [1, 1, 0, 0, 1, 0],
    "ulb_fraud": [0, 0, 1, 0, 1, 0],
    "berka": [0, 1, 1, 0, 1, 1],
    "hillstrom": [0, 0, 0, 1, 1, 1],
    "lendingclub": [1, 1, 0, 0, 1, 0],
    "uci_bank_marketing": [0, 0, 0, 1, 1, 1],
    "synthetic_its": [1, 1, 1, 1, 1, 1],
}

_EXPECTED_CLASS = {
    "synthetic_its": "Public",
    "hillstrom": "Internal",
    "lendingclub": "Internal",
    "uci_bank_marketing": "Internal",
    "uci_taiwan_credit": "Restricted",
    "german_credit": "Restricted",
    "berka": "Confidential",
    "ulb_fraud": "Confidential",
}


# -- the matrix matches the PRD, cell for cell -----------------------------


def test_purposes_are_the_six_prd_columns():
    assert PURPOSES == ["fair_lending", "credit_risk", "fraud", "marketing", "quality", "causal"]


@pytest.mark.parametrize("dataset", list(_EXPECTED))
def test_every_cell_matches_the_prd(dataset):
    expected = _EXPECTED[dataset]
    for purpose, want in zip(PURPOSES, expected, strict=True):
        got = ep(dataset, purpose).permitted
        assert got is bool(want), f"{dataset} x {purpose}: expected {bool(want)}, got {got}"


def test_classification_matches_the_prd():
    assert DATA_CLASSIFICATION == _EXPECTED_CLASS


def test_matrix_covers_all_eight_datasets():
    assert set(DATA_CLASSIFICATION) == set(_EXPECTED)
    assert {r["dataset"] for r in matrix_rows()} == set(_EXPECTED)


# -- evaluate_purpose: the verdicts ----------------------------------------


def test_showpiece_is_refused_with_ctl_purp_01():
    d = evaluate_purpose(*SHOWPIECE)  # german_credit x marketing
    assert d.permitted is False
    assert d.control == CTL_PURP_01
    assert d.classification == "Restricted"
    # The reason names why the purpose is wrong, not the role.
    assert "not a permitted purpose" in d.reason
    assert "not a permissions gap" in d.reason
    assert "credit-decision data" in d.reason


def test_a_permitted_cell_grants_access():
    d = evaluate_purpose("german_credit", "fair_lending")
    assert d.permitted is True
    assert d.control is None
    assert "permitted purpose" in d.reason


def test_synthetic_its_permits_every_purpose():
    for purpose in PURPOSES:
        assert evaluate_purpose("synthetic_its", purpose).permitted is True


def test_unknown_cell_raises():
    with pytest.raises(UnknownCell):
        evaluate_purpose("german_credit", "not_a_purpose")
    with pytest.raises(UnknownCell):
        evaluate_purpose("not_a_dataset", "fair_lending")


def test_decision_to_dict_is_public_safe():
    d = evaluate_purpose(*SHOWPIECE)
    pub = d.to_dict()
    assert pub["control"] == CTL_PURP_01
    assert pub["permitted"] is False


# -- the flow enforces the gate at Access ----------------------------------


def test_marketing_purpose_blocks_the_flow_at_access():
    r = run_governed_analysis(
        "target older applicants for a campaign",
        intent="fair_lending",
        purpose_key="marketing",
    )
    assert r.status == STATUS_BLOCKED
    assert CTL_PURP_01 in r.controls_fired
    access = next(s for s in r.stages if s.stage == "Access")
    assert access.status == "blocked"
    assert access.controls == [CTL_PURP_01]
    # Nothing downstream ran, and no evidence pack was assembled.
    assert r.generated_code == ""
    assert r.evidence is None
    for stage in ("Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
        assert next(s for s in r.stages if s.stage == stage).status == "skipped"


def test_default_fair_lending_purpose_passes_access():
    r = run_governed_analysis("older applicants declined more?", intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    access = next(s for s in r.stages if s.stage == "Access")
    assert access.status == "ok"
    assert "fair_lending permitted" in access.detail


def test_permitted_but_unwired_purpose_stops_without_ctl_purp_01():
    # quality is permitted for german_credit by the matrix, but this build wires
    # only the fair_lending analysis. Honest stop, not a policy refusal.
    r = run_governed_analysis("profile data quality", intent="fair_lending", purpose_key="quality")
    assert r.status == STATUS_BLOCKED
    assert CTL_PURP_01 not in r.controls_fired
    access = next(s for s in r.stages if s.stage == "Access")
    assert access.status == "blocked"
    assert "no analysis is wired" in access.detail
