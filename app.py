"""Sentinel — Streamlit UI (six tabs over the governed pipeline).

Run: uv run streamlit run app.py

The analysis underneath is always real. In scripted mode the step narration is
deterministic (labeled honestly); the Live LLM toggle routes narration through
a real model behind a cost cap.
"""

from __future__ import annotations

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
from sentinel.datasets import all_datasets
from sentinel.datasets import available as dataset_available
from sentinel.govflow.controls_info import control_info
from sentinel.harness.controls import CONTROL_CATALOG, ControlSettings, from_disabled
from sentinel.harness.identity import all_personas, default_persona, get_persona
from sentinel.harness.model_card import ModelCard, render_markdown, render_pdf
from sentinel.orchestrator import (
    STATUS_AWAITING,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_REJECTED,
    Orchestrator,
)
from sentinel.platform import (
    adoption_metrics,
    agent_registry,
    all_patterns,
    all_templates,
    load_playbooks,
    model_versions,
    reuse_metrics,
)
from sentinel.platform.certification import CertificationError, assign_validator
from sentinel.platform.certification import all_entries as cert_entries
from sentinel.platform.certification import evaluate as evaluate_cert
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED
from sentinel.platform.templates import AVAILABLE, LIVE
from sentinel.rag import corpus_summary
from sentinel.ui.govflow import render_govflow

st.set_page_config(page_title="Sentinel — Governed Agentic Analysis", layout="wide")

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
      .topbar {
        display:flex; align-items:center; gap:18px; background:var(--chrome-bg);
        border:1px solid var(--chrome-border); border-radius:var(--r-md);
        padding:10px 16px; box-shadow:var(--shadow-sm);
      }
      .topbar .brand { display:flex; align-items:center; gap:11px; }
      .topbar .brand svg { width:26px; height:26px; display:block; }
      .topbar .wm { font-weight:700; letter-spacing:.22em; font-size:15px;
        color:var(--chrome-ink); }
      .topbar .sub { color:var(--chrome-muted); font-size:11px; letter-spacing:.05em;
                     border-left:1px solid var(--chrome-border); padding-left:11px; }
      .topbar .spacer { flex:1; }
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
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label {
        display:flex; width:100%; padding:8px 11px; border-radius:9px;
        border:1px solid transparent; margin:1px 0;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background:var(--chrome-hover);
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] {
        background:var(--chrome-abg); border-color:var(--chrome-aborder);
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] p {
        color:var(--chrome-aink); font-weight:650;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label > div > div
        > div:nth-of-type(1) {
        display:none;  /* hide the radio circle; the row itself is the affordance */
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size:13.5px; font-weight:600; color:var(--chrome-muted);
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
      .enginebar { display:flex; flex-wrap:wrap; align-items:center; gap:7px;
                   margin:0 0 14px; padding:10px 13px; background:var(--surface);
                   border:1px solid var(--border); border-radius:var(--r-md);
                   box-shadow:var(--shadow-sm); }
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

      /* ---------- sidebar nav groups (ui-spec 2.2) ---------- */
      .gl { font-size:9.5px; font-weight:700; letter-spacing:.11em; text-transform:uppercase;
            color:var(--chrome-muted); padding:0 10px; margin:14px 0 4px 0; }
      section[data-testid="stSidebar"] .stButton button {
        display:flex; justify-content:flex-start; width:100%; padding:8px 11px;
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
      section[data-testid="stSidebar"] .stButton button p { font-size:13.5px; }

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
      .barchart { display:flex; align-items:flex-end; gap:10px; height:70px;
        padding-top:14px; margin-top:6px; }
      .barchart .bcol { flex:1; display:flex; flex-direction:column; align-items:center;
        justify-content:flex-end; height:100%; gap:3px; }
      .barchart .bar { width:100%; background:var(--accent-soft);
        border:1px solid var(--accent-soft-border); border-radius:4px 4px 0 0; }
      .barchart .v { font-family:var(--mono); font-size:10.5px; color:var(--muted); }
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

if "orch" not in st.session_state:
    st.session_state.orch = Orchestrator()
    st.session_state.run_id = None
orch: Orchestrator = st.session_state.orch

if "analysis_engine" not in st.session_state:
    st.session_state.analysis_engine = AnalysisEngine()
    st.session_state.analysis_run = None
analysis_engine: AnalysisEngine = st.session_state.analysis_engine


# --------------------------------------------------------------------------
# Login gate (ui-spec 3.1): the six personas as cards, before any chrome.
# --------------------------------------------------------------------------
_SHIELD_SVG = (
    "<svg viewBox='0 0 24 24' aria-hidden='true'>"
    "<path d='M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5z' fill='#1e50a0'/>"
    "<path d='M8 12l3 3 5-6' fill='none' stroke='#fff' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'/></svg>"
)

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
                    st.session_state.section = "Overview"
                    st.rerun()
    st.markdown(
        "<div class='login-foot'>Faux sign-in for the demo. No credentials, no auth. "
        "Pick anyone to enter.</div>",
        unsafe_allow_html=True,
    )


if "persona_id" not in st.session_state:
    render_login()
    st.stop()


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
    can_toggle = persona is not None and persona.can_toggle_controls
    st.markdown("<span class='eyebrow'>Pipeline harness</span>", unsafe_allow_html=True)
    catalog = {c[0]: c for c in CONTROL_CATALOG}
    for cid in _PLANE_CATALOG:
        info = control_info(cid)
        if cid in catalog and can_toggle:
            st.checkbox(
                f"Disable {info.name}",
                key=f"ctrl_off_{cid}",
                help=f"{info.what} If off: {catalog[cid][3]}",
            )
        else:
            st.markdown(
                f"<div style='margin:4px 0'><span class='ctlchip pass'>"
                f"<span class='st'></span>{info.name}</span> "
                f"<span class='muted'>{info.what}</span></div>",
                unsafe_allow_html=True,
            )
    if not can_toggle:
        st.caption("Toggling requires the Platform Admin persona.")
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


def header(persona=None) -> None:  # noqa: ANN001
    """The topbar command frame (ui-spec 2.1): brand lockup + live context chips
    + the Controls popover. The chips reflect the actual session state (persona,
    dataset, purpose, computed tier), not decoration."""
    draft = st.session_state.get("govflow_draft") or {}
    pub = st.session_state.get("govflow_result") or {}
    dataset = pub.get("dataset") or draft.get("dataset") or "german_credit"
    purpose = pub.get("purpose") or draft.get("purpose") or "fair_lending"
    from sentinel.govflow import matrix_rows, resolve_tier_for_dataset
    from sentinel.govflow.purpose_matrix import PURPOSE_LABEL

    classification = next(
        (r["classification"] for r in matrix_rows() if r["dataset"] == dataset), ""
    )
    cls_kind = classification.lower() if classification else "internal"
    tier = "—"
    dot = "#9aa8c0"
    pname = "—"
    if persona is not None:
        pname = persona.name
        tier = resolve_tier_for_dataset(
            dataset, persona.tier_role, persona.attestations
        ).tier
        dot = "#5fdc8a" if "certified" in persona.attestations else "#e2a03a"
    purpose_label = PURPOSE_LABEL.get(purpose, purpose)
    any_off = _control_settings(persona).any_disabled
    gov_badge = (
        "<span class='badge warn'>UNGOVERNED next run</span>"
        if any_off
        else "<span class='badge ok'>governed</span>"
    )
    left, right = st.columns([11, 2], vertical_alignment="center")
    with left:
        st.markdown(
            f"""
            <div class='topbar'>
              <div class='brand'>{_SHIELD_SVG}
                <span class='wm'>SENTINEL</span>
                <span class='sub'>Governed Agentic Analysis</span>
              </div>
              <div class='spacer'></div>
              <div class='ctx'>
                <span class='ctx-chip'><span class='dot' style='background:{dot}'></span>
                  <span class='k'>Acting as</span> {pname}</span>
                <span class='ctx-chip'><span class='k'>Data</span> {dataset}
                  <span class='cls {cls_kind}'>{classification or "n/a"}</span></span>
                <span class='ctx-chip'><span class='k'>Purpose</span> {purpose_label}</span>
                <span class='ctx-chip tier'><span class='k'>Tier</span>
                  <span class='tier-badge'>{tier}</span></span>
                {gov_badge}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        with st.popover("Controls"):
            _controls_plane(persona)


def _control_settings(persona) -> ControlSettings:  # noqa: ANN001
    """Read the header-chip toggles into the settings for the next run. Only a
    persona holding toggle authority can have live toggles; anyone else runs
    fully governed even if stale ctrl_off_* keys linger from an Admin session."""
    if persona is None or not persona.can_toggle_controls:
        return ControlSettings()
    return from_disabled(
        [c[0] for c in CONTROL_CATALOG if st.session_state.get(f"ctrl_off_{c[0]}")]
    )


def controls(persona) -> None:
    questions = orch.questions()
    labels = {q["id"]: q["label"] for q in questions}
    c1, c2, c3 = st.columns([4, 2, 1])
    with c1:
        qid = st.selectbox(
            "Preset question",
            options=list(labels),
            format_func=lambda k: labels[k],
        )
        st.selectbox(
            "Dataset", ["UCI German Credit (1,000 loan applicants)"], disabled=True
        )
    with c2:
        mode = st.radio(
            "Narration",
            ["scripted", "live"],
            format_func=lambda m: "Scripted (free)" if m == "scripted" else "Live LLM",
            horizontal=True,
        )
        st.caption(
            "Scripted = deterministic narration over a live analysis (zero cost). "
            "Live = real model, cost-capped."
        )
    with c3:
        st.write("")
        st.write("")
        run_clicked = st.button(
            "Run", type="primary", width="stretch", disabled=not persona.can_run
        )
    if not persona.can_run:
        st.caption(
            f"Your role ({persona.name}) cannot run analyses. "
            "Switch to an Analyst or Admin to run."
        )

    settings = _control_settings(persona)
    if settings.any_disabled:
        st.error(
            "Controls disabled via the header chips: "
            + ", ".join(settings.disabled_names())
            + ". The next run executes UNGOVERNED and the disabling is audited."
        )
    elif persona.can_toggle_controls:
        st.caption(
            "Admin: click a governance chip in the header to disable a control "
            "for the next run and watch the failure it prevents."
        )

    if run_clicked:
        state = orch.start_run(
            qid, narration_mode=mode, controls=settings, actor=persona
        )
        st.session_state.run_id = state.run_id


# --------------------------------------------------------------------------
# Tab renderers
# --------------------------------------------------------------------------
def tab_pipeline(pub: dict, state) -> None:
    st.subheader("Agent pipeline")
    st.caption(f"Narration: {pub['narration_label']}")
    with st.expander("Orchestration graph (LangGraph)", expanded=False):
        st.graphviz_chart(orch.graph_dot(), width="stretch")
        st.caption(
            "A LangGraph workflow, not an autonomous agent. The graph is static: "
            "fixed nodes and edges an examiner can read. The human gate is a "
            "LangGraph interrupt; the approve/reject branch is the dashed edge. "
            "Dynamic self-decomposition (orchestrator-workers) is deliberately "
            "avoided so the control flow stays fixed and auditable."
        )

    # Control envelope: the guardrails wrapped around this run, on or off.
    disabled = set(pub.get("controls_disabled", []))
    chips = []
    for _cid, name, _desc, _breaks in CONTROL_CATALOG:
        on = name not in disabled
        cls = "pill-in_use" if on else "pill-avoided"
        chips.append(f"<span class='pill {cls}'>{name}: {'on' if on else 'OFF'}</span>")
    st.markdown(
        "<span class='muted'>Control envelope:</span> " + " ".join(chips),
        unsafe_allow_html=True,
    )

    for step in pub["steps"]:
        icon = {
            "done": "[done]",
            "approved": "[approved]",
            "awaiting_approval": "[awaiting approval]",
            "rejected": "[rejected]",
        }.get(step["status"], f"[{step['status']}]")
        tag = "LIVE" if step["live"] else "scripted"
        with st.container(border=True):
            st.markdown(f"**{step['title']}**  `{icon}`  · _{tag}_")
            st.write(step["narration"])
            if step["fell_back"]:
                st.warning(f"Live narration fell back to scripted: {step['fallback_reason']}")
            if step["status"] == "awaiting_approval":
                persona = get_persona(
                    st.session_state.get("persona_id", default_persona().id)
                )
                st.info(
                    "Human-in-the-loop gate: approve to promote this model, or "
                    f"reject. Acting as **{persona.name}** — "
                    + (
                        "holds promotion authority."
                        if persona.can_approve
                        else "does NOT hold promotion authority (segregation of "
                        "duties); an Approve attempt will be denied and logged."
                    )
                )
                a, r, _ = st.columns([1, 1, 4])
                if a.button("Approve", type="primary"):
                    orch.approve(state.run_id, approved=True, actor=persona)
                    st.rerun()
                if r.button("Reject"):
                    orch.approve(state.run_id, approved=False, actor=persona)
                    st.rerun()
    if pub.get("summary_narration"):
        st.success(pub["summary_narration"])
    if pub["status"] == STATUS_REJECTED:
        st.error("Run stopped by human rejection. No model promoted.")


def tab_results(pub: dict) -> None:
    model = pub.get("model")
    if not model:
        st.info("Run a model to see results.")
        return
    m = model["metrics"]
    cols = st.columns(5)
    for col, (k, v) in zip(cols, m.items(), strict=True):
        col.metric(k.upper(), v)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Class balance**")
        cb = model["profile"]["class_balance"]
        st.bar_chart(pd.DataFrame({"count": cb}))
        st.markdown("**Confusion matrix (test)**")
        cm = model["confusion"]
        st.dataframe(
            pd.DataFrame(
                [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]],
                index=["actual good", "actual default"],
                columns=["pred good", "pred default"],
            )
        )
    with c2:
        st.markdown("**Top features (|coefficient|)**")
        tf = pd.DataFrame(model["top_features"]).set_index("name")["coefficient"]
        st.bar_chart(tf)
        st.markdown("**ROC curve**")
        roc = model["roc_curve"]
        st.line_chart(pd.DataFrame({"TPR": roc["tpr"]}, index=roc["fpr"]))


def tab_audit(pub: dict) -> None:
    st.subheader("Audit log (append-only)")
    st.caption(
        "Every agent action, incl. one RBAC denial and one PII redaction. Each "
        "event is stamped with the acting identity and the policy version."
    )
    rows = []
    for e in pub["audit"]:
        rows.append(
            {
                "seq": e["seq"],
                "level": e["level"],
                "actor": e.get("actor", e["agent"]),
                "action": e["action"],
                "summary": e["output_summary"],
                "data_touched": ", ".join(e["data_touched"]),
                "policy": e.get("policy_version", ""),
            }
        )
    df = pd.DataFrame(rows)

    def _style(row):
        color = {
            "blocked": "background-color:#fde7e6",
            "redaction": "background-color:#fff4e0",
            "gate": "background-color:#eef2fb",
        }.get(row["level"], "")
        return [color] * len(row)

    st.dataframe(df.style.apply(_style, axis=1), width="stretch", height=460)


def tab_fairness(pub: dict) -> None:
    fr = pub.get("fairness")
    if not fr:
        st.info("Approve the model to run the fairness review.")
        return
    verdict = (
        "<span class='ok'>within tolerance</span>"
        if fr["passes"]
        else "<span class='flag'>FLAGGED for review</span>"
    )
    st.subheader(f"Fairness across {fr['protected_attribute']}")
    st.markdown(
        f"Disparity ratio **{fr['disparity_ratio']}** "
        f"(threshold {fr['threshold']}) — {verdict}",
        unsafe_allow_html=True,
    )
    groups = pd.DataFrame(fr["groups"])
    st.bar_chart(groups.set_index("group")["selection_rate"])
    st.dataframe(groups, width="stretch")
    st.caption(fr["note"])


def tab_model_card(pub: dict) -> None:
    card_dict = pub.get("model_card")
    if not card_dict:
        st.info("Approve the model to generate the model card.")
        return
    card = ModelCard(**card_dict)
    st.markdown(render_markdown(card))
    pdf_path = render_pdf(card, "runtime/model_card_download.pdf")
    st.download_button(
        "Download model card (PDF)",
        data=pdf_path.read_bytes(),
        file_name=f"model_card_{pub['run_id']}.pdf",
        mime="application/pdf",
        type="primary",
    )


def tab_cost(pub: dict) -> None:
    c = pub["cost"]
    st.subheader("Cost & KPIs")
    a, b, d, e = st.columns(4)
    a.metric("Tokens", c.get("tokens", 0))
    b.metric("Cost (USD)", f"${c.get('cost_usd', 0)}")
    d.metric("Cycle time", f"{c.get('cycle_time_s', 0)}s")
    e.metric("Eval pass-rate", c.get("eval_pass_rate", 0))
    f, g = st.columns(2)
    f.metric("Human overrides", c.get("human_overrides", 0))
    g.metric("Narration mode", c.get("narration_mode", "templated"))
    evals = pub.get("evals")
    if evals:
        st.markdown("**Eval gate**")
        promoted = evals["promoted"]
        st.markdown(
            f"{evals['passed']}/{evals['passed'] + evals['failed']} checks passed — "
            + (
                "<span class='ok'>promotion allowed</span>"
                if promoted
                else "<span class='flag'>BLOCKED from promotion</span>"
            ),
            unsafe_allow_html=True,
        )
        st.dataframe(pd.DataFrame(evals["results"]), width="stretch")


def tab_knowledge(pub: dict) -> None:
    st.subheader("Knowledge & citations")
    st.caption(
        "Agents ground compliance claims in the governed corpus and cite the "
        "passage, instead of asserting it. Retrieval runs on a local vector index "
        "by default; a real-AWS pgvector store is available behind a config switch."
    )
    retrieval = pub.get("retrieval")
    if not retrieval:
        st.info("Approve the model to run the fairness review and its retrieval.")
    else:
        st.markdown(
            f"**Retrieval query** (via `{retrieval['backend']}` vector store)"
        )
        st.code(retrieval["query"], language="text")
        st.markdown("**Retrieved passages (cited into the fairness review)**")
        for c in retrieval["citations"]:
            tag = "public" if c["provenance"] == "public" else "synthetic"
            cls = "pill-in_use" if c["provenance"] == "public" else "pill-planned"
            st.markdown(
                f"<span class='pill {cls}'>{tag}</span> "
                f"**{c['citation']}** &nbsp;<span class='muted'>score "
                f"{c['score']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<span class='muted'>{c['text']}</span>", unsafe_allow_html=True)
            st.write("")

    st.divider()
    st.markdown("**Corpus**")
    st.caption(
        "Real public regulation plus synthetic internal standards, labeled by "
        "provenance. No confidential bank documents are used."
    )
    st.dataframe(pd.DataFrame(corpus_summary()), width="stretch")


def tab_traces(pub: dict) -> None:
    st.subheader("Traces (OpenTelemetry)")
    st.caption(
        "Every agent step and gateway call emits an OpenTelemetry span, the "
        "recognized tracing standard. An OTLP exporter can ship these to Jaeger, "
        "Tempo, or Honeycomb without changing the call sites."
    )
    traces = pub.get("traces", [])
    if not traces:
        st.info("Run an analysis to produce a trace.")
        return
    total = round(sum(t["duration_ms"] for t in traces), 2)
    st.metric("Spans", len(traces), f"{total} ms total")
    rows = [
        {
            "span": t["name"],
            "duration_ms": t["duration_ms"],
            **{k: v for k, v in t.get("attributes", {}).items()},
        }
        for t in traces
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", height=360)


def tab_memory(pub: dict) -> None:
    st.subheader("Memory & retention")
    st.caption(
        "Governed memory is a data-retention control. Short-term working context "
        "is ephemeral; long-term precedent is retained under policy."
    )
    mem = pub.get("memory", {})

    st.markdown("**Short-term (working context)**")
    st.caption("Held for this run only, then discarded. Retention: ephemeral.")
    st_keys = mem.get("short_term", [])
    if st_keys:
        st.markdown(
            " ".join(f"<span class='ctrl-chip'>{k}</span>" for k in st_keys),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No working context yet.")

    st.divider()
    st.markdown("**Long-term (precedent)**")
    st.caption(
        "Prior outcomes for this question, retained to inform future runs. "
        "Retention: records-retention policy."
    )
    lt = mem.get("long_term", [])
    if lt:
        rows = []
        for p in lt:
            d = dict(p)
            d["origin"] = "seeded" if p.get("seeded") else "live"
            rows.append(d)
        st.dataframe(
            pd.DataFrame(rows)[
                ["question_id", "status", "disparity_ratio", "origin", "created_at"]
            ],
            width="stretch",
        )
    else:
        st.info("No precedent recorded for this question yet.")


def tab_gateway(pub: dict) -> None:
    st.subheader("Model gateway ledger")
    st.caption(
        "The central control point for model access. Every call is classified, "
        "routed to a model tier, checked against the cache, and cost-capped. In "
        "scripted mode calls execute as templates (zero cost); the routing "
        "decision is still recorded so you can see how live calls would be routed."
    )
    ledger = pub.get("gateway_ledger", [])
    if not ledger:
        st.info("Run an analysis to populate the gateway ledger.")
        return
    total_cost = sum(e["cost_usd"] for e in ledger)
    hits = sum(1 for e in ledger if e["cache"] == "hit")
    elevated = sum(1 for e in ledger if e["stakes"] == "elevated")
    a, b, c, d = st.columns(4)
    a.metric("Calls", len(ledger))
    b.metric("Elevated-stakes", elevated)
    c.metric("Cache hits", hits)
    d.metric("Cost (USD)", f"${round(total_cost, 6)}")
    df = pd.DataFrame(ledger)[
        [
            "seq",
            "call_kind",
            "stakes",
            "routed_tier",
            "routed_model",
            "provider",
            "cache",
            "tokens",
            "cost_usd",
            "policy",
        ]
    ]
    st.dataframe(df, width="stretch", height=360)
    st.caption(
        "Routing: elevated-stakes narration (model performance, promotion) routes "
        "to a capable model; routine narration to a cheap one. Re-run the same "
        "question to see cache hits."
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
        "pre-wired: tool allow-list, RBAC scope, and evals. New agents start from a "
        "governed blueprint, not a blank file.</span>",
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
    for t in all_templates():
        realized = (
            f" · realized by: {', '.join(t.realized_by)}" if t.realized_by else ""
        )
        st.markdown(
            f"**{t.name}** {_pill(t.status)}<br>"
            f"<span class='muted'>{t.purpose}</span><br>"
            f"<span class='muted'>pattern: {t.pattern} · tools: "
            f"{', '.join(t.tools)} · RBAC: {t.rbac_scope}{realized}</span>",
            unsafe_allow_html=True,
        )
        st.write("")

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


def render_registry() -> None:
    st.subheader("Model & agent registry")
    st.markdown(
        "<span class='muted'>The MRM model inventory. Every trained model is "
        "versioned with its metrics, fairness verdict, and promotion status; every "
        "agent is versioned with its template lineage and tool scope.</span>",
        unsafe_allow_html=True,
    )

    st.markdown("### Models")
    mv = model_versions()
    if mv:
        rows = []
        for m in mv:
            d = m.to_dict()
            d["origin"] = "seeded" if m.seeded else ("ungoverned" if m.ungoverned else "live")
            rows.append(d)
        df = pd.DataFrame(rows)[
            [
                "version",
                "question_id",
                "auc",
                "disparity_ratio",
                "fairness_pass",
                "status",
                "origin",
                "created_at",
            ]
        ]
        st.dataframe(df, width="stretch")
        st.caption(
            "Status comes from the eval gate and the human decision: promoted, "
            "blocked, or rejected. 'seeded' rows are labeled demo history; 'live' "
            "rows accumulate as you complete runs this session."
        )
    else:
        st.info("No models registered yet.")

    st.markdown("### Agents")
    ar = agent_registry()
    st.dataframe(pd.DataFrame([a.to_dict() for a in ar]), width="stretch")
    st.caption(
        "Each agent is derived from a template and carries its tool scope and RBAC "
        "scope. This is where new agents built from templates would be inventoried."
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
            for g in decision.gates:
                mark = "✓" if g.passed else "✗"
                cls = "muted" if g.passed else "flag"
                ctl = f" <span class='ctrl-chip'>{g.control}</span>" if g.control else ""
                st.markdown(
                    f"<span class='{cls}'>{mark} {g.name}</span>{ctl} "
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


def render_datasets() -> None:
    st.subheader("Dataset registry")
    st.markdown(
        "<span class='muted'>The onboarded-dataset inventory. Each dataset carries "
        "its license (and a commercial-use flag the platform enforces), the "
        "capabilities it provides, and its provenance. Analyses match against "
        "these via data contracts.</span>",
        unsafe_allow_html=True,
    )
    rows = []
    for d in all_datasets():
        rows.append(
            {
                "id": d.id,
                "name": d.name,
                "provides": ", ".join(sorted(d.provides)),
                "rows": d.rows,
                "tables": d.tables,
                "license": d.license,
                "commercial": "yes" if d.commercial_ok else "flagged",
                "onboarded": "yes" if dataset_available(d.id) else "registered",
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch")
    st.caption(
        "All 8 registered datasets ship onboarded (scripts/onboard_datasets.py "
        "produces their local files). 'flagged' commercial status means the "
        "license restricts commercial use and the platform blocks it."
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
            st.session_state.section = "Run"
            st.rerun()

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
                st.session_state.section = section_target
                st.rerun()
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
    bars = "".join(
        f"<div class='bcol'><span class='v'>{n}</span>"
        f"<div class='bar' style='height:{max(6, int(n / peak * 46))}px'></div>"
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
def persona_picker():
    """Sidebar identity selector. No real auth; role-aware governance demo."""
    personas = all_personas()
    ids = [p.id for p in personas]
    labels = {p.id: p.name for p in personas}
    default_id = st.session_state.get("persona_id", default_persona().id)
    chosen = st.sidebar.selectbox(
        "Acting as",
        options=ids,
        index=ids.index(default_id),
        format_func=lambda k: labels[k],
    )
    st.session_state.persona_id = chosen
    persona = get_persona(chosen)
    caps = []
    caps.append("run" if persona.can_run else "no-run")
    caps.append("approve" if persona.can_approve else "no-approve")
    if persona.read_only:
        caps.append("read-only")
    if persona.can_toggle_controls:
        caps.append("toggle-controls")
    st.sidebar.caption(f"{persona.role} · {', '.join(caps)}")
    st.sidebar.caption(persona.description)
    return persona


# The grouped sidebar (ui-spec 2.2): Overview, then Workspace / Governance /
# Platform groups. Buttons write st.session_state.section; the active item
# renders as the primary variant (styled as the nav active state).
_NAV_GROUPS: list[tuple[str | None, list[str]]] = [
    (None, ["Overview"]),
    ("Workspace", ["Run", "Pipeline", "Analyses"]),
    ("Governance", ["Datasets", "Registry"]),
    ("Platform", ["Platform", "Adoption"]),
]
_NAV_KEYS = {
    "Overview": "nav_home",
    "Run": "nav_run",
    "Pipeline": "nav_pipeline",
    "Analyses": "nav_analyses",
    "Datasets": "nav_datasets",
    "Registry": "nav_registry",
    "Platform": "nav_platform",
    "Adoption": "nav_adoption",
}

section = st.session_state.setdefault("section", "Overview")
_nav_counts = {
    "Datasets": len(all_datasets()),
    "Registry": len(cert_entries()),
    "Platform": reuse_metrics()["templates_total"],
}
for _glabel, _items in _NAV_GROUPS:
    if _glabel:
        st.sidebar.markdown(f"<div class='gl'>{_glabel}</div>", unsafe_allow_html=True)
    for _item in _items:
        _n = _nav_counts.get(_item)
        _label = f"{_item} · {_n}" if _n is not None else _item
        # Guard on _item != section: re-clicking the active item must be a
        # no-op. Writing + rerun mid-loop truncates the run before the section
        # body renders, so Streamlit would cull the visible section's widgets.
        if (
            st.sidebar.button(
                _label,
                key=_NAV_KEYS[_item],
                type="primary" if _item == section else "secondary",
                use_container_width=True,
            )
            and _item != section
        ):
            st.session_state.section = _item
            st.rerun()

st.sidebar.divider()
persona = persona_picker()

header(persona)
st.divider()

if section == "Overview":
    render_home(persona)
    st.stop()

if section == "Run":
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

if section == "Registry":
    render_registry()
    st.stop()

if section == "Adoption":
    render_adoption()
    st.stop()

# Fall-through: the credit-pipeline hero ("Pipeline" in the sidebar).
controls(persona)
st.divider()

run_id = st.session_state.get("run_id")
state = orch.get_run(run_id) if run_id else None

if state is None:
    st.info("Choose a preset question and click Run to start a governed analysis.")
else:
    pub = state.to_public_dict()
    status_note = {
        STATUS_AWAITING: "Paused at the human approval gate.",
        STATUS_COMPLETED: "Completed and promoted.",
        STATUS_BLOCKED: "Completed but blocked from promotion by the eval gate.",
        STATUS_REJECTED: "Rejected by the human reviewer.",
    }.get(pub["status"], pub["status"])
    st.caption(f"Run {pub['run_id']} · {status_note}")
    if pub.get("ungoverned"):
        st.error(
            "UNGOVERNED demo run — controls disabled: "
            + ", ".join(pub["controls_disabled"])
            + ". This is not a governed run; the disabling is recorded in the "
            "audit log. Re-run with controls on for a governed analysis."
        )

    tabs = st.tabs(
        [
            "Pipeline",
            "Results",
            "Audit Log",
            "Fairness",
            "Model Card",
            "Cost & KPIs",
            "Gateway",
            "Knowledge",
            "Memory",
            "Traces",
        ]
    )
    with tabs[0]:
        tab_pipeline(pub, state)
    with tabs[1]:
        tab_results(pub)
    with tabs[2]:
        tab_audit(pub)
    with tabs[3]:
        tab_fairness(pub)
    with tabs[4]:
        tab_model_card(pub)
    with tabs[5]:
        tab_cost(pub)
    with tabs[6]:
        tab_gateway(pub)
    with tabs[7]:
        tab_knowledge(pub)
    with tabs[8]:
        tab_memory(pub)
    with tabs[9]:
        tab_traces(pub)
