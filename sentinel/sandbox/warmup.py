"""Warm the bytecode cache for the packages the allowlist grants.

Why this exists. The sandbox's wall clock is 10s and the sandbox is a fresh
subprocess every run, so the cost of importing a granted package is charged to
every analysis that uses it. `shap` is the expensive one, because it pulls numba
and llvmlite. Measured on a 2026 MacBook, importing it costs:

    48s   first import of five freshly-synced packages, worst case observed
    15.5s first import after a clean install of shap alone
    4.8s  second import (bytecode written, page cache partly warm)
    1.2s  fully warm

Only the last two fit under the wall clock, and a t3.small is slower than the
machine those came from. Without warming, the first generated analysis that
reaches for shap on a fresh instance is killed and the audit log records
`CTL-TIME-01` against code that had done nothing wrong. A control that fires for
an environmental reason is the same defect as a control that clears for one; it
just fails in the safer direction.

The cost is a mix of bytecode compilation and reading a few hundred MB off cold
disk, and both caches live outside the process, which is what makes this work:
warming once in a throwaway subprocess makes every later sandbox subprocess
fast, and the memory numba needs is released when that subprocess exits.
Importing into the Streamlit process instead would hold a few hundred MB of RSS
for the life of an instance with 2GB.

The module list is derived from ALLOWED_IMPORTS rather than hardcoded, so a
package granted later is warmed automatically. `pip install` compiles bytecode
by default (`uv` does not), so a pip-installed instance starts from the 4.8s
case rather than the 15.5s one; this closes the rest of the gap.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from ..codegen.allowlist import L3_ALLOWED_IMPORTS

# Warming is per-interpreter, and the flag is only read and written from the
# main thread's entry point below.
_started = False

# A generous ceiling: this is a background nicety, and a machine slow enough to
# exceed it will not be helped by waiting longer.
_TIMEOUT_S = 300


def _modules_to_warm() -> list[str]:
    """Every third-party module the gate can approve, deduplicated by root.

    L3's list is a superset of L2's. Roots rather than submodules because the
    cost is the package's own import, and stdlib is skipped because it is warm
    already in any process that got this far.
    """
    roots = {m.split(".", 1)[0] for m in L3_ALLOWED_IMPORTS}
    return sorted(r for r in roots if r not in sys.stdlib_module_names)


def _warm(modules: list[str]) -> None:
    # Each import is separate and failure-tolerant: this is a cache warmer, not
    # a dependency check. tests/test_allowlist_env.py is the thing that fails
    # when a granted package is missing, and it fails loudly at the right time.
    src = "\n".join(
        f"try:\n    import {m}\nexcept Exception:\n    pass" for m in modules
    )
    try:
        subprocess.run(
            [sys.executable, "-c", src],
            capture_output=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        pass  # best effort; the sandbox still works, the first run is just slow


def is_disabled() -> bool:
    """True under pytest, or when an operator has switched warming off.

    Inert under pytest on purpose: the AppTest suite boots the app dozens of
    times, and a background subprocess per boot would be pure noise competing
    for CPU with the tests measuring it.
    """
    return bool(os.environ.get("SENTINEL_NO_WARMUP")) or "pytest" in sys.modules


def start_background_warmup() -> bool:
    """Warm the allowlist's bytecode cache once per interpreter, off-thread.

    Returns True if this call started the warm-up, False if it was already
    running, already done, or disabled. A daemon thread so it never holds up
    shutdown, and a subprocess so the memory is not kept.
    """
    global _started
    if _started or is_disabled():
        return False
    _started = True
    threading.Thread(
        target=_warm,
        args=(_modules_to_warm(),),
        name="sentinel-sandbox-warmup",
        daemon=True,
    ).start()
    return True
