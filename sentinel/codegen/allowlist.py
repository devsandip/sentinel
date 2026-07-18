"""The L2 import allowlist and the denied-module -> control mapping.

This is the fence's dictionary. The gate (gate.py) walks generated code; this
module answers the one question the gate asks over and over: is this name
allowed at L2, and if not, which control does it violate.

Source of truth: docs/features/governed-codegen.md section 6. Keep the sets in
sync with that section; a name added here without a doc change is a silent
policy change.
"""

from __future__ import annotations

# -- Control ids (the gate's vocabulary) -----------------------------------
# These name the static-analysis controls in section 5, Stage 5. They are the
# strings that reach the audit log and the Gate screen, so a control tester can
# read them. CTL-SOD-01 (v0) and the disclosure controls (Screen) live
# elsewhere; these are the pre-execution code controls only.
CTL_CODE_01 = "CTL-CODE-01"  # every import is on the allowlist
CTL_CODE_02 = "CTL-CODE-02"  # no filesystem writes, no open() in write mode
CTL_CODE_03 = "CTL-CODE-03"  # no eval/exec/compile/__import__/importlib, no pickle
CTL_CODE_04 = "CTL-CODE-04"  # no dunder-escape attribute access
CTL_EGRESS_01 = "CTL-EGRESS-01"  # no network module referenced at all
CTL_COL_01 = "CTL-COL-01"  # every column literal appears in the grant
# A parse failure is refused before any deeper check: code that will not compile
# cannot be reasoned about, so it never reaches execution.
CTL_CODE_00 = "CTL-CODE-00"  # generated code does not parse

# -- Allowlisted imports at L2 (section 6) ---------------------------------
# A dotted module is allowed if it equals one of these or is a submodule of one
# (e.g. "sklearn.metrics.pairwise" under "sklearn.metrics"). A bare parent whose
# only allowed children are listed (e.g. `import scipy`, `import sklearn`) is NOT
# allowed: the grant is per-submodule on purpose.
ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {
        "pandas",
        "numpy",
        "scipy.stats",
        "statsmodels.api",
        "statsmodels.formula.api",
        "sklearn.metrics",
        "sklearn.linear_model",
        "sklearn.model_selection",
        "fairlearn.metrics",
        "fairlearn.reductions",
        "lifelines",
        "shap",
        "dowhy",
        "econml",
    }
)

# -- Denied, always (section 6). Keyed by root module -> control ------------
# Network egress: the highest-signal block, and the one the v1 done-when turns
# on. Any reference at all, imported or not, is a violation.
EGRESS_MODULES: frozenset[str] = frozenset(
    {
        "requests",
        "urllib",
        "urllib3",
        "http",
        "httpx",
        "aiohttp",
        "socket",
        "ftplib",
        "smtplib",
        "telnetlib",
        "websocket",
        "websockets",
    }
)

# Filesystem and process reach.
FS_MODULES: frozenset[str] = frozenset(
    {"os", "sys", "subprocess", "pathlib", "shutil", "tempfile"}
)

# Dynamic code and unsafe deserialization.
DYNCODE_MODULES: frozenset[str] = frozenset(
    {"importlib", "pickle", "marshal", "ctypes"}
)

# Builtins that execute strings or import dynamically. Flagged when called.
DYNCODE_BUILTINS: frozenset[str] = frozenset(
    {"eval", "exec", "compile", "__import__"}
)

# Attribute names that walk the object graph out of the sandbox. Any access is a
# violation regardless of the object it is read from.
DUNDER_ESCAPES: frozenset[str] = frozenset(
    {
        "__globals__",
        "__subclasses__",
        "__class__",
        "__bases__",
        "__base__",
        "__mro__",
        "__dict__",
        "__builtins__",
        "__code__",
        "__closure__",
        "__reduce__",
        "__reduce_ex__",
        "__getattribute__",
        "__init_subclass__",
    }
)

# Write-mode markers for open(mode=...). Read-only open is not a CTL-CODE-02
# violation by itself (section 6 says "no open in write mode").
_WRITE_MODE_CHARS = frozenset({"w", "a", "x", "+"})


def _root(module: str) -> str:
    """The top-level package of a dotted module path ('urllib.request' -> 'urllib')."""
    return module.split(".", 1)[0] if module else module


def import_verdict(module: str) -> str | None:
    """Return the control a given imported module violates, or None if allowed.

    Denial by category takes precedence over the generic allowlist miss, so
    `import requests` is reported as CTL-EGRESS-01 (what it actually is), not as
    a bland CTL-CODE-01 allowlist miss. A relative import (module is empty)
    cannot be resolved against the allowlist and is refused as CTL-CODE-01.
    """
    root = _root(module)
    if root in EGRESS_MODULES:
        return CTL_EGRESS_01
    if root in FS_MODULES:
        return CTL_CODE_02
    if root in DYNCODE_MODULES:
        return CTL_CODE_03
    if not module:
        return CTL_CODE_01  # relative import; unresolvable against the allowlist
    if any(module == a or module.startswith(a + ".") for a in ALLOWED_IMPORTS):
        return None
    return CTL_CODE_01


def name_verdict(name: str) -> str | None:
    """Return the control a bare name reference violates, or None if benign.

    Catches a denied module used without importing it (the webhook case: bare
    `requests.post(...)` with no `import requests`). Only exact, specific module
    names are matched, so common analysis variables do not trip it.
    """
    if name in EGRESS_MODULES:
        return CTL_EGRESS_01
    if name in FS_MODULES:
        return CTL_CODE_02
    if name in DYNCODE_MODULES:
        return CTL_CODE_03
    return None


def open_mode_is_write(mode: str) -> bool:
    """True if an open() mode string requests write/append/create access."""
    return any(c in _WRITE_MODE_CHARS for c in mode)
