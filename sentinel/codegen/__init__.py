"""Governed code generation (the v1 vertical slice).

This package is the fence around L2 autonomy: a data scientist may write Python
against an allowlisted API, and nothing runs until a static gate has read the
code and judged its intent. See docs/features/governed-codegen.md sections 5
(the request lifecycle), 6 (the allowlisted `ctx` API), and 14 (v1 scope).

Modules:
  allowlist -- the L2 import allowlist and the denied-module -> control mapping.
  gate      -- the `ast` walker that refuses code before execution, naming the
               control and the line (CTL-CODE-01..04, CTL-EGRESS-01, CTL-COL-01).

`ctx.sql` and its sqlglot gate are deferred to v2; v1 fences the DataFrame API
only (`ctx.table`, `ctx.param`, `ctx.emit`).
"""

from __future__ import annotations

from .gate import GateResult, Violation, gate_code

__all__ = ["GateResult", "Violation", "gate_code"]
