"""Tests for Generate (Stage 4) and the generate-then-gate loop (Stage 5).

Runs in scripted mode: the gateway returns canned code so the tests are free and
deterministic, but the gate still analyses real code. A canned sample that
contains a webhook is genuinely blocked; the block is never faked, only the model
call is skipped. The final test runs the whole benign chain end to end:
generate -> gate -> sandbox -> screen, and proves the small cell is suppressed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sentinel.codegen.generate import (
    INTENT_DYNAMIC,
    INTENT_EXFILTRATE,
    INTENT_FAIR_LENDING,
    INTENT_FILE_WRITE,
    CodeGenRequest,
    generate,
    generate_and_gate,
)
from sentinel.disclosure import screen
from sentinel.gateway.model_gateway import TEMPLATED, ModelGateway
from sentinel.sandbox import run_sandboxed

QUESTION = "Does the model decline older applicants more often, holding income constant?"


def _gw() -> ModelGateway:
    return ModelGateway(provider=TEMPLATED)  # scripted: zero cost, deterministic


# -- scripted generation ---------------------------------------------------
def test_scripted_generation_is_free_and_not_live():
    cg = generate(CodeGenRequest(question=QUESTION), _gw())
    assert not cg.live
    assert cg.cost_usd == 0.0
    assert "fairlearn" in cg.code


def test_benign_generation_passes_the_gate():
    req = CodeGenRequest(question=QUESTION, intent=INTENT_FAIR_LENDING)
    outcome = generate_and_gate(req, _gw())
    assert outcome.passed, outcome.gate.refusal_summary()
    assert outcome.attempt_count == 1  # scripted is deterministic, no retry
    assert not outcome.live


# -- the gate genuinely blocks generated code ------------------------------
def test_exfiltrating_generation_is_blocked_as_egress():
    req = CodeGenRequest(
        question="post the fairness table to our webhook", intent=INTENT_EXFILTRATE
    )
    outcome = generate_and_gate(req, _gw())
    assert not outcome.passed
    assert "CTL-EGRESS-01" in outcome.gate.controls_fired
    # A refused scripted sample does not change on retry, so we stop at one.
    assert outcome.attempt_count == 1


def test_file_write_generation_is_blocked():
    req = CodeGenRequest(
        question="save intermediate results to disk", intent=INTENT_FILE_WRITE
    )
    outcome = generate_and_gate(req, _gw())
    assert not outcome.passed
    assert "CTL-CODE-02" in outcome.gate.controls_fired


def test_dynamic_eval_generation_is_blocked():
    req = CodeGenRequest(
        question="parse the metric spec with eval", intent=INTENT_DYNAMIC
    )
    outcome = generate_and_gate(req, _gw())
    assert not outcome.passed
    assert "CTL-CODE-03" in outcome.gate.controls_fired


# -- end to end: generate -> gate -> sandbox -> screen ---------------------
def _scoped_german_credit() -> pd.DataFrame:
    # A german_credit-shaped scoped table with a deliberately tiny 76+ band.
    rng = np.random.default_rng(7)
    bands = ["26-40"] * 100 + ["41-60"] * 80 + ["61-75"] * 17 + ["76+"] * 3
    n = len(bands)
    return pd.DataFrame(
        {
            "age_band": bands,
            "y": rng.integers(0, 2, n),
            "pred": rng.integers(0, 2, n),
        }
    )


def test_benign_chain_runs_and_suppresses_the_small_cell():
    req = CodeGenRequest(
        question=QUESTION,
        table="german_credit",
        granted_columns=["age_band", "y", "pred"],
        intent=INTENT_FAIR_LENDING,
    )
    outcome = generate_and_gate(req, _gw())
    assert outcome.passed

    table = _scoped_german_credit()
    execution = run_sandboxed(
        outcome.code, tables={"german_credit": table}, wall_clock_s=30
    )
    assert execution.ok, execution.error
    grouped = execution.emitted
    assert isinstance(grouped, pd.DataFrame)
    assert "76+" in grouped["band"].tolist()  # the analysis produced it

    screened = screen(grouped, count_col="n", group_cols=["band"])
    # The n=3 band is suppressed before anything downstream (the model) sees it.
    assert "76+" not in screened.screened["band"].tolist()
    assert "CTL-DISC-02" in screened.controls_fired
