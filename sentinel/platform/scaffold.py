"""The scaffolding path: the only way to create an analysis-agent (section 10.6).

`sentinel new-agent <name> --template <t>` writes a spec, a test, and an eval
suite, and registers a draft entry with owner UNASSIGNED. The scaffold is the
only path to an agent, which is what makes an ungoverned agent structurally
impossible rather than merely discouraged: a new agent starts at draft and cannot
reach certified until it passes the four gates (section 11), which the scaffold
prints so the author knows what is missing.

The generated files are stubs on purpose: the eval suite has no cases, so the
eval gate fails, so a freshly scaffolded agent cannot be selected by Plan until
someone does the work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .certification import (
    CertificationDecision,
    RegistryEntry,
    evaluate,
    register,
)

TEMPLATES = {
    "read-only-analysis": "A read-only tabular analysis over a scoped table.",
    "fairness-review": "A fair-lending review using fairlearn over a protected attribute.",
}

DEFAULT_TEMPLATE = "read-only-analysis"


class ScaffoldError(Exception):
    """Raised when a scaffold request is invalid (unknown template, bad name)."""


def _slug(name: str) -> str:
    """A python-safe module slug: 'cohort-retention' -> 'cohort_retention'."""
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name.strip())
    return cleaned.replace("-", "_").lower()


@dataclass
class ScaffoldResult:
    name: str
    version: str
    template: str
    files_created: list[Path] = field(default_factory=list)
    entry: RegistryEntry | None = None
    decision: CertificationDecision | None = None

    def report(self) -> str:
        """The CLI's stdout, matching the shape in section 10.6."""
        lines = [f"  created  {p}" for p in self.files_created]
        if self.entry is not None:
            lines.append(
                f"  registry {self.entry.id} v{self.entry.version} "
                f"status={self.decision.status} owner={self.entry.owner}"
            )
        if self.decision is not None and not self.decision.certifiable:
            lines.append("  note     status cannot reach 'certified' until:")
            for g in self.decision.blocking:
                lines.append(f"             - {g.name} (currently: {g.detail})")
        return "\n".join(lines)


def _spec_yaml(name: str, slug: str, template: str, version: str) -> str:
    return (
        f"# Scaffolded by `sentinel new-agent`. Fill in steps and params.\n"
        f"id: {name}\n"
        f"slug: {slug}\n"
        f"version: {version}\n"
        f"template: {template}\n"
        f"engine: linear\n"
        f"status: draft\n"
        f"owner: UNASSIGNED\n"
        f"data_contract: null   # declare <dataset>@sha:<hash> before certification\n"
        f"steps: []             # TODO: define the analysis steps\n"
    )


def _test_py(name: str, slug: str) -> str:
    return (
        f'"""Scaffolded test for the {name!r} analysis-agent. TODO: assert behavior."""\n\n'
        f"import pytest\n\n\n"
        f"@pytest.mark.skip(reason='scaffolded stub: no behavior defined yet')\n"
        f"def test_{slug}_placeholder():\n"
        f"    assert False, 'define {name} behavior and remove the skip'\n"
    )


def _eval_yaml(name: str, slug: str) -> str:
    return (
        f"# Eval suite for {name!r}. The certification eval gate needs cases here\n"
        f"# and a faithfulness score at or above the floor (0.90).\n"
        f"suite: {slug}\n"
        f"floor: 0.90\n"
        f"cases: []   # TODO: add eval cases; an empty suite cannot pass the gate\n"
    )


def scaffold_agent(
    name: str,
    template: str = DEFAULT_TEMPLATE,
    *,
    base_dir: Path,
    version: str = "0.1",
    author: str = "UNKNOWN",
    register_entry: bool = True,
) -> ScaffoldResult:
    """Write the three stub files and produce a draft registry entry.

    `base_dir` is the repo root the files are written under (a tmp dir in tests,
    so the scaffold never pollutes the working tree). `register_entry=False`
    returns the draft entry without appending it to the process registry.
    """
    if template not in TEMPLATES:
        raise ScaffoldError(
            f"unknown template {template!r}; choose one of {sorted(TEMPLATES)}"
        )
    slug = _slug(name)
    if not slug:
        raise ScaffoldError(f"name {name!r} produces an empty slug")

    base = Path(base_dir)
    targets = {
        base / "sentinel" / "analyses" / "specs" / f"{slug}.yaml": _spec_yaml(
            name, slug, template, version
        ),
        base / "tests" / f"test_{slug}.py": _test_py(name, slug),
        base / "evals" / f"{slug}.yaml": _eval_yaml(name, slug),
    }

    created: list[Path] = []
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        created.append(path)

    entry = RegistryEntry(
        id=name,
        version=version,
        author=author,
        owner="UNASSIGNED",
        owner_is_person=False,
        eval_suite_ref=None,  # the stub has no cases; the gate must fail
    )
    if register_entry:
        register(entry)

    return ScaffoldResult(
        name=name,
        version=version,
        template=template,
        files_created=created,
        entry=entry,
        decision=evaluate(entry),
    )
