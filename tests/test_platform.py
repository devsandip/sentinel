"""Tests for the platform asset repository: patterns and playbooks."""

from __future__ import annotations

import pytest

from sentinel.platform import (
    AGENT_LINEAGE,
    all_patterns,
    all_templates,
    get_pattern,
    get_playbook,
    get_template,
    load_playbooks,
    reuse_metrics,
)
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED
from sentinel.platform.templates import AVAILABLE, LIVE

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


# -- templates (item 11) -----------------------------------------------------


@pytest.mark.parametrize("template", all_templates())
def test_each_template_is_complete(template):
    assert template.name and template.purpose
    assert template.tools  # a pre-wired allow-list
    assert template.rbac_scope
    assert template.status in {LIVE, AVAILABLE}
    assert template.pattern in {p.id for p in all_patterns()}


def test_template_lineage_matches_agent_classes():
    """The AGENT_LINEAGE map must match the `template` attribute on each agent."""
    from sentinel.agents.eda import EDAAgent
    from sentinel.agents.modeler import ModelerAgent
    from sentinel.agents.profiler import ProfilerAgent
    from sentinel.agents.validator import ValidatorAgent

    live = {
        ProfilerAgent.id: ProfilerAgent.template,
        EDAAgent.id: EDAAgent.template,
        ModelerAgent.id: ModelerAgent.template,
        ValidatorAgent.id: ValidatorAgent.template,
    }
    assert live == AGENT_LINEAGE
    # And every lineage target names a real template.
    for template_id in AGENT_LINEAGE.values():
        assert get_template(template_id) is not None


def test_live_templates_are_realized_and_available_are_not():
    for t in all_templates():
        if t.status == LIVE:
            assert t.realized_by, f"{t.id} is live but has no realizing agent"
        else:
            assert not t.realized_by, f"{t.id} is available but claims a live agent"


def test_reuse_metrics_are_coherent():
    m = reuse_metrics()
    assert m["agents_total"] == len(AGENT_LINEAGE)
    assert m["agents_covered"] == m["agents_total"]  # all four realize a template
    assert 0.0 <= m["coverage_rate"] <= 1.0
    assert m["templates_live"] <= m["templates_total"]
    assert m["est_hours_saved"] >= 0
