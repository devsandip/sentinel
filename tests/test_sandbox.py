"""Tests for the ctx fence and the subprocess sandbox (section 5, Stage 6; 6).

The sandbox runs gated code in a separate process with a wall-clock cap. These
tests cover the fence's scope errors, the happy path (a DataFrame emitted by the
analysis survives the process boundary), a crash reported rather than hidden,
and the CTL-TIME-01 wall-clock kill.
"""

from __future__ import annotations

import textwrap

import pandas as pd
import pytest

from sentinel.codegen.ctx import Ctx, CtxError
from sentinel.sandbox import CTL_TIME_01, run_sandboxed


def _dedent(code: str) -> str:
    return textwrap.dedent(code).strip("\n") + "\n"


# -- the ctx fence ---------------------------------------------------------
def test_ctx_table_returns_a_defensive_copy():
    original = pd.DataFrame({"a": [1, 2, 3]})
    ctx = Ctx(tables={"t": original})
    handed = ctx.table("t")
    handed.loc[0, "a"] = 999
    assert original.loc[0, "a"] == 1  # platform's view is untouched


def test_ctx_unknown_table_and_param_raise():
    ctx = Ctx(tables={"t": pd.DataFrame()}, params={"k": 5})
    with pytest.raises(CtxError):
        ctx.table("missing")
    with pytest.raises(CtxError):
        ctx.param("missing")
    assert ctx.param("k") == 5


def test_ctx_emit_and_sql_surface():
    ctx = Ctx()
    assert not ctx.has_emitted
    ctx.emit({"result": 1})
    assert ctx.has_emitted and ctx.emitted == {"result": 1}
    with pytest.raises(NotImplementedError):
        ctx.sql("SELECT 1")


# -- the sandbox happy path ------------------------------------------------
def test_sandboxed_analysis_emits_a_dataframe():
    code = _dedent(
        """
        import pandas as pd
        df = ctx.table("t")
        grouped = df.groupby("band", as_index=False).size()
        grouped = grouped.rename(columns={"size": "n"})
        ctx.emit(grouped)
        """
    )
    tables = {"t": pd.DataFrame({"band": ["a", "a", "b"], "x": [1, 2, 3]})}
    result = run_sandboxed(code, tables=tables, wall_clock_s=30)
    assert result.ok, result.error
    assert result.has_emitted
    emitted = result.emitted
    assert isinstance(emitted, pd.DataFrame)
    assert dict(zip(emitted["band"], emitted["n"], strict=True)) == {"a": 2, "b": 1}


def test_sandbox_can_use_a_param():
    code = _dedent(
        """
        floor = ctx.param("floor")
        ctx.emit(floor * 2)
        """
    )
    result = run_sandboxed(code, params={"floor": 10}, wall_clock_s=30)
    assert result.ok
    assert result.emitted == 20


def test_sandbox_no_emit_is_reported():
    result = run_sandboxed("x = 1 + 1\n", wall_clock_s=30)
    assert result.ok
    assert not result.has_emitted
    assert result.emitted is None


def test_sandbox_runtime_error_is_reported_not_raised():
    result = run_sandboxed("raise ValueError('boom')\n", wall_clock_s=30)
    assert not result.ok
    assert "ValueError" in (result.error or "")
    assert "boom" in (result.error or "")


# -- CTL-TIME-01: the wall-clock cap ---------------------------------------
def test_wall_clock_cap_kills_and_reports_ctl_time_01():
    code = _dedent(
        """
        import time
        time.sleep(30)
        ctx.emit("should never get here")
        """
    )
    result = run_sandboxed(code, wall_clock_s=1.0)
    assert not result.ok
    assert result.control == CTL_TIME_01
    assert not result.has_emitted


# -- result serialization --------------------------------------------------
def test_execution_result_to_dict_serializes_dataframe():
    code = _dedent(
        """
        import pandas as pd
        ctx.emit(pd.DataFrame({"band": ["a"], "n": [5]}))
        """
    )
    result = run_sandboxed(code, wall_clock_s=30)
    d = result.to_dict()
    assert d["ok"] is True
    assert d["emitted"] == [{"band": "a", "n": 5}]
