"""The sqlglot half of the gate: gate_sql, rewrite_sql, and ctx.sql end to end.

Covers section 5 Stage 5 (the SQL parser) and section 6 (the ctx.sql rewrite that
injects the identity row filter the model never sees).
"""

from __future__ import annotations

import pandas as pd
import pytest

from sentinel.codegen.ctx import Ctx, CtxError
from sentinel.codegen.gate import gate_code
from sentinel.codegen.sql_gate import (
    SqlGateError,
    gate_sql,
    rewrite_sql,
)

GRANT = {"age_band", "pred", "y", "credit_amount"}
TABLES = {"german_credit"}


# -- gate_sql: the static SQL gate ----------------------------------------


def test_benign_query_passes():
    r = gate_sql(
        "SELECT age_band, AVG(pred) AS ar FROM german_credit GROUP BY age_band",
        granted_columns=GRANT,
        allowed_tables=TABLES,
    )
    assert r.passed
    assert r.controls_fired == []


def test_ungranted_column_is_col_01():
    r = gate_sql("SELECT age_band, race FROM german_credit", granted_columns=GRANT)
    assert not r.passed
    assert r.controls_fired == ["CTL-COL-01"]
    assert any("race" in v.detail for v in r.violations)


def test_select_star_is_col_01():
    r = gate_sql("SELECT * FROM german_credit", granted_columns=GRANT)
    assert not r.passed
    assert "CTL-COL-01" in r.controls_fired
    # The star is reported once, not also as a spurious column named '*'.
    assert sum("*" in v.detail for v in r.violations) == 1


def test_qualified_star_is_col_01_once():
    r = gate_sql("SELECT german_credit.* FROM german_credit", granted_columns=GRANT)
    assert not r.passed
    assert r.controls_fired == ["CTL-COL-01"]


def test_table_outside_purpose_is_purp_01():
    r = gate_sql(
        "SELECT age_band FROM customers", granted_columns=GRANT, allowed_tables=TABLES
    )
    assert not r.passed
    assert "CTL-PURP-01" in r.controls_fired


def test_cross_join_is_complex_01():
    r = gate_sql(
        "SELECT g.age_band FROM german_credit g CROSS JOIN german_credit h",
        granted_columns=GRANT,
        allowed_tables=TABLES,
    )
    assert not r.passed
    assert "CTL-COMPLEX-01" in r.controls_fired


def test_comma_join_without_condition_is_complex_01():
    r = gate_sql(
        "SELECT age_band FROM german_credit, german_credit",
        granted_columns=GRANT,
        allowed_tables=TABLES,
    )
    assert "CTL-COMPLEX-01" in r.controls_fired


def test_join_count_ceiling():
    q = (
        "SELECT a.age_band FROM german_credit a "
        "JOIN german_credit b ON a.age_band=b.age_band "
        "JOIN german_credit c ON a.age_band=c.age_band "
        "JOIN german_credit d ON a.age_band=d.age_band"
    )
    r = gate_sql(q, granted_columns=GRANT, allowed_tables=TABLES, join_ceiling=2)
    assert "CTL-COMPLEX-01" in r.controls_fired


def test_column_check_is_case_insensitive():
    r = gate_sql("SELECT AGE_BAND, PRED FROM german_credit", granted_columns=GRANT)
    assert r.passed


def test_unparseable_sql_refused():
    r = gate_sql("SELECT FROM WHERE", granted_columns=GRANT)
    assert not r.passed


def test_multiple_statements_refused():
    r = gate_sql("SELECT age_band FROM german_credit; DROP TABLE german_credit", GRANT)
    assert not r.passed


# -- rewrite_sql: governance by construction ------------------------------


def test_rewrite_injects_row_filter():
    out = rewrite_sql(
        "SELECT age_band, AVG(pred) AS ar FROM german_credit GROUP BY age_band",
        granted_columns=GRANT,
        allowed_tables=TABLES,
        row_filter_sql="credit_amount < 15000",
    )
    assert "credit_amount < 15000" in out
    assert "GROUP BY age_band" in out


def test_rewrite_and_combines_with_existing_where():
    out = rewrite_sql(
        "SELECT age_band FROM german_credit WHERE pred = 1",
        granted_columns=GRANT,
        allowed_tables=TABLES,
        row_filter_sql="credit_amount < 15000",
    )
    # The model's own WHERE survives, ANDed with the injected filter: it cannot
    # widen its scope by writing a broader WHERE.
    assert "pred = 1" in out
    assert "AND credit_amount < 15000" in out


def test_rewrite_refuses_ungated_sql():
    with pytest.raises(SqlGateError):
        rewrite_sql("SELECT * FROM german_credit", granted_columns=GRANT)


# -- gate_code integration: the Python gate reads ctx.sql literals ---------


def test_gate_code_reads_ctx_sql_literal():
    code = (
        "df = ctx.sql('SELECT age_band, race FROM german_credit')\n"
        "ctx.emit(df)\n"
    )
    r = gate_code(code, granted_columns=GRANT, allowed_tables=TABLES)
    assert not r.passed
    assert "CTL-COL-01" in r.controls_fired
    # The SQL violation is stamped with the Python line of the ctx.sql call.
    assert any(v.line == 1 and "ctx.sql" in v.detail for v in r.violations)


def test_gate_code_refuses_non_literal_sql():
    code = "q = 'SELECT ' + col\ndf = ctx.sql(q)\n"
    r = gate_code(code, granted_columns=GRANT, allowed_tables=TABLES)
    assert not r.passed
    assert any("static string literal" in v.detail for v in r.violations)


def test_gate_code_passes_benign_ctx_sql():
    code = (
        "df = ctx.sql('SELECT age_band, AVG(pred) AS ar "
        "FROM german_credit GROUP BY age_band')\n"
        "ctx.emit(df)\n"
    )
    r = gate_code(code, granted_columns=GRANT, allowed_tables=TABLES)
    assert r.passed


def test_gate_code_flags_ctx_sql_out_of_scope_table():
    code = "df = ctx.sql('SELECT age_band FROM customers')\nctx.emit(df)\n"
    r = gate_code(code, granted_columns=GRANT, allowed_tables=TABLES)
    assert "CTL-PURP-01" in r.controls_fired


# -- ctx.sql end to end: gate, rewrite, run on DuckDB ---------------------


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age_band": ["18-25", "18-25", "26-35", "26-35"],
            "pred": [1, 0, 1, 1],
            "y": [1, 0, 1, 0],
            "credit_amount": [5000, 9000, 20000, 8000],
        }
    )


def test_ctx_sql_runs_and_aggregates():
    ctx = Ctx(tables={"german_credit": _frame()}, granted_columns=list(GRANT))
    out = ctx.sql(
        "SELECT age_band, AVG(pred) AS rate, COUNT(*) AS n "
        "FROM german_credit GROUP BY age_band ORDER BY age_band"
    )
    assert list(out["age_band"]) == ["18-25", "26-35"]
    assert out.loc[out["age_band"] == "18-25", "n"].iloc[0] == 2


def test_ctx_sql_applies_injected_row_filter():
    ctx = Ctx(
        tables={"german_credit": _frame()},
        granted_columns=list(GRANT),
        row_filter_sql="credit_amount < 15000",
    )
    out = ctx.sql("SELECT age_band, COUNT(*) AS n FROM german_credit GROUP BY age_band")
    # The 26-35 row with credit_amount=20000 is filtered out by the injected
    # predicate, so that band drops to n=1.
    by_band = dict(zip(out["age_band"], out["n"], strict=True))
    assert by_band["26-35"] == 1


def test_ctx_sql_refuses_ungranted_column_at_runtime():
    ctx = Ctx(tables={"german_credit": _frame()}, granted_columns=list(GRANT))
    with pytest.raises(CtxError):
        ctx.sql("SELECT age_band, race FROM german_credit")
