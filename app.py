"""Sentinel — Streamlit UI (six tabs over the governed pipeline).

Run: uv run streamlit run app.py

The analysis underneath is always real. In scripted mode the step narration is
deterministic (labeled honestly); the Live LLM toggle routes narration through
a real model behind a cost cap.
"""

from __future__ import annotations

import html
import json

import pandas as pd
import streamlit as st

from sentinel.analyses import AnalysisEngine, all_analyses, get_analysis
from sentinel.analyses.spec import (
    ENGINE_LINEAR,
    P_BOOL,
    P_CHOICE,
    P_FLOAT,
    P_INT,
    ParamError,
)
from sentinel.datasets import all_datasets, get_dataset, role_note, schema
from sentinel.datasets import available as dataset_available
from sentinel.govflow.controls_info import control_info, implemented_ids
from sentinel.govflow.purpose_matrix import PURPOSE_LABEL, PURPOSES, matrix_rows
from sentinel.govflow.tiers import CLASSIFICATION_CEILING
from sentinel.harness.controls import CONTROL_CATALOG
from sentinel.harness.identity import (
    all_personas,
    get_persona,
    policy_version,
)
from sentinel.harness.model_card import ModelCard, render_markdown, render_pdf
from sentinel.orchestrator import (
    STATUS_REJECTED,
)
from sentinel.platform import (
    adoption_metrics,
    agent_registry,
    all_patterns,
    load_playbooks,
    model_versions,
    reuse_metrics,
)
from sentinel.platform.audit_stages import (
    CANONICAL_STAGES,
    NOT_IN_ROUTE,
    canonical_steps,
)
from sentinel.platform.audit_store import (
    OUTCOME_AWAITING,
    OUTCOME_OK,
    OUTCOME_REFUSED,
    audit_runs,
    visible_runs,
)
from sentinel.platform.audit_store import summary as audit_summary
from sentinel.platform.certification import CertificationError, assign_validator
from sentinel.platform.certification import all_entries as cert_entries
from sentinel.platform.certification import evaluate as evaluate_cert
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED
from sentinel.platform.run_history import KIND_CREDIT_RISK
from sentinel.platform.templates import AVAILABLE, LIVE
from sentinel.sandbox.warmup import start_background_warmup
from sentinel.ui.agent_templates import SECTION as _SECTION_TEMPLATES
from sentinel.ui.agent_templates import render_agent_templates
from sentinel.ui.brand import SHIELD_SVG
from sentinel.ui.govflow import (
    cls_label,
    control_popover,
    purpose_extra,
    render_architecture,
    render_govflow,
)
from sentinel.ui.help import render_ask, render_faq
from sentinel.ui.manual import render_manual
from sentinel.ui.nav import NAV_GROUPS, NAV_ICONS, NAV_KEYS
from sentinel.ui.tables import table_head, table_row, td

st.set_page_config(page_title="Sentinel — Governed Agentic Analysis", layout="wide")

# Warm the sandbox's import caches off-thread, once per server process. A cold
# `import shap` costs 15s or more against a 10s sandbox wall clock, so without
# this the first generated analysis reaching for it is killed by CTL-TIME-01 for
# a reason that has nothing to do with the code. Returns immediately; the
# measurements are in sentinel/sandbox/warmup.py.
start_background_warmup()

ACCENT = "#1e50a0"

# The design system (docs/ui-spec.md): every color is a token from the spec's
# light palette; components style through the tokens. The mockup
# (docs/mockups/sentinel-stepper-mockup.html) is the pixel target.
st.markdown(
    """
    <style>
      :root {
        --canvas:#e9edf4; --surface:#ffffff; --surface-2:#f4f7fb;
        --border:#dde4ee; --border-strong:#c4d0e2;
        --ink:#0f1b2d; --muted:#57647a; --faint:#66717f;
        --accent:#1e50a0; --accent-strong:#17417f; --accent-ink:#ffffff;
        --accent-soft:#e8eef9; --accent-soft-border:#cddbf1;
        --ok:#1b7f3b; --ok-soft:#e6f5ec; --ok-border:#bfe3cc; --ok-ink:#12692f;
        --warn:#b26a00; --warn-soft:#fbf0dc; --warn-border:#f0d9ad; --warn-ink:#8a5200;
        --danger:#b3261e; --danger-soft:#fdeceb; --danger-border:#f3ccc9; --danger-ink:#8f1d17;
        --chrome-bg:#ffffff; --chrome-bg-2:#eef2f8; --chrome-ink:#0f1b2d;
        --chrome-muted:#5b6a82; --chrome-border:#d6deea; --chrome-hover:#e3e9f3;
        --chrome-abg:#e8eef9; --chrome-aink:#1e50a0; --chrome-aborder:#cddbf1;
        --code-bg:#f4f7fc; --code-ink:#2a3852; --code-cm:#8a94a6; --code-kw:#1e50a0;
        --code-str:#1b7f3b; --code-fn:#a35a00; --code-ln:#aab4c6;
        --code-viol-bg:rgba(179,38,30,.08); --code-viol-ln:#b3261e; --code-border:#d6deea;
        --mono:"SF Mono","JetBrains Mono","Fira Code","Cascadia
          Code",ui-monospace,Menlo,Consolas,monospace;
        --shadow-sm:0 1px 2px rgba(15,27,45,.06);
        --shadow-md:0 8px 26px -12px rgba(15,27,45,.22);
        --r-sm:7px; --r-md:11px; --r-lg:16px;
      }
      /* Hide Streamlit's own chrome so this reads as product, not a Streamlit app. */
      #MainMenu, footer { visibility:hidden; }
      header[data-testid="stHeader"] { background:transparent; height:0; }
      .stApp { background:var(--canvas); }
      .block-container { padding-top:1.1rem; max-width:1120px; }
      h1, h2, h3, h4 { letter-spacing:-0.011em; font-weight:650; }

      /* ---------- topbar ---------- */
      /* The topbar is a horizontal container, not a markdown blob: its scope
         chips are real popover triggers so they can explain themselves, and a
         popover cannot live inside raw HTML. Skin per ui-spec 2.1. */
      .st-key-topbar { align-items:center; gap:12px; background:var(--chrome-bg);
        border:1px solid var(--chrome-border); border-radius:var(--r-md);
        padding:10px 16px; box-shadow:var(--shadow-sm); }
      /* nowrap + margin-left:auto keeps the four context/menu buttons together
         and right-aligned. If they ever stop fitting beside the brand, the
         cluster drops to a tidy second row rather than splitting mid-cluster
         with one lonely button underneath. */
      .st-key-topbarctx { align-items:center; gap:7px; flex-wrap:nowrap;
        margin-left:auto; }
      .st-key-topbar .brand { display:flex; align-items:center; gap:11px; }
      .st-key-topbar .brand svg { width:26px; height:26px; display:block; }
      .st-key-topbar .wm { font-weight:700; letter-spacing:.22em; font-size:15px;
        color:var(--chrome-ink); }
      .st-key-topbar .sub { color:var(--chrome-muted); font-size:11px;
                     letter-spacing:.05em;
                     border-left:1px solid var(--chrome-border); padding-left:11px; }
      /* Scope chips wear the neutral chrome pill, not the accent control-chip
         skin: on the topbar they read as context, and the classification badge
         next to them carries the only colour that means something. */
      div[class*="st-key-ctx_"] button[data-testid="stPopoverButton"] {
        background:var(--chrome-bg-2); color:var(--chrome-ink);
        border:1px solid var(--chrome-border); border-radius:999px;
        font-family:inherit; font-size:12px; padding:3px 9px;
      }
      div[class*="st-key-ctx_"] button[data-testid="stPopoverButton"] p {
        font-family:inherit; font-size:12px; font-weight:400;
      }
      div[class*="st-key-ctx_"] button[data-testid="stPopoverButton"]::before {
        display:none;
      }
      /* No dropdown chevron: these read as chips, not menus (the Acting-as and
         Controls buttons next to them keep theirs, because they are menus). */
      div[class*="st-key-ctx_"] button[data-testid="stPopoverButton"]
        span[data-testid="stIconMaterial"] { display:none; }
      .ctx { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
      .ctx-chip {
        display:inline-flex; align-items:center; gap:7px; background:var(--chrome-bg-2);
        border:1px solid var(--chrome-border); color:var(--chrome-ink);
        padding:4px 10px; border-radius:999px; font-size:12px; white-space:nowrap;
      }
      .ctx-chip .k { color:var(--chrome-muted); }
      .ctx-chip .dot { width:6px; height:6px; border-radius:50%; }
      .ctx-chip.tier { border-color:var(--chrome-aborder); }
      .tier-badge { font-weight:700; letter-spacing:.04em; color:var(--accent);
        font-family:var(--mono); }

      /* ---------- sidebar as the nav rail ---------- */
      section[data-testid="stSidebar"] {
        background:var(--chrome-bg-2); border-right:1px solid var(--chrome-border);
        width:222px !important; min-width:222px !important; max-width:222px !important;
      }

      /* ---------- type + text utilities ---------- */
      .eyebrow { font-size:11px; font-weight:700; letter-spacing:.13em;
                 text-transform:uppercase; color:var(--faint); }
      .mono { font-family:var(--mono); font-variant-numeric:tabular-nums; }
      .muted { color:var(--muted); font-size:0.85rem; }
      .flag { color:var(--danger); font-weight:700; }
      .ok { color:var(--ok); font-weight:700; }

      /* ---------- badges + classification chips ---------- */
      .badge { display:inline-flex; align-items:center; gap:6px; font-size:11px;
               font-weight:700; padding:3px 8px; border-radius:999px; letter-spacing:.02em; }
      .badge.ok { background:var(--ok-soft); color:var(--ok-ink); border:1px solid
        var(--ok-border); }
      .badge.warn { background:var(--warn-soft); color:var(--warn-ink); border:1px solid
        var(--warn-border); }
      .badge.danger { background:var(--danger-soft); color:var(--danger-ink); border:1px solid
        var(--danger-border); }
      .badge.info { background:var(--accent-soft); color:var(--accent); border:1px solid
        var(--accent-soft-border); }
      .badge.neutral { background:var(--surface-2); color:var(--muted); border:1px solid
        var(--border-strong); }
      .cls { font-size:10px; font-weight:800; padding:2px 7px; border-radius:5px;
             letter-spacing:.03em; text-transform:uppercase; }
      .cls.public { background:var(--ok-soft); color:var(--ok-ink); border:1px solid
        var(--ok-border); }
      .cls.internal { background:var(--accent-soft); color:var(--accent); border:1px solid
        var(--accent-soft-border); }
      .cls.confidential { background:var(--warn-soft); color:var(--warn-ink); border:1px solid
        var(--warn-border); }
      .cls.restricted { background:var(--danger-soft); color:var(--danger-ink); border:1px solid
        var(--danger-border); }

      /* legacy pill classes kept for the platform surfaces */
      .sentinel-badge { display:inline-block; background:var(--accent); color:#fff; font-weight:600;
        padding:2px 10px; border-radius:12px; font-size:0.8rem; margin-right:6px; }
      .sentinel-badge-warn { background:var(--warn); }
      .ctrl-chip { display:inline-block; background:var(--accent-soft); color:var(--accent);
        font-weight:600;
        padding:2px 9px; border-radius:8px; font-size:0.75rem; margin-right:5px;
        border:1px solid var(--accent-soft-border); font-family:var(--mono); }
      .pill { display:inline-block; padding:1px 9px; border-radius:10px;
        font-size:0.72rem; font-weight:700; margin-left:6px; }
      .pill-in_use { background:var(--ok-soft); color:var(--ok-ink); border:1px solid
        var(--ok-border); }
      .pill-planned { background:var(--accent-soft); color:var(--accent); border:1px solid
        var(--accent-soft-border); }
      .pill-avoided { background:var(--danger-soft); color:var(--danger-ink); border:1px solid
        var(--danger-border); }

      /* ---------- hand-laid catalog tables (ui-spec 4.4) ---------- */
      /* Bordered, radius-clipped, uppercase muted headers on a --surface-2
         band. Built from st.columns rows rather than st.dataframe so a cell can
         hold a chip and a chip can be a popover. */
      div[class*="st-key-tblhead_"] { background:var(--surface-2);
        border:1px solid var(--border); border-radius:var(--r-md) var(--r-md) 0 0;
        padding:7px 12px; margin-bottom:0; }
      div[class*="st-key-tblrow_"] { background:var(--surface);
        border:1px solid var(--border); border-top:none; padding:6px 12px; }
      div[class*="st-key-tblrow_"]:hover { background:var(--surface-2); }
      .th { font-size:10.5px; font-weight:700; letter-spacing:.07em;
            text-transform:uppercase; color:var(--faint); }
      .td { font-size:12.5px; color:var(--ink); display:block; }
      .td.mono { font-family:var(--mono); font-variant-numeric:tabular-nums;
                 font-size:11.5px; }
      /* Chips living in a table cell: tighter than a standalone control chip,
         and no dropdown chevron (they read as cell values, not menus). */
      div[class*="st-key-tblrow_"] button[data-testid="stPopoverButton"],
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"] {
        padding:1px 8px; min-height:1.4rem; }
      div[class*="st-key-tblrow_"] button[data-testid="stPopoverButton"]::before,
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"]::before {
        display:none; }
      div[class*="st-key-tblrow_"] button[data-testid="stPopoverButton"]
        span[data-testid="stIconMaterial"],
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"]
        span[data-testid="stIconMaterial"] { display:none; }
      /* The run id in the Audit Log is the drill-down link. Streamlit renders
         a tertiary button as plain body text, which made the id look like an
         inert cell value, so it gets link affordances explicitly: accent
         colour, mono, and an underline on hover. */
      div[class*="st-key-tblrow_aud"] button[data-testid="stBaseButton-tertiary"] {
        font-family:var(--mono); font-size:12px; font-weight:700;
        color:var(--accent); padding:0; min-height:0; text-align:left; }
      div[class*="st-key-tblrow_aud"] button[data-testid="stBaseButton-tertiary"]:hover {
        color:var(--accent-strong); text-decoration:underline; }
      div[class*="st-key-tblrow_aud"] button[data-testid="stBaseButton-tertiary"] p {
        font-family:var(--mono); font-size:12px; font-weight:700; }
      /* The trailing Open cell: small, quiet until hovered, never wider than
         its column. */
      div[class*="st-key-tblrow_aud"] button[data-testid="stBaseButton-secondary"] {
        padding:2px 9px; min-height:1.6rem; font-size:11.5px; white-space:nowrap; }

      /* A column header that explains itself keeps the header's own type, but
         earns a dotted underline so it does not read as inert like its
         neighbours. */
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"] {
        background:transparent; border-color:transparent;
        border-bottom:1px dotted var(--faint); border-radius:0; padding:1px 2px; }
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"]:hover {
        border-bottom-color:var(--accent); transform:none; box-shadow:none; }
      div[class*="st-key-tblhead_"] button[data-testid="stPopoverButton"] p {
        font-family:inherit; font-size:10.5px; font-weight:700;
        letter-spacing:.07em; text-transform:uppercase; }
      /* A push button living in a table cell (the dataset registry's Contract
         drill-down): compact, and never wrapping its label mid-word, which is
         what a narrow cell does to a two-syllable button by default. */
      div[class*="st-key-tblrow_"] div[data-testid="stButton"] button {
        padding:2px 8px; min-height:1.5rem; white-space:nowrap; font-size:11.5px; }
      div[class*="st-key-tblrow_"] div[data-testid="stButton"] button p {
        font-size:11.5px; white-space:nowrap; }
      /* A selectable row: the mockup's .row-sel accent tint plus the .rowgood
         left bar, on the row the user has picked. The key carries the state
         because CSS cannot reach a Streamlit container any other way. */
      div[class*="st-key-tblrow_sel_"] { background:var(--accent-soft);
        box-shadow:inset 3px 0 0 var(--accent); }
      div[class*="st-key-tblrow_sel_"]:hover { background:var(--accent-soft); }
      /* The per-row radio is the select control: no label, no gap, and the
         option text is the dataset id, so the cell reads as one thing. */
      div[class*="st-key-tblrow_"] div[data-testid="stRadio"] { margin:0; }
      div[class*="st-key-tblrow_"] div[data-testid="stRadio"] label { padding:0; }
      div[class*="st-key-tblrow_"] div[data-testid="stRadio"] code {
        font-size:11.5px; }

      /* ---------- purpose grid + scope notes (Ask stage, ui-spec 3.3) ------ */
      /* The mockup's .pmatrix: every purpose in the matrix for one dataset,
         permitted or refused, shown before the dataset is committed to. */
      .pgrid { display:flex; flex-wrap:wrap; gap:7px; margin:2px 0 4px; }
      .pcell { display:inline-flex; align-items:center; gap:7px; padding:5px 10px;
        border-radius:var(--r-md); border:1px solid var(--border);
        background:var(--surface); font-size:12px; }
      .pcell .mk { font-family:var(--mono); font-weight:700; }
      .pcell.allow { border-color:var(--ok-border); background:var(--ok-soft);
        color:var(--ok-ink); }
      .pcell.deny { border-color:var(--danger-border); background:var(--danger-soft);
        color:var(--danger-ink); }
      /* A definition block for "what this is / what it is not": the same shape
         serves a purpose's scope and an analysis's method. */
      .scope { border:1px solid var(--border); border-left:3px solid var(--accent);
        border-radius:var(--r-md); background:var(--surface-2);
        padding:9px 13px; margin:8px 0 2px; }
      .scope .r { display:grid; grid-template-columns:96px 1fr; gap:10px;
        padding:3px 0; align-items:baseline; }
      .scope .k { font-size:9.5px; font-weight:700; letter-spacing:.09em;
        text-transform:uppercase; color:var(--faint); }
      .scope .v { font-size:12.5px; color:var(--ink); }

      /* ---------- the data contract (dataset catalogue detail) ---------- */
      /* The contract view publishes metadata only, so the one thing it must
         never look like is a data grid. The notice band says so in the page,
         and the column table carries no value column at all. */
      .cnotice { border:1px solid var(--accent-soft-border); border-left:3px solid
        var(--accent); background:var(--accent-soft); border-radius:var(--r-md);
        padding:10px 14px; margin:6px 0 14px; font-size:12.5px; color:var(--ink); }
      .cnotice b { font-weight:650; }
      .cnotice .ids { font-family:var(--mono); font-size:11.5px; color:var(--accent); }
      /* Role chips. Colour carries meaning: red for what is never granted,
         amber for what a purpose must justify, neutral for ordinary inputs. */
      .role { font-size:10px; font-weight:700; padding:2px 7px; border-radius:5px;
        letter-spacing:.02em; white-space:nowrap; border:1px solid var(--border);
        background:var(--surface-2); color:var(--muted); }
      .role.pii { background:var(--danger-soft); color:var(--danger-ink);
        border-color:var(--danger-border); }
      .role.protected { background:var(--warn-soft); color:var(--warn-ink);
        border-color:var(--warn-border); }
      .role.target, .role.treatment { background:var(--accent-soft); color:var(--accent);
        border-color:var(--accent-soft-border); }
      .role.outcome, .role.entity_id, .role.timestamp { background:var(--surface-2);
        color:var(--faint); }
      /* The role legend: what each role in this dataset costs a requester at
         Access, stated once rather than on every row it applies to. */
      .rleg { border:1px solid var(--border); border-radius:var(--r-md);
        background:var(--surface-2); padding:8px 12px; margin:4px 0 10px; }
      .rleg .r { display:grid; grid-template-columns:88px 1fr; gap:10px;
        align-items:baseline; padding:2px 0; }
      .rleg .v { font-size:12px; color:var(--muted); }
      /* The column dictionary. One HTML table rather than per-row Streamlit
         containers: lendingclub is 152 columns wide and a widget per row would
         crawl. Nothing here needs a popover, so nothing here needs a widget. */
      .dict { width:100%; border-collapse:collapse; margin:2px 0 6px; }
      .dict th { font-size:10.5px; font-weight:700; letter-spacing:.07em;
        text-transform:uppercase; color:var(--faint); text-align:left;
        padding:7px 10px; border-bottom:1px solid var(--border-strong); }
      .dict td { font-size:12.5px; color:var(--ink); padding:7px 10px;
        border-bottom:1px solid var(--border); vertical-align:top; }
      .dict tr:hover td { background:var(--surface-2); }
      .dict .cn { font-family:var(--mono); font-size:12px; white-space:nowrap; }
      .dict .ty { font-family:var(--mono); font-size:11.5px; color:var(--muted); }
      .dict .undoc { color:var(--faint); font-style:italic; }
      .dict .drv { font-size:9.5px; font-weight:700; letter-spacing:.05em;
        color:var(--faint); border:1px solid var(--border); border-radius:4px;
        padding:1px 5px; margin-left:6px; }
      /* Foreign keys, as the catalogue publishes them: an edge list, not an
         ERD. The relationships are the fact; a diagram would be decoration. */
      .fk { display:grid; grid-template-columns:1fr auto; gap:10px;
        align-items:baseline; padding:7px 12px; border:1px solid var(--border);
        border-radius:var(--r-sm); background:var(--surface); margin-bottom:6px; }
      .fk .e { font-family:var(--mono); font-size:12px; color:var(--ink); }
      .fk .e .ar { color:var(--accent); font-weight:700; padding:0 4px; }
      .fk .c { font-size:11px; color:var(--faint); white-space:nowrap; }
      .fk .n { grid-column:1 / -1; font-size:11.5px; color:var(--muted); }
      /* Documentation coverage: a bar, because the number is a governance
         metric and a bar is how a governance office reads one. */
      .cov { height:6px; border-radius:3px; background:var(--surface-2);
        border:1px solid var(--border); overflow:hidden; margin-top:6px; }
      .cov > i { display:block; height:100%; background:var(--accent); }

      /* ---------- cards ---------- */
      div[data-testid="stVerticalBlockBorderWrapper"] {
        background:var(--surface); border:1px solid var(--border) !important;
        border-radius:var(--r-lg); box-shadow:var(--shadow-sm);
      }
      div[data-testid="stMetric"] {
        background:var(--surface); border:1px solid var(--border); border-radius:var(--r-md);
        padding:12px 15px;
      }
      div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:var(--r-md); }
      div[data-testid="stExpander"] details {
        border:1px solid var(--border); border-radius:var(--r-md); background:var(--surface);
      }

      /* ---------- notes / alerts ---------- */
      div[data-testid="stAlert"] { border-radius:var(--r-md); }

      /* ---------- control chips (popover triggers) ---------- */
      div[data-testid="stPopover"] > div > button {
        background:var(--accent-soft); color:var(--accent);
        border:1px solid var(--accent-soft-border);
        border-radius:8px; font-size:11.5px; font-weight:600;
        padding:2px 9px; min-height:1.65rem; line-height:1.2; white-space:nowrap;
        font-family:var(--mono);
      }
      div[data-testid="stPopover"] > div > button p {
        white-space:nowrap; font-size:11.5px; font-family:var(--mono); font-weight:600;
      }
      div[data-testid="stPopover"] > div > button::before {
        content:""; display:inline-block; width:7px; height:7px; border-radius:50%;
        background:var(--accent); margin-right:6px; flex:none;
      }
      div[data-testid="stPopover"] > div > button:hover {
        box-shadow:var(--shadow-sm); transform:translateY(-1px);
          border-color:var(--accent-soft-border);
      }

      /* ---------- phead + In/Does/Out + engine bar (stage panels) ---------- */
      .phead { margin:2px 0 14px; }
      .phead .eyebrow { display:flex; align-items:center; gap:9px; }
      .phead h2 { font-size:26px; margin:8px 0 6px; color:var(--ink); }
      .phead .lede { color:var(--muted); font-size:14.5px; max-width:64ch; }
      .iodid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:14px 0 16px; }
      .iocard { background:var(--surface-2); border:1px solid var(--border);
                border-radius:var(--r-md); padding:11px 13px; }
      .iocard .k { font-size:10.5px; font-weight:700; letter-spacing:.11em;
                   text-transform:uppercase; color:var(--faint); margin-bottom:5px; }
      .iocard .v { font-size:12.5px; color:var(--ink); }
      .iocard.does { background:var(--accent-soft); border-color:var(--accent-soft-border); }
      /* The engine bar's governance chips are real popovers (they have to be, to
         be clickable), so the strip is a horizontal container rather than one
         markdown blob. Skin per ui-spec 4.6. */
      div[class*="st-key-gv_eb_"] { flex-wrap:wrap; align-items:center; gap:7px;
                   margin:0 0 14px; padding:10px 13px; background:var(--surface);
                   border:1px solid var(--border); border-radius:var(--r-md);
                   box-shadow:var(--shadow-sm); }
      div[class*="st-key-gv_eb_"] .eb-sep { display:inline-block; width:1px; height:15px;
                   vertical-align:middle; margin:0 5px 0 0; }
      /* Chip rows that are label + control popovers (Architecture stop, the
         import allowlist, the certification gates): no card skin, just a tight
         inline row. */
      div[class*="st-key-gv_arch_"], div[class*="st-key-gv_imp_"],
      div[class*="st-key-cert_gate_"] { flex-wrap:wrap; align-items:center; gap:7px;
                   margin:0; padding:0; }
      .eb-lab { font-size:9.5px; font-weight:700; letter-spacing:.11em;
                text-transform:uppercase; color:var(--faint); }
      .eb-sep { width:1px; align-self:stretch; background:var(--border); margin:0 5px; }
      .lib { display:inline-flex; align-items:center; gap:6px; font-family:var(--mono);
             font-size:11.5px; font-weight:600; padding:3px 9px; border-radius:8px;
             border:1px solid var(--border-strong); background:var(--surface-2); color:var(--ink); }
      .lib .d { width:6px; height:6px; border-radius:50%; background:#2f9c94; }
      .lib.none { color:var(--muted); font-family:inherit; font-style:italic; border-style:dashed; }
      .ctlchip { display:inline-flex; align-items:center; gap:6px; font-family:var(--mono);
             font-size:11.5px; font-weight:600; padding:3px 9px; border-radius:8px;
             border:1px solid var(--accent-soft-border); background:var(--accent-soft);
               color:var(--accent); }
      .ctlchip .st { width:7px; height:7px; border-radius:50%; background:var(--faint); }
      .ctlchip.pass { background:var(--ok-soft); border-color:var(--ok-border);
        color:var(--ok-ink); }
      .ctlchip.pass .st { background:var(--ok); }
      .ctlchip.fired { background:var(--warn-soft); border-color:var(--warn-border);
        color:var(--warn-ink); }
      .ctlchip.fired .st { background:var(--warn); }
      .ctlchip.block { background:var(--danger-soft); border-color:var(--danger-border);
        color:var(--danger-ink); }
      .ctlchip.block .st { background:var(--danger); }

      /* ---------- the stepper rail (the govflow stage radio, restyled) ---------- */
      .st-key-govflow_stage div[role="radiogroup"] {
        display:flex; flex-wrap:nowrap; align-items:flex-start; gap:0; counter-reset:step;
        background:var(--chrome-bg-2); border:1px solid var(--chrome-border);
        border-radius:var(--r-md); padding:14px 10px 12px; overflow-x:auto;
      }
      .st-key-govflow_stage div[role="radiogroup"] label {
        position:relative; flex:1 0 auto; min-width:88px; margin:0; padding:0 4px;
        display:flex; flex-direction:column; align-items:center; gap:6px;
        counter-increment:step;
      }
      .st-key-govflow_stage div[role="radiogroup"] label > div > div > div:nth-of-type(1) {
        display:none;  /* the native radio circle; the node replaces it */
      }
      .st-key-govflow_stage div[role="radiogroup"] label::before {
        content:counter(step); width:30px; height:30px; border-radius:50%;
        display:grid; place-items:center; font-family:var(--mono);
        font-size:12.5px; font-weight:700; z-index:1;
        background:var(--chrome-bg); border:2px solid var(--chrome-border);
        color:var(--chrome-muted); transition:transform .15s ease;
      }
      .st-key-govflow_stage div[role="radiogroup"] label[data-selected="true"]::before {
        background:var(--accent); border-color:var(--accent); color:#fff;
        box-shadow:0 0 0 4px rgba(47,111,208,.28); transform:scale(1.06);
      }
      .st-key-govflow_stage div[role="radiogroup"] label::after {
        content:""; position:absolute; top:15px; left:calc(-50% + 15px);
        right:calc(50% + 15px); height:2px; background:var(--chrome-border);
      }
      .st-key-govflow_stage div[role="radiogroup"] label:first-child::after { display:none; }
      .st-key-govflow_stage div[role="radiogroup"] label:last-child::before {
        content:"\\25A6"; border-style:dashed; font-size:14px;
      }
      .st-key-govflow_stage div[role="radiogroup"] label:last-child::after {
        background:none; border-top:2px dashed var(--chrome-border); height:0;
      }
      .st-key-govflow_stage div[role="radiogroup"] label p {
        font-size:11.5px; color:var(--chrome-muted); font-weight:600;
        letter-spacing:.02em; white-space:nowrap;
      }
      .st-key-govflow_stage div[role="radiogroup"] label[data-selected="true"] p {
        color:var(--chrome-ink);
      }

      /* ---------- code block ---------- */
      .codeblk { background:var(--code-bg); border:1px solid var(--code-border);
                 border-radius:var(--r-md); overflow:auto; margin:6px 0; }
      .codeblk table { border-collapse:collapse; font-family:var(--mono);
                       font-size:12.5px; width:100%; }
      .codeblk td { border:0; padding:2px 0; color:var(--code-ink); white-space:pre; }
      .codeblk td.ln { width:38px; text-align:right; padding-right:14px;
                       color:var(--code-ln); user-select:none; }
      .codeblk tr.viol td { background:var(--code-viol-bg); }
      .codeblk tr.viol td.ln { color:var(--code-viol-ln); font-weight:700; }
      .codeblk .cm { color:var(--code-cm); }
      .codeblk .kw { color:var(--code-kw); }
      .codeblk .stlit { color:var(--code-str); }
      .codeblk .viol-tag { color:var(--code-viol-ln); font-weight:700; }

      /* ---------- spec tables ---------- */
      .gv-scroll { overflow-x:auto; border:1px solid var(--border); border-radius:var(--r-md); }
      /* Audit Log step detail: the step's own account of what happened,
         indented under its name so the status line stays scannable. */
      .stepdetail { font-size:12.5px; color:var(--muted); margin:2px 0 4px 18px;
        padding-left:10px; border-left:2px solid var(--border); }
      .stepmeta { font-size:11.5px; color:var(--faint); margin:0 0 6px 18px;
        padding-left:10px; }
      .stepmeta .fired { color:var(--warn-ink); font-weight:700; }
      .stepdetail b { color:var(--ink); }
      .stepmeta code, .stepdetail code { font-family:var(--mono); font-size:11px;
        background:var(--surface-2); padding:1px 4px; border-radius:4px; }
      .gv-table { border-collapse:collapse; font-size:13px; width:100%; }
      .gv-table th { text-align:left; font-size:11px; letter-spacing:.06em;
                     text-transform:uppercase; color:var(--muted); font-weight:700;
                     padding:9px 13px; background:var(--surface-2);
                     border-bottom:1px solid var(--border); white-space:nowrap; }
      .gv-table td { padding:8px 13px; border-bottom:1px solid var(--border); }
      .gv-table tbody tr:last-child td { border-bottom:0; }
      .gv-withheld { color:var(--danger-ink); text-decoration:line-through;
                     text-decoration-color:var(--danger); }
      .gv-masked { color:var(--faint); font-family:var(--mono); letter-spacing:2px; }
      .gv-struck td, td.gv-struck { color:var(--danger-ink); background:var(--danger-soft);
                  text-decoration:line-through; text-decoration-color:var(--danger); }
      .gv-amber td, tr.gv-amber { background:var(--warn-soft); }
      .gv-below { color:var(--warn-ink); font-size:0.75rem; font-weight:600; white-space:nowrap; }
      .stage-status { margin:6px 0 10px 0; }

      /* ---------- the Gate's read (Gate stage) ---------- */
      /* Nine checks as nine cells, each carrying the count of constructs it
         actually judged. The count is the point: a tick mark cannot tell a
         check that read 16 names from one that had nothing to read, and the
         four states below are four different facts (see codegen/gate.py). */
      .gatein { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
                gap:10px; margin:4px 0 18px; }
      .gatein .t { background:var(--surface); border:1px solid var(--border);
                border-radius:var(--r-md); padding:10px 13px; box-shadow:var(--shadow-sm); }
      .gatein .t .k { font-size:9.5px; font-weight:700; letter-spacing:.11em;
                text-transform:uppercase; color:var(--faint); margin-bottom:5px; }
      .gatein .t .v { font-size:13px; color:var(--ink); font-weight:600; }
      .gatein .t .s { font-family:var(--mono); font-size:11px; color:var(--muted);
                margin-top:3px; word-break:break-word; }

      .gateread { display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
                gap:9px; margin:4px 0 6px; }
      .gateread .cell { border:1px solid var(--border); border-radius:var(--r-md);
                padding:9px 11px 10px; background:var(--surface); min-width:0; }
      .gateread .cell .cid { font-family:var(--mono); font-size:9.5px; font-weight:700;
                letter-spacing:.04em; color:var(--faint); display:flex; align-items:center;
                gap:5px; }
      .gateread .cell .cid .d { width:7px; height:7px; border-radius:50%;
                background:var(--faint); flex:none; }
      /* The count and its unit are siblings, not nested: nesting the unit inside
         the mono number would inherit mono, and there is no sans token to
         override it with. */
      .gateread .cell .nrow { display:flex; align-items:baseline; gap:5px;
                margin:5px 0 1px; min-width:0; }
      .gateread .cell .n { font-family:var(--mono); font-size:23px; font-weight:700;
                font-variant-numeric:tabular-nums; line-height:1.15; color:var(--ink); }
      .gateread .cell .nu { font-size:10.5px; font-weight:600; letter-spacing:.02em;
                color:var(--muted); overflow:hidden; text-overflow:ellipsis;
                white-space:nowrap; }
      .gateread .cell .lab { font-size:11px; line-height:1.32; color:var(--muted); }
      .gateread .cell.cleared { background:var(--ok-soft); border-color:var(--ok-border); }
      .gateread .cell.cleared .cid, .gateread .cell.cleared .n { color:var(--ok-ink); }
      .gateread .cell.cleared .cid .d { background:var(--ok); }
      .gateread .cell.cleared .lab { color:var(--ok-ink); opacity:.86; }
      .gateread .cell.refused { background:var(--danger-soft); border-color:var(--danger-border); }
      .gateread .cell.refused .cid, .gateread .cell.refused .n { color:var(--danger-ink); }
      .gateread .cell.refused .cid .d { background:var(--danger); }
      .gateread .cell.refused .lab { color:var(--danger-ink); opacity:.86; }
      /* Armed, but this code held nothing for it to judge. Not an assurance. */
      .gateread .cell.none { background:var(--surface-2); border-style:dashed; }
      .gateread .cell.none .n { color:var(--faint); }
      /* Could not run: its rule was never supplied. A gap, so it reads amber. */
      .gateread .cell.unarmed { background:var(--warn-soft); border-color:var(--warn-border); }
      .gateread .cell.unarmed .cid, .gateread .cell.unarmed .n { color:var(--warn-ink); }
      .gateread .cell.unarmed .cid .d { background:var(--warn); }
      .gateread .cell.unarmed .lab { color:var(--warn-ink); opacity:.86; }

      /* The verdict, stated once, with the reason under it. */
      .gvd { border:1px solid var(--border); border-left-width:4px;
             border-radius:var(--r-md); padding:12px 15px; margin:2px 0 14px;
             background:var(--surface); }
      .gvd.pass { border-left-color:var(--ok); background:var(--ok-soft);
             border-color:var(--ok-border); border-left-color:var(--ok); }
      .gvd.block { border-left-color:var(--danger); background:var(--danger-soft);
             border-color:var(--danger-border); border-left-color:var(--danger); }
      .gvd .h { font-size:15px; font-weight:700; letter-spacing:.01em; margin-bottom:5px; }
      .gvd.pass .h { color:var(--ok-ink); }
      .gvd.block .h { color:var(--danger-ink); }
      .gvd .why { font-size:13px; line-height:1.5; color:var(--ink); max-width:78ch; }
      .gvd .why code { font-family:var(--mono); font-size:11.5px; background:var(--surface);
             padding:1px 5px; border-radius:4px; border:1px solid var(--border); }
      .gvd .then { font-size:12px; color:var(--muted); margin-top:6px; }

      /* Evidence chips: one construct the gate judged. */
      .ev { display:inline-block; font-family:var(--mono); font-size:11px; font-weight:600;
            padding:2px 7px; border-radius:6px; margin:2px 4px 2px 0;
            background:var(--ok-soft); color:var(--ok-ink);
            border:1px solid var(--ok-border); white-space:nowrap; }
      .ev.no { background:var(--danger-soft); color:var(--danger-ink);
            border-color:var(--danger-border); }
      .ev.muted { background:var(--surface-2); color:var(--muted); border-color:var(--border);
            font-family:inherit; font-style:italic; }
      .evline { font-size:11.5px; color:var(--faint); font-family:var(--mono); }
      /* The read, drawn in the code gutter: which check judged this line. */
      .codeblk td.rd { width:74px; padding-right:12px; text-align:right;
            font-size:9.5px; font-weight:700; letter-spacing:.03em;
            color:var(--code-ln); user-select:none; white-space:nowrap; opacity:.85; }
      .codeblk tr.viol td.rd { color:var(--code-viol-ln); }

      /* ---------- sidebar nav groups (ui-spec 2.2) ---------- */
      /* Rhythm from the mockup's .sidenav: rows stack flush (the padding is the
         row height), and the only vertical air is between groups. Streamlit's
         default 16px block gap doubled that and left the rail loose. */
      section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0; }
      .gl { font-size:9.5px; font-weight:700; letter-spacing:.11em; text-transform:uppercase;
            color:var(--chrome-muted); padding:0 11px; margin:14px 0 6px 0; }
      /* Streamlit puts margin-bottom:-16px on every stMarkdownContainer to cancel
         the 16px that a markdown <p> carries. .gl is a bare div with a 6px bottom
         margin, so that -16px over-pulls: it eats the 6px and 10px more, dragging
         the next nav row up over the label. The row then paints its hover/active
         background across the group name and hides it. Drop the negative margin on
         the containers that hold a .gl; nothing else in the rail is markdown. */
      section[data-testid="stSidebar"]
        [data-testid="stMarkdownContainer"]:has(> .gl) { margin-bottom:0; }
      section[data-testid="stSidebar"] .stButton button {
        display:flex; justify-content:flex-start; width:100%; padding:9px 11px;
        border-radius:9px; border:1px solid transparent; background:transparent;
        color:var(--chrome-muted); font-size:13.5px; font-weight:600; min-height:0;
      }
      section[data-testid="stSidebar"] .stButton button:hover {
        background:var(--chrome-hover); color:var(--chrome-ink); border-color:transparent;
      }
      section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background:var(--chrome-abg); color:var(--chrome-aink);
        border:1px solid var(--chrome-aborder);
      }
      section[data-testid="stSidebar"] .stButton button p { font-size:13.5px; line-height:1.25; }
      /* icon buttons wrap icon+label in an inner flex div that centers by
         default; left-align it so each link sits under its group header */
      section[data-testid="stSidebar"] .stButton button > div { justify-content:flex-start; }
      /* keep Back reachable: pin it to the top of the scrolling rail, with a
         rule under it so the pinned control reads as separate from the nav */
      section[data-testid="stSidebar"] .st-key-nav_back {
        position:sticky; top:0; z-index:10; background:var(--chrome-bg-2);
        border-bottom:1px solid var(--chrome-border);
        padding-bottom:10px; margin-bottom:10px;
      }

      /* ---------- command-center dashboard (ui-spec 3.2) ---------- */
      .dashhead .h2 { font-size:22px; font-weight:650; color:var(--ink); margin:2px 0 4px 0; }
      .dashhead .lede { color:var(--muted); font-size:13.5px; max-width:70ch; }
      /* the CTA lives in an st.container(border=True); elevate that wrapper
         (shadow-md, strong border) via :has() so it reads as ui-spec 3.2's
         elevated card rather than a plain bordered box. */
      div[data-testid="stVerticalBlockBorderWrapper"]:has(.cta-t) {
        border-color:var(--border-strong); box-shadow:var(--shadow-md);
        border-radius:var(--r-lg); }
      .cta-t { font-size:18px; font-weight:650; color:var(--ink); }
      .cta-d { font-size:12.5px; color:var(--muted); margin-top:3px; }
      .tile-stat { display:flex; align-items:baseline; gap:9px; }
      .tile-stat .big { font-size:30px; font-weight:700;
        font-variant-numeric:tabular-nums; color:var(--ink); }
      .tile-stat .unit { font-size:12.5px; color:var(--muted); }
      .breakrow { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 4px 0; }
      /* ui-spec 4.10: height-proportional accent-gradient bars, the value
         printed *above* each bar, a mono caption below. Both halves of that had
         drifted, and the second half was a bug, not a style difference.
         The value was a flex sibling of the bar rather than a label floating
         over it, so it took 16.8px out of every column. With the chart at a
         fixed 70px and the column at height:100%, each column had 56px to hold
         38.8px of value + caption + gaps, and the bar - the only element with
         no intrinsic size - absorbed the entire 23px deficit. Every column
         carries identical text, so every bar shrank to an identical 17.2px:
         four weeks of different data rendered as four identical rectangles.
         Taking the value out of flow (position:absolute, per the mockup) gives
         the space back, flex:none stops the bar being a shrink candidate at
         all, and the chart sizes from its content so the tallest bar has
         somewhere to go: 46px peak + 3px gap + 16px caption + 14px of padding
         for the floating label is ~79px. */
      /* padding-top clears the floating value label (17px above the tallest
         bar) with 3px to spare, so a slightly larger font does not clip it. */
      .barchart { display:flex; align-items:flex-end; gap:10px; min-height:70px;
        padding-top:20px; margin-top:6px; }
      .barchart .bcol { flex:1; display:flex; flex-direction:column; align-items:center;
        justify-content:flex-end; gap:3px; }
      .barchart .bar { width:100%; flex:none; position:relative; min-height:4px;
        background:linear-gradient(180deg,var(--accent),var(--accent-strong));
        border-radius:4px 4px 0 0; }
      .barchart .v { position:absolute; top:-17px; left:0; right:0; text-align:center;
        font-family:var(--mono); font-size:10.5px; font-weight:700; color:var(--muted); }
      .barchart .bcap { font-size:10px; color:var(--faint); }
    </style>
    """,
    unsafe_allow_html=True,
)

# The always-dark login gate (ui-spec 1.5 + 3.1): rail tokens are hardcoded on
# purpose; the sign-in moment does not follow the app theme.
_LOGIN_CSS = """
    <style>
      .stApp { background:radial-gradient(1100px 560px at 50% -8%, #16274a, #0d1a30); }
      .block-container { max-width:900px; padding-top:4rem; }
      .login-brand { display:flex; align-items:center; justify-content:center; gap:12px; }
      .login-brand svg { width:30px; height:30px; }
      .login-brand .wm { font-weight:700; letter-spacing:.24em; font-size:16px; color:#eef3fc; }
      .login-brand .sub { color:#93a4c2; font-size:11.5px; letter-spacing:.05em;
        border-left:1px solid #243a5e; padding-left:11px; }
      .login-eyebrow { text-align:center; font-size:11px; font-weight:700;
        letter-spacing:.16em; text-transform:uppercase; color:#7fa6e6; margin-top:26px; }
      .login-h { text-align:center; font-size:28px; font-weight:650; color:#ffffff;
        margin:6px 0 8px 0; }
      .login-sub { text-align:center; color:#93a4c2; font-size:14px; max-width:54ch;
        margin:0 auto 10px auto; }
      .login-foot { text-align:center; color:#93a4c2; font-size:11.5px; margin-top:18px; }
      .pcard { position:relative; background:rgba(255,255,255,.04);
        border:1px solid #243a5e; border-radius:14px 14px 0 0; border-bottom:0;
        padding:16px 16px 8px 16px; text-align:left; min-height:148px; }
      .pcard.hero { border-color:#3f6bb0; background:rgba(91,141,239,.1); }
      .pcard .picon { width:46px; height:46px; border-radius:12px;
        background:rgba(91,141,239,.14); color:#9dc0f5; display:flex; align-items:center;
        justify-content:center; font-size:20px; font-weight:700; }
      .pcard .pname { font-size:15px; font-weight:650; color:#ffffff; margin-top:10px; }
      .pcard .prole { font-size:11.5px; color:#93a4c2; }
      .pcard .pcap { font-size:12px; color:#b9c8e2; line-height:1.45; margin-top:6px; }
      .pcard .ptier { position:absolute; top:14px; right:14px; font-family:var(--mono);
        font-size:11px; font-weight:700; background:rgba(91,141,239,.16);
        border:1px solid #2f4d7e; color:#9dc0f5; padding:2px 8px; border-radius:999px; }
      .pcard .phero-tag { font-size:10px; font-weight:700; letter-spacing:.06em;
        text-transform:uppercase; color:#5fdc8a; margin-top:6px; }
      div[data-testid="stVerticalBlockBorderWrapper"]:has(.pcard) { gap:0; }
      .stButton button[kind="secondary"], .stButton button[kind="primary"] {
        width:100%; border-radius:0 0 14px 14px;
      }
    </style>
"""

if "analysis_engine" not in st.session_state:
    st.session_state.analysis_engine = AnalysisEngine()
    st.session_state.analysis_run = None
analysis_engine: AnalysisEngine = st.session_state.analysis_engine


# --------------------------------------------------------------------------
# Login gate (ui-spec 3.1): the six personas as cards, before any chrome.
# --------------------------------------------------------------------------
# The mark itself lives in sentinel/ui/brand.py: the User Manual's cover slide
# draws it too, and a logo pasted into two files goes stale in one of them.
_SHIELD_SVG = SHIELD_SVG

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
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='login-brand'>{_SHIELD_SVG}
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


# --------------------------------------------------------------------------
# In-app navigation with history (Back button)
# --------------------------------------------------------------------------
# Screens route through st.session_state.section, which the browser's history
# never sees, so the browser Back button leaves Sentinel entirely. We keep our
# own bounded history stack and expose a Back control that returns to the
# previous screen within the app. (Wiring the browser's own Back button would
# need the st.navigation multipage migration; tracked as a follow-up.)
def _nav_to(target: str) -> None:
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


def _nav_back() -> None:
    """Return to the previous screen on the history stack."""
    stack = st.session_state.get("nav_stack", [])
    if not stack:
        return
    st.session_state.section = stack.pop()
    st.rerun()


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


def _classification_of(dataset: str) -> str:
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
            <div class='brand'>{_SHIELD_SVG}
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






# --------------------------------------------------------------------------
# Tab renderers
# --------------------------------------------------------------------------




# Row tint by audit level, shared by the Pipeline audit tab and the Audit Log's
# event stream so the two surfaces converge rather than drift. These are the
# ui-spec 1.2 semantic soft tokens verbatim; the three hexes previously inlined
# here (#fde7e6 / #fff4e0 / #eef2fb) were near-misses on them, and an audit
# screen is a bad place to have two reds.
_AUDIT_LEVEL_TINT = {
    "blocked": "background-color:#fdeceb",  # --danger-soft
    "redaction": "background-color:#fbf0dc",  # --warn-soft
    "gate": "background-color:#e8eef9",  # --accent-soft
}


def _audit_level_style(row):  # noqa: ANN001, ANN201
    return [_AUDIT_LEVEL_TINT.get(row["level"], "")] * len(row)






def _model_card_popover(version: str, card_dict: dict | None, container) -> None:  # noqa: ANN001
    """One model's SR 11-7 documentation, opened from its registry row.

    This was the Pipeline screen's Model Card tab, where it hung off whichever
    run you had just executed. That was the wrong anchor: a card documents a
    model, and the place a bank looks for a model's documentation is the model
    inventory. Here it is one click from the row, which is also the only place
    it can be shown for the seeded runs, since the run objects it was generated
    from do not outlive the process that made them.
    """
    if not card_dict:
        with container.popover("no card", use_container_width=True):
            st.caption(
                "No model card. The card is generated after a model clears the "
                "human gate, so a run that was rejected, blocked, or refused "
                "before the gate has none. That absence is the record."
            )
        return
    card = ModelCard(**card_dict)
    with container.popover("card", use_container_width=True):
        st.markdown(render_markdown(card))
        # Rendered to a version-scoped path: a single shared filename meant two
        # rows opened in one session could hand you the other one's PDF.
        pdf_path = render_pdf(card, f"runtime/model_card_{version}.pdf")
        st.download_button(
            "Download model card (PDF)",
            data=pdf_path.read_bytes(),
            file_name=f"model_card_{version}.pdf",
            mime="application/pdf",
            key=f"mcdl_{version}",
            type="primary",
        )












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
        _nav_to(_SECTION_TEMPLATES)
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


_MV_COLS = (2.6, 1.9, 1.1, 1.4, 1.3, 1.5, 1.2, 1.3, 1.2)
_MV_HEAD = (
    "version",
    "question",
    "auc",
    "disparity",
    "fairness",
    "status",
    "origin",
    "created",
    "card",
)
# Status words as markdown badges (a popover label cannot carry a .badge span).
_STATUS_MD = {
    "promoted": ":green-background[promoted]",
    "blocked": ":red-background[blocked]",
    "rejected": ":red-background[rejected]",
}
_FAIR_BADGE = {
    True: "<span class='badge ok'>pass</span>",
    False: "<span class='badge danger'>fail</span>",
    None: "<span class='badge neutral'>n/a</span>",
}
_AG_COLS = (1.7, 0.8, 4.9, 1.8, 2.9, 3.0)


def _model_status_extra(d: dict) -> str:
    """This model's own numbers, stated under the eval gate's catalogue entry.
    Read off the registry row so the popover cannot drift from the table."""
    if d["fairness_pass"] is None:
        return (
            f"Here: {d['version']} computed no fairness verdict (the "
            f"{d['question_id']} question trains no model), so there was nothing "
            f"for the gate to pass; the run was {d['status']}."
        )
    verdict = "passed" if d["fairness_pass"] else "failed"
    return (
        f"Here: {d['version']} scored auc {d['auc']:.4f} with a disparity ratio of "
        f"{d['disparity_ratio']:.3f}, so the fairness check {verdict}. Status: "
        f"{d['status']}. A failed fairness check is recorded, not hidden: whether "
        "it blocks promotion is the human gate's call, and this registry shows "
        "what was actually decided."
    )


def _agent_table_head() -> None:
    head = st.container(key="tblhead_ag")
    cols = head.columns(_AG_COLS, vertical_alignment="center")
    # "ver" not "version": at laptop widths Streamlit shrinks this column to its
    # min-content and the longer word breaks mid-header.
    labels = ("agent", "ver", "what it does", "template")
    for col, label in zip(cols[:4], labels, strict=True):
        col.markdown(f"<span class='th'>{label}</span>", unsafe_allow_html=True)
    with cols[4]:
        control_popover("guardrails", label=":gray[tools]", key="agtools")
    with cols[5]:
        control_popover("rbac", label=":gray[rbac scope]", key="agrbac")


def render_registry() -> None:
    st.subheader("Model & agent registry")
    st.markdown(
        "<span class='muted'>The MRM model inventory. Three different things are "
        "inventoried here, and they are not interchangeable:</span>",
        unsafe_allow_html=True,
    )
    # The page holds three registries and the names are close enough to blur, so
    # say the distinction once, up front, in terms of what each thing *is* in a
    # run: the output, the workers, and the thing a run is allowed to be.
    st.markdown(
        "<span class='muted'><b>Models</b> are what a run produces — a trained "
        "classifier, versioned with its metrics, fairness verdict, and promotion "
        "status.<br>"
        "<b>Agents</b> are the workers inside a run — the four pipeline agents "
        "that do the profiling, modeling, and validation, each with a tool "
        "allow-list and an RBAC scope.<br>"
        "<b>Analysis-agents</b> are what a run is allowed to be — named, owned, "
        "certified analyses. Only a certified one is visible to the Plan stage, "
        "so an uncertified analysis cannot reach a user. The four agents above "
        "execute whichever analysis-agent Plan binds.</span>",
        unsafe_allow_html=True,
    )

    st.markdown("### Models")
    st.markdown(
        "<span class='muted'>Every trained model, newest first. One row per run "
        "that trained something.</span>",
        unsafe_allow_html=True,
    )
    mv = model_versions()
    if mv:
        table_head(_MV_HEAD, _MV_COLS, "mv")
        for m in mv:
            d = m.to_dict()
            origin = "seeded" if m.seeded else ("ungoverned" if m.ungoverned else "live")
            cols = table_row(_MV_COLS, f"mv_{d['version']}")
            td(cols[0], d["version"], mono=True)
            td(cols[1], d["question_id"])
            td(cols[2], f"{d['auc']:.4f}" if d["auc"] is not None else "-", num=True)
            td(
                cols[3],
                f"{d['disparity_ratio']:.3f}" if d["disparity_ratio"] is not None else "-",
                num=True,
            )
            cols[4].markdown(_FAIR_BADGE[d["fairness_pass"]], unsafe_allow_html=True)
            with cols[5]:
                # Status is the eval gate's verdict plus the human decision, so
                # the chip opens the eval gate's catalogue entry and states this
                # model's actual numbers underneath it.
                control_popover(
                    "eval_gate",
                    label=_STATUS_MD.get(d["status"], d["status"]),
                    key=f"mvst_{d['version']}",
                    extra=_model_status_extra(d),
                )
            td(cols[6], origin)
            td(cols[7], d["created_at"][:10])
            _model_card_popover(d["version"], m.model_card, cols[8])
        st.caption(
            "Status comes from the eval gate and the human decision: promoted, "
            "blocked, or rejected. 'seeded' rows are labeled demo history; 'live' "
            "rows accumulate as you complete runs this session. The card column "
            "opens each model's SR 11-7 documentation, generated from that run."
        )
    else:
        st.info("No models registered yet.")

    st.markdown("### Agents")
    st.markdown(
        "<span class='muted'>The four workers of the governed pipeline, in run "
        "order. Every governed run executes these same four; what changes between "
        "runs is the dataset and the analysis they are pointed at.</span>",
        unsafe_allow_html=True,
    )
    # The two governed columns explain themselves once at the header rather than
    # once per row: the control is the same for every agent, only the value
    # differs, so a chip per row would be four copies of one explanation.
    _agent_table_head()
    for a in agent_registry():
        d = a.to_dict()
        cols = table_row(_AG_COLS, f"ag_{d['agent_id']}")
        # Id and human title stack in one cell: the id is what the audit trail
        # records, the title is what a reviewer calls it.
        cols[0].markdown(
            f"<span class='td mono'>{d['agent_id']}</span>"
            f"<span class='muted'>{d['title']}</span>",
            unsafe_allow_html=True,
        )
        td(cols[1], d["version"], mono=True)
        td(cols[2], d["does"])
        td(cols[3], d["template"])
        td(cols[4], d["tools"])
        td(cols[5], d["rbac_scope"])
    st.caption(
        "Each agent is derived from a template and carries its tool scope and RBAC "
        "scope; the description is read off the agent class, so it cannot drift "
        "from the code that runs. This is where new agents built from templates "
        "would be inventoried."
    )

    render_agent_certification()


_CERT_PILL = {
    "certified": ("#1a7f37", "#e6f4ea"),
    "candidate": ("#9a6700", "#fff8e1"),
    "refused": ("#b3261e", "#fce8e6"),
    "draft": ("#57606a", "#eef1f4"),
    "deprecated": ("#57606a", "#eef1f4"),
}


def _cert_pill(status: str) -> str:
    fg, bg = _CERT_PILL.get(status, ("#57606a", "#eef1f4"))
    return (
        f"<span style='background:{bg};color:{fg};padding:2px 8px;border-radius:10px;"
        f"font-size:0.8em;font-weight:600'>{status}</span>"
    )


def render_agent_certification() -> None:
    st.markdown("### Analysis-agents (certification lifecycle)")
    st.markdown(
        "<span class='muted'>Not the four agents above. An analysis-agent is a "
        "named analysis with an owner, a data contract, and an eval suite — the "
        "unit the Plan stage binds and a reviewer signs off on.</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span class='muted'>An analysis-agent earns the right to run. It moves "
        "draft → candidate → certified, and only a certified agent is visible to "
        "Plan. Four gates stand between an agent and certified: an eval suite that "
        "passes the faithfulness floor, a person as owner, a declared data "
        "contract, and an independent validator who is not the author "
        "(CTL-SOD-01). Everyone demos the happy path; the refusal is the "
        "differentiator.</span>",
        unsafe_allow_html=True,
    )
    for entry in cert_entries():
        decision = evaluate_cert(entry)
        header = (
            f"{entry.label()} — {decision.status.upper()} · owner {entry.owner}"
        )
        with st.expander(header, expanded=decision.status in ("refused", "candidate")):
            st.markdown(
                _cert_pill(decision.status)
                + f" &nbsp; author <code>{entry.author}</code>"
                + (f" · validator <code>{entry.validator}</code>" if entry.validator else "")
                + (
                    f" · faithfulness {entry.faithfulness:.2f}"
                    if entry.faithfulness is not None
                    else ""
                ),
                unsafe_allow_html=True,
            )
            for gi, g in enumerate(decision.gates):
                mark = "✓" if g.passed else "✗"
                cls = "muted" if g.passed else "flag"
                if not g.control:
                    st.markdown(
                        f"<span class='{cls}'>{mark} {g.name}</span> "
                        f"<span class='muted'>— {g.detail}</span>",
                        unsafe_allow_html=True,
                    )
                    continue
                # The gate names a catalogue control, so the chip explains itself
                # through the same popover the run walkthrough uses.
                row = st.container(
                    horizontal=True,
                    vertical_alignment="center",
                    key=f"cert_gate_{entry.id}_{gi}",
                )
                with row:
                    st.markdown(
                        f"<span class='{cls}'>{mark} {g.name}</span>",
                        unsafe_allow_html=True,
                    )
                    control_popover(g.control, key=f"certctl_{entry.id}_{gi}")
                    st.markdown(
                        f"<span class='muted'>— {g.detail}</span>",
                        unsafe_allow_html=True,
                    )
            _assign_validator_action(entry, decision)


def _assign_validator_action(entry, decision) -> None:  # noqa: ANN001
    """Offer the Registry action from section 10.4: assign an independent
    validator. Refuses a self-signoff (CTL-SOD-01) exactly as the flow does."""
    validator_gate = next(
        (g for g in decision.gates if g.name == "independent validator"), None
    )
    if validator_gate is None or validator_gate.passed:
        return
    with st.form(f"assign_validator_{entry.id}"):
        st.caption(
            "Action: assign an independent validator. The author cannot validate "
            "their own work (CTL-SOD-01)."
        )
        validator = st.text_input(
            "Validator id", key=f"val_{entry.id}", placeholder="e.g. dana.okafor"
        )
        submitted = st.form_submit_button("Assign validator")
    if submitted and validator:
        try:
            new_decision = assign_validator(entry, validator)
        except CertificationError as ex:
            st.error(str(ex))
            return
        if new_decision.status == "certified":
            st.success(f"{entry.label()} is now certified.")
        else:
            st.warning(new_decision.summary())
        st.rerun()


_DS_COLS = (2.0, 2.8, 1.9, 1.0, 0.8, 1.8, 1.2, 1.2, 1.6)
_DS_HEAD = (
    "id",
    "name",
    "classification",
    "rows",
    "tables",
    "license",
    "commercial",
    "onboarded",
    "",
)


def _open_contract(ds_id: str) -> None:
    st.session_state.ds_contract = ds_id


def render_datasets() -> None:
    # The registry is the list; the contract is the detail. Same screen, so the
    # sidebar nav item stays lit and the app's Back stack is not spent on a
    # drill-down that belongs to this page.
    if st.session_state.get("ds_contract"):
        render_dataset_contract(st.session_state.ds_contract)
        return
    st.subheader("Dataset registry")
    st.markdown(
        "<span class='muted'>The onboarded-dataset inventory. Each dataset carries "
        "its classification (which sets the autonomy ceiling), its license (and a "
        "commercial-use flag the platform enforces), the capabilities it provides, "
        "and its provenance. Analyses match against these via data "
        "contracts.</span>",
        unsafe_allow_html=True,
    )
    # The class-count breakdown row above the table (ui-spec 3.4), same chips
    # the dashboard tile uses.
    counts: dict[str, int] = {}
    for d in all_datasets():
        cls = _classification_of(d.id)
        counts[cls] = counts.get(cls, 0) + 1
    st.markdown(
        "".join(
            f"<span class='cls {name.lower()}'>{name} {counts[name]}</span> "
            for name in ("Restricted", "Confidential", "Internal", "Public")
            if name in counts
        ),
        unsafe_allow_html=True,
    )
    table_head(_DS_HEAD, _DS_COLS, "ds")
    for d in all_datasets():
        classification = _classification_of(d.id)
        cols = table_row(_DS_COLS, f"ds_{d.id}")
        td(cols[0], d.id, mono=True)
        td(cols[1], d.name)
        with cols[2]:
            # The classification is the one cell here that is a governance
            # decision rather than a fact about the file, so it is the cell that
            # explains itself: same CTL-PURP-01 popover as the topbar Data chip,
            # carrying this dataset's ceiling and permitted purposes.
            control_popover(
                "CTL-PURP-01",
                label=cls_label(classification) if classification else "n/a",
                key=f"dscls_{d.id}",
                extra=purpose_extra(d.id),
            )
        td(cols[3], f"{d.rows:,}", num=True)
        td(cols[4], d.tables, num=True)
        td(cols[5], d.license)
        cols[6].markdown(
            "<span class='badge ok'>yes</span>"
            if d.commercial_ok
            else "<span class='badge danger'>flagged</span>",
            unsafe_allow_html=True,
        )
        cols[7].markdown(
            "<span class='badge ok'>yes</span>"
            if dataset_available(d.id)
            else "<span class='badge neutral'>registered</span>",
            unsafe_allow_html=True,
        )
        cols[8].button(
            "Contract",
            key=f"dsopen_{d.id}",
            use_container_width=True,
            on_click=_open_contract,
            args=(d.id,),
            help="Schema, column dictionary, roles and relationships. Metadata "
            "only: no values.",
        )
    st.caption(
        "All 8 registered datasets ship onboarded (scripts/onboard_datasets.py "
        "produces their local files). 'flagged' commercial status means the "
        "license restricts commercial use and the platform blocks it; no control "
        "id is claimed for it, because the enforcement lives in the dataset "
        "registry rather than in the control catalogue."
    )


_UNDOC = "<span class='undoc'>not documented</span>"


def _compact(n: int) -> str:
    """A row count that fits a metric tile. 2,260,000 truncates to '2,260,...'
    at this tile width, which reads as broken rather than as a big number."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M".replace(".00M", "M")
    return f"{n:,}"


def _role_chip(role: str) -> str:
    return f"<span class='role {html.escape(role)}'>{html.escape(role)}</span>"


def _role_legend(sch) -> str:  # noqa: ANN001
    """What each role in this dataset costs a requester at Access, once.

    The consequence belongs next to the chip that carries it, but repeating it
    on every protected column turns a dictionary into a lecture. One legend,
    listing only the roles this dataset actually uses.
    """
    seen: list[str] = []
    for table in sch.tables:
        for col in table.columns:
            if col.role not in seen:
                seen.append(col.role)
    return "<div class='rleg'>" + "".join(
        f"<div class='r'>{_role_chip(r)}"
        f"<span class='v'>{html.escape(role_note(r))}</span></div>"
        for r in seen
    ) + "</div>"


def _dict_table(table) -> str:  # noqa: ANN001
    """The column dictionary for one table, as one HTML table.

    There is deliberately no value column, no example, and no distribution. A
    reader learns what a column *is* and what requesting it will cost them at
    Access; what it *contains* is data, and data needs a purpose.
    """
    rows = []
    for c in table.columns:
        drv = "<span class='drv'>derived</span>" if c.derived else ""
        desc = html.escape(c.description) if c.documented else _UNDOC
        rows.append(
            f"<tr><td class='cn'>{html.escape(c.name)}{drv}</td>"
            f"<td class='ty'>{html.escape(c.dtype)}</td>"
            f"<td>{_role_chip(c.role)}</td>"
            f"<td>{desc}</td></tr>"
        )
    return (
        "<table class='dict'><thead><tr><th>column</th><th>type</th><th>role</th>"
        "<th>description</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _close_contract() -> None:
    st.session_state.ds_contract = ""


def render_dataset_contract(ds_id: str) -> None:
    """The data contract for one dataset: schema, dictionary, roles, foreign
    keys, and the purposes the matrix permits on it.

    This is a catalogue, not a data browser, and the distinction is the whole
    point. A bank publishes metadata far more widely than data: you read the
    catalogue to decide what to ask for, then declare a purpose to get values.
    An "explore the data" button on this page would hand out values with no
    declared purpose, no resolved tier, no column grant and no disclosure
    screen, quietly undoing four controls the rest of the app spends its time
    proving. So the page shows the contract, and the route to values is the Run
    flow, where those controls are.
    """
    spec = get_dataset(ds_id)
    if spec is None:
        st.error(f"Unknown dataset {ds_id!r}.")
        st.button("Back to registry", on_click=_close_contract)
        return

    sch = schema(ds_id)
    classification = _classification_of(ds_id)
    ceiling = CLASSIFICATION_CEILING.get(classification, "n/a")

    st.button(
        "Dataset registry",
        key="ds_contract_back",
        icon=":material/arrow_back:",
        on_click=_close_contract,
    )
    st.subheader(f"Data contract · {spec.name}")
    st.markdown(
        f"<span class='muted'><code>{html.escape(ds_id)}</code> · "
        f"{html.escape(spec.license)} · "
        f"<a href='{html.escape(spec.source_url)}'>provenance</a></span>",
        unsafe_allow_html=True,
    )
    if spec.notes:
        st.markdown(
            f"<span class='muted'>{html.escape(spec.notes)}</span>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div class='cnotice'><b>Metadata only.</b> This page publishes the "
        "schema, the column dictionary, roles and foreign keys. It shows no cell "
        "values, no distributions and no samples, because reading values is data "
        "access and data access needs a declared purpose "
        "(<span class='ids'>CTL-PURP-01</span>), a resolved autonomy tier, a "
        "column grant (<span class='ids'>CTL-COL-01</span>) and a disclosure "
        "screen (<span class='ids'>CTL-DISC-02</span>). Read the contract here; "
        "request the values in Run.</div>",
        unsafe_allow_html=True,
    )

    if not sch.onboarded:
        st.warning(
            "Registered but not onboarded: the local file is not present, so the "
            "schema cannot be published yet. Run "
            f"`uv run python scripts/onboard_datasets.py {ds_id}`."
        )
        return

    local_rows = sum(t.rows for t in sch.tables)
    m = st.columns(5)
    m[0].metric("Rows at source", _compact(spec.rows))
    m[1].metric("Tables", len(sch.tables))
    m[2].metric("Columns", sch.n_columns)
    m[3].metric("Documented", f"{sch.coverage:.0%}")
    m[4].metric("Sensitive columns", len(sch.sensitive_columns()))
    if local_rows != spec.rows:
        # The registry counts the source; the file on disk is a sample for the
        # big sets. Publishing both is the honest option, and a row count is a
        # shape fact, not a value.
        st.caption(
            f"Onboarded as a sample: {local_rows:,} rows locally against "
            f"{spec.rows:,} at source. Analyses run on the sample."
        )
    st.markdown(
        f"<div class='cov'><i style='width:{sch.coverage * 100:.0f}%'></i></div>"
        f"<span class='muted'>{sch.n_documented} of {sch.n_columns} columns carry a "
        "description. Coverage is reported rather than smoothed over: an "
        "undocumented column is one nobody can request responsibly, so the gap is "
        "a governance metric, not a cosmetic one.</span>",
        unsafe_allow_html=True,
    )

    st.markdown("**What this dataset may be used for**")
    row = next((r for r in matrix_rows() if r["dataset"] == ds_id), {})
    st.markdown(
        "<div class='pgrid'>"
        + "".join(
            f"<span class='pcell {'allow' if row.get(p) else 'deny'}'>"
            f"<span class='mk'>{'✓' if row.get(p) else '✕'}</span>"
            f"{html.escape(PURPOSE_LABEL[p])}</span>"
            for p in PURPOSES
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='muted'>Classified <b>{html.escape(classification)}</b>, which "
        f"caps autonomy on this data at <b>{html.escape(ceiling)}</b> however "
        "trusted the requester is. A refused purpose is refused at Access before "
        "any code is generated: same person, same role, different reason, "
        "different answer.</span>",
        unsafe_allow_html=True,
    )

    if len(sch.tables) > 1:
        st.markdown("**Tables**")
        st.markdown(
            "<table class='dict'><thead><tr><th>table</th><th>rows</th>"
            "<th>columns</th><th>description</th></tr></thead><tbody>"
            + "".join(
                f"<tr><td class='cn'>{html.escape(t.name)}</td>"
                f"<td class='ty'>{t.rows:,}</td>"
                f"<td class='ty'>{len(t.columns)}</td>"
                f"<td>{html.escape(t.description) or _UNDOC}</td></tr>"
                for t in sch.tables
            )
            + "</tbody></table>",
            unsafe_allow_html=True,
        )

    if sch.relationships:
        st.markdown("**Relationships**")
        st.markdown(
            "".join(
                f"<div class='fk'><span class='e'>"
                f"{html.escape(r.from_table)}.{html.escape(r.from_column)}"
                f"<span class='ar'>-&gt;</span>"
                f"{html.escape(r.to_table)}.{html.escape(r.to_column)}</span>"
                f"<span class='c'>{html.escape(r.cardinality)}</span>"
                + (f"<span class='n'>{html.escape(r.note)}</span>" if r.note else "")
                + "</div>"
                for r in sch.relationships
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "Foreign keys as the catalogue publishes them. A join is where "
            "minimisation leaks: two individually harmless tables can re-identify "
            "a person once joined, which is why the relationship map is metadata "
            "an analyst should see before requesting either side."
        )

    st.markdown("**Column dictionary**")
    st.markdown(_role_legend(sch), unsafe_allow_html=True)
    if len(sch.tables) > 1:
        for t in sch.tables:
            with st.expander(f"{t.name} · {len(t.columns)} columns · {t.rows:,} rows"):
                st.markdown(_dict_table(t), unsafe_allow_html=True)
    else:
        st.markdown(_dict_table(sch.tables[0]), unsafe_allow_html=True)

    # Table-qualified, because on a relational dataset a bare `account` or
    # `birth_number` does not say which table it is a risk in.
    qualified = [
        f"{t.name}.{c.name}" if len(sch.tables) > 1 else c.name
        for t in sch.tables
        for c in t.columns
        if c.role in ("pii", "protected")
    ]
    if qualified:
        n = len(qualified)
        st.caption(
            f"{n} column{'' if n == 1 else 's'} carr{'ies' if n == 1 else 'y'} a "
            "PII or protected role: "
            + ", ".join(f"`{q}`" for q in qualified)
            + ". PII is never granted and is redacted before any text reaches a "
            "model; a protected attribute is granted only to the purpose whose "
            "axis it is, and is excluded from model features."
        )

    st.divider()
    st.markdown("**To see values, take this dataset through a control**")
    a, b = st.columns(2)
    # Imperative rather than on_click: _nav_to reruns, and a rerun belongs in
    # the script body, not in a widget callback.
    if a.button(
        "Declare a purpose in Run",
        key="ds_contract_to_run",
        icon=":material/play_arrow:",
        use_container_width=True,
        help="The governed route: declare a purpose, resolve a tier, take the "
        "column grant, and let the disclosure screen run on the output.",
    ):
        _close_contract()
        _nav_to("Run")
    if b.button(
        "Profile it under governance",
        key="ds_contract_to_analyses",
        icon=":material/query_stats:",
        use_container_width=True,
        help="The data_profiling analysis computes distributions, missingness "
        "and cardinality as a certified analysis, audited and gated.",
    ):
        _close_contract()
        _nav_to("Analyses")
    st.caption(
        "Missingness, cardinality and distributions look like metadata but are "
        "computed from values, so they are profile outputs rather than catalogue "
        "entries. The catalogue knows the shape; the profile knows the contents; "
        "only the profile is data access."
    )


def render_adoption() -> None:
    st.subheader("Adoption & utilization")
    st.markdown(
        "<span class='muted'>Who uses what agent, how often, and with what "
        "outcome. Aggregated over the registry plus seeded weekly history. The "
        "platform-stage signal: is the platform compounding, not just "
        "accumulating one-offs.</span>",
        unsafe_allow_html=True,
    )
    m = adoption_metrics()
    a, b, c, d = st.columns(4)
    a.metric("Total runs", m["total_runs"], f"{m['live_session_runs']} this session")
    b.metric(
        "Promotion rate",
        f"{round(m['promotion_rate'] * 100)}%",
        help=f"Over the {m['credit_risk_runs']} credit-pipeline runs (the only "
        "kind that promotes a model).",
    )
    c.metric("Human-override rate", f"{round(m['override_rate'] * 100)}%")
    d.metric("Template coverage", f"{round(m['template_coverage'] * 100)}%")

    st.markdown(
        f"**Agent utilization** (invocations across the {m['credit_risk_runs']} "
        "credit-pipeline runs)"
    )
    st.bar_chart(
        pd.DataFrame(
            {"invocations": m["per_agent_invocations"]}
        )
    )

    st.markdown("**Runs per week** (seeded demo history)")
    wk = pd.DataFrame(m["weekly"], columns=["week", "runs"]).set_index("week")
    st.bar_chart(wk)

    st.markdown("**Runs per dataset** (seeded demo history)")
    pds = pd.DataFrame(m["per_dataset"], columns=["dataset", "runs"]).set_index("dataset")
    st.bar_chart(pds, horizontal=True)
    st.caption(
        "Seeded history comes from actually executed runs (see "
        "scripts/seed_runs.py) and is labeled demo telemetry; the totals above "
        "include live runs completed this session. Enterprise: this view reads "
        "the platform's real run store."
    )


# --------------------------------------------------------------------------
# Audit log (docs/features/audit-log.md): the one cross-run surface.
# --------------------------------------------------------------------------
# Harness actions are not catalogue ids, and minting CTL- ids to give a chip
# something to open is the governance theatre ui-spec 4.3 refuses. So the
# actions that DO have an explanation map onto the catalogue entry that holds
# it; anything unmapped renders as an inert chip rather than a popover
# claiming "not implemented" beside a control that demonstrably fired.
_AUDIT_CTL_ALIAS = {
    "rbac_access_denied": "rbac",
    "pii_redacted": "pii",
    "eval_gate": "eval_gate",
    "approval_requested": "human_gate",
    "approval_decision": "human_gate",
    "approval_auto": "human_gate",
    "tier_block": "CTL-TIER-01",
}
# approval_denied is deliberately absent. Two different refusals write it and
# only one stamps a control id, so the run detail explains it in prose where
# it can say which one fired; a single chip would have to pick one and be
# wrong half the time.

# A drill-down screen, deliberately NOT in NAV_GROUPS: you reach it by opening
# a run, not from the rail. It still participates in the nav stack, so the
# sidebar Back button returns to the ledger like any other screen.
_SECTION_AUDIT_RUN = "Audit Run"

_AUD_HEAD = ("when", "run / analysis", "kind", "dataset", "ran by", "second signature",
             "outcome", "caught", "")
_AUD_COLS = (0.9, 1.3, 1.05, 1.3, 1.25, 1.4, 1.1, 1.9, 0.85)

# The store's kind constants are snake_case; a pill is easier to read, and
# harder to wrap mid-word, with a space.
_AUD_KIND_LABEL = {"credit_risk": "credit risk", "l3": "L3"}

_OUTCOME_BADGE = {
    OUTCOME_OK: ("ok", "completed"),
    OUTCOME_REFUSED: ("danger", "refused"),
    OUTCOME_AWAITING: ("warn", "awaiting"),
}


def _audit_ctl_chip(cid: str, col, key: str, fired: bool | None = None) -> None:  # noqa: ANN001
    """One control, explained through the catalogue where it can be.

    `fired` distinguishes a control that was *armed* at a stage from one that
    actually fired on this run. A stage arming eight code checks and tripping
    none of them is the normal case, and reading those eight as eight refusals
    would be the same over-count the KPI tiles already avoid.
    """
    target = _AUDIT_CTL_ALIAS.get(cid, cid)
    info = control_info(target)
    # A leading dot marks the ones that actually fired, so an eight-chip
    # Gate row reads at a glance as "eight armed, none tripped".
    label = f"● {cid}" if fired else cid
    if info.implemented:
        control_popover(target, label=label, key=key, container=col)
    else:
        col.markdown(
            f"<span class='ctlchip'><span class='st'></span>{html.escape(cid)}</span>",
            unsafe_allow_html=True,
        )


def _audit_second_signature(r, col) -> None:  # noqa: ANN001
    """The four-eyes cell. Five states, and two of them are not the same.

    approve() tests promotion authority before segregation of duties, so an
    author without authority is refused before CTL-SOD-01 is ever reached.
    Collapsing the two into one "refused" badge would credit CTL-SOD-01 with a
    refusal it did not make.
    """
    denial = next((e for e in r.events if e.get("action") == "approval_denied"), None)
    if r.four_eyes:
        who = get_persona(r.approver)
        col.markdown(
            f"<span class='badge ok'>signed</span><br>"
            f"<span class='muted' style='font-size:11px'>"
            f"{html.escape(who.name if who else r.approver)}</span>",
            unsafe_allow_html=True,
        )
    elif denial and (denial.get("extra") or {}).get("control") == "CTL-SOD-01":
        control_popover(
            "CTL-SOD-01",
            label="self-approval refused",
            key=f"aud4e_{r.run_id}",
            container=col,
        )
    elif denial:
        col.markdown(
            "<span class='badge danger'>no authority</span><br>"
            "<span class='muted' style='font-size:11px'>role check</span>",
            unsafe_allow_html=True,
        )
    elif r.run_kind == KIND_CREDIT_RISK:
        col.markdown("<span class='badge neutral'>not reached</span>", unsafe_allow_html=True)
    else:
        col.markdown("<span class='badge neutral'>not required</span>", unsafe_allow_html=True)


_STEP_MARK = {
    "blocked": "✕", "error": "✕", "rejected": "✕",
    "skipped": "—", "awaiting_approval": "●", NOT_IN_ROUTE: "·",
}
_STEP_BADGE = {
    "ok": ("ok", "ok"), "blocked": ("danger", "blocked"), "error": ("danger", "error"),
    "rejected": ("danger", "rejected"), "skipped": ("neutral", "skipped"),
    "awaiting_approval": ("warn", "awaiting"),
    NOT_IN_ROUTE: ("neutral", "not in this route"),
}


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _audit_event_row(e: dict) -> dict:
    return {
        "seq": e["seq"],
        "ts": e["ts"][11:19],
        "agent": e["agent"],
        "action": e["action"],
        "level": e["level"],
        "data touched": ", ".join(e.get("data_touched") or []),
        "summary": e["output_summary"],
    }


def _audit_stage_events(events: list[dict], label: str) -> None:
    """The events belonging to one stage, folded away until asked for."""
    with st.expander(label):
        st.dataframe(
            pd.DataFrame([_audit_event_row(e) for e in events]).style.apply(
                _audit_level_style, axis=1
            ),
            hide_index=True,
            width="stretch",
        )


def _audit_steps(r) -> None:  # noqa: ANN001
    """The run, read as the nine governance stages the Run screen teaches.

    Every run kind renders in one vocabulary, so an auditor learns the spine
    once instead of learning four. The native step names stay visible inside
    each stage, so nothing is renamed away.

    Three statuses are kept apart on purpose, because collapsing them is how a
    normalization starts lying: `ok` ran, `skipped` was reached and declined,
    and `not in this route` means the route has no such stage at all. A linear
    analysis generates no code, so its Generate stage is not a skipped step, it
    is an absent one.

    Frameworks and governance come from the same table the Run screen renders
    (`_ENGINE`) for the nine-stage routes, so the two surfaces cannot drift.
    The other two routes declare their own, grounded in what those modules
    actually import: printing govflow's duckdb sandbox against a credit-risk
    run that trains a scikit-learn model would be a plain falsehood.
    """
    st.markdown("**Stages**")
    st.caption(
        "The nine governance stages, the same spine the Run screen walks. "
        "Every run kind is read in this shape; each stage names the steps it "
        "actually ran, the events it recorded, what it was built with, and "
        "what governed it."
    )

    # Two attribution paths, and the first one wins where it exists.
    #
    # An event that carries its own `stage` is filed there, full stop: the
    # emitting call site is the only thing that knows which stage it ran in,
    # and now it says so. The nine-stage routes (govflow, L3) stamp all of it.
    #
    # Everything else falls back to matching the event's agent against a native
    # step's agent, which is exact for the analysis and credit-risk routes
    # because there one agent runs one step. It is not exact for the nine-stage
    # routes, which is why they stamp the stage instead.
    by_stage: dict[str, list[dict]] = {}
    by_agent: dict[str, list[dict]] = {}
    for e in r.events:
        if e.get("stage"):
            by_stage.setdefault(str(e["stage"]), []).append(e)
        else:
            by_agent.setdefault(e["agent"], []).append(e)

    for i, c in enumerate(canonical_steps(r)):
        status = c["status"]
        badge_cls, badge_txt = _STEP_BADGE.get(status, ("neutral", status))
        absent = status == NOT_IN_ROUTE
        name = f"~~{c['stage']}~~" if status == "skipped" else f"**{c['stage']}**"
        st.markdown(
            f"{_STEP_MARK.get(status, '✓')} {name} &nbsp;"
            f"<span class='badge {badge_cls}'>{badge_txt}</span> &nbsp;"
            f"<span class='muted' style='font-size:12px'>{html.escape(c['purpose'])}</span>",
            unsafe_allow_html=True,
        )
        if absent:
            continue

        if c["note"]:
            st.markdown(
                f"<div class='stepdetail'><i>{html.escape(c['note'])}</i></div>",
                unsafe_allow_html=True,
            )

        for s in c["native"]:
            detail = str(s.get("detail") or "").strip()
            agent = str(s.get("agent", ""))
            events = by_agent.get(agent, []) if s.get("attributable") and agent else []
            st.markdown(
                f"<div class='stepdetail'><b>{html.escape(str(s.get('name', '')))}</b>"
                + (f" <span class='muted'>({html.escape(agent)})</span>" if agent else "")
                + (f"<br>{html.escape(detail)}" if detail else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            if events:
                _audit_stage_events(
                    events,
                    f"{_plural(len(events), 'event')} at {s.get('name', 'this step')}",
                )

        stage_events = by_stage.get(c["stage"], [])
        if stage_events:
            _audit_stage_events(
                stage_events,
                f"{_plural(len(stage_events), 'event')} recorded at {c['stage']}",
            )

        if c["libraries"]:
            st.markdown(
                "<div class='stepmeta'><b>Framework &amp; tools</b> "
                + " ".join(f"<code>{html.escape(x)}</code>" for x in c["libraries"])
                + "</div>",
                unsafe_allow_html=True,
            )
        if c["controls"]:
            st.markdown(
                "<div class='stepmeta'><b>Governance armed</b>"
                + (
                    f" &middot; <span class='fired'>{len(c['fired'])} fired on this run</span>"
                    if c["fired"]
                    else " &middot; none fired on this run"
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            cc = st.columns(min(len(c["controls"]), 6))
            for j, ctl in enumerate(c["controls"]):
                _audit_ctl_chip(
                    ctl, cc[j % len(cc)], f"audsc_{r.run_id}_{i}_{j}",
                    fired=ctl in c["fired"],
                )

    # What is left over after both attribution paths. An event with a stage
    # this route does not render is counted here too rather than dropped: a
    # stage string the screen cannot place is a mismatch worth showing, not a
    # line to swallow.
    placed_agents = {s.get("agent") for s in r.steps if s.get("attributable")}
    unplaced = [
        e
        for e in r.events
        if (
            str(e.get("stage") or "") not in CANONICAL_STAGES
            and e["agent"] not in placed_agents
        )
    ]
    if unplaced:
        st.caption(
            f"{len(unplaced)} of {len(r.events)} events are run-level rather "
            "than stage-level: the run starting and ending, and the model "
            "being registered. They carry no stage because they belong to "
            "none. All of them are in the stream below."
        )


def _audit_detail(r) -> None:  # noqa: ANN001
    """One run opened: what it was allowed, what was caught, who signed."""
    st.markdown(f"#### Run `{r.run_id}`")
    tier = r.metrics.get("tier")
    st.markdown(
        f"<span class='muted'>analysis <b>{html.escape(r.ref_id)}</b> &middot; "
        f"dataset <b>{html.escape(r.dataset_id)}</b> &middot; tier "
        + (f"<b>{html.escape(str(tier))}</b>" if tier else
           "<i>n/a, this run kind predates the autonomy ladder</i>")
        + f" &middot; origin <b>{html.escape(r.origin)}</b> &middot; policy "
        f"<b>{html.escape(policy_version())}</b></span>",
        unsafe_allow_html=True,
    )

    st.markdown("**Decision summary**")
    caught = r.refusal_controls
    stopped = 1 if r.stopped_at else 0
    if not r.has_events:
        # Not the same statement as "nothing was refused", and the difference
        # is the whole credibility of the screen.
        st.error(
            "No event trail was persisted for this run. This is not the same "
            "as nothing having been refused: the record is absent, not clean."
        )
    elif caught:
        st.warning(
            f"**Caught.** {len(caught)} refusal{'s' if len(caught) != 1 else ''}. "
            f"**{stopped} stopped the run"
            + (f" (at {r.stopped_at})" if r.stopped_at else "")
            + f".** **{len(caught) - stopped} "
            f"{'was' if len(caught) - stopped == 1 else 'were'} recorded and the "
            "run continued.**"
        )
        cols = st.columns(min(len(caught), 5) or 1)
        for i, c in enumerate(caught):
            _audit_ctl_chip(c, cols[i % len(cols)], f"audd_{r.run_id}_{i}")
    else:
        st.success("Nothing was refused, suppressed or flagged on this run.")

    actor = get_persona(r.actor)
    st.markdown(
        f"**Approvals.** Ran by **{html.escape(actor.name if actor else r.actor)}**"
        + (f", {html.escape(actor.role)}" if actor else "")
        + ". "
        + _audit_approval_prose(r)
    )
    st.caption(
        "Persona selection is a demo sign-in with no credential, so this "
        "identity is self-asserted. Sentinel has no dual-control path: no "
        "quorum, no second-signature state. Four-eyes here means the approver "
        "is not the author, and that is all it means."
    )

    _audit_steps(r)

    st.markdown("**Event stream**")
    if r.events:
        gaps = r.seq_gaps
        st.caption(
            (f"seq 0-{len(r.events) - 1}, no gaps."
             if not gaps else f"GAP: sequence numbers {gaps} are missing.")
            + " Sequence is monotonic within a run and resets per run. There is "
            "no global ordering and no hash chain: this record is immutable by "
            "convention, not by cryptography."
        )
        events_df = pd.DataFrame(
            [
                {
                    "seq": e["seq"], "ts": e["ts"][11:19], "agent": e["agent"],
                    "actor": e["actor"],
                    # Blank where the route has no stage spine, which is a fact
                    # about the route and not a hole in the record.
                    "stage": e.get("stage", ""),
                    "action": e["action"], "level": e["level"],
                    "data touched": ", ".join(e.get("data_touched") or []),
                    "summary": e["output_summary"],
                }
                for e in r.events
            ]
        )
        st.dataframe(
            events_df.style.apply(_audit_level_style, axis=1),
            hide_index=True,
            width="stretch",
            height=320,
        )
        st.download_button(
            "Events (JSONL)",
            "\n".join(json.dumps(e) for e in r.events),
            file_name=f"audit_{r.run_id}.jsonl",
            key=f"auddl_{r.run_id}",
        )
    st.caption(
        "tokens and cost are omitted deliberately: no call site populates them, "
        "so they are always 0. Not captured at all: a written rationale on "
        "approve or reject (the gate takes two buttons and no text), and an "
        "authenticated principal."
    )


def _audit_approval_prose(r) -> str:  # noqa: ANN001
    denial = next((e for e in r.events if e.get("action") == "approval_denied"), None)
    if r.four_eyes:
        who = get_persona(r.approver)
        verb = "rejected" if r.status == STATUS_REJECTED else "approved"
        return (
            f"**{who.name if who else r.approver}** {verb} at the model gate. "
            "Author and approver are different identities, which is what "
            "CTL-SOD-01 requires."
        )
    if denial and (denial.get("extra") or {}).get("control") == "CTL-SOD-01":
        return (
            "The author tried to approve their own run and was refused by "
            "**CTL-SOD-01**, the four-eyes control, enforced by identity "
            "comparison rather than by role. The run is still awaiting an "
            "independent approver."
        )
    if denial:
        return (
            "The author tried to promote their own model and was refused for "
            "**lacking promotion authority**. Note this is not CTL-SOD-01: "
            "approve() tests authority first, so the four-eyes check was never "
            "reached."
        )
    if r.run_kind == KIND_CREDIT_RISK:
        return "No approval decision was reached before the run ended."
    return (
        "Not required: this run kind has no human promotion gate. The govflow "
        "and L3 routes produce an evidence pack instead, and it ships pending "
        "because sign_evidence_pack is never called from app code."
    )


def _audit_open(run_id: str) -> None:
    """Open one run as its own screen.

    A drill-down, not an accordion. Two things follow from that. The sidebar
    Back button works, because this pushes onto the same nav stack every other
    screen uses. And the run id goes into the query string, so a single run's
    evidence has a real address: an auditor can link it, bookmark it, or open
    it in a new browser tab. That matters more here than anywhere else in the
    app, because "send me the evidence for that run" is the actual workflow.
    """
    st.session_state["aud_sel"] = run_id
    st.query_params["run"] = run_id
    _nav_to(_SECTION_AUDIT_RUN)


def render_audit_run(persona) -> None:  # noqa: ANN001
    """One run, full screen: the evidence for a single execution."""
    run_id = st.session_state.get("aud_sel") or st.query_params.get("run", "")
    all_runs = audit_runs(live=st.session_state.get("live_audit_runs", []))
    run = next((r for r in all_runs if r.run_id == run_id), None)
    # The same entitlement the ledger applies, applied again here. This screen
    # is reachable by typing ?run=<id>, so checking only on the ledger would
    # make the deep link a way around the check rather than a link to a run.
    permitted = {r.run_id for r in visible_runs(all_runs, persona)}

    back, _ = st.columns([1, 5])
    if back.button("Back to audit log", icon=":material/arrow_back:", key="audrun_back"):
        st.query_params.pop("run", None)
        _nav_to("Audit Log")

    if run is not None and run.run_id not in permitted:
        # Says the run exists and is withheld, rather than claiming it does not
        # exist. Hiding existence would be the stronger control, and on an
        # external surface it is the right one; here the reader is an employee
        # holding a link a colleague sent them, and "no such run" would send
        # them chasing a bug instead of asking for access.
        who = get_persona(run.actor)
        st.warning(
            f"Run `{run_id}` was executed by "
            f"**{html.escape(who.name if who else run.actor)}**, and "
            f"**{html.escape(persona.name)}** reads only its own runs. "
            "The record exists and is unchanged; it is not shown to this role."
        )
        return

    if run is None:
        # Reachable by editing the URL, so it says which id failed rather than
        # rendering an empty screen.
        st.error(
            f"No run on file with id `{run_id}`. It may have been a live run "
            "from a previous session: those write to runtime/, which does not "
            "survive a restart."
        )
        return
    _audit_detail(run)


def render_audit_log(persona) -> None:  # noqa: ANN001
    st.subheader("Audit log")
    st.markdown(
        "<span class='muted'>Every run the platform has executed, every step "
        "inside it, everything a control refused, and who signed off. "
        "Append-only; nothing here is editable from the app.</span>",
        unsafe_allow_html=True,
    )
    # The ledger is scoped to what this role may read before anything is
    # counted, so the tiles below describe the reader's own view and not the
    # platform. Every number on this screen is derived from `runs`.
    all_runs = audit_runs(live=st.session_state.get("live_audit_runs", []))
    runs = visible_runs(all_runs, persona)
    hidden = len(all_runs) - len(runs)
    m = audit_summary(runs)
    st.caption(
        f"{m['runs']} runs on file, {m['events']} committed events. Seeded runs "
        "were executed by scripts/seed_runs.py and ship with the build; refusal "
        "density among them is a seeding choice, stated so the ledger is not "
        "read as a natural rate. Live runs write to runtime/, which is "
        "gitignored and excluded from the deploy bundle, so they do not survive "
        "a restart."
    )
    if hidden:
        # Named, not silently applied. A filtered ledger that does not say it
        # is filtered reads as the whole record, and every tile under it would
        # then be a quiet understatement.
        st.info(
            f"**Scoped to your runs.** {hidden} further "
            f"run{'s' if hidden != 1 else ''} on this platform "
            f"{'are' if hidden != 1 else 'is'} not shown: "
            f"**{html.escape(persona.name)}** reads its own runs only. The "
            "counts and filters below describe this scoped view. Oversight "
            "roles (Internal Auditor, Model Validator, MRM Approver, Platform "
            "Admin) read the whole ledger; switch to one from the identity "
            "chip above to see it, which is possible at all because that chip "
            "is a demo sign-in with no credential behind it."
        )

    a, b, c, d = st.columns(4)
    a.metric("Runs logged", m["runs"], f"{m['live_runs']} this session")
    b.metric(
        "Runs with a refusal",
        f"{m['refused']} of {m['runs']}",
        help=f"{m['stopped']} stopped outright (the run ended at a control); "
        f"{m['withheld']} completed with something withheld (a column denied, a "
        "cell suppressed, a value redacted). A gate that fired and passed is "
        "not counted.",
    )
    c.metric(
        "Four-eyes coverage",
        f"{m['four_eyes']} of {m['gated']}",
        help="Of runs that reached a human gate, those signed by someone other "
        "than the author. A refused self-approval counts as a refusal, not as "
        "coverage.",
    )
    d.metric(
        "Controls fired",
        f"{len(m['controls_fired'])} of {len(implemented_ids())}",
        help="Distinct controls that have actually fired, over the implemented "
        "catalogue. This is coverage, not refusal: an eval gate that fired and "
        "passed counts here.",
    )

    # "Refusals only" used to mean "a control caught something on this run",
    # which includes runs that then completed: a denied column or a redacted
    # value is a refusal the run survived. Reading that label next to an
    # "approved" outcome is a fair contradiction to raise, so the filter now
    # splits on the same axis the KPI caption does, and counts each option so
    # the split is legible before you pick one.
    n_stopped = sum(1 for r in runs if r.has_refusal and r.stopped_run)
    n_withheld = sum(1 for r in runs if r.has_refusal and not r.stopped_run)
    n_gated = sum(1 for r in runs if r.reached_gate)
    _POSTURE_ALL = "All runs"
    _POSTURE_STOPPED = f"Stopped by a control ({n_stopped})"
    _POSTURE_WITHHELD = f"Withheld, ran on ({n_withheld})"
    _POSTURE_GATED = f"Reached a human gate ({n_gated})"
    # Drilling into a run unmounts these widgets, and Streamlit drops the state
    # of a widget it did not render. Without this, Back returns you to the
    # ledger with every filter reset, which is the opposite of going back.
    # Durable copies live under _-prefixed keys and re-seed the widgets.
    for _wk in ("aud_posture", "aud_kind", "aud_who", "aud_ctl"):
        if _wk not in st.session_state and f"_{_wk}" in st.session_state:
            st.session_state[_wk] = st.session_state[f"_{_wk}"]

    posture = st.segmented_control(
        "Show",
        [_POSTURE_ALL, _POSTURE_STOPPED, _POSTURE_WITHHELD, _POSTURE_GATED],
        default=_POSTURE_ALL,
        key="aud_posture",
        help="Stopped: the run ended at a control. Withheld: a control refused "
        "something (a column, a cell, a value) and the run continued to a "
        "normal outcome. The two are different findings and the ledger keeps "
        "them apart.",
    )
    f1, f2, f3 = st.columns(3)
    kinds = sorted({r.run_kind for r in runs})
    kind = f1.selectbox(
        "Kind",
        ["All kinds", *kinds],
        format_func=lambda k: _AUD_KIND_LABEL.get(k, k),
        key="aud_kind",
    )
    # Built from the scoped set, so it can only ever offer people whose runs
    # this role may already read: the filter narrows a view, it never widens
    # one. For a role scoped to itself that leaves a single option, and the
    # control is disabled and says why rather than pretending to be a choice.
    people = sorted({r.actor for r in runs})
    scoped_to_self = not persona.can_view_all_runs
    who = f2.selectbox(
        "Ran by",
        ["Anyone", *people],
        format_func=lambda x: (get_persona(x).name if get_persona(x) else x)
        if x != "Anyone"
        else x,
        key="aud_who",
        disabled=scoped_to_self,
        help="Your role reads its own runs only, so there is nobody else to "
        "filter by." if scoped_to_self else None,
    )
    ctls = sorted({c for r in runs for c in r.refusal_controls})
    ctl = f3.selectbox("Control", ["Any control", *ctls], key="aud_ctl")

    for _wk in ("aud_posture", "aud_kind", "aud_who", "aud_ctl"):
        st.session_state[f"_{_wk}"] = st.session_state.get(_wk)

    shown = [
        r
        for r in runs
        if (posture != _POSTURE_STOPPED or (r.has_refusal and r.stopped_run))
        and (posture != _POSTURE_WITHHELD or (r.has_refusal and not r.stopped_run))
        and (posture != _POSTURE_GATED or r.reached_gate)
        and (kind == "All kinds" or r.run_kind == kind)
        and (who == "Anyone" or r.actor == who)
        and (ctl == "Any control" or ctl in r.refusal_controls)
    ]
    st.caption(f"showing {len(shown)} of {len(runs)} runs, newest first")

    if not shown:
        st.info(
            "You have not run anything yet, and your role reads only its own "
            "runs. Run an analysis from the Run or Analyses screen to add one."
            if not runs and hidden
            else "No runs match these filters. Clear them, or run an analysis "
            "from the Run or Analyses screen to add a live one."
        )
        return

    table_head(_AUD_HEAD, _AUD_COLS, "aud")
    # Row containers are keyed by POSITION, not by run id. Streamlit reconciles
    # keyed containers across reruns by key, so run-id keys leave orphaned rows
    # in the DOM the moment a filter changes the set: 9 visible rows rendered as
    # 12 containers, 3 of them stale copies from the previous render. Positional
    # keys shrink cleanly from the tail. Nothing is lost, because the CSS hooks
    # off the key prefix rather than the id.
    for i, r in enumerate(shown):
        # Tint the row you last opened, so Back lands you where you left off.
        sel = st.session_state.get("aud_sel") == r.run_id
        cols = table_row(_AUD_COLS, f"aud_{'sel_' if sel else ''}{i}")
        td(cols[0], r.when[:16].replace("T", " "), mono=True)
        with cols[1]:
            # The id is the link. Styled as one (accent, mono, underline on
            # hover) because a tertiary button renders as plain text, and a
            # run id that looks like a value nobody clicks is a drill-down
            # nobody finds.
            if st.button(r.run_id, key=f"audopen_{r.run_id}", type="tertiary"):
                _audit_open(r.run_id)
            st.markdown(
                f"<span class='muted' style='font-size:11px'>{html.escape(r.ref_id)}</span>",
                unsafe_allow_html=True,
            )
        cols[2].markdown(
            "<span class='badge neutral'>"
            f"{html.escape(_AUD_KIND_LABEL.get(r.run_kind, r.run_kind))}</span>",
            unsafe_allow_html=True,
        )
        with cols[3]:
            st.markdown(
                f"<span class='td mono'>{html.escape(r.dataset_id)}</span>",
                unsafe_allow_html=True,
            )
            classification = _classification_of(r.dataset_id)
            if classification:
                control_popover(
                    "CTL-PURP-01",
                    label=cls_label(classification),
                    key=f"audds_{r.run_id}",
                    extra=purpose_extra(r.dataset_id),
                )
        actor = get_persona(r.actor)
        td(cols[4], actor.name if actor else r.actor)
        _audit_second_signature(r, cols[5])
        badge, label = _OUTCOME_BADGE[r.outcome]
        cols[6].markdown(
            f"<span class='badge {badge}'>{label}</span>"
            + (f"<br><span class='muted' style='font-size:11px'>at {html.escape(r.stopped_at)}"
               "</span>" if r.stopped_at else ""),
            unsafe_allow_html=True,
        )
        with cols[7]:
            caught = r.refusal_controls
            if not caught:
                st.markdown(
                    "<span class='muted' style='font-size:12px'>nothing refused</span>",
                    unsafe_allow_html=True,
                )
            else:
                for i, c in enumerate(caught[:2]):
                    _audit_ctl_chip(c, st, f"audc_{r.run_id}_{i}")
                if len(caught) > 2:
                    st.markdown(
                        f"<span class='muted' style='font-size:11px'>"
                        f"+{len(caught) - 2} more</span>",
                        unsafe_allow_html=True,
                    )
        # An explicit affordance as well as the linked id. On a screen whose
        # whole job is "open the evidence", one discoverable way in is thin.
        # "Open" is the verb the dashboard tiles already use.
        if cols[8].button(
            "Open", key=f"audopen2_{r.run_id}", icon=":material/arrow_forward:"
        ):
            _audit_open(r.run_id)

    st.caption(
        "Newest first, fixed sort. Seeded rows carry the demo-timeline date; "
        "live rows carry real execution time. Click a run id to open it."
    )

    st.caption(
        "A run opens as its own screen. Sidebar Back returns here, and the "
        "address bar carries ?run=<id>, so a single run's evidence can be "
        "linked, bookmarked, or opened in a new browser tab."
    )


def _param_widget(spec_id: str, p):  # noqa: ANN001
    """Render the right input widget for a ParamSpec and return the value."""
    key = f"ap_{spec_id}_{p.name}"
    if p.kind == P_CHOICE:
        opts = list(p.choices)
        return st.selectbox(
            p.label, opts, index=opts.index(p.default), key=key, help=p.help
        )
    if p.kind == P_BOOL:
        return st.checkbox(p.label, value=bool(p.default), key=key, help=p.help)
    if p.kind == P_INT:
        return int(
            st.number_input(
                p.label,
                min_value=int(p.minimum) if p.minimum is not None else None,
                max_value=int(p.maximum) if p.maximum is not None else None,
                value=int(p.default),
                step=1,
                key=key,
                help=p.help,
            )
        )
    if p.kind == P_FLOAT:
        return float(
            st.number_input(
                p.label,
                min_value=float(p.minimum) if p.minimum is not None else None,
                max_value=float(p.maximum) if p.maximum is not None else None,
                value=float(p.default),
                step=0.05,
                key=key,
                help=p.help,
            )
        )
    return st.text_input(p.label, value=str(p.default), key=key, help=p.help)


def _matching_datasets(spec) -> list[str]:  # noqa: ANN001
    """Onboarded datasets whose capabilities satisfy the analysis contract."""
    c = spec.contract()
    out = []
    for d in all_datasets():
        ok, _ = c.satisfied_by(set(d.provides), d.rows)
        if ok and dataset_available(d.id):
            out.append(d.id)
    return out


def _step_line(step: dict) -> str:
    status = step["status"]
    color = {"ok": "#1b7f3b", "blocked": "#b3261e", "error": "#b3261e"}.get(
        status, "#5f6b7a"
    )
    return (
        f"<div style='margin:2px 0'><b>{step['title']}</b> "
        f"<span class='muted'>agent <code>{step['agent']}</code> · tool "
        f"<code>{step['tool']}</code></span> "
        f"<span style='color:{color};font-weight:700'>[{status}]</span><br>"
        f"<span class='muted'>{step['summary']}</span></div>"
    )


def _render_profile(profile: dict) -> None:
    a, b, c, d = st.columns(4)
    a.metric("Rows", f"{profile['n_rows']:,}")
    b.metric("Columns", profile["n_cols"])
    c.metric("Duplicate rows", profile["duplicate_rows"])
    d.metric("Memory (MB)", profile["memory_mb"])
    flags = []
    if profile["fully_null_columns"]:
        flags.append(f"fully-null: {', '.join(profile['fully_null_columns'])}")
    if profile["constant_columns"]:
        flags.append(f"constant: {', '.join(profile['constant_columns'])}")
    if profile["high_cardinality_columns"]:
        flags.append(
            f"high-cardinality: {', '.join(profile['high_cardinality_columns'])}"
        )
    if flags:
        st.caption(" · ".join(flags))
    if profile["class_balance"]:
        st.caption(f"Target class balance: {profile['class_balance']}")
    st.dataframe(pd.DataFrame(profile["columns"]), width="stretch")


def _render_quality(quality: dict) -> None:
    verdict = quality["verdict"]
    msg = f"Quality gate: {verdict.upper()} — {quality['headline']}"
    (st.success if verdict == "pass" else st.warning if verdict == "warn" else st.error)(
        msg
    )
    st.dataframe(pd.DataFrame(quality["expectations"]), width="stretch")


def _render_features(features: dict) -> None:
    st.caption(features["headline"])
    st.markdown("**Feature sample** (one row per entity)")
    st.dataframe(pd.DataFrame(features["sample"]), width="stretch")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Lineage** (feature → source · transform)")
        st.dataframe(pd.DataFrame(features["lineage"]), width="stretch")
    with cols[1]:
        st.markdown("**Leakage notes** (build-time)")
        st.dataframe(pd.DataFrame(features["leakage_notes"]), width="stretch")


def _render_leakage(leak: dict) -> None:
    (st.success if leak["passed"] else st.error)(f"Leakage scan: {leak['headline']}")
    st.dataframe(pd.DataFrame(leak["findings"]), width="stretch")
    if leak["suspects"]:
        st.error("Suspected leakage: " + ", ".join(s["feature"] for s in leak["suspects"]))


def _render_analysis_run(pub: dict) -> None:
    st.caption(
        f"Run {pub['run_id']} · analysis '{pub['analysis_name']}' on "
        f"'{pub['dataset_id']}' · status {pub['status']}"
    )
    c = pub["contract"]
    if c["ok"]:
        st.success(
            f"Contract satisfied — requires {c['requires']}; dataset provides "
            f"{c['provides']}; {c['rows']:,} rows (min {c['min_rows']})."
        )
    else:
        st.error("Contract not satisfied — " + "; ".join(c["reasons"]))

    st.markdown("**Governed pipeline**")
    st.markdown(
        "".join(_step_line(s) for s in pub["steps"]) or "<i>no steps ran</i>",
        unsafe_allow_html=True,
    )

    results = pub["results"]
    if "profile" in results:
        st.divider()
        st.markdown("### Profile")
        _render_profile(results["profile"])
    if "quality" in results:
        st.divider()
        st.markdown("### Data-quality expectations")
        _render_quality(results["quality"])
    if "features" in results:
        st.divider()
        st.markdown("### Engineered features")
        _render_features(results["features"])
    if "leakage" in results:
        st.divider()
        st.markdown("### Leakage scan (independent)")
        _render_leakage(results["leakage"])

    st.divider()
    with st.expander("Audit trail + cost (governance evidence)"):
        cost = pub["cost"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Audit events", len(pub["audit"]))
        m2.metric("Cycle time (s)", cost.get("cycle_time_s", 0))
        m3.metric("Cost (USD)", cost.get("cost_usd", 0))
        audit_df = pd.DataFrame(pub["audit"])
        if not audit_df.empty:
            show = [
                col
                for col in ["seq", "agent", "action", "level", "output_summary"]
                if col in audit_df.columns
            ]
            st.dataframe(audit_df[show], width="stretch")


def render_analyses(persona) -> None:  # noqa: ANN001
    st.subheader("Analyses")
    st.markdown(
        "<span class='muted'>The analysis catalog. An analysis is a declarative "
        "spec: a data contract, editable parameters, and governed steps. The engine "
        "checks the contract against the dataset, then runs each step through the "
        "same harness as the hero pipeline (guardrails, RBAC, audit, tracing).</span>",
        unsafe_allow_html=True,
    )

    specs = all_analyses()
    labels = {s.id: s.name for s in specs}
    chosen_id = st.selectbox(
        "Analysis", [s.id for s in specs], format_func=lambda k: labels[k]
    )
    spec = get_analysis(chosen_id)

    st.markdown(
        f"**{spec.name}** — <span class='muted'>{spec.description}</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Contract: requires {sorted(spec.requires)} · min {spec.min_rows} rows · "
        f"controls: {', '.join(spec.controls)}"
    )

    if spec.engine != ENGINE_LINEAR:
        st.info(
            "This is the governed model-training pipeline. It promotes a model and "
            "pauses at the human approval gate, so it runs from the **Run analysis** "
            "section (left), executed by the LangGraph orchestrator — not the linear "
            "engine. Its steps are shown here for the catalog."
        )
        st.markdown(
            "".join(
                f"<div style='margin:2px 0'><b>{s.title}</b> "
                f"<span class='muted'>agent <code>{s.agent}</code> · tool "
                f"<code>{s.tool}</code>{' · GATE' if s.gate else ''}</span></div>"
                for s in spec.steps
            ),
            unsafe_allow_html=True,
        )
        return

    candidates = _matching_datasets(spec)
    if not candidates:
        st.warning("No onboarded dataset satisfies this analysis's contract yet.")
        return

    default_ds = (
        spec.default_dataset_id
        if spec.default_dataset_id in candidates
        else candidates[0]
    )
    left, right = st.columns([2, 3])
    with left:
        dataset_id = st.selectbox(
            "Dataset (contract-matched)",
            candidates,
            index=candidates.index(default_ds),
        )
    with right:
        st.markdown("**Parameters** <span class='muted'>(editable)</span>", unsafe_allow_html=True)
        overrides = {}
        pcols = st.columns(2)
        for i, p in enumerate(spec.params):
            with pcols[i % 2]:
                overrides[p.name] = _param_widget(spec.id, p)

    run_clicked = st.button(
        "Run analysis", type="primary", disabled=not persona.can_run
    )
    if not persona.can_run:
        st.caption(f"Your role ({persona.name}) is read-only and cannot run analyses.")

    if run_clicked:
        try:
            run = analysis_engine.run(spec, dataset_id, overrides, actor=persona)
            st.session_state.analysis_run = run
        except ParamError as exc:
            st.error(f"Parameter error: {exc}")
            st.session_state.analysis_run = None

    run = st.session_state.get("analysis_run")
    if run is not None and run.analysis_id == spec.id:
        st.divider()
        _render_analysis_run(run.to_public_dict())


# --------------------------------------------------------------------------
# Command-center landing (ui-spec 3.2)
# --------------------------------------------------------------------------
def render_home(persona) -> None:  # noqa: ANN001
    """The tile dashboard: four live-number tiles + the Start-a-governed-run CTA.
    Every number comes from the same helpers the surfaces themselves render."""
    from sentinel.govflow import matrix_rows, resolve_tier_for_dataset
    from sentinel.platform.certification import status_of

    st.markdown(
        "<div class='dashhead'><span class='eyebrow'>Governance command center</span>"
        "<div class='h2'>The whole governed platform, at a glance</div>"
        "<div class='lede'>Every surface is a live tile: data under classification, "
        "analyses under certification, agents under templates, adoption trending up. "
        "Start a governed run and watch one request flow through all of it.</div></div>",
        unsafe_allow_html=True,
    )

    tier = resolve_tier_for_dataset(
        "german_credit", persona.tier_role, persona.attestations
    ).tier
    with st.container(border=True):
        cta_l, cta_r = st.columns([8, 3], vertical_alignment="center")
        cta_l.markdown(
            f"<div><div class='cta-t'>Start a governed run</div>"
            f"<div class='cta-d'>german_credit · fair-lending review · resolves to "
            f"{tier} · nine controls arm before any code runs</div></div>",
            unsafe_allow_html=True,
        )
        if cta_r.button(
            "Launch walkthrough →", key="cta_run", type="primary", use_container_width=True
        ):
            _nav_to("Run")

    ds = all_datasets()
    cls_counts: dict[str, int] = {}
    for r in matrix_rows():
        cls_counts[r["classification"]] = cls_counts.get(r["classification"], 0) + 1
    cert_status: dict[str, int] = {}
    for entry in cert_entries():
        s = status_of(entry)
        cert_status[s] = cert_status.get(s, 0) + 1
    reuse = reuse_metrics()
    m = adoption_metrics()

    def _tile(col, title, section_target, key, body_html):  # noqa: ANN001
        with col, st.container(border=True):
            h_l, h_r = st.columns([7, 3], vertical_alignment="center")
            h_l.markdown(f"**{title}**")
            if h_r.button("Open →", key=key, use_container_width=True):
                _nav_to(section_target)
            st.markdown(body_html, unsafe_allow_html=True)

    cls_chips = "".join(
        f"<span class='cls {name.lower()}'>{name} {cls_counts[name]}</span> "
        for name in ("Restricted", "Confidential", "Internal", "Public")
        if name in cls_counts
    )
    cert_badges = (
        f"<span class='badge ok'>{cert_status.get('certified', 0)} certified</span> "
        f"<span class='badge warn'>{cert_status.get('candidate', 0)} candidate</span> "
        f"<span class='badge danger'>{cert_status.get('refused', 0)} refused</span>"
    )
    avail_templates = reuse["templates_total"] - reuse["templates_live"]
    plat_badges = (
        f"<span class='badge ok'>{reuse['agents_covered']}/{reuse['agents_total']} "
        f"agents covered</span> "
        f"<span class='badge warn'>{avail_templates} available</span>"
    )
    weekly = m["weekly"]
    peak = max((n for _, n in weekly), default=1)
    # The value rides inside the bar as an absolutely-positioned label (ui-spec
    # 4.10, "printed above each bar"), not as a sibling above it. As a sibling
    # it consumed column height, which is what squashed every bar to the same
    # 17px; see the .barchart rules for the full account.
    bars = "".join(
        f"<div class='bcol'>"
        f"<div class='bar' style='height:{max(6, int(n / peak * 46))}px'>"
        f"<span class='v'>{n}</span></div>"
        f"<span class='bcap'>{wk.split('-')[-1]}</span></div>"
        for wk, n in weekly
    )

    row1 = st.columns(2)
    _tile(
        row1[0],
        "Datasets",
        "Datasets",
        "tile_open_datasets",
        f"<div class='tile-stat'><span class='big'>{len(ds)}</span>"
        "<span class='unit'>datasets under classification</span></div>"
        f"<div class='breakrow'>{cls_chips}</div>",
    )
    _tile(
        row1[1],
        "Registry",
        "Registry",
        "tile_open_registry",
        f"<div class='tile-stat'><span class='big'>{len(cert_entries())}</span>"
        "<span class='unit'>analyses in the certification lifecycle</span></div>"
        f"<div class='breakrow'>{cert_badges}</div>",
    )
    row2 = st.columns(2)
    _tile(
        row2[0],
        "Platform",
        "Platform",
        "tile_open_platform",
        f"<div class='tile-stat'><span class='big'>{reuse['templates_total']}</span>"
        f"<span class='unit'>agent templates · {reuse['templates_live']} live</span></div>"
        f"<div class='breakrow'>{plat_badges}</div>",
    )
    _tile(
        row2[1],
        "Adoption",
        "Adoption",
        "tile_open_adoption",
        f"<div class='tile-stat'><span class='big'>{m['total_runs']}</span>"
        f"<span class='unit'>runs · {m['promoted']} of {m['credit_risk_runs']} "
        "models promoted</span></div>"
        f"<div class='barchart'>{bars}</div>",
    )
    st.caption(
        "Run history is seeded demo telemetry from actually executed runs, plus "
        "live runs this session; every seeded row is labeled on its surface."
    )


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
# The nav's definition moved to sentinel/ui/nav.py when the manual had to
# describe it: the screens chapter opened with a hand-typed count that a new nav
# item silently falsified. Both read the one list now.

# Deep link. ?run=<id> lands directly on that run's evidence, so an audit-log
# URL opened in a new tab or pasted to a colleague resolves to the run rather
# than the landing screen. Honoured once per session: after that the nav stack
# owns where you are, or the param would drag you back on every rerun.
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
    st.session_state["section"] = _SECTION_AUDIT_RUN
    st.session_state.setdefault("nav_stack", []).append("Audit Log")

section = st.session_state.setdefault("section", "Overview")

# In-app Back: return to the previous screen instead of leaving Sentinel.
# Disabled when there is nowhere to go back to.
if st.sidebar.button(
    "Back",
    key="nav_back",
    icon=":material/arrow_back:",
    disabled=not st.session_state.get("nav_stack"),
    use_container_width=True,
):
    _nav_back()

for _glabel, _items in NAV_GROUPS:
    if _glabel:
        st.sidebar.markdown(f"<div class='gl'>{_glabel}</div>", unsafe_allow_html=True)
    for _item in _items:
        # _nav_to no-ops when _item == section, so re-clicking the active item
        # does not push a duplicate onto the history or trigger a truncating
        # rerun that would cull the visible section's widgets.
        if st.sidebar.button(
            _item,
            key=NAV_KEYS[_item],
            type="primary" if _item == section else "secondary",
            icon=NAV_ICONS.get(_item),
            use_container_width=True,
        ):
            _nav_to(_item)

persona = get_persona(st.session_state.persona_id)

header(persona)
st.divider()

if section == "Overview":
    render_home(persona)
    st.stop()

if section == "Run":
    # The stepper's "Audit trail" button needs _audit_open, and govflow cannot
    # import it: app.py imports sentinel.ui.govflow, so importing back would be
    # a cycle. Same injection the manual and FAQ take, through session state
    # rather than an argument because the panel that needs it is four calls
    # deep and threading it down would touch every panel signature.
    st.session_state["_govflow_open_audit"] = _audit_open
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

if section == _SECTION_TEMPLATES:
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
    # _nav_to is passed in rather than imported by the manual: app.py imports
    # sentinel.ui.manual, so the manual importing back would be a cycle.
    render_manual(_nav_to)
    st.stop()

if section == "FAQ":
    # Same injection as the manual: these screens jump into a chapter, so they
    # need _nav_to, and importing it back would be a cycle.
    render_faq(_nav_to)
    st.stop()

if section == "Ask me":
    render_ask(_nav_to)
    st.stop()

if section == _SECTION_AUDIT_RUN:
    render_audit_run(persona)
    st.stop()

# Fall-through. Every section above stops explicitly, so reaching here means
# st.session_state.section holds a screen that no longer exists -- in practice
# "Pipeline", left in a session that was open when the screen was retired.
# Land on Overview rather than rendering a blank page below the nav.
st.session_state["section"] = "Overview"
render_home(persona)
