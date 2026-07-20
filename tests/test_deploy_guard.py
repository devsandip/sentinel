"""The deploy guard that refuses to ship a tree main has not seen.

`deploy.sh` builds its bundle with `zip`, which walks the filesystem, so the
artifact is the working tree and not `HEAD`. On 2026-07-20 this repo's primary
checkout sat on `main` at exactly `origin/main` with a full revert of three
merges staged in its index, and every check in use at the time passed it. The
bundle would have gone Green without the changes it was meant to carry.

The guard is shell, so these tests slice it out of `deploy.sh` and run it in a
throwaway repo. That means the tests exercise the shipped code rather than a
copy of it, and the slice fails loudly if either anchor line moves.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SH = REPO_ROOT / "deploy" / "aws" / "deploy.sh"

# The guard runs between these two lines. Anchored on content rather than line
# numbers, so an edit above it does not silently shift the slice.
_START = 'echo "==> Checking the tree being zipped is what origin/main says it is"'
_END = "# Guard: prod installs from requirements.txt"


def _guard_script() -> str:
    lines = DEPLOY_SH.read_text().splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == _START]
    ends = [i for i, ln in enumerate(lines) if ln.startswith(_END)]
    assert len(starts) == 1, f"expected one guard start line in deploy.sh, found {len(starts)}"
    assert ends, "the requirements guard that terminates the slice is gone from deploy.sh"
    end = next(i for i in ends if i > starts[0])
    return "set -euo pipefail\n" + "\n".join(lines[starts[0] : end]) + "\n"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A clean checkout on main, with an origin whose main matches HEAD."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    init = ["git", "init", "-b", "main"]
    subprocess.run([*init, "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run([*init, str(work)], check=True, capture_output=True)
    _git("config", "user.email", "t@example.com", cwd=work)
    _git("config", "user.name", "T", cwd=work)
    (work / "app.py").write_text("x = 1\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-q", "origin", "main", cwd=work)
    (tmp_path / "guard.sh").write_text(_guard_script())
    return work


def _run(checkout: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(checkout.parent / "guard.sh")],
        cwd=checkout,
        capture_output=True,
        text=True,
    )


def test_a_clean_checkout_on_main_deploys(checkout: Path) -> None:
    r = _run(checkout)
    assert r.returncode == 0, r.stderr
    assert "clean, and HEAD is on origin/main" in r.stdout


def test_a_staged_revert_on_the_right_commit_is_refused(checkout: Path) -> None:
    """The 2026-07-20 near-miss, reproduced.

    HEAD is exactly origin/main, so the ancestor clause passes. The tree is not,
    which is the whole point: `zip` would have shipped this."""
    (checkout / "app.py").write_text("")
    _git("add", "-A", cwd=checkout)

    r = _run(checkout)
    assert r.returncode == 1
    assert "DIRTY" in r.stderr
    assert "app.py" in r.stderr


def test_an_untracked_module_is_refused(checkout: Path) -> None:
    """A new file under a zipped path ships without ever being in git."""
    (checkout / "brand_new.py").write_text("import os\n")

    r = _run(checkout)
    assert r.returncode == 1
    assert "brand_new.py" in r.stderr


def test_a_commit_main_has_not_seen_is_refused(checkout: Path) -> None:
    (checkout / "app.py").write_text("x = 2\n")
    _git("commit", "-am", "unreviewed", cwd=checkout)

    r = _run(checkout)
    assert r.returncode == 1
    assert "NOT an ancestor" in r.stderr


def test_being_behind_main_is_allowed(checkout: Path) -> None:
    """Behind is not the failure mode this guard exists for.

    An older commit is still a commit main has reviewed. Refusing it would block
    a deliberate rollback, which is the one deploy you least want to argue with."""
    _git("commit", "--allow-empty", "-m", "later", cwd=checkout)
    _git("push", "-q", "origin", "main", cwd=checkout)
    _git("checkout", "-q", "HEAD~1", cwd=checkout)

    r = _run(checkout)
    assert r.returncode == 0, r.stderr


def test_the_guard_names_both_clauses_in_deploy_sh() -> None:
    """The comment is the only place the reasoning survives; keep it load-bearing."""
    text = DEPLOY_SH.read_text()
    assert "git status --porcelain" in text
    assert "merge-base --is-ancestor" in text
    assert "working TREE" in text, "the comment must say why HEAD is the wrong noun"
