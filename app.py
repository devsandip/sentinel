"""Sentinel — the Streamlit entry point.

Run: uv run streamlit run app.py

This file is the router and nothing else. It boots the session, decides whether
to show the login gate, and dispatches one screen. Every screen lives in
sentinel/ui/screens/, the chrome around them in sentinel/ui/shell.py, and the
stylesheet in sentinel/ui/theme.py.

It used to be all of that in one 3,200 line module, which is what made any two
branches touching a screen unmergeable, and so produced abandoned worktrees
rather than parallel work.

The analysis underneath is always real. In scripted mode the step narration is
deterministic (labeled honestly); the Live LLM toggle routes narration through
a real model behind a cost cap.
"""

from __future__ import annotations

import streamlit as st

from sentinel.harness.identity import all_personas, get_persona
from sentinel.sandbox.warmup import start_background_warmup
from sentinel.ui.agent_templates import SECTION as SECTION_TEMPLATES
from sentinel.ui.agent_templates import render_agent_templates
from sentinel.ui.govflow import render_govflow
from sentinel.ui.help import render_ask, render_faq
from sentinel.ui.manual import render_manual
from sentinel.ui.screens.adoption import render_adoption
from sentinel.ui.screens.analyses import render_analyses
from sentinel.ui.screens.audit import (
    SECTION_AUDIT_RUN,
    audit_open,
    render_audit_log,
    render_audit_run,
)
from sentinel.ui.screens.datasets import render_datasets
from sentinel.ui.screens.home import render_home
from sentinel.ui.screens.login import render_login
from sentinel.ui.screens.platform import render_platform
from sentinel.ui.screens.registry import render_registry
from sentinel.ui.shell import header, render_sidebar
from sentinel.ui.theme import inject_app_css

st.set_page_config(page_title="Sentinel — Governed Agentic Analysis", layout="wide")

# Warm the sandbox's import caches off-thread, once per server process. A cold
# `import shap` costs 15s or more against a 10s sandbox wall clock, so without
# this the first generated analysis reaching for it is killed by CTL-TIME-01 for
# a reason that has nothing to do with the code. Returns immediately; the
# measurements are in sentinel/sandbox/warmup.py.
start_background_warmup()

inject_app_css()

# Restore the persona from the URL so a refresh keeps the user signed in
# instead of bouncing to the faux login gate. The gate shows only on a truly
# fresh visit: no persona chosen this session and none pinned in the URL.
if "persona_id" not in st.session_state:
    _pinned = st.query_params.get("persona")
    if _pinned and any(p.id == _pinned for p in all_personas()):
        st.session_state.persona_id = _pinned
    else:
        render_login()
        st.stop()

# Deep link. ?run=<id> lands directly on that run's evidence, so an audit-log
# URL opened in a new tab or pasted to a colleague resolves to the run rather
# than the landing screen.
# Honoured once per distinct id, not once per session: keying on a bare flag
# meant a second link pasted into the same tab was silently ignored and you
# landed on the ledger. Re-honour whenever the id in the URL changes; after
# that the nav stack owns where you are, or the param would drag you back on
# every rerun.
if "run" in st.query_params and (
    st.session_state.get("aud_deeplinked") != st.query_params["run"]
):
    st.session_state["aud_deeplinked"] = st.query_params["run"]
    st.session_state["aud_sel"] = st.query_params["run"]
    st.session_state["section"] = SECTION_AUDIT_RUN
    st.session_state.setdefault("nav_stack", []).append("Audit Log")

section = st.session_state.setdefault("section", "Overview")

render_sidebar(section)

persona = get_persona(st.session_state.persona_id)

header(persona)
st.divider()

if section == "Overview":
    render_home(persona)
    st.stop()

if section == "Run":
    # The stepper's "Audit trail" button needs audit_open, and govflow cannot
    # import it: the audit screen imports govflow's control popover, so
    # importing back would be a cycle. Same injection the manual and FAQ take,
    # through session state rather than an argument because the panel that
    # needs it is four calls deep and threading it down would touch every
    # panel signature.
    st.session_state["_govflow_open_audit"] = audit_open
    render_govflow(persona)
    st.stop()

if section == "Analyses":
    render_analyses(persona)
    st.stop()

if section == "Platform":
    render_platform()
    st.stop()

if section == "Datasets":
    render_datasets()
    st.stop()

if section == SECTION_TEMPLATES:
    render_agent_templates(persona)
    st.stop()

if section == "Registry":
    render_registry()
    st.stop()

if section == "Adoption":
    render_adoption()
    st.stop()

if section == "Audit Log":
    render_audit_log(persona)
    st.stop()

if section == "User Manual":
    render_manual()
    st.stop()

if section == "FAQ":
    render_faq()
    st.stop()

if section == "Ask me":
    render_ask()
    st.stop()

if section == SECTION_AUDIT_RUN:
    render_audit_run(persona)
    st.stop()

# Fall-through. Every section above stops explicitly, so reaching here means
# st.session_state.section holds a screen that no longer exists -- in practice
# "Pipeline", left in a session that was open when the screen was retired.
# Land on Overview rather than rendering a blank page below the nav.
st.session_state["section"] = "Overview"
render_home(persona)
