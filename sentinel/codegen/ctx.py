"""The allowlisted API (`ctx`) that L2 code is allowed to touch (section 6).

This is the fence, from the inside. Generated code never imports the dataset,
opens a file, or reaches a network; it calls `ctx`. The object is constructed by
the platform with tables that are already policy-scoped (row-filtered and
column-projected at the Access stage), so a column Priya may not see does not
exist on the table she receives.

    ctx.table(name)  -> DataFrame   # policy-scoped: only granted columns exist
    ctx.param(name)  -> value       # typed params from the analysis spec
    ctx.emit(obj)    -> None        # the only way to return a result
    ctx.sql(query)   -> DataFrame   # parsed and rewritten by sqlglot, run on DuckDB

`ctx.sql` (v2) parses the query with sqlglot, refuses it if the SQL gate does
(ungranted column, SELECT *, out-of-scope table, Cartesian join), injects the
identity row filter the model never sees, and runs the rewritten query on DuckDB
over the same scoped tables. The static gate (gate.py) has already read the same
SQL before execution; the check here is the runtime backstop.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .sql_gate import DEFAULT_JOIN_CEILING, SqlGateError, rewrite_sql


class CtxError(Exception):
    """Raised when generated code asks `ctx` for something outside its scope."""


_UNSET = object()


class Ctx:
    """The single object generated L2 code is given. Everything else is fenced off.

    Tables handed in are already scoped by the Access stage; `ctx.table` returns
    a defensive copy so the analysis cannot mutate the platform's view.

    `granted_columns` and `row_filter_sql` back the `ctx.sql` path: the grant
    bounds which columns the query may name, and the row filter is injected into
    every query so the model cannot widen its own scope.
    """

    def __init__(
        self,
        tables: dict[str, pd.DataFrame] | None = None,
        params: dict[str, Any] | None = None,
        granted_columns: list[str] | None = None,
        row_filter_sql: str = "",
        join_ceiling: int = DEFAULT_JOIN_CEILING,
    ) -> None:
        self._tables = tables or {}
        self._params = params or {}
        self._granted_columns = set(granted_columns) if granted_columns is not None else None
        self._row_filter_sql = row_filter_sql
        self._join_ceiling = join_ceiling
        self._emitted: Any = _UNSET

    def table(self, name: str) -> pd.DataFrame:
        if name not in self._tables:
            raise CtxError(
                f"table {name!r} is not available in this scope; "
                f"available: {sorted(self._tables)}"
            )
        return self._tables[name].copy()

    def param(self, name: str) -> Any:
        if name not in self._params:
            raise CtxError(f"param {name!r} was not provided by the analysis spec")
        return self._params[name]

    def emit(self, obj: Any) -> None:
        self._emitted = obj

    def sql(self, query: str) -> pd.DataFrame:
        """Gate, rewrite, and run one SQL query over the scoped tables.

        Refuses (as CtxError) anything the SQL gate refuses, then injects the
        identity row filter and executes the rewritten query on DuckDB. The
        tables available are exactly those handed to the Access stage.
        """
        try:
            runnable = rewrite_sql(
                query,
                granted_columns=self._granted_columns,
                allowed_tables=set(self._tables),
                row_filter_sql=self._row_filter_sql,
                join_ceiling=self._join_ceiling,
            )
        except SqlGateError as ex:
            raise CtxError(ex.result.refusal_summary()) from ex

        import duckdb

        con = duckdb.connect(database=":memory:")
        try:
            for name, frame in self._tables.items():
                con.register(name, frame)
            return con.execute(runnable).df()
        finally:
            con.close()

    @property
    def has_emitted(self) -> bool:
        return self._emitted is not _UNSET

    @property
    def emitted(self) -> Any:
        return None if self._emitted is _UNSET else self._emitted
