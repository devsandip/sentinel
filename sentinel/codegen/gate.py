"""The static gate: read the code before the machine does (section 5, Stage 5).

The gate parses generated Python with the stdlib `ast` and walks it. It never
imports, never executes, never `eval`s. It answers one question in language a
control tester can read: what did this code intend, and is any of it refused.

A gate tells you what was intended before it happens; a sandbox tells you what
happened after. Both are needed; this is the one that is demonstrable. The v1
done-when turns on it: a generated webhook call is caught here as CTL-EGRESS-01
and never reaches the sandbox.

Two parsers, not one (section 5, Stage 5). This module runs the Python `ast`
half; when it finds a `ctx.sql(<literal>)` call it hands the literal to the
sqlglot half (sql_gate.py) and stamps the Python line of the call onto each SQL
violation, so the Gate screen still reads top to bottom. A `ctx.sql` argument
that is not a static string literal is refused: the gate cannot verify columns in
SQL it cannot read.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, field

from .allowlist import (
    CTL_CODE_00,
    CTL_CODE_02,
    CTL_CODE_03,
    CTL_CODE_04,
    CTL_COL_01,
    DUNDER_ESCAPES,
    DYNCODE_BUILTINS,
    import_verdict,
    name_verdict,
    open_mode_is_write,
)
from .sql_gate import gate_sql

_CONTROL_MESSAGES = {
    "CTL-CODE-00": "generated code does not parse",
    "CTL-CODE-01": "import is not on the L2 allowlist",
    "CTL-CODE-02": "filesystem or process access is not permitted at L2",
    "CTL-CODE-03": "dynamic code execution or unsafe deserialization is not permitted",
    "CTL-CODE-04": "attribute access escapes the sandbox object graph",
    "CTL-EGRESS-01": "network egress is not permitted; no network module may be referenced",
    "CTL-COL-01": "column is not in the grant for this purpose",
    "CTL-PURP-01": "table is not in scope for this purpose",
    "CTL-COMPLEX-01": "query is too complex (Cartesian join or too many joins)",
}


@dataclass(frozen=True)
class Violation:
    """One refusal: which control fired, on which line, and why."""

    control: str
    line: int
    detail: str  # the specific offending name/column

    @property
    def message(self) -> str:
        base = _CONTROL_MESSAGES.get(self.control, "policy violation")
        return f"{self.control} (line {self.line}): {base} -- {self.detail}"


@dataclass(frozen=True)
class GateResult:
    """The gate's verdict on one code string."""

    passed: bool
    violations: list[Violation] = field(default_factory=list)

    @property
    def controls_fired(self) -> list[str]:
        # Deduped, in the order first seen.
        seen: list[str] = []
        for v in self.violations:
            if v.control not in seen:
                seen.append(v.control)
        return seen

    def refusal_summary(self) -> str:
        if self.passed:
            return "Gate passed: no violations."
        lines = [v.message for v in self.violations]
        return "Gate blocked:\n" + "\n".join(f"  - {m}" for m in lines)

    def feedback_for_regeneration(self) -> str:
        """A terse instruction the model can act on to regenerate (Stage 5 loop)."""
        if self.passed:
            return ""
        return "The gate refused this code. Fix each and regenerate:\n" + "\n".join(
            f"  - {v.message}" for v in self.violations
        )


class _GateVisitor(ast.NodeVisitor):
    """Collects violations. One pass; table-variable tracking is done up front."""

    def __init__(
        self,
        granted_columns: set[str],
        table_vars: set[str],
        allowed_tables: set[str] | None,
        join_ceiling: int,
    ) -> None:
        self.granted_columns = granted_columns
        self.table_vars = table_vars
        self.allowed_tables = allowed_tables
        self.join_ceiling = join_ceiling
        self.violations: list[Violation] = []

    def _add(self, control: str, line: int, detail: str) -> None:
        self.violations.append(Violation(control=control, line=line, detail=detail))

    # -- imports (CTL-CODE-01/02/03, CTL-EGRESS-01) ------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            verdict = import_verdict(alias.name)
            if verdict is not None:
                self._add(verdict, node.lineno, f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # Relative import (level > 0) has no resolvable module; import_verdict
        # treats an empty module as an allowlist miss.
        module = "" if node.level and not node.module else (node.module or "")
        verdict = import_verdict(module)
        if verdict is not None:
            shown = ("." * (node.level or 0)) + (node.module or "")
            self._add(verdict, node.lineno, f"from {shown} import ...")
        self.generic_visit(node)

    # -- bare name references (CTL-EGRESS-01 / CTL-CODE-02/03 without import) --
    def visit_Name(self, node: ast.Name) -> None:
        verdict = name_verdict(node.id)
        if verdict is not None:
            self._add(verdict, node.lineno, node.id)
        self.generic_visit(node)

    # -- calls: eval/exec/compile/__import__, open() write, and ctx.sql(...) --
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in DYNCODE_BUILTINS:
                self._add(CTL_CODE_03, node.lineno, f"{func.id}(...)")
            elif func.id == "open" and self._open_is_write(node):
                self._add(CTL_CODE_02, node.lineno, "open(..., write mode)")
        elif self._is_ctx_sql(func):
            self._gate_ctx_sql(node)
        self.generic_visit(node)

    @staticmethod
    def _is_ctx_sql(func: ast.expr) -> bool:
        return (
            isinstance(func, ast.Attribute)
            and func.attr == "sql"
            and isinstance(func.value, ast.Name)
            and func.value.id == "ctx"
        )

    def _gate_ctx_sql(self, node: ast.Call) -> None:
        """Run the sqlglot half on the literal passed to ctx.sql, stamping the
        Python line of the call onto each SQL violation. A non-literal argument is
        refused: the gate cannot verify columns in SQL it cannot statically read."""
        arg = node.args[0] if node.args else None
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            self._add(
                CTL_COL_01,
                node.lineno,
                "ctx.sql argument must be a static string literal so the gate can read it",
            )
            return
        result = gate_sql(
            arg.value,
            granted_columns=self.granted_columns or None,
            allowed_tables=self.allowed_tables,
            join_ceiling=self.join_ceiling,
        )
        for sv in result.violations:
            self._add(sv.control, node.lineno, f"in ctx.sql: {sv.detail}")

    @staticmethod
    def _open_is_write(node: ast.Call) -> bool:
        # Positional mode is the second arg; keyword is mode=.
        mode_node = None
        if len(node.args) >= 2:
            mode_node = node.args[1]
        for kw in node.keywords:
            if kw.arg == "mode":
                mode_node = kw.value
        if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
            return open_mode_is_write(mode_node.value)
        # No explicit mode -> defaults to read; not a CTL-CODE-02 violation.
        return False

    # -- attribute access: dunder escapes (CTL-CODE-04), columns (CTL-COL-01) --
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in DUNDER_ESCAPES:
            self._add(CTL_CODE_04, node.lineno, f".{node.attr}")
        # Column access as an attribute on a scoped table (df.age_band) is only
        # checkable when we can confirm the base is a table var AND the attr is
        # not a known DataFrame method. That is ambiguous, so attribute-style
        # column access is left to enforcement-by-construction (the ScopedTable
        # simply lacks the column). CTL-COL-01 here checks the unambiguous case:
        # string-literal subscripts, handled in visit_Subscript.
        self.generic_visit(node)

    # -- subscripts: df["col"] against the grant (CTL-COL-01) --------------
    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self.granted_columns and isinstance(node.value, ast.Name):
            if node.value.id in self.table_vars:
                key = _string_const(node.slice)
                if key is not None and key not in self.granted_columns:
                    self._add(CTL_COL_01, node.lineno, f'{node.value.id}["{key}"]')
        self.generic_visit(node)


def _string_const(node: ast.expr) -> str | None:
    """The string value of a constant subscript key, or None if not a str literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_table_vars(tree: ast.AST) -> set[str]:
    """Names bound to the result of `ctx.table(...)`.

    A light, reliable dataflow: only direct assignments `x = ctx.table(...)` are
    tracked, which is how generated analysis code fetches its data. This keeps
    CTL-COL-01's DataFrame check low-false-positive: we only judge column access
    on variables we know are scoped tables.
    """
    table_vars: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_ctx_table_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    table_vars.add(target.id)
    return table_vars


def _is_ctx_table_call(value: ast.expr) -> bool:
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "table"
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id == "ctx"
    )


def gate_code(
    code: str,
    granted_columns: Iterable[str] | None = None,
    allowed_tables: Iterable[str] | None = None,
    join_ceiling: int = 2,
) -> GateResult:
    """Statically gate a generated code string. Never executes it.

    Returns a GateResult naming every control that fired and the line it fired
    on. Pass `granted_columns` to enable the CTL-COL-01 column check (DataFrame
    subscripts and ctx.sql). Pass `allowed_tables` to enable the CTL-PURP-01
    table-scope check inside ctx.sql; omit it to skip that check.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 0
        return GateResult(
            passed=False,
            violations=[Violation(CTL_CODE_00, line, exc.msg or "syntax error")],
        )

    granted = set(granted_columns) if granted_columns is not None else set()
    tables = set(allowed_tables) if allowed_tables is not None else None
    table_vars = _collect_table_vars(tree)
    visitor = _GateVisitor(
        granted_columns=granted,
        table_vars=table_vars,
        allowed_tables=tables,
        join_ceiling=join_ceiling,
    )
    visitor.visit(tree)

    # Stable order: by line, then by control id, so the Gate screen reads top to
    # bottom like the code does.
    violations = sorted(visitor.violations, key=lambda v: (v.line, v.control, v.detail))
    return GateResult(passed=not violations, violations=violations)
