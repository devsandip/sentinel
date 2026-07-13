"""Tests for the platform asset repository: patterns and playbooks."""

from __future__ import annotations

import pytest

from sentinel.platform import (
    all_patterns,
    get_pattern,
    get_playbook,
    load_playbooks,
)
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED

VALID_STATUSES = {IN_USE, PLANNED, AVOIDED}


# -- patterns (item 12) ------------------------------------------------------


def test_patterns_catalog_shape():
    patterns = all_patterns()
    assert len(patterns) == 5  # the five workflow patterns
    ids = {p.id for p in patterns}
    assert ids == {
        "prompt_chaining",
        "evaluator_optimizer",
        "routing",
        "parallelization",
        "orchestrator_workers",
    }


@pytest.mark.parametrize("pattern", all_patterns())
def test_each_pattern_is_complete(pattern):
    assert pattern.name and pattern.summary and pattern.where
    assert pattern.status in VALID_STATUSES


def test_backbone_pattern_in_use_and_orchestrator_avoided():
    # The pipeline is prompt chaining and it must be in use.
    assert get_pattern("prompt_chaining").status == IN_USE
    # Orchestrator-workers is the pattern we deliberately avoid; that stance is
    # load-bearing for the governance argument.
    assert get_pattern("orchestrator_workers").status == AVOIDED


def test_get_pattern_unknown_returns_none():
    assert get_pattern("does_not_exist") is None


# -- playbooks (item 10) -----------------------------------------------------


def test_playbooks_load_and_are_complete():
    books = load_playbooks()
    assert len(books) >= 3
    for book in books:
        assert book.id and book.title
        assert book.jtbd  # job-to-be-done is required
        assert book.body.strip()  # the markdown body rendered in the UI
        assert book.pattern  # every playbook names its architecture pattern


def test_implemented_playbook_sorts_first():
    books = load_playbooks()
    # The credit-risk playbook is the one the live app implements; it should be
    # surfaced first.
    assert books[0].id == "governed-credit-risk-model"
    assert books[0].status == "implemented"


def test_playbook_patterns_reference_the_catalog():
    catalog_ids = {p.id for p in all_patterns()}
    for book in load_playbooks():
        assert book.pattern in catalog_ids, (
            f"{book.id} names pattern '{book.pattern}' not in the catalog"
        )


def test_get_playbook_roundtrip_and_unknown():
    assert get_playbook("onboard-new-dataset").title == "Onboard a new dataset to the platform"
    assert get_playbook("nope") is None
