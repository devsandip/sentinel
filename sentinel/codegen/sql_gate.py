"""The SQL half of the gate: read the query before the engine does (Stage 5).

The Python `ast` gate (gate.py) does not understand SQL, and `sqlglot` does not
analyse Python. The gate runs both. This module is the `sqlglot` half: it parses
the string passed to `ctx.sql(...)`, walks the parsed tree, and answers the same
kind of question the Python gate answers, in the same vocabulary a control tester
reads:

  - every column reference resolves to the grant            -> CTL-COL-01
  - no `SELECT *`                                            -> CTL-COL-01
  - every table reference is inside the purpose's scope      -> CTL-PURP-01
  - no join without a condition (Cartesian product), and the
    join count is within a ceiling                          -> CTL-COMPLEX-01

`rewrite_sql` is the governance-by-construction half of `ctx.sql` (section 6): it
injects the identity's row filter into the query after generation and before
execution, so the model never sees the filter and cannot remove it.

SQL has no Python line numbers, so a `SqlViolation` names the offending token.
When the Python gate finds a `ctx.sql(<literal>)` call it runs this gate on the
literal and stamps the Python line of the call onto each SQL violation, so the
Gate screen still reads top to bottom.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from .allowlist import CTL_COL_01, CTL_COMPLEX_01, CTL_PURP_01

# A single-table read of a scoped view needs no joins. A couple are allowed for a
# lookup or a self-join; a Cartesian product is refused at any count.
DEFAULT_JOIN_CEILING = 2

_SQL_CONTROL_MESSAGES = {
    CTL_COL_01: "column is not in the grant, or SELECT * was used",
    CTL_PURP_01: "table is not in scope for this purpose",
    CTL_COMPLEX_01: "query is too complex (Cartesian join or too many joins)",
}


class SqlGateError(Exception):
    """Raised by rewrite_sql when the query does not pass the gate. Carries the
    result so the caller can report which control fired."""

    def __init__(self, result: SqlGateResult) -> None:
        self.result = result
        super().__init__(result.refusal_summary())


@dataclass(frozen=True)
class SqlViolation:
    """One SQL refusal: which control fired and the offending token."""

    control: str
    detail: str

    @property
    def message(self) -> str:
        base = _SQL_CONTROL_MESSAGES.get(self.control, "SQL policy violation")
        return f"{self.control}: {base} -- {self.detail}"


@dataclass(frozen=True)
class SqlGateResult:
    passed: bool
    violations: list[SqlViolation] = field(default_factory=list)

    @property
    def controls_fired(self) -> list[str]:
        seen: list[str] = []
        for v in self.violations:
            if v.control not in seen:
                seen.append(v.control)
        return seen

    def refusal_summary(self) -> str:
        if self.passed:
            return "SQL gate passed: no violations."
        return "SQL gate blocked:\n" + "\n".join(f"  - {v.message}" for v in self.violations)


def _parse(query: str) -> exp.Expression:
    """Parse one statement. A parse failure or a multi-statement string is a
    refusal: the gate cannot reason about what it cannot parse."""
    try:
        statements = sqlglot.parse(query, read="duckdb")
    except Exception as ex:  # noqa: BLE001 - sqlglot raises several parse types
        raise SqlGateError(
            SqlGateResult(False, [SqlViolation(CTL_COL_01, f"SQL does not parse: {ex}")])
        ) from ex
    parsed = [s for s in statements if s is not None]
    if len(parsed) != 1:
        raise SqlGateError(
            SqlGateResult(
                False,
                [SqlViolation(CTL_COL_01, "exactly one SQL statement is allowed")],
            )
        )
    return parsed[0]


def _column_names(tree: exp.Expression) -> list[str]:
    """Every real column reference in the tree, by bare name. Aliases and function
    names are not columns, so `AVG(pred) AS avg_pred` yields only `pred`. A `t.*`
    wildcard is reported by _has_star, not here."""
    return [
        c.name
        for c in tree.find_all(exp.Column)
        if c.name and not isinstance(c.this, exp.Star)
    ]


def _table_names(tree: exp.Expression) -> list[str]:
    return [t.name for t in tree.find_all(exp.Table) if t.name]


def _has_star(tree: exp.Expression) -> bool:
    # A wildcard is a Star *in a projection list*: `SELECT *` (bare Star) or
    # `SELECT t.*` (a Column whose `this` is a Star). A Star that is a function
    # argument, like `COUNT(*)`, is not a wildcard projection and is allowed.
    for select in tree.find_all(exp.Select):
        for proj in select.expressions:
            if isinstance(proj, exp.Star):
                return True
            if isinstance(proj, exp.Column) and isinstance(proj.this, exp.Star):
                return True
    return False


def gate_sql(
    query: str,
    granted_columns: set[str] | None = None,
    allowed_tables: set[str] | None = None,
    join_ceiling: int = DEFAULT_JOIN_CEILING,
) -> SqlGateResult:
    """Statically gate one SQL string. Never executes it.

    `granted_columns` is the column grant for the request; a column outside it
    (or a `SELECT *`) fires CTL-COL-01. `allowed_tables` is the purpose's table
    scope; a table outside it fires CTL-PURP-01. Comparisons are case-insensitive
    so a benign casing difference is not a false block, while a genuinely
    different name is still caught.
    """
    try:
        tree = _parse(query)
    except SqlGateError as ex:
        return ex.result

    violations: list[SqlViolation] = []
    grant = {c.lower() for c in (granted_columns or set())}
    tables_ok = {t.lower() for t in allowed_tables} if allowed_tables is not None else None

    # CTL-COL-01: SELECT * and ungranted columns.
    if _has_star(tree):
        violations.append(SqlViolation(CTL_COL_01, "SELECT * is not permitted"))
    if grant:
        for col in _column_names(tree):
            if col.lower() not in grant:
                violations.append(SqlViolation(CTL_COL_01, f"column {col!r}"))

    # CTL-PURP-01: tables outside the purpose scope.
    if tables_ok is not None:
        for tbl in _table_names(tree):
            if tbl.lower() not in tables_ok:
                violations.append(SqlViolation(CTL_PURP_01, f"table {tbl!r}"))

    # CTL-COMPLEX-01: Cartesian products (a join with neither ON nor USING,
    # including a comma join) and the join-count ceiling.
    joins = list(tree.find_all(exp.Join))
    for j in joins:
        if not j.args.get("on") and not j.args.get("using"):
            violations.append(
                SqlViolation(CTL_COMPLEX_01, "join without a condition (Cartesian product)")
            )
    if len(joins) > join_ceiling:
        violations.append(
            SqlViolation(
                CTL_COMPLEX_01,
                f"{len(joins)} joins exceeds the ceiling of {join_ceiling}",
            )
        )

    # Dedupe while preserving order (a repeated bad column need only be said once).
    unique: list[SqlViolation] = []
    for v in violations:
        if v not in unique:
            unique.append(v)
    return SqlGateResult(passed=not unique, violations=unique)


def rewrite_sql(
    query: str,
    granted_columns: set[str] | None = None,
    allowed_tables: set[str] | None = None,
    row_filter_sql: str = "",
    join_ceiling: int = DEFAULT_JOIN_CEILING,
) -> str:
    """Gate the query, inject the identity row filter, return the runnable SQL.

    Governance by construction: the row filter is AND-combined onto any WHERE the
    model wrote, so the model cannot widen its own scope by writing a broader
    WHERE. The rewrite happens after generation and before execution; the model
    never sees the injected predicate. Raises SqlGateError if the query does not
    pass the gate, so ungated SQL never reaches the engine.
    """
    result = gate_sql(query, granted_columns, allowed_tables, join_ceiling)
    if not result.passed:
        raise SqlGateError(result)

    tree = _parse(query)
    if row_filter_sql:
        if not isinstance(tree, exp.Select):
            raise SqlGateError(
                SqlGateResult(
                    False,
                    [SqlViolation(CTL_COL_01, "row-filtered queries must be SELECT")],
                )
            )
        # append=True AND-combines with any existing WHERE.
        tree = tree.where(row_filter_sql, append=True, dialect="duckdb")
    return tree.sql(dialect="duckdb")
