"""The login gate (ui-spec 3.1): six persona cards, before any chrome."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import streamlit as st

from sentinel.harness.identity import (
    all_personas,
)
from sentinel.ui.brand import SHIELD_SVG
from sentinel.ui.theme import inject_login_css

# --------------------------------------------------------------------------
# Login gate (ui-spec 3.1): the six personas as cards, before any chrome.
# --------------------------------------------------------------------------



# Card copy per ui-spec 3.1 (display name, role line, capability, tier badge).
# `name` is the spec's card name (shorter than the persona's full config name,
# which carries a qualifier the role line already states).
_LOGIN_CARDS: dict[str, dict] = {
    "analyst": {
        "name": "Data Scientist",
        "role": "First line · certified",
        "cap": "Writes gated code against the fenced API. Runs this walkthrough.",
        "tier": "L2",
        "icon": "DS",
        "hero": True,
    },
    "junior_analyst": {
        "name": "Junior Analyst",
        "role": "First line · uncertified",
        "cap": "Picks a certified analysis and fills typed params. Writes no code.",
        "tier": "L1",
        "icon": "JA",
        "hero": False,
    },
    "model_validator": {
        "name": "Model Validator",
        "role": "Second line · MRM",
        "cap": "Independently reviews fairness and evals. Does not run.",
        "tier": "L0",
        "icon": "MV",
        "hero": False,
    },
    "mrm_approver": {
        "name": "MRM Approver",
        "role": "Second line · sign-off",
        "cap": "Holds the promotion sign-off. Four-eyes, never self-approves.",
        "tier": "L0",
        "icon": "AP",
        "hero": False,
    },
    "auditor": {
        "name": "Internal Auditor",
        "role": "Third line",
        "cap": "Read-only across the audit trail, evidence, and lineage.",
        "tier": "L0",
        "icon": "AU",
        "hero": False,
    },
    "admin": {
        "name": "Platform Admin",
        "role": "Platform",
        "cap": "May toggle a control (audited). L3 on Public data, caps at L2 here.",
        "tier": "L3",
        "icon": "AD",
        "hero": False,
    },
}




def render_login() -> None:
    """The faux sign-in (ui-spec 3.1): always-dark, six persona cards, no auth.
    Picking a card writes persona_id and reruns into the shell."""
    inject_login_css()
    st.markdown(
        f"""
        <div class='login-brand'>{SHIELD_SVG}
          <span class='wm'>SENTINEL</span>
          <span class='sub'>Governed agentic analysis</span></div>
        <div class='login-eyebrow'>Acting as</div>
        <div class='login-h'>Choose an identity</div>
        <div class='login-sub'>Every persona is governed differently. Your role and
        attestations set how much machine autonomy the platform grants, computed as
        the lower of the two.</div>
        """,
        unsafe_allow_html=True,
    )
    personas = {p.id: p for p in all_personas()}
    ordered = [pid for pid in _LOGIN_CARDS if pid in personas]
    for row_ids in (ordered[:3], ordered[3:]):
        cols = st.columns(3)
        for col, pid in zip(cols, row_ids, strict=False):
            card = _LOGIN_CARDS[pid]
            hero_cls = " hero" if card["hero"] else ""
            hero_tag = (
                "<div class='phero-tag'>Runs this walkthrough</div>" if card["hero"] else ""
            )
            with col:
                st.markdown(
                    f"""
                    <div class='pcard{hero_cls}'>
                      <span class='ptier'>{card["tier"]}</span>
                      <div class='picon'>{card["icon"]}</div>
                      <div class='pname'>{card["name"]}</div>
                      <div class='prole'>{card["role"]}</div>
                      <div class='pcap'>{card["cap"]}</div>
                      {hero_tag}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Act as this persona",
                    key=f"login_{pid}",
                    type="primary" if card["hero"] else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.persona_id = pid
                    st.query_params["persona"] = pid
                    st.session_state.section = "Overview"
                    st.session_state.nav_stack = []
                    st.rerun()
    st.markdown(
        "<div class='login-foot'>Faux sign-in for the demo. No credentials, no auth. "
        "Pick anyone to enter.</div>",
        unsafe_allow_html=True,
    )
