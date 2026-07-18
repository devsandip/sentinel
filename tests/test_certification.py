"""The certification lifecycle (section 11): the four gates, the refused agent,
and the rule that only certified agents are visible to Plan.

Mutation tests build local entries so they never contaminate the shared seeded
registry that the visibility tests read.
"""

from __future__ import annotations

import pytest

from sentinel.platform.certification import (
    STATUS_CANDIDATE,
    STATUS_CERTIFIED,
    STATUS_DEPRECATED,
    STATUS_DRAFT,
    STATUS_REFUSED,
    CertificationError,
    RegistryEntry,
    assign_validator,
    evaluate,
    get_entry,
    plan_visible_entries,
    status_of,
)


def _certifiable_entry(**overrides) -> RegistryEntry:
    base = dict(
        id="temp-agent",
        version="0.1",
        author="ana.author",
        owner="Dana Okafor",
        owner_is_person=True,
        validator="val.idator",
        data_contract="german_credit@sha:4f2a1c",
        eval_suite_ref="evals/temp.yaml",
        faithfulness=0.95,
    )
    base.update(overrides)
    return RegistryEntry(**base)


# -- the seeded registry ---------------------------------------------------


def test_fair_lending_is_certified():
    entry = get_entry("fair-lending")
    assert entry is not None
    assert status_of(entry) == STATUS_CERTIFIED


def test_cohort_retention_is_refused_on_two_grounds():
    entry = get_entry("cohort-retention")
    decision = evaluate(entry)
    assert decision.status == STATUS_REFUSED
    blocking = {g.name for g in decision.blocking}
    assert "eval suite passes" in blocking
    assert "independent validator" in blocking


def test_deposit_elasticity_is_candidate():
    entry = get_entry("deposit-elasticity")
    decision = evaluate(entry)
    assert decision.status == STATUS_CANDIDATE
    # Only the validator gate blocks it.
    assert [g.name for g in decision.blocking] == ["independent validator"]


def test_only_certified_visible_to_plan():
    visible = {e.id for e in plan_visible_entries()}
    assert visible == {"fair-lending"}


# -- the four gates --------------------------------------------------------


def test_all_gates_pass_is_certified():
    assert evaluate(_certifiable_entry()).status == STATUS_CERTIFIED


def test_no_eval_suite_is_draft():
    entry = _certifiable_entry(eval_suite_ref=None, faithfulness=None)
    assert evaluate(entry).status == STATUS_DRAFT


def test_low_faithfulness_is_refused():
    entry = _certifiable_entry(faithfulness=0.80)
    assert evaluate(entry).status == STATUS_REFUSED


def test_team_owner_blocks_certification():
    entry = _certifiable_entry(owner="Risk Team", owner_is_person=False)
    decision = evaluate(entry)
    assert not decision.certifiable
    assert any(g.name == "owner is a person" and not g.passed for g in decision.gates)


def test_missing_contract_blocks_certification():
    entry = _certifiable_entry(data_contract=None)
    assert not evaluate(entry).certifiable


def test_deprecated_flag_overrides():
    entry = _certifiable_entry(deprecated=True)
    assert evaluate(entry).status == STATUS_DEPRECATED


# -- assign_validator: CTL-SOD-01 reused at certification ------------------


def test_assign_validator_refuses_self_signoff():
    entry = _certifiable_entry(author="priya.raman", validator=None)
    with pytest.raises(CertificationError, match="CTL-SOD-01"):
        assign_validator(entry, "priya.raman")


def test_assign_independent_validator_certifies_a_candidate():
    entry = _certifiable_entry(validator=None)  # otherwise certifiable
    assert evaluate(entry).status == STATUS_CANDIDATE
    decision = assign_validator(entry, "independent.person")
    assert decision.status == STATUS_CERTIFIED
    assert entry.validator == "independent.person"


def test_assign_validator_does_not_certify_low_faithfulness():
    # A valid validator clears the SoD gate but the eval floor still blocks.
    entry = _certifiable_entry(author="priya.raman", validator=None, faithfulness=0.72)
    decision = assign_validator(entry, "independent.person")
    assert decision.status == STATUS_REFUSED
    assert any(g.name == "eval suite passes" and not g.passed for g in decision.gates)
