"""Governed code generation (the v1 vertical slice).

This package is the fence around L2 autonomy: a data scientist may write Python
against an allowlisted API, and nothing runs until a static gate has read the
code and judged its intent. See docs/features/governed-codegen.md sections 5
(the request lifecycle), 6 (the allowlisted `ctx` API), and 14 (v1 scope).

Modules:
  allowlist -- the L2 import allowlist and the denied-module -> control mapping.
  gate      -- the `ast` walker that refuses code before execution, naming the
               control and the line (CTL-CODE-01..04, CTL-EGRESS-01, CTL-COL-01).
  sql_gate  -- the sqlglot half: gates and rewrites the SQL passed to ctx.sql
               (CTL-COL-01, CTL-PURP-01, CTL-COMPLEX-01), injecting the row filter.

The gate runs both parsers (section 5, Stage 5): `ast` reads the Python, sqlglot
reads the SQL. `ctx.sql` (v2) parses, gates, rewrites, and runs the query on
DuckDB over the scoped tables.
"""

from __future__ import annotations

from .gate import GateResult, Violation, gate_code
from .generate import (
    CodeGenRequest,
    GenerationOutcome,
    generate,
    generate_and_gate,
)
from .sql_gate import SqlGateError, SqlGateResult, SqlViolation, gate_sql, rewrite_sql

__all__ = [
    "CodeGenRequest",
    "GateResult",
    "GenerationOutcome",
    "SqlGateError",
    "SqlGateResult",
    "SqlViolation",
    "Violation",
    "gate_code",
    "gate_sql",
    "generate",
    "generate_and_gate",
    "rewrite_sql",
]
