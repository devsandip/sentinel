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
    ALLOWED_IMPORTS,
    CTL_CODE_00,
    CTL_CODE_01,
    CTL_CODE_02,
    CTL_CODE_03,
    CTL_CODE_04,
    CTL_COL_01,
    CTL_COMPLEX_01,
    CTL_EGRESS_01,
    CTL_PURP_01,
    DUNDER_ESCAPES,
    DYNCODE_BUILTINS,
    DYNCODE_MODULES,
    EGRESS_MODULES,
    FS_MODULES,
    L3_ALLOWED_IMPORTS,
    import_verdict,
    name_verdict,
    open_mode_is_write,
)
from .sql_gate import SqlReading, gate_sql

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


# --------------------------------------------------------------------------
# What the gate read, as opposed to what it refused
# --------------------------------------------------------------------------
# A gate that records only its refusals can say nothing at all about the run it
# cleared: nine checks, nine ticks, no evidence. That is the same shape of
# mistake the Audit Log had to unlearn -- a control being *consulted* is not the
# control saying no -- and the fix is the same. The walk below now records every
# construct it judged, so a passing verdict can be audited rather than believed.
#
# The four verdicts are four different facts and collapsing any pair of them is
# how a gate screen starts lying:
#   REFUSED   the check found something and said no.
#   CLEARED   the check judged N constructs and permitted all of them.
#   NO_SUBJECT the check was armed and this code contained nothing for it to
#             judge (no SQL, so no table can be out of scope).
#   NOT_ARMED  the check could not run: its rule was not supplied (no column
#             grant means CTL-COL-01's DataFrame half is inert).
# Only the first two are verdicts on the code. The last two are verdicts on the
# check, and a screen that paints them green is claiming an assurance nobody
# ever established.
REFUSED = "refused"
CLEARED = "cleared"
NO_SUBJECT = "no_subject"
NOT_ARMED = "not_armed"


@dataclass(frozen=True)
class Observation:
    """One construct the gate judged, and what it decided about it."""

    subject: str  # what the parser read, as close to verbatim as it can be shown
    line: int
    allowed: bool
    reason: str  # why it was permitted, or why it was not
    control: str = ""  # the control that refused it; empty when permitted

    def to_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "line": self.line,
            "allowed": self.allowed,
            "reason": self.reason,
            "control": self.control,
        }


@dataclass(frozen=True)
class CheckReading:
    """One check's account of itself on one code string.

    `examined` counts constructs judged, which is the number a reviewer needs
    and the one a tick mark hides. `items` are named observations: for an
    allow-list check (imports, columns, tables) that is every construct, so the
    list is the evidence; for a deny-list scan (egress, filesystem, dynamic
    code, escapes) naming all of them would mean printing every identifier in
    the file, so only the hits are named and `itemized` is False -- the count
    plus the rule is the evidence there.
    """

    key: str
    label: str
    controls: tuple[str, ...]
    examines: str  # the population, in words
    rule: str  # what that population was tested against
    unit: str  # singular noun for one member of the population
    plural: str = ""  # its plural, where -s will not do
    armed: bool = True
    examined: int = 0
    items: tuple[Observation, ...] = ()
    itemized: bool = True

    @property
    def refusals(self) -> tuple[Observation, ...]:
        return tuple(o for o in self.items if not o.allowed)

    @property
    def verdict(self) -> str:
        if self.refusals:
            return REFUSED
        if not self.armed:
            return NOT_ARMED
        if self.examined == 0:
            return NO_SUBJECT
        return CLEARED

    @property
    def summary(self) -> str:
        """The check's one line, written where the check runs so no screen has
        to guess what the count means."""
        n = self.examined
        noun = self.unit if n == 1 else (self.plural or f"{self.unit}s")
        if self.verdict == NOT_ARMED:
            return f"Not armed: {self.rule}."
        if self.verdict == NO_SUBJECT:
            return f"No {self.unit} in this code, so there was nothing to judge."
        if self.key == _PARSE:
            first = self.items[0] if self.items else None
            if first is None:
                return "The source was not read."
            if self.verdict == REFUSED:
                return f"Did not parse: {first.reason} (line {first.line})."
            return f"Parsed: {first.subject}."
        if self.verdict == REFUSED:
            return f"{n} {noun} read, {len(self.refusals)} refused."
        # A deny-list sweep permits nothing; it looks for hits and finds none.
        # Saying "all permitted" would claim a judgement it never made.
        if not self.itemized:
            return f"{n} {noun} read, none matched the deny list."
        return f"{n} {noun} read, all inside the rule."

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "controls": list(self.controls),
            "examines": self.examines,
            "rule": self.rule,
            "armed": self.armed,
            "examined": self.examined,
            "itemized": self.itemized,
            "verdict": self.verdict,
            "summary": self.summary,
            "items": [o.to_dict() for o in self.items],
        }


def _tier_label(allowed_imports: frozenset[str]) -> str:
    if allowed_imports == ALLOWED_IMPORTS:
        return "L2"
    if allowed_imports == L3_ALLOWED_IMPORTS:
        return "L3"
    return "custom"


# -- the check catalogue ----------------------------------------------------
# The nine checks, defined where they are enforced. The Gate screen used to
# carry its own copy of this list; a screen that keeps its own list of what the
# gate does is a claim nothing holds to the code, which is the failure this
# build keeps finding in itself. The screen now reads this.
_PARSE = "parse"
_IMPORTS = "imports"
_EGRESS = "egress"
_FS = "filesystem"
_DYNCODE = "dyncode"
_ESCAPE = "escape"
_COLUMNS = "columns"
_TABLES = "tables"
_JOINS = "joins"

# key -> (label, controls, what it examines, noun for one member, its plural)
_CHECK_SPEC: dict[str, tuple[str, tuple[str, ...], str, str, str]] = {
    _PARSE: (
        "Parses as Python",
        (CTL_CODE_00,),
        "the source, as one unit",
        "source",
        "sources",
    ),
    _IMPORTS: (
        "Imports on the tier's allowlist",
        (CTL_CODE_01,),
        "every import statement",
        "import",
        "imports",
    ),
    _EGRESS: (
        "No network egress, referenced or imported",
        (CTL_EGRESS_01,),
        "every import and every bare name in the file",
        "construct",
        "constructs",
    ),
    _FS: (
        "No filesystem or process access",
        (CTL_CODE_02,),
        "every import, every bare name, and every open() call",
        "construct",
        "constructs",
    ),
    _DYNCODE: (
        "No dynamic code or unsafe deserialization",
        (CTL_CODE_03,),
        "every import, every bare name, and every direct call",
        "construct",
        "constructs",
    ),
    _ESCAPE: (
        "No sandbox-escape attribute access",
        (CTL_CODE_04,),
        "every attribute access",
        "attribute access",
        "attribute accesses",
    ),
    _COLUMNS: (
        "Every column inside the grant; no SELECT *",
        (CTL_COL_01,),
        "every column named by a scoped-table subscript or by SQL",
        "column reference",
        "column references",
    ),
    _TABLES: (
        "SQL tables inside the purpose scope",
        (CTL_PURP_01,),
        "every table named in ctx.sql",
        "table reference",
        "table references",
    ),
    _JOINS: (
        "Join complexity under the ceiling",
        (CTL_COMPLEX_01,),
        "the join shape of every ctx.sql query",
        "query",
        "queries",
    ),
}

_CHECK_KEYS = tuple(_CHECK_SPEC)

# Which check owns each control, so a violation lands in the row that made it.
_CHECK_OF_CONTROL = {
    CTL_CODE_00: _PARSE,
    CTL_CODE_01: _IMPORTS,
    CTL_EGRESS_01: _EGRESS,
    CTL_CODE_02: _FS,
    CTL_CODE_03: _DYNCODE,
    CTL_CODE_04: _ESCAPE,
    CTL_COL_01: _COLUMNS,
    CTL_PURP_01: _TABLES,
    CTL_COMPLEX_01: _JOINS,
}

# Checks whose population is a deny-list sweep over every identifier in the
# file. Naming each member would mean printing the whole file back, so these
# report the size of the sweep and name only the hits.
_SWEEPS = frozenset({_EGRESS, _FS, _DYNCODE, _ESCAPE})


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _rules(
    granted: set[str],
    tables: set[str] | None,
    join_ceiling: int,
    allowed_imports: frozenset[str],
) -> dict[str, tuple[str, bool]]:
    """Each check's rule text and whether that rule was actually supplied."""
    return {
        _PARSE: ("the stdlib ast parser, which must accept it", True),
        _IMPORTS: (
            f"the {_tier_label(allowed_imports)} import allowlist "
            f"({len(allowed_imports)} modules)",
            True,
        ),
        _EGRESS: (f"{len(EGRESS_MODULES)} denied network modules", True),
        _FS: (
            f"{len(FS_MODULES)} denied modules, plus open() in write mode",
            True,
        ),
        _DYNCODE: (
            f"{len(DYNCODE_MODULES)} denied modules and "
            f"{len(DYNCODE_BUILTINS)} denied builtins",
            True,
        ),
        _ESCAPE: (f"{len(DUNDER_ESCAPES)} denied dunder attributes", True),
        _COLUMNS: (
            f"the column grant for this purpose ({_plural(len(granted), 'column')})"
            if granted
            else "no column grant was supplied, so only SELECT * can be refused",
            bool(granted),
        ),
        _TABLES: (
            f"the purpose's table scope ({_plural(len(tables), 'table')})"
            if tables is not None
            else "no table scope was supplied to the gate",
            tables is not None,
        ),
        _JOINS: (
            f"a ceiling of {join_ceiling} joins, and no join without a condition",
            True,
        ),
    }


@dataclass(frozen=True)
class GateResult:
    """The gate's verdict on one code string."""

    passed: bool
    violations: list[Violation] = field(default_factory=list)
    # What the walk read, per check, and the scope it was read against. Both are
    # additive: `passed` and `violations` are unchanged and still the verdict.
    checks: tuple[CheckReading, ...] = ()
    scope: dict[str, object] = field(default_factory=dict)

    @property
    def examined(self) -> int:
        """Judgements made across every check.

        Not a count of constructs: one import is judged by four checks (the
        allowlist and the three deny lists), so it lands here four times. Use
        `constructs` for the distinct count. Presenting either number as the
        other is the exact sloppiness the read exists to remove.
        """
        return sum(c.examined for c in self.checks)

    @property
    def constructs(self) -> int:
        """Distinct constructs the gate formed a view about, counted once each.
        The same total the per-line gutter adds up to."""
        counts = self.scope.get("line_counts") or {}
        return sum(counts.values()) if isinstance(counts, dict) else 0

    def check(self, key: str) -> CheckReading | None:
        return next((c for c in self.checks if c.key == key), None)

    @property
    def controls_fired(self) -> list[str]:
        # Deduped, in the order first seen.
        seen: list[str] = []
        for v in self.violations:
            if v.control not in seen:
                seen.append(v.control)
        return seen

    def to_public_dict(self) -> dict[str, object]:
        """The payload the UI and the audit surfaces read.

        `passed`, `controls_fired` and `violations` are the pinned shape and are
        unchanged; `checks` and `scope` are additive and carry the read.
        """
        return {
            "passed": self.passed,
            "controls_fired": self.controls_fired,
            "violations": [
                {"control": v.control, "line": v.line, "message": v.message}
                for v in self.violations
            ],
            "checks": [c.to_dict() for c in self.checks],
            "scope": dict(self.scope),
        }

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
        allowed_imports: frozenset[str],
        derived_columns: dict[str, int] | None = None,
    ) -> None:
        self.granted_columns = granted_columns
        self.table_vars = table_vars
        # Columns the analysis builds on the scoped table; see
        # _collect_derived_columns for why they join the effective grant.
        self.derived_columns = derived_columns or {}
        self.allowed_tables = allowed_tables
        self.join_ceiling = join_ceiling
        self.allowed_imports = allowed_imports
        self.violations: list[Violation] = []
        # The read, recorded as it happens. Keyed by check; see CheckReading.
        self.seen: dict[str, list[Observation]] = {}
        self.counts: dict[str, int] = dict.fromkeys(_CHECK_KEYS, 0)
        # Constructs judged per source line. Counted once per construct, not
        # once per check that judged it, so the number reads as "things on this
        # line the gate formed a view about" rather than a judgement tally.
        self.line_counts: dict[int, int] = {}
        self.sql_readings: list[tuple[int, SqlReading]] = []

    def _add(self, control: str, line: int, detail: str) -> None:
        self.violations.append(Violation(control=control, line=line, detail=detail))

    def _note(self, check: str, obs: Observation) -> None:
        self.seen.setdefault(check, []).append(obs)

    def _count(self, *checks: str, n: int = 1) -> None:
        for c in checks:
            self.counts[c] = self.counts.get(c, 0) + n

    def _touch(self, line: int, n: int = 1) -> None:
        self.line_counts[line] = self.line_counts.get(line, 0) + n

    # -- imports (CTL-CODE-01/02/03, CTL-EGRESS-01) ------------------------
    def _read_import(self, module: str, shown: str, line: int) -> None:
        """One import, judged once and recorded against every check that judged
        it. `import_verdict` tests the module against the three deny lists and
        the allowlist in that order, so all four checks genuinely read it."""
        self._count(_IMPORTS, _EGRESS, _FS, _DYNCODE)
        self._touch(line)
        verdict = import_verdict(module, self.allowed_imports)
        if verdict is None:
            self._note(
                _IMPORTS,
                Observation(shown, line, True, "on the tier's import allowlist"),
            )
            return
        self._add(verdict, line, shown)
        self._note(
            _CHECK_OF_CONTROL[verdict],
            Observation(shown, line, False, _CONTROL_MESSAGES[verdict], verdict),
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._read_import(alias.name, f"import {alias.name}", node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # Relative import (level > 0) has no resolvable module; import_verdict
        # treats an empty module as an allowlist miss.
        module = "" if node.level and not node.module else (node.module or "")
        shown = ("." * (node.level or 0)) + (node.module or "")
        self._read_import(
            self._bound_module(module, node), f"from {shown} import ...", node.lineno
        )
        self.generic_visit(node)

    def _bound_module(self, module: str, node: ast.ImportFrom) -> str:
        """The module an ImportFrom should be judged as.

        `from scipy import stats` binds exactly `scipy.stats`, which the grant
        names, though bare `scipy` is not granted. Judging the parent refuses an
        import the allowlist permits: the per-submodule rule exists to stop
        `import scipy` handing over every submodule, not to refuse the one
        submodule that was granted. A live model writing idiomatic Python hit
        this and was blocked for it.

        Only an allowlist miss is reconsidered, so a denied category is untouched
        (`from os import path` stays CTL-CODE-02 whatever it binds), and every
        bound name must resolve, so one ungranted member refuses the whole
        statement. `import *` resolves to `module.*`, which no grant matches.
        """
        if node.level or not node.names:
            return module
        if import_verdict(module, self.allowed_imports) != CTL_CODE_01:
            return module
        bound = [f"{module}.{a.name}" for a in node.names]
        if all(import_verdict(m, self.allowed_imports) is None for m in bound):
            return bound[0]
        return module

    # -- bare name references (CTL-EGRESS-01 / CTL-CODE-02/03 without import) --
    def visit_Name(self, node: ast.Name) -> None:
        # Every identifier in the file is tested against all three deny lists,
        # which is what makes the webhook case (bare `requests.post` with no
        # import) catchable. Counting them is how the screen can say how wide
        # the sweep was rather than asserting that one happened.
        self._count(_EGRESS, _FS, _DYNCODE)
        self._touch(node.lineno)
        verdict = name_verdict(node.id)
        if verdict is not None:
            self._add(verdict, node.lineno, node.id)
            self._note(
                _CHECK_OF_CONTROL[verdict],
                Observation(
                    node.id, node.lineno, False, _CONTROL_MESSAGES[verdict], verdict
                ),
            )
        self.generic_visit(node)

    # -- calls: eval/exec/compile/__import__, open() write, and ctx.sql(...) --
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            self._count(_DYNCODE)
            if func.id in DYNCODE_BUILTINS:
                self._add(CTL_CODE_03, node.lineno, f"{func.id}(...)")
                self._note(
                    _DYNCODE,
                    Observation(
                        f"{func.id}(...)",
                        node.lineno,
                        False,
                        "executes a string as code",
                        CTL_CODE_03,
                    ),
                )
            elif func.id == "open":
                self._count(_FS)
                if self._open_is_write(node):
                    self._add(CTL_CODE_02, node.lineno, "open(..., write mode)")
                    self._note(
                        _FS,
                        Observation(
                            "open(..., write mode)",
                            node.lineno,
                            False,
                            "opens a file for writing",
                            CTL_CODE_02,
                        ),
                    )
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
            detail = (
                "ctx.sql argument must be a static string literal so the gate can read it"
            )
            self._count(_COLUMNS)
            self._touch(node.lineno)
            self._add(CTL_COL_01, node.lineno, detail)
            self._note(
                _COLUMNS,
                Observation("ctx.sql(<not a literal>)", node.lineno, False, detail, CTL_COL_01),
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
        if result.reading is not None:
            self.sql_readings.append((node.lineno, result.reading))
            self._record_sql(node.lineno, result.reading)

    def _record_sql(self, line: int, reading: SqlReading) -> None:
        """Fold one query's reading into the column, table and join checks.

        The verdicts are re-derived from the same grant the SQL gate used, so
        the screen shows the sqlglot half's actual reasoning rather than a
        restatement of it.
        """
        if not reading.parsed:
            return
        grant = {c.lower() for c in self.granted_columns}
        scope = (
            {t.lower() for t in self.allowed_tables}
            if self.allowed_tables is not None
            else None
        )
        if reading.star:
            self._count(_COLUMNS)
            self._touch(line)
            self._note(
                _COLUMNS,
                Observation(
                    "SELECT *", line, False, "a wildcard projection names no column", CTL_COL_01
                ),
            )
        for col in reading.columns:
            self._count(_COLUMNS)
            self._touch(line)
            ok = not grant or col.lower() in grant
            self._note(
                _COLUMNS,
                Observation(
                    f"{col} (SQL)",
                    line,
                    ok,
                    "in the grant" if ok else "not in the grant for this purpose",
                    "" if ok else CTL_COL_01,
                ),
            )
        for tbl in reading.tables:
            self._count(_TABLES)
            self._touch(line)
            ok = scope is None or tbl.lower() in scope
            self._note(
                _TABLES,
                Observation(
                    f"{tbl} (SQL)",
                    line,
                    ok,
                    "in the purpose's table scope"
                    if ok
                    else "outside the purpose's table scope",
                    "" if ok else CTL_PURP_01,
                ),
            )
        # The join check judges the query's shape, so the query is the construct
        # it read: a query with no joins was still examined and cleared, which a
        # count of joins would report as "nothing to test".
        self._count(_JOINS)
        self._touch(line)
        shape = f"{reading.joins} join{'' if reading.joins == 1 else 's'}"
        if reading.cartesian:
            reason = f"{reading.cartesian} of them carry neither ON nor USING"
        elif reading.joins > self.join_ceiling:
            reason = f"over the ceiling of {self.join_ceiling}"
        else:
            reason = f"at or under the ceiling of {self.join_ceiling}, each with a condition"
        ok = not reading.cartesian and reading.joins <= self.join_ceiling
        self._note(
            _JOINS,
            Observation(shape, line, ok, reason, "" if ok else CTL_COMPLEX_01),
        )

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
        self._count(_ESCAPE)
        self._touch(node.lineno)
        if node.attr in DUNDER_ESCAPES:
            self._add(CTL_CODE_04, node.lineno, f".{node.attr}")
            self._note(
                _ESCAPE,
                Observation(
                    f".{node.attr}",
                    node.lineno,
                    False,
                    "walks the object graph out of the sandbox",
                    CTL_CODE_04,
                ),
            )
        # Column access as an attribute on a scoped table (df.age_band) is only
        # checkable when we can confirm the base is a table var AND the attr is
        # not a known DataFrame method. That is ambiguous, so attribute-style
        # column access is left to enforcement-by-construction (the ScopedTable
        # simply lacks the column). CTL-COL-01 here checks the unambiguous case:
        # string-literal subscripts, handled in visit_Subscript.
        self.generic_visit(node)

    def _column_ok(self, key: str, line: int) -> bool:
        """A column read is permitted if the purpose granted it, or if this code
        built it earlier out of granted data (see _collect_derived_columns).
        `earlier` is load-bearing: a name created below the read does not excuse
        it."""
        if key in self.granted_columns:
            return True
        created = self.derived_columns.get(key)
        return created is not None and created <= line

    # -- subscripts: df["col"] against the grant (CTL-COL-01) --------------
    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self.granted_columns and isinstance(node.value, ast.Name):
            if node.value.id in self.table_vars:
                for key in _subscript_columns(node.slice):
                    self._count(_COLUMNS)
                    self._touch(node.lineno)
                    shown = f'{node.value.id}["{key}"]'
                    ok = self._column_ok(key, node.lineno)
                    if not ok:
                        self._add(CTL_COL_01, node.lineno, shown)
                    self._note(
                        _COLUMNS,
                        Observation(
                            shown,
                            node.lineno,
                            ok,
                            "in the grant"
                            if ok
                            else "not in the grant for this purpose",
                            "" if ok else CTL_COL_01,
                        ),
                    )
        self.generic_visit(node)


def _subscript_columns(slice_node: ast.expr) -> list[str]:
    """Every column name a subscript names, as string literals.

    `df["pred"]` names one. `df[["age_band", "pred"]]` names two, and until now
    named none as far as the gate was concerned: the check asked for a string
    constant, a list is not one, so multi-column selection -- the ordinary way to
    project a frame -- went unjudged. CTL-COL-01 would refuse
    `df["applicant_email"]` and clear `df[["age_band", "applicant_email"]]`.
    Non-literal keys are still unreadable and still skipped; enforcement by
    construction is what covers those.
    """
    key = _string_const(slice_node)
    if key is not None:
        return [key]
    if isinstance(slice_node, ast.List | ast.Tuple):
        return [k for k in (_string_const(e) for e in slice_node.elts) if k is not None]
    return []


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


def _collect_derived_columns(tree: ast.AST, table_vars: set[str]) -> dict[str, int]:
    """Column names the analysis *creates* on a scoped table.

    `df["decline"] = 1 - df["pred"]` is a write, not a read. CTL-COL-01 judged
    the subscript without looking at its context, so it refused a column the
    model was building out of granted data, and the identical code written on
    `df.copy()` passed -- a distinction with no meaning from the model's side.
    One live generation in five hit this.

    Reading such a column back is equally safe, so a derived name joins the
    effective grant. The reason it is safe is enforcement by construction, not
    leniency: the Access stage projects the frame to the granted columns, so an
    ungranted column is not in the object at all. A read of one raises KeyError
    in the sandbox, and no assignment can conjure data that was never handed
    over -- the right-hand side can only be built from what the frame already
    holds. CTL-COL-01 is the declaration of intent over that projection, and
    the projection is what actually withholds the data.

    Returns each derived name with the line it is first created on, because the
    grant it joins starts there. Without the line, `x = df["applicant_ssn"]`
    followed by `df["applicant_ssn"] = 1` would retroactively excuse the read:
    harmless to the data, since the projection means that read is a KeyError,
    but it would let generated code silence a control by writing a line that
    never runs. A control that can be talked out of firing is not one a tester
    can trust.
    """
    derived: dict[str, int] = {}
    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id in table_vars
            ):
                key = _string_const(target.slice)
                if key is not None:
                    derived[key] = min(derived.get(key, node.lineno), node.lineno)
    return derived


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
    allowed_imports: frozenset[str] = ALLOWED_IMPORTS,
) -> GateResult:
    """Statically gate a generated code string. Never executes it.

    Returns a GateResult naming every control that fired and the line it fired
    on. Pass `granted_columns` to enable the CTL-COL-01 column check (DataFrame
    subscripts and ctx.sql). Pass `allowed_tables` to enable the CTL-PURP-01
    table-scope check inside ctx.sql; omit it to skip that check. `allowed_imports`
    defaults to the L2 allowlist; pass L3_ALLOWED_IMPORTS for the broad L3 gate,
    which widens the analytical allowlist but not the egress/fs/dyncode deny lists.
    """
    granted = set(granted_columns) if granted_columns is not None else set()
    tables = set(allowed_tables) if allowed_tables is not None else None
    rules = _rules(granted, tables, join_ceiling, allowed_imports)
    scope: dict[str, object] = {
        "tier": _tier_label(allowed_imports),
        "allowed_imports": sorted(allowed_imports),
        "granted_columns": sorted(granted),
        "allowed_tables": sorted(tables) if tables is not None else None,
        "join_ceiling": join_ceiling,
        "lines": len(code.splitlines()),
    }

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 0
        detail = exc.msg or "syntax error"
        # Nothing downstream ran: the walk needs a tree. Every other check is
        # unarmed rather than clear, because code that will not compile cannot
        # be reasoned about and reporting eight green ticks on it would be a
        # straight falsehood.
        checks = [
            CheckReading(
                key=_PARSE,
                label=_CHECK_SPEC[_PARSE][0],
                controls=_CHECK_SPEC[_PARSE][1],
                examines=_CHECK_SPEC[_PARSE][2],
                unit=_CHECK_SPEC[_PARSE][3],
                plural=_CHECK_SPEC[_PARSE][4],
                rule=rules[_PARSE][0],
                armed=True,
                examined=1,
                items=(Observation(f"line {line}", line, False, detail, CTL_CODE_00),),
            )
        ] + [
            CheckReading(
                key=k,
                label=_CHECK_SPEC[k][0],
                controls=_CHECK_SPEC[k][1],
                examines=_CHECK_SPEC[k][2],
                unit=_CHECK_SPEC[k][3],
                plural=_CHECK_SPEC[k][4],
                rule="the source did not parse, so the walk never ran",
                armed=False,
                itemized=k not in _SWEEPS,
            )
            for k in _CHECK_KEYS
            if k != _PARSE
        ]
        return GateResult(
            passed=False,
            violations=[Violation(CTL_CODE_00, line, detail)],
            checks=tuple(checks),
            scope=scope,
        )

    table_vars = _collect_table_vars(tree)
    visitor = _GateVisitor(
        granted_columns=granted,
        table_vars=table_vars,
        derived_columns=_collect_derived_columns(tree, table_vars),
        allowed_tables=tables,
        join_ceiling=join_ceiling,
        allowed_imports=allowed_imports,
    )
    visitor.visit(tree)

    stmts = len(getattr(tree, "body", []))
    parsed_note = Observation(
        f"{scope['lines']} lines, {stmts} top-level statements",
        0,
        True,
        "the ast parser accepted it, so the walk below could run",
    )
    checks = []
    for key in _CHECK_KEYS:
        label, controls, examines, unit, plural = _CHECK_SPEC[key]
        rule, armed = rules[key]
        if key == _PARSE:
            examined, items = 1, (parsed_note,)
        else:
            items = tuple(visitor.seen.get(key, ()))
            examined = visitor.counts.get(key, 0)
            if key in _SWEEPS:
                items = tuple(o for o in items if not o.allowed)
        checks.append(
            CheckReading(
                key=key,
                label=label,
                controls=controls,
                examines=examines,
                rule=rule,
                unit=unit,
                plural=plural,
                armed=armed,
                examined=examined,
                items=items,
                itemized=key not in _SWEEPS,
            )
        )
    scope["queries"] = [
        {"line": line, "query": r.query} for line, r in visitor.sql_readings
    ]
    scope["line_counts"] = dict(sorted(visitor.line_counts.items()))

    # Stable order: by line, then by control id, so the Gate screen reads top to
    # bottom like the code does.
    violations = sorted(visitor.violations, key=lambda v: (v.line, v.control, v.detail))
    return GateResult(
        passed=not violations,
        violations=violations,
        checks=tuple(checks),
        scope=scope,
    )
