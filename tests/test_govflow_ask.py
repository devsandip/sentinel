"""The Ask stage's three sub-steps: pick a dataset, declare a purpose, select
an analysis.

Two kinds of test here. The first kind drives the real Streamlit surface through
AppTest: the dataset table selects one row at a time, the Confirm button gates
what comes after it, and the flow that reaches Plan is the one the user picked.

The second kind is the anti-drift check. Ask now describes each prebuilt
analysis: what it is, how it computes, and which control refuses it. Those are
descriptions of code, so they are re-derived here from the gate and the scripted
samples rather than trusted. A sample that changes its violation and does not
change its copy fails.
"""

from __future__ import annotations

import os
import re

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from sentinel.codegen.allowlist import L3_ALLOWED_IMPORTS  # noqa: E402
from sentinel.codegen.gate import gate_code  # noqa: E402
from sentinel.codegen.generate import _TEMPLATED_CODE  # noqa: E402
from sentinel.govflow.l3 import L3_GRANT, L3_INTENTS  # noqa: E402
from sentinel.govflow.purpose_matrix import (  # noqa: E402
    PURPOSE_LABEL,
    PURPOSE_SCOPE,
    PURPOSES,
)
from sentinel.ui.govflow import (  # noqa: E402
    _ANALYSIS_NOTE,
    _GOVFLOW_STYLES,
    _L3_STYLES,
)

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")

# The fair-lending grant, which is what the L2 samples are gated against.
_L2_GRANT = [
    "age_band",
    "y",
    "pred",
    "credit_amount",
    "duration_months",
    "digital_engagement_score",
]


def _ask(persona_id: str = "analyst", timeout: int = 60) -> AppTest:
    at = AppTest(script_path=APP, default_timeout=timeout)
    at.session_state["persona_id"] = persona_id
    at.run()
    at.button(key="nav_run").click().run()
    return at


# -- step 1: the dataset table ----------------------------------------------


def test_dataset_table_is_a_single_select():
    """One radio per row, and picking one clears the other. Streamlit has no
    radio group that spans containers, so exclusivity is code, and code that
    enforces a rule gets a test."""
    at = _ask()
    assert at.radio(key="gv_dspick_german_credit").value == "german_credit"
    assert at.radio(key="gv_dspick_synthetic_its").value is None
    at.radio(key="gv_dspick_synthetic_its").set_value("synthetic_its").run()
    assert at.radio(key="gv_dspick_german_credit").value is None
    assert at.session_state["govflow_draft"]["dataset_pick"] == "synthetic_its"


def _purpose_grid(at) -> dict[str, bool]:  # noqa: ANN001
    """The rendered purpose grid as {label: permitted}."""
    grid = next(m.value for m in at.markdown if "class='pgrid'" in m.value)
    cells = re.findall(r"<span class='pcell (allow|deny)'>.*?</span>([^<]+)</span>", grid)
    return {label: verdict == "allow" for verdict, label in cells}


def test_picking_a_row_shows_the_purposes_permitted_on_it():
    """Selecting a dataset says what may be asked of it, read off the real
    matrix: german_credit refuses marketing, synthetic_its (Public) refuses
    nothing."""
    at = _ask()
    grid = _purpose_grid(at)
    assert grid[PURPOSE_LABEL["marketing"]] is False
    assert grid[PURPOSE_LABEL["fair_lending"]] is True
    assert set(grid) == {PURPOSE_LABEL[p] for p in PURPOSES}
    at.radio(key="gv_dspick_synthetic_its").set_value("synthetic_its").run()
    assert all(_purpose_grid(at).values())


def test_confirm_gates_the_purpose_and_the_analysis():
    """The Confirm button is load-bearing: before it, there is no purpose
    dropdown and no analysis dropdown, and Plan has nothing to run."""
    at = _ask()
    keys = {w.key for w in at.selectbox}
    assert "govflow_purpose" not in keys
    assert "govflow_style" not in keys
    at.radio(key="govflow_stage").set_value("Plan").run()
    assert any("Configure the request in the Ask stage first" in i.value for i in at.info)

    at.radio(key="govflow_stage").set_value("Ask").run()
    at.button(key="gv_ds_confirm").click().run()
    keys = {w.key for w in at.selectbox}
    assert "govflow_purpose" in keys
    assert "govflow_style" in keys


def test_changing_the_pick_drops_the_confirmation():
    """A purpose and an analysis are declared against a dataset, so swapping the
    dataset invalidates both rather than silently carrying them over."""
    at = _ask()
    at.button(key="gv_ds_confirm").click().run()
    assert at.session_state["govflow_draft"]["dataset_confirmed"] == "german_credit"
    at.radio(key="gv_dspick_synthetic_its").set_value("synthetic_its").run()
    assert at.session_state["govflow_draft"]["dataset_confirmed"] == ""
    assert at.session_state["govflow_draft"]["question"] == ""
    assert at.button(key="gv_ds_confirm") is not None


def test_confirming_the_l3_row_routes_the_run_to_l3():
    """Picking synthetic_its is how the L3 route is chosen now; the old mode
    radio is gone. The draft must come out of Ask on the L3 route."""
    at = _ask(persona_id="admin")
    at.radio(key="gv_dspick_synthetic_its").set_value("synthetic_its").run()
    at.button(key="gv_ds_confirm").click().run()
    draft = at.session_state["govflow_draft"]
    assert draft["is_l3"] is True
    assert draft["dataset"] == "synthetic_its"
    assert draft["purpose"] == "causal_impact"


# -- step 2: the purpose ----------------------------------------------------


def test_purpose_options_are_sentence_case():
    at = _ask()
    at.button(key="gv_ds_confirm").click().run()
    options = at.selectbox(key="govflow_purpose").options
    assert options[0] == "Fair lending review"
    assert all(o[0].isupper() for o in options), options


def test_every_purpose_has_a_scope_and_the_selected_one_renders():
    """A purpose the UI offers but cannot describe is a purpose the user is
    guessing at."""
    for purpose in PURPOSES:
        assert purpose in PURPOSE_SCOPE, purpose
    at = _ask()
    at.button(key="gv_ds_confirm").click().run()
    body = " ".join(m.value for m in at.markdown)
    assert PURPOSE_SCOPE["fair_lending"].covers[:40] in body
    assert PURPOSE_SCOPE["fair_lending"].excludes[:40] in body
    at.selectbox(key="govflow_purpose").set_value("marketing").run()
    body = " ".join(m.value for m in at.markdown)
    assert PURPOSE_SCOPE["marketing"].excludes[:40] in body


# -- step 3: the analysis ---------------------------------------------------


def test_analysis_step_describes_the_selected_analysis():
    at = _ask()
    at.button(key="gv_ds_confirm").click().run()
    body = " ".join(m.value for m in at.markdown)
    assert "Step 3 of 3 · Select the Analysis" in body
    note = _ANALYSIS_NOTE["Fair lending: selection rate by age band (benign)"]
    assert note.method[:40] in body
    assert "fairlearn.metrics" in body


def test_every_prebuilt_analysis_has_a_note():
    for style in list(_GOVFLOW_STYLES) + list(_L3_STYLES):
        note = _ANALYSIS_NOTE.get(style)
        assert note is not None, style
        assert note.what and note.method and note.libraries, style


def test_analysis_notes_name_the_control_the_gate_actually_returns():
    """The honesty check. Every note claiming a control must be describing a
    sample the gate genuinely refuses on that control, and every note claiming
    none must be describing one that genuinely passes."""
    for style, entry in _GOVFLOW_STYLES.items():
        result = gate_code(
            _TEMPLATED_CODE[entry[0]],
            granted_columns=_L2_GRANT,
            allowed_tables=["german_credit"],
        )
        _assert_note_matches(style, result)
    for style, entry in _L3_STYLES.items():
        result = gate_code(
            L3_INTENTS[entry[0]][1],
            granted_columns=L3_GRANT,
            allowed_tables=["synthetic_its"],
            allowed_imports=L3_ALLOWED_IMPORTS,
        )
        _assert_note_matches(style, result)


def _assert_note_matches(style: str, result) -> None:  # noqa: ANN001
    note = _ANALYSIS_NOTE[style]
    fired = {v.control for v in result.violations}
    if note.control:
        assert not result.passed, f"{style}: note names {note.control}, gate passed it"
        assert note.control in fired, f"{style}: gate fired {sorted(fired)}"
    else:
        assert result.passed, f"{style}: note claims no refusal, gate fired {sorted(fired)}"
