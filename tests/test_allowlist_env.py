"""The allowlist is reconciled against the environment that has to honour it.

Found 2026-07-20 by a cold-visit audit of the live site: the L2 allowlist
advertised statsmodels, lifelines, shap, dowhy and econml, and none of the five
were in `requirements.txt`. The allowlist is fed verbatim to the model in the
codegen system prompt, so every name on it is an instruction to use that
package. The result was a gate that stamped "imports on the tier's allowlist,
clear" over code the sandbox then killed with ModuleNotFoundError. The crash is
the small half. The governance half is that a control approved something the
environment refuses, which is not a control that held, it is a control that
guessed.

`requirements.txt` is the target rather than the local virtualenv on purpose:
it is the artifact the instance pip-installs, and a local env hides this defect
precisely when it matters, by carrying packages transitively that prod does not.

This is the third dependency list in the repo (pyproject/uv.lock, requirements.txt,
and this allowlist). The deploy script already diffs the first two. This diffs
the third against them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

from sentinel.codegen.allowlist import ALLOWED_IMPORTS, L3_ALLOWED_IMPORTS

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

# Import root -> the distribution that provides it on PyPI. Every non-stdlib root
# on either allowlist must appear here, so granting a new import is a deliberate
# act that names what has to be installed for it.
DISTRIBUTION_FOR_ROOT: dict[str, str] = {
    "pandas": "pandas",
    "numpy": "numpy",
    "scipy": "scipy",
    "sklearn": "scikit-learn",
    "statsmodels": "statsmodels",
    "fairlearn": "fairlearn",
}


def _root(module: str) -> str:
    return module.split(".", 1)[0]


def _declared_distributions() -> set[str]:
    """Distribution names pinned in requirements.txt, normalised per PEP 503."""
    names: set[str] = set()
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>!~\[; ]", line, maxsplit=1)[0].strip()
        if name:
            names.add(re.sub(r"[-_.]+", "-", name).lower())
    return names


def _third_party_roots() -> set[str]:
    """Non-stdlib import roots granted at either tier."""
    roots = {_root(m) for m in (ALLOWED_IMPORTS | L3_ALLOWED_IMPORTS)}
    return {r for r in roots if r not in sys.stdlib_module_names}


def test_every_granted_root_names_a_distribution():
    """A new allowlist entry must say what installs it, or this fails."""
    unmapped = _third_party_roots() - set(DISTRIBUTION_FOR_ROOT)
    assert not unmapped, (
        f"allowlisted imports with no known distribution: {sorted(unmapped)}. "
        "Add them to DISTRIBUTION_FOR_ROOT, and to the dependencies, before granting them."
    )


@pytest.mark.parametrize("root", sorted(_third_party_roots()))
def test_granted_import_is_installed_in_prod(root: str):
    """Every package the allowlist grants is pinned in what prod installs."""
    dist = DISTRIBUTION_FOR_ROOT[root]
    declared = _declared_distributions()
    assert re.sub(r"[-_.]+", "-", dist).lower() in declared, (
        f"the allowlist grants '{root}' but '{dist}' is not in requirements.txt. "
        "The gate would clear code importing it and the sandbox would then die "
        "with ModuleNotFoundError. Add the dependency or drop the grant."
    )


@pytest.mark.parametrize("root", sorted(_third_party_roots()))
def test_granted_import_actually_imports(root: str):
    """And it resolves here too, so the gate's verdict holds where tests run.

    A hard failure rather than an importorskip: a skip is the silent pass this
    whole module exists to remove.
    """
    assert importlib.util.find_spec(root) is not None, (
        f"the allowlist grants '{root}' but it does not import in this environment. "
        "Run `uv sync --extra dev --extra pgvector --extra live`."
    )


def test_stdlib_grants_are_really_stdlib():
    """L3 grants bare stdlib names; a typo there would be silently unenforceable."""
    stdlib_grants = {_root(m) for m in L3_ALLOWED_IMPORTS} & sys.stdlib_module_names
    assert "statistics" in stdlib_grants and "math" in stdlib_grants
