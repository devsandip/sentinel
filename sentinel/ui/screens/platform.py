"""The Platform screen: the central asset repository.

Playbooks, patterns and agent templates, which is the reuse story rather than
the run story."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import streamlit as st

from sentinel.platform import (
    all_patterns,
    load_playbooks,
    reuse_metrics,
)
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED
from sentinel.platform.templates import AVAILABLE, LIVE
from sentinel.ui.agent_templates import SECTION as _SECTION_TEMPLATES
from sentinel.ui.shell import nav_to

# --------------------------------------------------------------------------
# Platform surface (the central asset repository: playbooks, patterns, templates)
# --------------------------------------------------------------------------
_STATUS_LABEL = {
    IN_USE: "in use",
    PLANNED: "planned",
    AVOIDED: "avoided by design",
    "implemented": "implemented",
    "template": "template",
    LIVE: "live",
    AVAILABLE: "available",
}



# Map every status onto one of the three pill colors.
_STATUS_CSS = {
    IN_USE: IN_USE,
    "implemented": IN_USE,
    LIVE: IN_USE,
    AVOIDED: AVOIDED,
    PLANNED: PLANNED,
    "template": PLANNED,
    AVAILABLE: PLANNED,
}




def _pill(status: str) -> str:
    css = _STATUS_CSS.get(status, PLANNED)
    return f"<span class='pill pill-{css}'>{_STATUS_LABEL.get(status, status)}</span>"




def _playbook_pack() -> str:
    """Concatenate every playbook into one downloadable markdown pack."""
    parts = ["# Sentinel AI Playbooks\n"]
    for book in load_playbooks():
        parts.append(f"\n\n---\n\n{book.body.strip()}\n")
    return "".join(parts)




def render_platform() -> None:
    st.subheader("Platform assets")
    st.markdown(
        "<span class='muted'>The central repository of reusable governance assets, "
        "packaged with the app. Playbooks encode the happy path, templates pre-wire "
        "the harness, and the pattern catalog names the architecture in use.</span>",
        unsafe_allow_html=True,
    )

    st.markdown("### AI Playbooks")
    st.markdown(
        "<span class='muted'>Opinionated, end-to-end guides for a use-case class. "
        "Follow the happy path and you comply by construction.</span>",
        unsafe_allow_html=True,
    )
    books = load_playbooks()
    for book in books:
        with st.expander(book.title, expanded=(book.status == "implemented")):
            st.markdown(
                f"{_pill(book.status)} &nbsp; "
                f"<span class='muted'>pattern: {book.pattern} · "
                f"{book.implemented_by}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Job to be done.** {book.jtbd}")
            st.markdown(book.body)
    st.download_button(
        "Download playbook pack (.md)",
        data=_playbook_pack(),
        file_name="sentinel-playbooks.md",
        mime="text/markdown",
    )

    st.divider()
    st.markdown("### Reusable agent templates")
    st.markdown(
        "<span class='muted'>Parameterized starter agents with the harness "
        "pre-wired: tool allow-list, column grant, purposes, tier ceiling and "
        "evals. New agents start from a governed blueprint, not a blank file."
        "</span>",
        unsafe_allow_html=True,
    )
    m = reuse_metrics()
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Templates", m["templates_total"], f"{m['templates_live']} live")
    t2.metric("Agent coverage", f"{m['agents_covered']}/{m['agents_total']}")
    t3.metric("Coverage rate", f"{int(m['coverage_rate'] * 100)}%")
    t4.metric("Est. hours saved", m["est_hours_saved"])
    st.caption(
        "Coverage = live pipeline agents that realize a template. Hours saved is an "
        "illustrative estimate of harness wiring avoided per reuse."
    )
    # The list itself lives on Governance > Agent Templates, where each one can
    # be opened, checked and deployed. Printing the five here as well would be
    # two screens claiming to be the catalogue, which is the confusion the
    # Registry screen already had to unpick once.
    if st.button(
        "Open agent templates", icon=":material/dashboard_customize:", key="plat_tpl"
    ):
        nav_to(_SECTION_TEMPLATES)
    st.caption(
        "The catalogue, the editor and the deploy path are on the Agent Templates "
        "screen under Governance."
    )

    st.divider()
    st.markdown("### Agentic architecture pattern catalog")
    st.markdown(
        "<span class='muted'>Anchored on Anthropic's Building Effective Agents. "
        "Each pattern names where Sentinel uses it, or why it is avoided.</span>",
        unsafe_allow_html=True,
    )
    for p in all_patterns():
        st.markdown(
            f"**{p.name}** {_pill(p.status)}<br>"
            f"<span class='muted'>{p.summary}</span><br>{p.where}",
            unsafe_allow_html=True,
        )
        st.write("")
