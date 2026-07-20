"""The agent-template spec: round trip, the checks, and the deploy path.

Two properties carry most of the weight here. First, the document is the
template: what `to_yaml` writes, `parse_yaml` reads back with nothing lost, so
the artifact you download is the object the screen was showing. Second, every
check is armed against a real module, which is asserted by mutating a shipped
template one field at a time and requiring the matching check to refuse. A check
that cannot be made to fail is a check that is not reading anything.
"""

from __future__ import annotations

import pytest

from sentinel.codegen.gate import CLEARED, NOT_ARMED, REFUSED
from sentinel.platform import certification
from sentinel.platform.certification import STATUS_DRAFT, parse_contract
from sentinel.platform.template_spec import (
    CHK_COLUMNS,
    CHK_CONTRACT,
    CHK_EVALS,
    CHK_IMPORTS,
    CHK_OWNER,
    CHK_PATTERN,
    CHK_PURPOSES,
    CHK_SCHEMA,
    CHK_SOD,
    CHK_TIER,
    CHK_TOOLS,
    DEPLOY_BLOCKING,
    DeployRefused,
    SpecError,
    blocking,
    deploy,
    deployable,
    parse_yaml,
    to_yaml,
    validate_text,
)
from sentinel.platform.templates import AVAILABLE, LIVE, UNASSIGNED, all_templates, get_template


@pytest.fixture
def clean_registry():
    """Deploy appends to the process-level certification registry. Snapshot and
    restore it so a deploy test cannot leak an entry into another test."""
    saved = list(certification._REGISTRY)
    yield
    certification._REGISTRY[:] = saved


def _checks_by_key(checks):
    return {c.key: c for c in checks}


def _verdict(text: str, key: str) -> str:
    _, checks = validate_text(text)
    return _checks_by_key(checks)[key].verdict


# --------------------------------------------------------------------------
# The document
# --------------------------------------------------------------------------
@pytest.mark.parametrize("template", all_templates(), ids=lambda t: t.id)
def test_yaml_round_trip_loses_nothing(template):
    spec, _doc = parse_yaml(to_yaml(template))
    assert spec.id == template.id
    assert spec.name == template.name
    assert spec.version == template.version
    assert spec.pattern == template.pattern
    # The folded block is where a round trip would silently reflow prose.
    assert spec.purpose == template.purpose
    assert spec.max_tier == template.max_tier
    assert list(spec.purposes) == list(template.purposes)
    assert spec.contract == template.contract
    assert list(spec.columns) == list(template.columns)
    assert list(spec.tools) == list(template.tools)
    assert list(spec.imports) == list(template.imports)
    assert spec.eval_floor == template.eval_floor
    assert list(spec.eval_hooks) == list(template.evals)
    assert spec.owner == template.owner
    assert spec.validator == template.validator


@pytest.mark.parametrize("template", all_templates(), ids=lambda t: t.id)
def test_shipped_templates_satisfy_the_schema(template):
    assert _verdict(to_yaml(template), CHK_SCHEMA) == CLEARED


@pytest.mark.parametrize("template", all_templates(), ids=lambda t: t.id)
def test_document_never_carries_a_status(template):
    """certification.py computes status from the gates and never stores one, so
    a document asserting one would be claiming a verdict nobody reached."""
    _spec, doc = parse_yaml(to_yaml(template))
    assert "status" not in doc
    assert "governance" not in doc


@pytest.mark.parametrize("template", all_templates(), ids=lambda t: t.id)
def test_shipped_templates_are_unowned(template):
    """A blueprint cannot own the instances made from it, so every template
    ships at UNASSIGNED and fails two certification gates until someone edits
    it. `sentinel new-agent` registers at UNASSIGNED for the same reason."""
    assert template.owner == UNASSIGNED
    assert template.validator is None
    checks = _checks_by_key(validate_text(to_yaml(template))[1])
    assert checks[CHK_OWNER].verdict == REFUSED
    assert checks[CHK_SOD].verdict == REFUSED


def test_empty_and_non_mapping_documents_raise():
    with pytest.raises(SpecError):
        parse_yaml("")
    with pytest.raises(SpecError):
        parse_yaml("- just\n- a list\n")
    with pytest.raises(SpecError):
        parse_yaml("tools: [unclosed\n")


# --------------------------------------------------------------------------
# Policy vs certification: which refusals block a deploy
# --------------------------------------------------------------------------
def test_live_templates_deploy_and_available_ones_do_not():
    """The split is not decoration: the two AVAILABLE templates have no dataset,
    which is exactly why they are not live, and the contract check says so."""
    for t in all_templates():
        _spec, checks = validate_text(to_yaml(t))
        if t.status == LIVE:
            assert deployable(checks), f"{t.id} should deploy: {blocking(checks)}"
        else:
            assert t.status == AVAILABLE
            assert not deployable(checks)
            assert [c.key for c in blocking(checks)] == [CHK_CONTRACT]


def test_certification_gates_never_block_a_deploy():
    """A draft with no owner and no validator is what the scaffolding CLI
    registers today. If those refusals blocked the deploy, the CLI and this
    screen would disagree about what a new agent looks like on day one."""
    _spec, checks = validate_text(to_yaml(get_template("validation")))
    refused = {c.key for c in checks if c.verdict == REFUSED}
    assert {CHK_OWNER, CHK_SOD} <= refused
    assert deployable(checks)
    assert not (refused & DEPLOY_BLOCKING)


def test_self_signoff_is_refused_but_still_deployable():
    text = (
        to_yaml(get_template("validation"))
        .replace('owner: "UNASSIGNED"', 'owner: "Dana Okafor"')
        .replace("validator: null", 'validator: "Dana Okafor"')
    )
    _spec, checks = validate_text(text)
    sod = _checks_by_key(checks)[CHK_SOD]
    assert sod.verdict == REFUSED
    assert "CTL-SOD-01" in sod.refusals[0].control
    assert deployable(checks)


# --------------------------------------------------------------------------
# Every check can be made to fail
# --------------------------------------------------------------------------
_BASE = "validation"

_MUTATIONS = [
    (CHK_IMPORTS, '"fairlearn.metrics"', '"requests"'),
    (CHK_PURPOSES, '["fair_lending"]', '["marketing"]'),
    (CHK_TIER, 'max_tier: "L2"', 'max_tier: "L3"'),
    (CHK_TOOLS, '"compute_fairness"', '"exfiltrate_everything"'),
    (CHK_PATTERN, 'pattern: "evaluator_optimizer"', 'pattern: "vibes"'),
    (CHK_COLUMNS, '"digital_engagement_score"', '"applicant_ssn"'),
    (CHK_CONTRACT, '"german_credit"', '"acme_internal"'),
    (CHK_SCHEMA, 'owner: "UNASSIGNED"', 'status: "certified"\nowner: "UNASSIGNED"'),
]


@pytest.mark.parametrize(("key", "old", "new"), _MUTATIONS, ids=[m[0] for m in _MUTATIONS])
def test_each_policy_check_refuses_its_own_violation(key, old, new):
    text = to_yaml(get_template(_BASE))
    assert old in text, f"fixture drifted: {old!r} is no longer in the document"
    mutated = text.replace(old, new)
    checks = _checks_by_key(validate_text(mutated)[1])
    assert checks[key].verdict == REFUSED, f"{key} did not refuse {new}"
    assert not deployable(validate_text(mutated)[1])


def test_a_template_may_not_pin_a_content_sha():
    """A SHA is a fact about one snapshot of a file. A blueprint pinning one
    would be claiming every instance runs against today's data; deploy computes
    it instead."""
    text = to_yaml(get_template(_BASE)).replace('"german_credit"', '"german_credit@sha:188808"')
    contract = _checks_by_key(validate_text(text)[1])[CHK_CONTRACT]
    assert contract.verdict == REFUSED
    assert any("sha" in o.subject for o in contract.refusals)


def test_imports_are_refused_at_a_tier_that_writes_no_code():
    text = to_yaml(get_template(_BASE)).replace('max_tier: "L2"', 'max_tier: "L1"')
    imports = _checks_by_key(validate_text(text)[1])[CHK_IMPORTS]
    assert imports.verdict == REFUSED
    assert "writes no code" in imports.refusals[0].reason


def test_l3_widens_the_import_allowlist():
    """`itertools` is refused at L2 and allowed at L3. The tier is read from the
    document, so the same import list rules differently on different tiers."""
    base = to_yaml(get_template(_BASE)).replace('"fairlearn.metrics"', '"itertools"')
    assert _verdict(base, CHK_IMPORTS) == REFUSED
    l3 = base.replace('max_tier: "L2"', 'max_tier: "L3"').replace(
        '"german_credit"', '"synthetic_its"'
    )
    assert _verdict(l3, CHK_IMPORTS) == CLEARED


def test_eval_floor_may_not_be_lowered_below_the_certification_floor():
    text = to_yaml(get_template(_BASE)).replace("floor: 0.9", "floor: 0.5")
    evals = _checks_by_key(validate_text(text)[1])[CHK_EVALS]
    assert evals.verdict == REFUSED
    # Not a deploy blocker: it is certification gate 1.
    assert deployable(validate_text(text)[1])


def test_an_owner_that_is_a_team_is_refused():
    text = to_yaml(get_template(_BASE)).replace(
        'owner: "UNASSIGNED"', 'owner: "Risk Analytics Team"'
    )
    owner = _checks_by_key(validate_text(text)[1])[CHK_OWNER]
    assert owner.verdict == REFUSED
    assert "team" in owner.refusals[0].reason


# --------------------------------------------------------------------------
# The fourth verdict: armed, unarmed, and nothing to read
# --------------------------------------------------------------------------
def test_column_check_is_armed_only_where_a_grant_exists():
    """fair_lending is the one purpose with a column grant in this build. On any
    other purpose the check is unarmed, which is a gap in the policy rather than
    a clean bill of health, and must not paint green."""
    armed = _checks_by_key(validate_text(to_yaml(get_template("validation")))[1])
    assert armed[CHK_COLUMNS].verdict == CLEARED

    unarmed = _checks_by_key(validate_text(to_yaml(get_template("data_analysis")))[1])
    assert unarmed[CHK_COLUMNS].verdict == NOT_ARMED


def test_a_missing_contract_leaves_three_checks_unable_to_read():
    """Purpose, tier and column all resolve through the dataset, so a document
    with no contract disarms them. Reporting that as three passes would be the
    exact lie the four verdicts exist to prevent."""
    checks = _checks_by_key(validate_text(to_yaml(get_template("retrieval_qa")))[1])
    assert checks[CHK_CONTRACT].verdict == REFUSED
    for key in (CHK_PURPOSES, CHK_TIER, CHK_COLUMNS):
        assert checks[key].verdict == NOT_ARMED


def test_no_check_reports_cleared_without_reading_something():
    for t in all_templates():
        for c in validate_text(to_yaml(t))[1]:
            if c.verdict == CLEARED:
                assert c.examined > 0, f"{t.id}/{c.key} cleared having judged nothing"


# --------------------------------------------------------------------------
# Deploy
# --------------------------------------------------------------------------
def test_deploy_registers_a_draft_with_a_computed_sha(clean_registry):
    t = get_template("validation")
    spec, checks = validate_text(to_yaml(t).replace('id: "validation"', 'id: "fl-review"'))
    result = deploy(spec, checks, author="sandip.dev")

    assert result.decision.status == STATUS_DRAFT
    assert certification.get_entry("fl-review") is not None
    # The SHA is computed at deploy from the real file, not copied from the doc.
    dataset, sha = parse_contract(result.contract)
    assert dataset == "german_credit"
    assert sha and sha == certification.parse_contract("german_credit@sha:188808")[1]
    # Gate 1 fails because no eval cases exist yet, exactly as the scaffold
    # leaves a new agent.
    assert result.entry.eval_suite_ref is None
    assert "cannot reach 'certified'" in result.report()


def test_deploy_carries_owner_and_validator_through(clean_registry):
    text = (
        to_yaml(get_template("validation"))
        .replace('id: "validation"', 'id: "fl-review-owned"')
        .replace('owner: "UNASSIGNED"', 'owner: "Dana Okafor"')
        .replace("validator: null", 'validator: "sam.mendes"')
    )
    spec, checks = validate_text(text)
    result = deploy(spec, checks, author="sandip.dev")
    assert result.entry.owner == "Dana Okafor"
    assert result.entry.owner_is_person
    assert result.entry.validator == "sam.mendes"
    # Only the eval gate is left, so the report names one blocker and not three.
    assert [g.name for g in result.decision.blocking] == ["eval suite passes"]


def test_deploy_is_refused_when_a_policy_check_refused(clean_registry):
    text = to_yaml(get_template("validation")).replace('"fairlearn.metrics"', '"socket"')
    spec, checks = validate_text(text)
    with pytest.raises(DeployRefused, match="Import allow-list"):
        deploy(spec, checks, author="x")
    assert certification.get_entry("validation") is None


def test_deploy_refuses_a_duplicate_id(clean_registry):
    spec, checks = validate_text(
        to_yaml(get_template("validation")).replace('id: "validation"', 'id: "dupe-me"')
    )
    deploy(spec, checks, author="x")
    with pytest.raises(DeployRefused, match="already in the registry"):
        deploy(spec, checks, author="x")


# --------------------------------------------------------------------------
# The nav, and the count the manual reads off it
# --------------------------------------------------------------------------
def test_agent_templates_sits_in_governance_between_datasets_and_registry():
    from sentinel.ui.nav import NAV_GROUPS, SECTION_TEMPLATES

    governance = next(items for group, items in NAV_GROUPS if group == "Governance")
    assert governance == ["Datasets", SECTION_TEMPLATES, "Registry"]


def test_the_manual_reads_its_screen_count_rather_than_stating_one():
    """The screens chapter opened with a hand-typed "Nine screens" that a tenth
    nav item silently falsified. Both numbers come off the nav now, so this
    fails if anyone types one back in."""
    import re
    from pathlib import Path

    from sentinel.ui.nav import product_screens, screen_count

    assert screen_count() == len(product_screens())
    source = Path("sentinel/ui/manual.py").read_text()
    written_out = r"\b(nine|ten|eleven|twelve|thirteen)\s+screens\b"
    assert not re.search(written_out, source, re.IGNORECASE), (
        "manual.py names a screen count in prose. Call screen_count() instead: "
        "a typed count goes stale the moment a nav item is added, and nothing fails."
    )


def test_help_screens_are_not_counted_as_product_screens():
    """The manual, the FAQ and Ask me are the manual describing itself. Counting
    them would tell a reader there are three more places to do work."""
    from sentinel.ui.nav import nav_items, product_screens

    assert set(product_screens()) < set(nav_items())
    for help_screen in ("User Manual", "FAQ", "Ask me"):
        assert help_screen in nav_items()
        assert help_screen not in product_screens()


def test_deploying_onto_a_seeded_id_is_refused(clean_registry):
    """fair-lending is already certified in the seeded registry. Deploying a
    draft over it would put two rows with one id in the inventory."""
    spec, checks = validate_text(
        to_yaml(get_template("validation")).replace('id: "validation"', 'id: "fair-lending"')
    )
    with pytest.raises(DeployRefused, match="already in the registry"):
        deploy(spec, checks, author="x")
