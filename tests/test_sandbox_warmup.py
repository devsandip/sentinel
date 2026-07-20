"""The sandbox bytecode warm-up (sentinel/sandbox/warmup.py).

The wall clock is a real control: it stops runaway generated code. It is only a
real control if it fires for that reason. A cold `import shap` costs 15s or more
against a 10s wall clock (numbers in the module docstring), so a fresh instance
would kill the first shap analysis and log CTL-TIME-01 against code that had
done nothing wrong. The warm-up pays that cost at boot instead.

What is worth testing here is the contract, not the timing: the warmed set
tracks the allowlist, it runs at most once, and it stays out of the way under
pytest.
"""

from __future__ import annotations

import sys

from sentinel.codegen.allowlist import ALLOWED_IMPORTS, L3_ALLOWED_IMPORTS
from sentinel.sandbox import warmup


def test_warms_every_third_party_package_the_gate_can_approve():
    """A package granted later is warmed without anyone remembering to add it."""
    warmed = set(warmup._modules_to_warm())
    granted_roots = {m.split(".", 1)[0] for m in ALLOWED_IMPORTS | L3_ALLOWED_IMPORTS}
    third_party = {r for r in granted_roots if r not in sys.stdlib_module_names}
    assert warmed == third_party
    # The slow ones are the reason this module exists.
    assert {"shap", "econml", "dowhy", "lifelines", "statsmodels"} <= warmed


def test_stdlib_is_not_warmed():
    """Warming stdlib would be work for nothing; it is loaded already."""
    warmed = set(warmup._modules_to_warm())
    assert not warmed & set(sys.stdlib_module_names)


def test_disabled_under_pytest():
    """Inert here, so the AppTest suite does not spawn a subprocess per boot."""
    assert warmup.is_disabled()
    assert warmup.start_background_warmup() is False


def test_disabled_by_environment(monkeypatch):
    monkeypatch.setenv("SENTINEL_NO_WARMUP", "1")
    assert warmup.is_disabled()


def test_runs_at_most_once(monkeypatch):
    """Streamlit re-executes app.py on every interaction; the warm-up must not
    re-run on each one. The guard is module state, so it survives a rerun."""
    calls: list[list[str]] = []
    monkeypatch.setattr(warmup, "_started", False)
    monkeypatch.setattr(warmup, "is_disabled", lambda: False)
    monkeypatch.setattr(
        warmup.threading,
        "Thread",
        lambda target, args, name, daemon: type(
            "FakeThread", (), {"start": lambda self: calls.append(args[0])}
        )(),
    )
    assert warmup.start_background_warmup() is True
    assert warmup.start_background_warmup() is False
    assert len(calls) == 1
    assert "shap" in calls[0]


def test_a_missing_package_does_not_crash_the_warmup(monkeypatch):
    """Best effort by design: a package that fails to import is skipped, because
    test_allowlist_env.py is what fails loudly on a missing grant, at the right
    time and with the right message."""
    warmup._warm(["definitely_not_a_real_module_xyz"])  # must not raise
