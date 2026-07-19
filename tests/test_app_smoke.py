"""Headless smoke test that the Streamlit app renders without exceptions.

Uses Streamlit's AppTest harness (no browser). Guards against import errors and
render-time exceptions across the login gate, the grouped sidebar shell, and
every top-level section.
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


def _boot(persona_id: str = "analyst", timeout: int = 60) -> AppTest:
    """A logged-in AppTest: pre-seed persona_id so the login gate passes.
    The gate itself is covered by the dedicated login tests below."""
    at = AppTest(script_path=APP, default_timeout=timeout)
    at.session_state["persona_id"] = persona_id
    return at.run()


# -- login gate (S1) ---------------------------------------------------------


def test_fresh_session_lands_on_the_login_gate():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    # The gate renders the six persona cards and nothing else: no sidebar nav,
    # no topbar, no section content.
    login_keys = [b.key for b in at.button if b.key and b.key.startswith("login_")]
    assert len(login_keys) == 6
    assert not at.sidebar.selectbox
    assert any("Choose an identity" in m.value for m in at.markdown)


@pytest.mark.parametrize(
    "persona_id",
    ["analyst", "junior_analyst", "model_validator", "mrm_approver", "auditor", "admin"],
)
def test_every_login_card_enters_the_shell_on_overview(persona_id):
    # Each of the six cards must sign in and render the Overview shell without
    # exception, which forces every persona through header() + render_home()
    # (both call resolve_tier_for_dataset with the persona's tier_role).
    at = AppTest(script_path=APP, default_timeout=60).run()
    at.button(key=f"login_{persona_id}").click().run()
    assert not at.exception
    assert at.session_state["persona_id"] == persona_id
    assert at.session_state["section"] == "Overview"
    # The shell is up: grouped sidebar nav + the persona switcher.
    assert at.button(key="nav_run") is not None
    # The persona switcher moved out of the sidebar into the header popover.
    assert at.selectbox(key="persona_switch").value == persona_id


def test_login_cards_cover_every_persona():
    # The gate must offer a card for every persona; a config addition that the
    # hardcoded card map misses would silently drop that identity.
    from sentinel.harness.identity import all_personas

    at = AppTest(script_path=APP, default_timeout=60).run()
    login_ids = {b.key[len("login_"):] for b in at.button if b.key and b.key.startswith("login_")}
    assert login_ids == {p.id for p in all_personas()}


def test_overview_tiles_show_live_numbers():
    at = _boot()
    assert not at.exception
    # The four tiles + CTA render with live numbers: 8 datasets, 3 cert
    # entries, 5 templates, and the seeded run total.
    body = " ".join(m.value for m in at.markdown)
    assert "datasets under classification" in body
    assert "analyses in the certification lifecycle" in body
    assert "agent templates" in body
    assert "models promoted" in body  # Adoption tile, credit-pipeline scoped
    assert at.button(key="cta_run") is not None


def test_cta_routes_to_the_run_walkthrough():
    at = _boot()
    at.button(key="cta_run").click().run()
    assert not at.exception
    assert at.session_state["section"] == "Run"
    assert at.radio(key="govflow_stage").value == "Ask"


# -- sections under the grouped sidebar (S2) ---------------------------------


def test_pipeline_section_renders():
    at = _boot()
    at.button(key="nav_pipeline").click().run()
    assert not at.exception
    # Pre-run, the credit-pipeline section prompts the user to start a run.
    assert any("click Run" in i.value for i in at.info)


def test_platform_section_renders():
    at = _boot()
    at.button(key="nav_platform").click().run()
    assert not at.exception
    assert any(s.value == "Platform assets" for s in at.subheader)
    # Three playbooks, each in an expander, plus the download pack button.
    assert len(at.expander) == 3
    assert any("playbook pack" in b.label for b in at.download_button)


def test_datasets_section_shows_8_of_8_onboarded():
    at = _boot()
    at.button(key="nav_datasets").click().run()
    assert not at.exception
    df = at.dataframe[0].value
    assert len(df) == 8
    assert (df["onboarded"] == "yes").all()


def test_adoption_section_renders_seeded_history():
    at = _boot()
    at.button(key="nav_adoption").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "Runs per week" in body
    assert "Runs per dataset" in body
    # AppTest exposes no accessor for st.bar_chart; the chart's data substance
    # (one row per seeded dataset, matching counts) is asserted at the metrics
    # layer in test_adoption.py::test_per_dataset_matches_the_store.


def test_context_chips_are_run_scoped():
    """Data/Purpose describe a run, so they must not follow the user onto
    screens that have no run in scope (the dashboard and the catalogs were
    inheriting a german_credit / fair-lending default that described nothing)."""
    def _topbar(at):
        return next(m.value for m in at.markdown if "class='topbar'" in m.value)

    at = _boot()
    # Overview: no run, no chips.
    assert "ctx-chip" not in _topbar(at)
    # Pipeline pre-run: still no run, still no chips.
    at.button(key="nav_pipeline").click().run()
    assert "ctx-chip" not in _topbar(at)
    # The Run screen is run-scoped: both chips, from the config defaults.
    at.button(key="nav_run").click().run()
    bar = _topbar(at)
    assert "german_credit" in bar
    assert bar.count("ctx-chip") == 2
    # Leaving the run screen drops them again, even with a draft in session.
    at.button(key="nav_datasets").click().run()
    assert at.session_state["govflow_draft"]["dataset"] == "german_credit"
    assert "ctx-chip" not in _topbar(at)


def test_pipeline_chips_appear_once_a_run_is_scoped():
    """An orchestrator run scopes the Pipeline screen: the Data chip shows the
    run's dataset. That run declares no purpose, so no Purpose chip is faked."""
    at = _boot(timeout=120)
    at.button(key="nav_pipeline").click().run()
    # The hero pipeline's Run button carries no key; the sidebar's does.
    next(b for b in at.button if b.label == "Run" and not b.key).click().run()
    assert not at.exception
    assert at.session_state["run_id"]
    bar = next(m.value for m in at.markdown if "class='topbar'" in m.value)
    assert "german_credit" in bar
    assert bar.count("ctx-chip") == 1
    assert "Purpose" not in bar


def test_reclicking_active_nav_item_is_a_noop():
    # Regression: re-clicking the already-active nav item must not reset the
    # visible section's widget state (it did while the handler wrote section +
    # reran unconditionally, truncating the run before the body rendered).
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    assert at.session_state["govflow_result"]["status"] == "completed"
    assert at.radio(key="govflow_stage").value == "Access"
    # Re-click the active "Run" nav item: the stepper must hold its position.
    at.button(key="nav_run").click().run()
    assert not at.exception
    assert at.session_state["section"] == "Run"
    assert at.radio(key="govflow_stage").value == "Access"


def test_registry_section_shows_certification_lifecycle():
    at = _boot()
    at.button(key="nav_registry").click().run()
    assert not at.exception
    # The certification lifecycle section and its visible refusal both render.
    assert any("certification lifecycle" in m.value for m in at.markdown)
    assert any("cohort-retention" in e.label for e in at.expander)


# -- the governed-run walkthrough (the Run section) --------------------------


def test_run_section_renders():
    at = _boot()
    at.button(key="nav_run").click().run()
    assert not at.exception
    assert any(s.value == "Governed code generation" for s in at.subheader)
    # Pre-run, the stepper prompts the user to configure and run.
    assert any("click Run" in i.value for i in at.info)
    # The stage stepper renders with Ask selected and the config sub-steps.
    assert at.radio(key="govflow_stage").value == "Ask"
    assert any("Step 1 of 3" in m.value for m in at.markdown)


def test_run_stepper_runs_and_walks_stages():
    """A scripted benign run completes and every stage panel renders. This is
    the show-and-tell rework (docs/features/govflow-showtell.md): the stepper
    walks a completed run, so each panel must render without exceptions."""
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
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


def test_run_fix_it_repairs_a_blocked_run():
    """The Gate's Fix it button: an adversarial request blocks, the repair run
    passes the same gate, and the blocked run stays linked for the diff."""
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
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


def test_run_marketing_refusal_walk():
    """A refused purpose blocks at Access; every panel still renders, showing
    the refusal and the skip reasons."""
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
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


def test_run_l1_walk():
    """The Junior Analyst resolves to L1: typed params instead of code, and
    every panel renders the L1 story (no sandbox claims for in-process runs)."""
    at = _boot(persona_id="junior_analyst", timeout=120)
    at.button(key="nav_run").click().run()
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


def test_run_l3_repair_walk():
    """The L3 route with the Platform Admin: adversarial block, Fix it, walk."""
    at = _boot(persona_id="admin", timeout=120)
    at.button(key="nav_run").click().run()
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


# -- persona switching (the retained sidebar switcher) -----------------------


def test_admin_header_chip_toggle_degrades_and_recovers():
    """The header-chip demo device: the Admin can disable a control (badge
    DEGRADED, UNGOVERNED warning); a persona without toggle authority never
    inherits the stale toggle."""
    at = _boot(persona_id="admin", timeout=120)
    at.button(key="nav_pipeline").click().run()
    at.checkbox(key="ctrl_off_pii").set_value(True).run()
    assert not at.exception
    assert any("UNGOVERNED" in e.value for e in at.error)
    # Switch to a persona that cannot toggle: the stale key must not degrade
    # their runs or their banner. The switcher now lives in the header popover.
    at.selectbox(key="persona_switch").set_value("analyst").run()
    assert not any("UNGOVERNED" in e.value for e in at.error)
