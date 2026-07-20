"""Parent-side sandbox: spawn the runner, cap it, collect the result (Stage 6).

The wall-clock cap (CTL-TIME-01) is enforced here with a subprocess timeout,
which is the portable mechanism that always works. Memory and CPU caps are set
inside the child as a backstop. The result travels back as a pickle file so a
DataFrame or dict emitted by the analysis survives the process boundary.
"""

from __future__ import annotations

import math
import pickle
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

CTL_TIME_01 = "CTL-TIME-01"

# 10.0 until 2026-07-20, when the L2 allowlist gained shap, dowhy and econml.
# The sandbox is a fresh subprocess per run, so importing what the allowlist
# grants is charged to every analysis before a line of it executes: measured
# warm on a 2026 MacBook, 0.66s of bare subprocess overhead, 1.0s with pandas,
# 4.2-4.6s with shap, and a t3.small is slower than that. A 10s budget was
# therefore close to firing on the imports rather than on the analysis.
#
# This control exists to stop runaway generated code. An infinite loop dies at
# 30s exactly as it dies at 10s; what changes is that the cap stops firing for
# a reason that has nothing to do with the code it is judging. Widening the
# allowlist widened this: an import grant is also a time budget.
DEFAULT_WALL_CLOCK_S = 30.0
DEFAULT_MEMORY_MB = 1024

# What the governed routes actually pass. Both `govflow/flow.py` (L2) and
# `govflow/l3.py` (L3) ran on a bare `wall_clock_s=15` literal, duplicated, with
# the default above documented everywhere as though it were the operative
# number. It is not: it is the fallback for a caller that names none, and the
# two callers that matter both name one. Their analyses are small and bounded,
# so they can afford a tighter cap than a generic sandbox invocation.
#
# Named here rather than typed twice because the User Manual and the Execute
# panel both have to state this number, and a magic literal in two call sites
# is a number no surface can read without guessing which one is authoritative.
GOVFLOW_WALL_CLOCK_S = 15.0


@dataclass
class ExecutionResult:
    """What the sandbox returns to the orchestrator."""

    ok: bool
    emitted: Any = None
    has_emitted: bool = False
    error: str | None = None
    control: str | None = None  # set to CTL-TIME-01 on a wall-clock kill
    wall_clock_s: float = 0.0
    traceback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        emitted = self.emitted
        # Keep the public payload JSON-friendly; a DataFrame becomes records.
        if isinstance(emitted, pd.DataFrame):
            emitted = emitted.to_dict(orient="records")
        return {
            "ok": self.ok,
            "has_emitted": self.has_emitted,
            "error": self.error,
            "control": self.control,
            "wall_clock_s": round(self.wall_clock_s, 3),
            "emitted": emitted,
        }


def run_sandboxed(
    code: str,
    tables: dict[str, pd.DataFrame] | None = None,
    params: dict[str, Any] | None = None,
    *,
    granted_columns: list[str] | None = None,
    row_filter_sql: str = "",
    wall_clock_s: float = DEFAULT_WALL_CLOCK_S,
    memory_mb: int | None = DEFAULT_MEMORY_MB,
    cpu_s: int | None = None,
) -> ExecutionResult:
    """Run gated code in an isolated subprocess and return what it emitted.

    Assumes `code` already passed the gate; this runs it, it does not re-check
    it. A wall-clock overrun is reported as CTL-TIME-01. A crash (including a
    memory-limit kill the OS honored) is reported as a non-ok result with the
    process detail. `granted_columns` and `row_filter_sql` back the ctx.sql path
    inside the child (the runtime backstop and the injected identity filter).
    """
    job = {
        "code": code,
        "tables": tables or {},
        "params": params or {},
        "granted_columns": granted_columns,
        "row_filter_sql": row_filter_sql,
        "memory_mb": memory_mb,
        # CPU backstop a couple seconds past the wall clock, so the wall-clock
        # timeout is what normally fires.
        "cpu_s": cpu_s if cpu_s is not None else math.ceil(wall_clock_s) + 2,
    }

    with tempfile.TemporaryDirectory(prefix="sentinel-sbx-") as d:
        job_path = Path(d) / "job.pkl"
        result_path = Path(d) / "result.pkl"
        with open(job_path, "wb") as f:
            pickle.dump(job, f)

        cmd = [sys.executable, "-m", "sentinel.sandbox.runner", str(job_path), str(result_path)]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=wall_clock_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                ok=False,
                error=f"wall-clock cap of {wall_clock_s}s exceeded; process killed",
                control=CTL_TIME_01,
                wall_clock_s=wall_clock_s,
            )
        elapsed = time.monotonic() - start

        if not result_path.exists():
            # Runner died before writing a result (e.g. OS killed it on the
            # memory cap). Report the process detail rather than pretend success.
            detail = (proc.stderr or "").strip().splitlines()[-1:] or ["no output"]
            return ExecutionResult(
                ok=False,
                error=(
                    f"sandbox process exited rc={proc.returncode} without a result "
                    f"(likely a resource limit): {detail[0]}"
                ),
                wall_clock_s=elapsed,
            )

        with open(result_path, "rb") as f:
            payload = pickle.load(f)

        return ExecutionResult(
            ok=bool(payload.get("ok")),
            emitted=payload.get("emitted"),
            has_emitted=bool(payload.get("has_emitted")),
            error=payload.get("error"),
            traceback=payload.get("traceback"),
            wall_clock_s=elapsed,
        )
