"""The application shell: navigation actions and the chrome around a screen.

Everything here is what a screen sits inside rather than what a screen shows.
It left `app.py` with the screens themselves, and it is a module rather than
part of `screens/` because a screen imports the shell and never the reverse.
"""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import streamlit as st

from sentinel.govflow.controls_info import control_info
from sentinel.harness.controls import CONTROL_CATALOG
from sentinel.harness.identity import (
    all_personas,
)
from sentinel.ui.brand import SHIELD_SVG
from sentinel.ui.govflow import (
    render_architecture,
)
from sentinel.ui.nav import NAV_GROUPS, NAV_ICONS, NAV_KEYS


# --------------------------------------------------------------------------
# In-app navigation with history (Back button)
# --------------------------------------------------------------------------
# Screens route through st.session_state.section, which the browser's history
# never sees, so the browser Back button leaves Sentinel entirely. We keep our
# own bounded history stack and expose a Back control that returns to the
# previous screen within the app. (Wiring the browser's own Back button would
# need the st.navigation multipage migration; tracked as a follow-up.)
def nav_to(target: str) -> None:
    """Switch top-level screen, remembering the current one for Back.

    A no-op if already on the target, so re-clicking the active nav item does
    not push a duplicate onto the history or trigger a truncating rerun.
    """
    cur = st.session_state.get("section", "Overview")
    if target == cur:
        return
    stack = st.session_state.setdefault("nav_stack", [])
    stack.append(cur)
    del stack[:-50]  # bound the history so a long session cannot grow it forever
    st.session_state.section = target
    st.rerun()




def nav_back() -> None:
    """Return to the previous screen on the history stack."""
    stack = st.session_state.get("nav_stack", [])
    if not stack:
        return
    st.session_state.section = stack.pop()
    st.rerun()




def render_sidebar(section: str) -> None:
    """The grouped nav rail, plus in-app Back.

    Groups, keys and icons come from sentinel/ui/nav.py, which is also what the
    manual counts its screens from."""
    # In-app Back: return to the previous screen instead of leaving Sentinel.
    # Disabled when there is nowhere to go back to.
    if st.sidebar.button(
        "Back",
        key="nav_back",
        icon=":material/arrow_back:",
        disabled=not st.session_state.get("nav_stack"),
        use_container_width=True,
    ):
        nav_back()

    for glabel, items in NAV_GROUPS:
        if glabel:
            st.sidebar.markdown(f"<div class='gl'>{glabel}</div>", unsafe_allow_html=True)
        for item in items:
            # nav_to no-ops when item == section, so re-clicking the active item
            # does not push a duplicate onto the history or trigger a truncating
            # rerun that would cull the visible section's widgets.
            if st.sidebar.button(
                item,
                key=NAV_KEYS[item],
                type="primary" if item == section else "secondary",
                icon=NAV_ICONS.get(item),
                use_container_width=True,
            ):
                nav_to(item)


# --------------------------------------------------------------------------
# Header + controls
# --------------------------------------------------------------------------
# The six toggleable/explainable harness controls shown in the control plane.
_PLANE_CATALOG = ["pii", "rbac", "guardrails", "audit", "human_gate", "eval_gate"]




def _controls_plane(persona) -> None:  # noqa: ANN001
    """The one Controls popover (ui-spec 4.8): every control, grouped, with the
    Admin-only toggles. Replaces the six vanity chips the brief called out."""
    st.markdown("**Control plane**")
    st.caption(
        "The harness controls on the pipeline (toggleable as a demo device) and "
        "the governed-codegen controls by stage. Disabling is audited and marks "
        "the run UNGOVERNED."
    )
    st.markdown("<span class='eyebrow'>Pipeline harness</span>", unsafe_allow_html=True)
    catalog = {c[0]: c for c in CONTROL_CATALOG}
    for cid in _PLANE_CATALOG:
        info = control_info(cid)
        st.markdown(
            f"<div style='margin:4px 0'><span class='ctlchip pass'>"
            f"<span class='st'></span>{info.name}</span> "
            f"<span class='muted'>{info.what}</span></div>",
            unsafe_allow_html=True,
        )
    # These six were toggleable while the Pipeline screen could start a run
    # with one switched off, and the point of the switch was to watch the
    # failure the control prevents. Retiring that screen took the run with it,
    # so the switches would have stayed on screen changing nothing. A control a
    # visitor can flick with no effect argues the opposite of what this page
    # claims, so they are read-only, and the runs that did exercise them are
    # still in the Audit Log rather than deleted along with the screen.
    st.caption(
        f"Enforced on the credit-risk route ({', '.join(sorted(catalog))}). Those "
        "runs are in the Audit Log, including the ones a control refused. The "
        "governed-codegen route below is what the Run screen executes."
    )
    st.markdown(
        "<span class='eyebrow'>Governed codegen (by stage)</span>",
        unsafe_allow_html=True,
    )
    from sentinel.govflow.controls_info import CONTROLS_INFO

    by_stage: dict[str, list[str]] = {}
    for cid, info in CONTROLS_INFO.items():
        if info.implemented:
            by_stage.setdefault(info.stage, []).append(cid)
    for stage in ["Ask", "Plan", "Access", "Gate", "Execute", "Screen", "Interpret", "Attest"]:
        ids = by_stage.get(stage)
        if not ids:
            continue
        chips = "".join(
            f"<span class='ctlchip'><span class='st'></span>{c}</span> " for c in sorted(ids)
        )
        st.markdown(
            f"<div style='margin:3px 0'><span class='muted'>{stage}:</span> {chips}</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "Every chip in the run walkthrough is clickable and explains what the "
        "control is, why it exists, and what it did on the run."
    )




# --------------------------------------------------------------------------
# Catalog tables (ui-spec 4.4)
# --------------------------------------------------------------------------
# st.dataframe renders every cell as plain text: it cannot carry the .cls and
# .badge chips ui-spec 4.2 specifies, and it certainly cannot carry a popover.
# So the catalog tables are laid out by hand -- a header band plus one
# st.columns row per record -- which is what lets a status chip be the thing
# you click to find out why the status is what it is. The helpers live in
# sentinel/ui/tables.py because the Ask stage's dataset picker needs the same
# table; the skin below is keyed off the container names they use.


def classification_of(dataset: str) -> str:
    from sentinel.govflow import matrix_rows

    return next(
        (r["classification"] for r in matrix_rows() if r["dataset"] == dataset), ""
    )




def header(persona) -> None:  # noqa: ANN001
    """The topbar command frame (ui-spec 2.1): brand lockup, the identity
    switcher, and the Controls popover. Identity lives here only (the sidebar
    block was removed), and it stays because switching persona is how the
    autonomy ladder is shown: the same request resolves to a different tier for
    a different role. The run-context chips (Data, Purpose) were removed: they
    restated globally what the Run flow already states where it is actionable.
    The resolved tier is run-scope too, so it lives in the Run flow rather than
    on this global bar.

    The UNGOVERNED badge that used to sit here went with the Pipeline screen.
    It warned that the next run would execute with a control switched off, and
    no run the app can now start is capable of that: the governed-codegen route
    has no disable path, by construction rather than by policy."""
    # One flex row (ui-spec 2.1): brand left, everything else right, each item
    # sized to its content.
    bar = st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        key="topbar",
    )
    with bar:
        st.markdown(
            f"""
            <div class='brand'>{SHIELD_SVG}
              <span class='wm'>SENTINEL</span>
              <span class='sub'>Governed Agentic Analysis</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ctx = st.container(
            horizontal=True, vertical_alignment="center", key="topbarctx"
        )
        with ctx:
            _persona_switcher(persona)
            with st.popover("Controls"):
                _controls_plane(persona)
            # Architecture sits beside Controls because both describe the
            # platform rather than advance a run. It was the Run stepper's tenth
            # stop, which made a nine-stage rail count to ten.
            with st.popover("Architecture"):
                render_architecture(persona)




def _persona_switcher(persona) -> None:  # noqa: ANN001
    """The single identity surface after login: shows who you are acting as and
    lets you switch. Replaces the old sidebar 'Acting as' block, so the persona
    is shown in exactly one place. A switch pins the new persona in the URL so a
    refresh keeps it."""
    personas = all_personas()
    ids = [p.id for p in personas]
    labels = {p.id: p.name for p in personas}
    caps = ["run" if persona.can_run else "no-run",
            "approve" if persona.can_approve else "no-approve"]
    if persona.read_only:
        caps.append("read-only")
    if persona.can_toggle_controls:
        caps.append("toggle-controls")
    # The trigger is the persona name behind the accent dot, which is the
    # mockup's persona chip (ui-spec 2.1); "Acting as" reads as the selectbox
    # label inside. Spelling it out on the trigger too cost ~60px and was what
    # pushed the topbar onto a second row once the scope chips became buttons.
    with st.popover(persona.name):
        chosen = st.selectbox(
            "Acting as",
            options=ids,
            index=ids.index(persona.id),
            format_func=lambda k: labels[k],
            key="persona_switch",
        )
        if chosen != persona.id:
            st.session_state.persona_id = chosen
            st.query_params["persona"] = chosen
            st.rerun()
        st.caption(f"{persona.role} · {', '.join(caps)}")
        st.caption(persona.description)
