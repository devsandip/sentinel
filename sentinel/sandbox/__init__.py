"""Subprocess isolation for gated code (section 5, Stage 6).

The gate reads intent before execution; the sandbox bounds what execution can
do. It runs gated code in a separate process with a wall-clock cap (CTL-TIME-01),
a best-effort memory/CPU cap, and no inherited handles beyond the pickled tables
it is given.

Honest limit (Stage 6): a subprocess is not a security boundary against a
determined attacker. It is a boundary against a language model doing something
dumb, which is the actual threat model here. Network egress and filesystem reach
are refused earlier, by the gate, not by an OS namespace. Said out loud rather
than overclaimed.
"""

from __future__ import annotations

from .execute import CTL_TIME_01, ExecutionResult, run_sandboxed

__all__ = ["CTL_TIME_01", "ExecutionResult", "run_sandboxed"]
