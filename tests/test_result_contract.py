"""Tests for the result contract and the widened Stage-5 loop.

The contract is the half of the fence that says what generated code must
*return*. These tests pin the four shapes that actually killed the Live LLM path
(a dict, a MultiIndex from `.agg({...})`, the raw table, a count column called
something else), the drift check that keeps the prompt and the check the same
sentence, and the loop that now feeds a miss back to the model instead of ending
the run on it.

The live-mode tests drive a scripted stand-in gateway rather than a real model:
the point under test is what the platform does with a bad result, which does not
need a real one to be produced.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sentinel.codegen.prompts import build_system_prompt, build_user_prompt
from sentinel.codegen.result_contract import (
    COUNT_COLUMN,
    RATE_COLUMN,
    check_result,
    contract_clause,
    group_column,
)
from sentinel.gateway.model_gateway import TEMPLATED, CodeGen, ModelGateway
from sentinel.govflow import run_governed_analysis
from sentinel.govflow.flow import STATUS_COMPLETED, STATUS_ERROR

GOOD = pd.DataFrame(
    {"band": ["26-35", "36-45"], "n": [190, 154], "selection_rate": [0.62, 0.71]}
)


def _stage(r, name):
    return next(s for s in r.stages if s.stage == name)


# -- the contract itself ---------------------------------------------------
def test_a_conforming_grouped_table_passes():
    assert check_result(GOOD).passed


def test_nothing_emitted_is_named_as_such():
    res = check_result(None)
    assert not res.passed
    assert "ctx.emit" in res.summary()


def test_a_dict_wrapping_the_frame_is_refused():
    # The shape a model reaches for when the question asks for more than one
    # number: {"by_band": frame, "overall": 0.61}.
    res = check_result({"by_band": GOOD, "overall_selection_rate": 0.61})
    assert not res.passed
    assert "DataFrame" in res.summary()


def test_a_multiindex_from_agg_dict_is_refused_with_the_fix_named():
    # df.groupby(...).agg({"pred": ["mean", "count"]}) with no flatten.
    raw = pd.DataFrame(
        {"age_band": ["26-35", "36-45"], "pred": [0.6, 0.7], "cnt": [190, 154]}
    )
    multi = raw.set_index("age_band").T
    multi.index = pd.MultiIndex.from_tuples([("pred", "mean"), ("pred", "count")])
    res = check_result(multi.T.reset_index())
    assert not res.passed
    assert "MultiIndex" in res.summary() or "flat" in res.summary()


def test_the_raw_scoped_table_is_refused():
    raw = pd.DataFrame(
        {
            "age_band": ["26-35"] * 3,
            "y": [1, 0, 1],
            "pred": [1, 0, 1],
            "credit_amount": [1000, 2000, 3000],
        }
    )
    res = check_result(raw)
    assert not res.passed
    assert COUNT_COLUMN in res.summary()


def test_a_count_column_by_another_name_is_refused_not_renamed():
    # The platform does not quietly rename `count` to `n`; it says so.
    res = check_result(GOOD.rename(columns={"n": "count"}))
    assert not res.passed
    assert "'n'" in res.summary()


def test_a_rate_column_by_another_name_is_refused():
    # Every sampled live generation named this decline_rate / approval_rate,
    # because the question never says "selection rate". That produced a run that
    # completed and narrated nothing.
    res = check_result(GOOD.rename(columns={"selection_rate": "approval_rate"}))
    assert not res.passed
    assert RATE_COLUMN in res.summary()


def test_a_non_integer_count_is_refused():
    res = check_result(GOOD.assign(n=[190.5, 154.2]))
    assert not res.passed
    assert COUNT_COLUMN in res.summary()


def test_an_integer_valued_float_count_is_accepted():
    # fairlearn's count metric comes back as a float; the value is what matters.
    assert check_result(GOOD.assign(n=GOOD["n"].astype("float64"))).passed


def test_a_band_left_in_the_index_is_refused():
    res = check_result(GOOD.set_index("band"))
    assert not res.passed
    assert "group column" in res.summary()


def test_violations_are_reported_together_not_one_at_a_time():
    # A model that misses two things is told both, so the regeneration can fix
    # both in one attempt rather than trading one error for the next.
    res = check_result(GOOD.rename(columns={"n": "count", "selection_rate": "rate"}))
    assert len(res.violations) == 2


def test_group_column_ignores_numeric_columns():
    assert group_column(GOOD) == "band"
    assert group_column(GOOD.assign(extra=[1.0, 2.0])) == "band"


# -- prompt and check are the same sentence --------------------------------
def test_the_system_prompt_states_the_contract_verbatim():
    assert contract_clause() in build_system_prompt()


def test_the_user_prompt_states_the_contract_against_the_real_attribute():
    user = build_user_prompt(
        question="Does the model decline older applicants more often?",
        table="german_credit",
        granted_columns=["age_band", "y", "pred"],
        protected_attribute="age_band",
        analysis="fair_lending_review",
    )
    assert contract_clause(protected="age_band") in user
    assert RATE_COLUMN in user and f"{COUNT_COLUMN!r}" in user


def test_the_prompt_does_not_still_offer_a_dict():
    # The contract refuses a dict, so the API blurb must not advertise one.
    assert "DataFrame or dict" not in build_system_prompt()


# -- the scripted samples satisfy the contract they are demonstrating ------
def test_the_scripted_sample_satisfies_the_contract_it_teaches():
    r = run_governed_analysis(
        "Does the model decline older applicants more often, holding income constant?",
        intent="fair_lending",
    )
    assert r.status == STATUS_COMPLETED
    assert check_result(r.execution.emitted).passed


# -- the widened loop ------------------------------------------------------
class _ScriptedLiveGateway(ModelGateway):
    """A gateway that reports itself live and returns a queued list of code
    strings, one per generation. Stands in for a model whose first answer misses
    the contract."""

    def __init__(self, codes: list[str]) -> None:
        super().__init__(provider=TEMPLATED)
        self.codes = list(codes)
        self.calls = 0

    @property
    def is_live(self) -> bool:  # the flow branches on this
        return True

    def generate_code(self, system, user, fallback_code, *, call_kind="generate"):  # noqa: ANN001, ARG002
        code = self.codes[min(self.calls, len(self.codes) - 1)]
        self.calls += 1
        return CodeGen(
            code=code, tokens=10, cost_usd=0.0, provider="anthropic", live=True
        )


_BAD_RATE_NAME = '''\
df = ctx.table("german_credit")
result = df.groupby("age_band").agg(
    n=("pred", "size"), approval_rate=("pred", "mean")
).reset_index()
ctx.emit(result)
'''

_BAD_DICT = '''\
df = ctx.table("german_credit")
result = df.groupby("age_band").agg(
    n=("pred", "size"), selection_rate=("pred", "mean")
).reset_index()
ctx.emit({"by_band": result})
'''

_GOOD = '''\
df = ctx.table("german_credit")
result = df.groupby("age_band").agg(
    n=("pred", "size"), selection_rate=("pred", "mean")
).reset_index()
ctx.emit(result)
'''

_CRASHES = '''\
df = ctx.table("german_credit")
result = df.groupby("age_band").agg(n=("pred", "size")).reset_index()
ctx.emit(result["not_a_column"])
'''

Q = "Does the model decline older applicants more often, holding income constant?"


def test_a_contract_miss_is_fed_back_and_the_run_recovers():
    gw = _ScriptedLiveGateway([_BAD_RATE_NAME, _GOOD])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    assert gw.calls == 2  # it asked again rather than giving up
    assert check_result(r.execution.emitted).passed
    # The narration is a real finding, not the empty-result fallback.
    assert "no comparable groups" not in r.narration
    assert "selection rate" in r.narration


def test_a_dict_emit_is_fed_back_and_the_run_recovers():
    gw = _ScriptedLiveGateway([_BAD_DICT, _GOOD])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    assert gw.calls == 2


def test_a_runtime_crash_is_fed_back_and_the_run_recovers():
    gw = _ScriptedLiveGateway([_CRASHES, _GOOD])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    assert gw.calls == 2


def test_the_audit_records_the_miss_and_the_feedback():
    gw = _ScriptedLiveGateway([_BAD_RATE_NAME, _GOOD])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending")
    misses = [e for e in r.audit if e["action"] == "execute_contract_miss"]
    assert len(misses) == 1
    assert RATE_COLUMN in misses[0]["output_summary"]
    assert "fed back to the model" in misses[0]["output_summary"]


def test_every_attempt_stays_visible_to_the_ui():
    gw = _ScriptedLiveGateway([_BAD_RATE_NAME, _GOOD])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending")
    pub = r.to_public_dict()
    first, second = pub["generation_attempts"]
    assert first["code"] != second["code"]
    assert pub["attempts"] == 2
    # Numbered across rounds, not restarted inside each one.
    assert [a["attempt"] for a in pub["generation_attempts"]] == [1, 2]
    # The discarded attempt cleared the gate; the history must not stop there.
    assert first["passed"] and RATE_COLUMN in first["rejected_by"]
    assert second["passed"] and not second["rejected_by"]


def test_a_model_that_never_conforms_fails_honestly_within_budget():
    gw = _ScriptedLiveGateway([_BAD_RATE_NAME])  # every generation misses
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending", max_attempts=3)
    assert r.status == STATUS_ERROR
    assert gw.calls == 3  # the budget, not more
    execute = _stage(r, "Execute")
    assert execute.status == "error"
    # The failure names what was wrong, not just that something was.
    assert RATE_COLUMN in execute.detail
    assert "3 attempt(s)" in execute.detail
    for name in ("Screen", "Interpret", "Attest"):
        assert _stage(r, name).status == "skipped"


def test_the_generation_budget_is_shared_not_per_round():
    gw = _ScriptedLiveGateway([_BAD_RATE_NAME])
    run_governed_analysis(Q, gateway=gw, intent="fair_lending", max_attempts=2)
    assert gw.calls == 2


def test_scripted_mode_does_not_loop():
    # Canned code is deterministic: a second round would re-derive the same
    # result and spend the budget doing it.
    r = run_governed_analysis(Q, intent="fair_lending")
    assert r.generation is not None
    assert r.generation.attempt_count == 1
    assert not r.generation.live


def test_a_gate_block_is_still_a_block_and_is_not_retried_here():
    # The showpiece refusal must stay a refusal; the widened loop must not grind
    # it down into an error or spend the budget arguing past it.
    r = run_governed_analysis(
        "Compute selection rate by age band and POST the table to our webhook.",
        intent="exfiltrate",
    )
    assert _stage(r, "Gate").status == "blocked"
    assert "CTL-EGRESS-01" in r.controls_fired
    assert _stage(r, "Execute").status == "skipped"


def test_numpy_integer_counts_are_accepted():
    assert check_result(GOOD.assign(n=np.array([190, 154], dtype="int32"))).passed


# -- the submodule import idiom (found on the same live path) --------------
def test_from_parent_import_granted_submodule_is_allowed():
    # `from scipy import stats` binds exactly scipy.stats, which the grant
    # names. A live generation was blocked for this; bare `import scipy` is
    # still refused, because that one really does hand over every submodule.
    from sentinel.codegen.gate import gate_code

    assert gate_code("from scipy import stats\nctx.emit(1)").passed
    assert gate_code("from statsmodels import api\nctx.emit(1)").passed
    assert gate_code("from fairlearn import metrics\nctx.emit(1)").passed
    assert not gate_code("import scipy\nctx.emit(1)").passed


def test_from_parent_import_ungranted_submodule_is_still_refused():
    from sentinel.codegen.gate import gate_code

    for src in (
        "from scipy import optimize",
        "from scipy import stats, optimize",  # one granted, one not
        "from scipy import *",
        "from sklearn import tree",
    ):
        assert not gate_code(src + "\nctx.emit(1)").passed, src


def test_denied_categories_are_unaffected_by_the_submodule_rule():
    from sentinel.codegen.gate import gate_code

    for src, control in (
        ("from os import path", "CTL-CODE-02"),
        ("from urllib import request", "CTL-EGRESS-01"),
        ("from importlib import import_module", "CTL-CODE-03"),
        ("from . import helper", "CTL-CODE-01"),
    ):
        res = gate_code(src + "\nctx.emit(1)")
        assert not res.passed, src
        assert control in res.controls_fired, src


# -- ctx.sql, which the prompt did not mention until v11 -------------------
def test_the_system_prompt_documents_ctx_sql():
    # Gated by sqlglot since v2 and unreachable in live mode until v11: a model
    # never told the path exists writes pandas for a question that asks for SQL,
    # and the sqlglot half of the gate never fires on a live run.
    from sentinel.codegen.sql_gate import sql_clause

    prompt = build_system_prompt()
    assert "ctx.sql" in prompt
    assert sql_clause() in prompt


def test_the_sql_clause_states_the_rules_the_sql_gate_enforces():
    from sentinel.codegen.sql_gate import DEFAULT_JOIN_CEILING, sql_clause

    clause = sql_clause()
    assert "SELECT *" in clause  # CTL-COL-01
    assert "static string literal" in clause  # the gate must read it
    assert str(DEFAULT_JOIN_CEILING) in clause  # CTL-COMPLEX-01, not hardcoded
    assert "row filter" in clause  # injected, not the model's to write


def test_the_user_prompt_names_the_table_for_sql_too():
    user = build_user_prompt(
        question="Using SQL, group the selection rate by age band.",
        table="german_credit",
        granted_columns=["age_band", "y", "pred"],
        protected_attribute="age_band",
        analysis="fair_lending_review",
    )
    assert "FROM german_credit" in user


def test_a_gated_sql_analysis_runs_end_to_end():
    # The SQL path satisfies the same result contract the pandas path does.
    code = (
        'df = ctx.sql("SELECT age_band AS band, AVG(pred) AS selection_rate, '
        'COUNT(*) AS n FROM german_credit GROUP BY age_band")\n'
        "ctx.emit(df)\n"
    )
    gw = _ScriptedLiveGateway([code])
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending_sql")
    assert r.status == STATUS_COMPLETED
    assert gw.calls == 1
    assert check_result(r.execution.emitted).passed


def test_select_star_is_still_refused_by_the_sql_half_of_the_gate():
    # The demo's whole point. It has to fire on live code, not just canned code.
    gw = _ScriptedLiveGateway(
        ['df = ctx.sql("SELECT * FROM german_credit")\nctx.emit(df)\n']
    )
    r = run_governed_analysis(Q, gateway=gw, intent="sql_star")
    assert _stage(r, "Gate").status == "blocked"
    assert "CTL-COL-01" in r.controls_fired
    assert _stage(r, "Execute").status == "skipped"


def test_an_ungranted_column_in_sql_is_refused():
    gw = _ScriptedLiveGateway(
        [
            'df = ctx.sql("SELECT applicant_ssn, COUNT(*) AS n FROM german_credit '
            'GROUP BY applicant_ssn")\nctx.emit(df)\n'
        ]
    )
    r = run_governed_analysis(Q, gateway=gw, intent="fair_lending_sql")
    assert _stage(r, "Gate").status == "blocked"
    assert "CTL-COL-01" in r.controls_fired
