"""Headless smoke test that the Streamlit app renders without exceptions.

Uses Streamlit's AppTest harness (no browser). Guards against import errors and
render-time exceptions in both top-level sections.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

# pyarrow's mimalloc allocator segfaults on macOS when Streamlit serializes a
# DataFrame; route to the system allocator before anything imports pyarrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def test_run_analysis_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    # Pre-run, the analysis section prompts the user to start a run.
    assert any("click Run" in i.value for i in at.info)


def test_platform_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Platform").run()
    assert not at.exception
    assert any(s.value == "Platform assets" for s in at.subheader)
    # Three playbooks, each in an expander, plus the download pack button.
    assert len(at.expander) == 3
    assert any("playbook pack" in b.label for b in at.download_button)


def test_governed_codegen_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Governed codegen").run()
    assert not at.exception
    assert any(s.value == "Governed code generation" for s in at.subheader)
    # Pre-run, the stepper prompts the user to configure and run.
    assert any("click Run" in i.value for i in at.info)
    # The stage stepper renders with Ask selected and the config sub-steps.
    assert at.radio(key="govflow_stage").value == "Ask"
    assert any("Step 1 of 3" in m.value for m in at.markdown)


def test_governed_codegen_stepper_runs_and_walks_stages():
    """A scripted benign run completes and every stage panel renders. This is
    the show-and-tell rework (docs/features/govflow-showtell.md): the stepper
    walks a completed run, so each panel must render without exceptions."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("Governed codegen").run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    assert not at.exception
    pub = at.session_state["govflow_result"]
    assert pub["status"] == "completed"
    # The run lands the user on Access, the first post-run stage.
    assert at.radio(key="govflow_stage").value == "Access"
    for stage in ["Ask", "Plan", "Access", "Generate", "Gate", "Execute",
                  "Screen", "Interpret", "Attest"]:
        at.radio(key="govflow_stage").set_value(stage).run()
        assert not at.exception, f"stage panel {stage} raised"


def test_governed_codegen_fix_it_repairs_a_blocked_run():
    """The Gate's Fix it button: an adversarial request blocks, the repair run
    passes the same gate, and the blocked run stays linked for the diff."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("Governed codegen").run()
    at.selectbox(key="govflow_style").set_value(
        "Adversarial: exfiltrate results to a webhook"
    ).run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    blocked = at.session_state["govflow_result"]
    assert blocked["status"] == "blocked_at_gate"
    assert "CTL-EGRESS-01" in blocked["controls_fired"]
    at.radio(key="govflow_stage").set_value("Gate").run()
    at.button(key="gv_fix").click().run()
    assert not at.exception
    repaired = at.session_state["govflow_result"]
    assert repaired["status"] == "completed"
    assert repaired["repaired_from"] == blocked["run_id"]
    assert at.session_state["govflow_prior"]["run_id"] == blocked["run_id"]


def test_governed_codegen_marketing_refusal_walk():
    """A refused purpose blocks at Access; every panel still renders, showing
    the refusal and the skip reasons."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.radio[0].set_value("Governed codegen").run()
    at.selectbox(key="govflow_purpose").set_value("marketing").run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    pub = at.session_state["govflow_result"]
    assert "CTL-PURP-01" in pub["controls_fired"]
    access = next(s for s in pub["stages"] if s["stage"] == "Access")
    assert access["status"] == "blocked"
    for stage in ["Access", "Generate", "Gate", "Execute", "Screen", "Attest"]:
        at.radio(key="govflow_stage").set_value(stage).run()
        assert not at.exception, f"stage panel {stage} raised on a refused run"


def test_governed_codegen_l1_walk():
    """The Junior Analyst resolves to L1: typed params instead of code, and
    every panel renders the L1 story (no sandbox claims for in-process runs)."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.selectbox[0].set_value("Junior Analyst (uncertified)").run()
    at.sidebar.radio[0].set_value("Governed codegen").run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    assert not at.exception
    pub = at.session_state["govflow_result"]
    assert pub["tier"] == "L1"
    assert pub["status"] == "completed"
    assert pub["generated_code"] == ""
    for stage in ["Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"]:
        at.radio(key="govflow_stage").set_value(stage).run()
        assert not at.exception, f"stage panel {stage} raised on an L1 run"


def test_governed_codegen_l3_repair_walk():
    """The L3 route with the Platform Admin: adversarial block, Fix it, walk."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.selectbox[0].set_value("Platform Admin").run()
    at.sidebar.radio[0].set_value("Governed codegen").run()
    at.radio(key="govflow_mode").set_value("Causal impact (synthetic_its, L3)").run()
    at.selectbox(key="govflow_style_l3").set_value(
        "Adversarial (L3): exfiltrate the series to a collector"
    ).run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    blocked = at.session_state["govflow_result"]
    assert blocked["status"] == "blocked_at_gate"
    at.radio(key="govflow_stage").set_value("Gate").run()
    at.button(key="gv_fix").click().run()
    repaired = at.session_state["govflow_result"]
    assert repaired["status"] == "completed"
    assert repaired["repaired_from"] == blocked["run_id"]
    for stage in ["Gate", "Execute", "Screen", "Interpret", "Attest"]:
        at.radio(key="govflow_stage").set_value(stage).run()
        assert not at.exception, f"stage panel {stage} raised on the L3 repair"


def test_admin_header_chip_toggle_degrades_and_recovers():
    """The header-chip demo device: the Admin can disable a control (badge
    DEGRADED, UNGOVERNED warning); a persona without toggle authority never
    inherits the stale toggle."""
    at = AppTest(script_path=APP, default_timeout=120).run()
    at.sidebar.selectbox[0].set_value("Platform Admin").run()
    at.checkbox(key="ctrl_off_pii").set_value(True).run()
    assert not at.exception
    assert any("UNGOVERNED" in e.value for e in at.error)
    # Switch to a persona that cannot toggle: the stale key must not degrade
    # their runs or their banner.
    at.sidebar.selectbox[0].set_value("Data Scientist / Analyst").run()
    assert not any("UNGOVERNED" in e.value for e in at.error)


def test_registry_section_shows_certification_lifecycle():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Registry").run()
    assert not at.exception
    # The certification lifecycle section and its visible refusal both render.
    assert any("certification lifecycle" in m.value for m in at.markdown)
    assert any("cohort-retention" in e.label for e in at.expander)
