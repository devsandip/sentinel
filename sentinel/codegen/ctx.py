"""The allowlisted API (`ctx`) that L2 code is allowed to touch (section 6).

This is the fence, from the inside. Generated code never imports the dataset,
opens a file, or reaches a network; it calls `ctx`. The object is constructed by
the platform with tables that are already policy-scoped (row-filtered and
column-projected at the Access stage), so a column Priya may not see does not
exist on the table she receives.

    ctx.table(name)  -> DataFrame   # policy-scoped: only granted columns exist
    ctx.param(name)  -> value       # typed params from the analysis spec
    ctx.emit(obj)    -> None        # the only way to return a result
    ctx.sql(query)   -> DataFrame   # v2: parsed and rewritten by sqlglot

`ctx.sql` is deferred to v2; v1 fences the DataFrame API only.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class CtxError(Exception):
    """Raised when generated code asks `ctx` for something outside its scope."""


_UNSET = object()


class Ctx:
    """The single object generated L2 code is given. Everything else is fenced off.

    Tables handed in are already scoped by the Access stage; `ctx.table` returns
    a defensive copy so the analysis cannot mutate the platform's view.
    """

    def __init__(
        self,
        tables: dict[str, pd.DataFrame] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self._tables = tables or {}
        self._params = params or {}
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

    def sql(self, query: str) -> pd.DataFrame:  # noqa: ARG002 - v2 surface
        raise NotImplementedError(
            "ctx.sql lands in v2; v1 fences the DataFrame API only "
            "(ctx.table / ctx.param / ctx.emit)"
        )

    @property
    def has_emitted(self) -> bool:
        return self._emitted is not _UNSET

    @property
    def emitted(self) -> Any:
        return None if self._emitted is _UNSET else self._emitted
