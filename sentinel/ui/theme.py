"""The design system, as CSS: one app theme and one login theme.

Both lived at the top of `app.py`, 680 lines of stylesheet ahead of the first
line of behaviour, which made the module's shape unreadable and kept the theme
in the same file as every screen consuming it.

Every color is a token from docs/ui-spec.md's light palette, and components
style through the tokens rather than restating hex values. The pixel target is
docs/mockups/sentinel-stepper-mockup.html.
"""

from __future__ import annotations

import streamlit as st

APP_CSS = """
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
    """


# The always-dark login gate (ui-spec 1.5 + 3.1): rail tokens are hardcoded on
# purpose; the sign-in moment does not follow the app theme.
LOGIN_CSS = """
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



def inject_app_css() -> None:
    """Paint the app theme. Called once, before any screen renders."""
    st.markdown(APP_CSS, unsafe_allow_html=True)


def inject_login_css() -> None:
    """Paint the login theme, replacing the app theme for the sign-in moment."""
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
