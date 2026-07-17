"""The scaffolding path (section 10.6): the only way to make an agent, and it
starts at draft. Files are written under a tmp base_dir so the working tree is
never touched, and entries are not registered globally unless asked.
"""

from __future__ import annotations

import pytest

from sentinel.cli import main
from sentinel.platform.certification import STATUS_DRAFT
from sentinel.platform.scaffold import ScaffoldError, scaffold_agent


def test_scaffold_writes_three_files(tmp_path):
    result = scaffold_agent(
        "cohort-retention", "read-only-analysis", base_dir=tmp_path, register_entry=False
    )
    assert len(result.files_created) == 3
    assert (tmp_path / "sentinel" / "analyses" / "specs" / "cohort_retention.yaml").exists()
    assert (tmp_path / "tests" / "test_cohort_retention.py").exists()
    assert (tmp_path / "evals" / "cohort_retention.yaml").exists()


def test_scaffolded_agent_starts_at_draft(tmp_path):
    result = scaffold_agent("new-thing", base_dir=tmp_path, register_entry=False)
    assert result.decision.status == STATUS_DRAFT
    assert result.entry.owner == "UNASSIGNED"
    # It cannot be certified: the report names the missing gates.
    assert not result.decision.certifiable
    report = result.report()
    assert "cannot reach 'certified'" in report
    assert "owner is a person" in report


def test_unknown_template_is_refused(tmp_path):
    with pytest.raises(ScaffoldError):
        scaffold_agent("x", "no-such-template", base_dir=tmp_path, register_entry=False)


def test_slug_normalizes_name(tmp_path):
    result = scaffold_agent("My Cool-Agent", base_dir=tmp_path, register_entry=False)
    # id keeps the human name; files use the python-safe slug.
    assert result.entry.id == "My Cool-Agent"
    assert (tmp_path / "tests" / "test_my_cool_agent.py").exists()


def test_cli_new_agent_writes_and_reports(tmp_path, capsys):
    rc = main(["new-agent", "billing-drift", "--into", str(tmp_path), "--author", "ana"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "status=draft" in out
    assert "owner=UNASSIGNED" in out
    assert (tmp_path / "evals" / "billing_drift.yaml").exists()


def test_cli_registry_lists_status(capsys):
    rc = main(["registry"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "certified" in out and "fair-lending" in out
    assert "refused" in out and "cohort-retention" in out


def test_cli_certify_refuses_self_signoff(capsys):
    # deposit-elasticity's author is marcus.lee; assigning him as validator is
    # refused by CTL-SOD-01 (exit 1), and does not mutate the entry.
    rc = main(["certify", "deposit-elasticity", "--validator", "marcus.lee"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "CTL-SOD-01" in err
