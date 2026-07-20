"""Headless smoke test that the Streamlit app renders without exceptions.

Uses Streamlit's AppTest harness (no browser). Guards against import errors and
render-time exceptions across the login gate, the grouped sidebar shell, and
every top-level section.
"""

from __future__ import annotations

import ast
import itertools
import os
import re

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from sentinel.sandbox.execute import DEFAULT_WALL_CLOCK_S  # noqa: E402

# pyarrow's mimalloc allocator segfaults on macOS when Streamlit serializes a
# DataFrame; route to the system allocator before anything imports pyarrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def _assert_run_completed(at) -> None:  # noqa: ANN001
    """Assert a governed run finished, and say which stage did not if it didn't.

    A bare `assert status == "completed"` reports 'error' != 'completed' and
    nothing else, which is useless for the intermittent failures these run-a-
    real-analysis tests produce under a loaded full-suite run: the interesting
    part is always which stage failed and on what control.
    """
    # Streamlit's session-state proxy has no .get(); it reads "get" as a key.
    result = at.session_state["govflow_result"] if "govflow_result" in at.session_state else {}
    if result.get("status") == "completed":
        return
    bad = [
        f"{s.get('stage')}={s.get('status')}: {str(s.get('detail'))[:200]}"
        for s in result.get("stages", [])
        if s.get("status") not in ("ok", "skipped")
    ]
    raise AssertionError(
        f"governed run status={result.get('status')!r}, expected 'completed'. "
        f"Failing stages: {bad or 'none recorded'}"
    )


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
    """The dataset registry is a hand-laid table now, not st.dataframe, so each
    row can carry a real classification chip. All 8 datasets ship onboarded, so
    no row shows the 'registered' badge."""
    from sentinel.datasets import all_datasets

    at = _boot()
    at.button(key="nav_datasets").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    for d in all_datasets():
        assert d.id in body, d.id
    assert "<span class='badge neutral'>registered</span>" not in body


def test_dataset_classification_chips_are_clickable():
    """Classification is the one dataset cell that is a governance decision, so
    it is a control popover: one per row, each carrying that dataset's ceiling
    and permitted purposes off the real matrix."""
    from sentinel.datasets import all_datasets

    at = _boot()
    at.button(key="nav_datasets").click().run()
    chips = [x for x in _popover_labels(at) if _MD_COLOUR.fullmatch(x)]
    assert len(chips) == len(all_datasets())
    captions = " ".join(c.value for c in at.caption)
    for d in all_datasets():
        assert f"Purposes permitted on {d.id}" in captions, d.id


def test_dataset_contract_publishes_the_schema_without_values():
    """The Contract button opens the catalogue view for a dataset: schema,
    dictionary, roles, foreign keys. It is metadata only, and the negative
    assertion is the one that matters -- no cell value reaches the page."""
    import pandas as pd

    from sentinel.datasets.loaders import local_path

    at = _boot(timeout=120)
    at.button(key="nav_datasets").click().run()
    at.button(key="dsopen_german_credit").click().run()
    assert not at.exception
    assert any("Data contract" in s.value for s in at.subheader)

    body = " ".join(m.value for m in at.markdown)
    # The dictionary is published: every column, its role, its description.
    assert "Column dictionary" in body
    assert "applicant_ssn" in body and "role pii" in body
    assert "Metadata only." in body
    # ...and no row of the file is on the page. Sampled over the string columns,
    # whose values would be recognisable if a value column ever crept in.
    head = pd.read_csv(local_path("german_credit"), nrows=40)
    codes = {str(v) for v in head["checking_status"]} | {
        str(v) for v in head["credit_history"]
    }
    for value in codes:
        assert f">{value}<" not in body, f"a cell value reached the page: {value}"


def test_dataset_contract_shows_berka_relationships():
    """The relationship map is metadata an analyst should see before requesting
    either side of a join, so the relational dataset publishes its keys."""
    at = _boot(timeout=120)
    at.button(key="nav_datasets").click().run()
    at.button(key="dsopen_berka").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "Relationships" in body
    assert "disp.client_id" in body and "client.client_id" in body
    # One expander per table in the dictionary.
    assert len(at.expander) == 8


def test_dataset_contract_returns_to_the_registry():
    at = _boot(timeout=120)
    at.button(key="nav_datasets").click().run()
    at.button(key="dsopen_german_credit").click().run()
    at.button(key="ds_contract_back").click().run()
    assert not at.exception
    assert any(s.value == "Dataset registry" for s in at.subheader)
    assert at.session_state["section"] == "Datasets"


def test_model_status_chips_explain_the_eval_gate():
    """A model's status is the eval gate's verdict plus the human decision, so
    the status chip opens the eval gate and states that model's own numbers."""
    from sentinel.platform import model_versions

    at = _boot(timeout=120)
    at.button(key="nav_registry").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    captions = " ".join(c.value for c in at.caption)
    for m in model_versions():
        assert m.version in body, m.version
        assert f"Here: {m.version}" in captions, m.version


def test_no_copy_sends_a_visitor_to_the_sidebar_for_identity():
    """Identity moved from the sidebar to the topbar chip in v7, and the L0
    "you cannot run analyses" caption went on telling people to switch persona
    in the sidebar until 2026-07-20, three versions later.

    Checked against the source rather than one rendered screen, because the
    failure is a class (copy naming a control that has moved) rather than one
    string, and the caption only renders for personas that cannot run.
    """
    ui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sentinel", "ui")
    files = [APP] + [
        os.path.join(ui_dir, n) for n in os.listdir(ui_dir) if n.endswith(".py")
    ]
    for path in files:
        for text in _display_strings(path):
            for line in text.splitlines():
                if "stSidebar" in line:  # a CSS selector, not prose
                    continue
                assert not re.search(r"(persona|identity|acting as)[^.]*sidebar", line, re.I), (
                    f"{os.path.basename(path)} points a visitor at the sidebar for "
                    f"identity, which has lived in the topbar since v7: {line.strip()}"
                )


def _display_strings(path: str) -> list[str]:
    """Every string literal in a module except docstrings.

    Docstrings are excluded deliberately: several of them describe the v7 move
    of identity out of the sidebar and are correct to say so. What must not say
    it is copy a visitor reads.
    """
    with open(path) as f:
        tree = ast.parse(f.read())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstrings
    ]


def test_landing_adoption_bars_are_proportional_and_do_not_shrink():
    """The Adoption tile's weekly bars encode the data in their height, and the
    audit on 2026-07-20 found all four rendering at an identical 17.2px.

    The cause was layout, not data: the value label was a flex sibling of the
    bar, so it took 16.8px out of a 56px column, and the bar - the only child
    with no intrinsic height - absorbed the whole deficit. Identical text in
    every column meant an identical leftover in every column, so four different
    weeks drew four identical rectangles while carrying correct inline heights.

    Both halves are pinned here, because the inline heights alone were never
    wrong and a test that only checked them would have passed throughout.
    """
    at = _boot()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)

    n_cols = body.count("<div class='bcol'>")
    assert n_cols >= 3, "the weekly bar chart is not on the landing tile"
    heights = [int(h) for h in re.findall(r"class='bar' style='height:(\d+)px'", body)]
    values = [int(v) for v in re.findall(r"class='v'>(\d+)</span>", body)]
    assert len(heights) == len(values) == n_cols

    # Height tracks value: equal values give equal bars, and the largest value
    # gives the tallest bar. This is what "four identical rectangles" violated.
    assert len(set(heights)) > 1, "every bar is the same height; the series is flat"
    assert heights[values.index(max(values))] == max(heights)
    for i, j in itertools.combinations(range(len(values)), 2):
        if values[i] == values[j]:
            assert heights[i] == heights[j]
        elif values[i] < values[j]:
            assert heights[i] < heights[j]

    # And the label sits inside the bar rather than above it as a sibling, which
    # is what stopped it consuming the column's height. ui-spec 4.10.
    assert re.search(r"<div class='bar'[^>]*><span class='v'>", body), (
        "the value label is a sibling of the bar again; it will steal the "
        "column height and squash every bar to the same size"
    )


def test_barchart_css_keeps_the_bar_out_of_the_flex_shrink_pool():
    """The CSS half of the same bug. A bar whose height is data must not be a
    shrink candidate, and the value label must not occupy column height."""
    with open(APP) as f:
        css = f.read()
    bar_rule = re.search(r"\.barchart \.bar \{(.*?)\}", css, re.S)
    assert bar_rule and "flex:none" in bar_rule.group(1)
    v_rule = re.search(r"\.barchart \.v \{(.*?)\}", css, re.S)
    assert v_rule and "position:absolute" in v_rule.group(1)
    # A fixed height on the chart plus height:100% on the column is the exact
    # geometry that left the bar 17px to live in.
    chart_rule = re.search(r"\.barchart \{(.*?)\}", css, re.S)
    assert chart_rule and "min-height" in chart_rule.group(1)
    col_rule = re.search(r"\.barchart \.bcol \{(.*?)\}", css, re.S)
    assert col_rule and "height:100%" not in col_rule.group(1)


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


def test_audit_log_section_renders_the_cross_run_ledger():
    at = _boot()
    at.button(key="nav_auditlog").click().run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "Every run the platform has executed" in body
    # The four KPI tiles, by their exact labels.
    labels = {m.label for m in at.metric}
    assert {"Runs logged", "Runs with a refusal", "Four-eyes coverage",
            "Controls fired"} <= labels


def test_audit_log_opens_a_run_and_shows_its_decision_summary():
    """The five things the feature exists to answer, on one screen."""
    at = _boot()
    at.button(key="nav_auditlog").click().run()
    # Open the run seeded to hit CTL-SOD-01: it is the only row that exercises
    # every part of the detail block at once.
    from sentinel.platform.audit_store import audit_runs

    target = next(
        r
        for r in audit_runs()
        if any(
            (e.get("extra") or {}).get("control") == "CTL-SOD-01" for e in r.events
        )
    )
    at.button(key=f"audopen_{target.run_id}").click().run()
    assert not at.exception
    # The decision summary spans markdown and the semantic callouts: the
    # "Caught" line is an st.warning, "nothing refused" an st.success.
    body = " ".join(
        [m.value for m in at.markdown]
        + [w.value for w in at.warning]
        + [e.value for e in at.success]
        + [e.value for e in at.error]
    )
    assert target.run_id in body
    assert "stopped the run" in body  # allowed vs caught, counted
    assert "CTL-SOD-01" in body  # who else had to sign, and what refused
    assert "MRM Approver" in body  # who ran it


def test_audit_log_posture_filter_separates_stopped_from_withheld():
    """A run that finished must never appear under a "stopped" filter.

    The first version of this screen offered one "Refusals only" option that
    meant "a control caught something here", so a promoted run whose only
    refusal was a denied column sat under a label implying it had been refused.
    Two different findings; the filter splits them now.
    """
    from sentinel.platform.audit_store import audit_runs

    runs = audit_runs()
    stopped = [r for r in runs if r.has_refusal and r.stopped_run]
    withheld = [r for r in runs if r.has_refusal and not r.stopped_run]

    assert stopped and withheld, "corpus needs both to make the split meaningful"
    # The whole point: nothing is in both, and every withheld run reached a
    # normal outcome despite a control firing on it.
    assert not ({r.run_id for r in stopped} & {r.run_id for r in withheld})
    for r in withheld:
        assert not r.stopped_run
        assert r.refusal_controls, "a withheld run must still name what fired"


def test_audit_run_opens_as_its_own_screen_and_back_returns():
    """Opening a run is a navigation, not an accordion under the table."""
    from sentinel.platform.audit_store import audit_runs

    target = audit_runs()[0]
    at = _boot()
    at.button(key="nav_auditlog").click().run()
    at.button(key=f"audopen_{target.run_id}").click().run()
    assert not at.exception
    assert at.session_state["section"] == "Audit Run"
    # The ledger is gone; this screen is just the run.
    body = " ".join(m.value for m in at.markdown)
    assert "showing" not in body
    assert target.run_id in body

    at.button(key="audrun_back").click().run()
    assert not at.exception
    assert at.session_state["section"] == "Audit Log"


def test_every_audit_row_has_two_ways_into_the_run():
    """The id is a link and there is an explicit Open button.

    A tertiary button renders as plain body text, so the run id alone read as
    an inert cell value and the drill-down was undiscoverable.
    """
    from sentinel.platform.audit_store import audit_runs

    at = _boot()
    at.button(key="nav_auditlog").click().run()
    keys = {b.key for b in at.button}
    for r in audit_runs()[:5]:
        assert f"audopen_{r.run_id}" in keys, "run id is not a button"
        assert f"audopen2_{r.run_id}" in keys, "row has no explicit Open action"


def test_the_row_open_button_reaches_the_same_run_as_the_id():
    from sentinel.platform.audit_store import audit_runs

    target = audit_runs()[1]
    at = _boot()
    at.button(key="nav_auditlog").click().run()
    at.button(key=f"audopen2_{target.run_id}").click().run()
    assert not at.exception
    assert at.session_state["section"] == "Audit Run"
    assert at.session_state["aud_sel"] == target.run_id


def test_audit_run_deep_link_resolves_a_run_by_url():
    """?run=<id> is a real address, so a run's evidence can be sent to someone.

    The examiner workflow is "send me the evidence for that run", which a
    session-state-only accordion cannot serve.
    """
    at = AppTest(script_path=APP, default_timeout=60)
    at.session_state["persona_id"] = "auditor"
    at.query_params["run"] = "e2694026ad0c"
    at.run()
    assert not at.exception
    assert at.session_state["section"] == "Audit Run"


def test_audit_run_deep_link_to_an_unknown_id_says_so():
    at = AppTest(script_path=APP, default_timeout=60)
    at.session_state["persona_id"] = "auditor"
    at.query_params["run"] = "deadbeefdead"
    at.run()
    assert not at.exception
    assert any("deadbeefdead" in e.value for e in at.error)


def test_audit_log_never_shows_a_refused_run_with_an_empty_caught_cell():
    """The screen-level counterpart to the store-level test.

    A run refused at Ask carries an empty controls_fired, so this would render
    a visibly-refused row with nothing explaining it.
    """
    at = _boot()
    at.button(key="nav_auditlog").click().run()
    body = " ".join(m.value for m in at.markdown)
    # The tier-block run is the case: its only refusal lives in the events.
    assert "tier_block" in body or "CTL-TIER-01" in body


def _popover_labels(at) -> list[str]:  # noqa: ANN001
    """Every popover trigger label on the current screen. A control chip that
    explains itself is a popover, so this is how the tests below tell a wired
    chip from a decorative span."""
    return [p.proto.popover.label for p in at.get("popover")]


_MD_COLOUR = re.compile(r":(?:gray|red|orange|blue|green)(?:-background)?\[([^\]]*)\]")


def test_topbar_carries_no_run_context_chips():
    """The Data and Purpose chips were removed from every screen: they restated
    globally what the Run flow already states where it is actionable. Identity
    and Controls stay, so the assertion is specific to the two context chips
    rather than to the topbar being empty. The muted-key prefix is what marks a
    scope chip; matching plain text would also catch the identity chip, whose
    label happens to start "Data Scientist / Analyst"."""
    at = _boot()
    for screen in ("nav_run", "nav_pipeline", "nav_datasets"):
        at.button(key=screen).click().run()
        assert not at.exception
        labels = _popover_labels(at)
        assert not [
            x for x in labels if x.startswith((":gray[Data]", ":gray[Purpose]"))
        ]
        # Identity and Controls are still there.
        assert "Data Scientist / Analyst" in labels
        assert "Controls" in labels


def test_ask_stage_classification_cell_explains_the_purpose_rule():
    """With the topbar Data chip gone, the Ask stage's dataset table is the one
    surface carrying the purpose line, off the real matrix and the
    classification ceiling rather than hand-written."""
    at = _boot()
    at.button(key="nav_run").click().run()
    captions = [c.value for c in at.caption]
    scope_lines = [c for c in captions if "Purposes permitted on german_credit" in c]
    assert len(scope_lines) == 1
    assert "Restricted" in scope_lines[0]
    assert "fair lending review" in scope_lines[0]


def test_engine_bar_controls_are_clickable():
    """The engine bar's 'Governance implemented' half used to render inert
    <span class='ctlchip'> markup next to the popover mechanism that already
    worked. Every id it names must now be a real control popover."""
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
    # Ask: the one control that acts before any data is touched.
    assert "CTL-PURP-01" in _popover_labels(at)
    # Gate: the parser controls, including CTL-CODE-00 (code must parse), which
    # the checks table named but the engine bar previously omitted.
    at.radio(key="govflow_stage").set_value("Gate").run()
    labels = _popover_labels(at)
    for cid in ("CTL-CODE-00", "CTL-CODE-01", "CTL-EGRESS-01", "CTL-COMPLEX-01"):
        assert cid in labels, cid


def test_architecture_stop_wires_its_controls_and_import_rows():
    """The Architecture stop lists every control by stage, and the import
    allowlist rows each carry the control that decides the row (a module name
    is not a control, so the module chips themselves stay inert)."""
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
    at.radio(key="govflow_stage").set_value("Architecture").run()
    assert not at.exception
    labels = _popover_labels(at)
    assert "CTL-SOD-01" in labels
    # One popover per deny/allow row: allowlist, egress, filesystem, dyncode.
    for cid in ("CTL-CODE-01", "CTL-EGRESS-01", "CTL-CODE-02", "CTL-CODE-03"):
        assert cid in labels, cid
    # The permitted column is the real allowlist, so it may only name libraries
    # the sandbox can import. Until 2026-07-20 it advertised five that were
    # installed nowhere; this screen is where a visitor reads the claim. That
    # the names appear here is only half the check, and the weaker half:
    # test_allowlist_env.py is what holds them to being installed.
    # Word-bounded because the page's CSS carries 'shape', which naive substring
    # matching reads as 'shap'.
    body = " ".join(m.value for m in at.markdown)
    for lib in ("statsmodels", "lifelines", "shap", "dowhy", "econml"):
        assert re.search(rf"\b{lib}\b", body), f"{lib} is granted at L2 but not shown here"


def test_no_screen_hardcodes_the_wall_clock():
    """The Execute panel's mechanics caption claimed a 15s wall clock from v6
    while the sandbox enforced 10s, and now 30s. It reads DEFAULT_WALL_CLOCK_S
    instead of restating it, which is the allowlist lesson applied to a number:
    what a visitor reads should come from the thing that enforces it.

    Checked against the source rather than a rendered page because the caption
    only renders once a run is published, and the regression to catch is someone
    retyping the number, which is visible here and cheap to see.
    """
    ui = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sentinel", "ui")
    for name in os.listdir(ui):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(ui, name)) as f:
            src = f.read()
        hits = re.findall(r"\d+\s*s(?:ec|econds)? wall clock", src)
        assert not hits, f"{name} states a wall clock literally: {hits}"
    # And the constant is what the caption interpolates.
    assert DEFAULT_WALL_CLOCK_S > 0


def test_certification_gates_explain_their_control():
    """A certification gate that names a catalogue control explains it through
    the same popover the run walkthrough uses, not a static .ctrl-chip span."""
    at = _boot(timeout=120)
    at.button(key="nav_registry").click().run()
    assert not at.exception
    labels = _popover_labels(at)
    assert "CTL-SOD-01" in labels
    assert "CTL-EVAL-01" in labels


def test_reclicking_active_nav_item_is_a_noop():
    # Regression: re-clicking the already-active nav item must not reset the
    # visible section's widget state (it did while the handler wrote section +
    # reran unconditionally, truncating the run before the body rendered).
    at = _boot(timeout=120)
    at.button(key="nav_run").click().run()
    at.button(key="gv_ds_confirm").click().run()
    at.radio(key="govflow_stage").set_value("Plan").run()
    at.button(key="gv_run").click().run()
    _assert_run_completed(at)
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
    at.button(key="gv_ds_confirm").click().run()
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
    at.button(key="gv_ds_confirm").click().run()
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
    at.button(key="gv_ds_confirm").click().run()
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
    at.button(key="gv_ds_confirm").click().run()
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
    # The L3 route is chosen by picking its dataset row, then confirming it.
    at.radio(key="gv_dspick_synthetic_its").set_value("synthetic_its").run()
    at.button(key="gv_ds_confirm").click().run()
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
