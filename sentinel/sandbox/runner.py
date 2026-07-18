"""The sandbox child entrypoint. Runs one gated code string, then exits.

Invoked as `python -m sentinel.sandbox.runner <job_path> <result_path>`. Reads a
pickled job (code + scoped tables + params + resource caps), sets best-effort
resource limits, execs the code with a `ctx` in scope, and writes back whatever
the code emitted. Never imported by the parent process; it only ever runs as a
fresh subprocess so a runaway analysis cannot take the app down with it.

The parent (execute.py) owns the wall-clock cap via subprocess timeout, which is
the portable, reliable mechanism. This child sets RLIMIT_AS / RLIMIT_CPU as a
backstop where the OS honors them.
"""

from __future__ import annotations

import pickle
import sys
import traceback
from typing import Any

from ..codegen.ctx import Ctx


def _apply_limits(memory_mb: int | None, cpu_s: int | None) -> None:
    """Best-effort resource caps. Silently skipped where unsupported (e.g. some
    macOS RLIMIT_AS behavior); the parent's wall-clock timeout is the real cap."""
    try:
        import resource
    except ImportError:  # non-POSIX
        return
    if memory_mb:
        _try_setrlimit(resource, resource.RLIMIT_AS, memory_mb * 1024 * 1024)
    if cpu_s:
        _try_setrlimit(resource, resource.RLIMIT_CPU, cpu_s)


def _try_setrlimit(resource_mod: Any, which: int, limit: int) -> None:
    try:
        soft, hard = resource_mod.getrlimit(which)
        new_hard = hard if hard != resource_mod.RLIM_INFINITY else limit
        resource_mod.setrlimit(which, (min(limit, new_hard), new_hard))
    except (ValueError, OSError):
        pass


def _run(job: dict[str, Any]) -> dict[str, Any]:
    ctx = Ctx(
        tables=job.get("tables") or {},
        params=job.get("params") or {},
        granted_columns=job.get("granted_columns"),
        row_filter_sql=job.get("row_filter_sql") or "",
    )
    # Imports in the generated code need real builtins (e.g. __import__ to load
    # pandas); the gate, not a stripped namespace, is what refuses dangerous
    # imports. The sandbox only isolates and caps.
    namespace: dict[str, Any] = {"__name__": "__sandbox__", "ctx": ctx}
    # Resource caps go on right before the untrusted code, so the runner's own
    # imports (pickle, pandas via unpickling) are not counted against them.
    _apply_limits(job.get("memory_mb"), job.get("cpu_s"))
    try:
        compiled = compile(job["code"], "<generated>", "exec")
        exec(compiled, namespace)  # noqa: S102 - the whole point; gated upstream
    except BaseException as exc:  # noqa: BLE001 - report any failure to the parent
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "has_emitted": ctx.has_emitted,
            "emitted": ctx.emitted if ctx.has_emitted else None,
        }
    return {
        "ok": True,
        "error": None,
        "has_emitted": ctx.has_emitted,
        "emitted": ctx.emitted,
    }


def main(argv: list[str]) -> int:
    job_path, result_path = argv[1], argv[2]
    with open(job_path, "rb") as f:
        job = pickle.load(f)
    result = _run(job)
    with open(result_path, "wb") as f:
        pickle.dump(result, f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
