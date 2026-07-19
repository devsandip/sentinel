"""The Governed codegen surface as a step-through walkthrough.

The brief (docs/more_ideas.md): the nine stages used to flash past in a
spinner; every stage should be explicit, with something to click and something
to read at each one. This module renders the flow as a stepper: Ask and Plan
are interactive configuration, Run executes the whole governed flow (the flow
module stays the single authority on stage order and stop behavior), and the
user then steps through Access to Attest over the completed run.

Presentation only. Controls are enforced in govflow/codegen/disclosure/
sandbox; their plain-language identity lives in govflow/controls_info.py.
"""

from __future__ import annotations

import html
import re
import time

import pandas as pd
import streamlit as st

from ..analyses.spec import P_BOOL, P_CHOICE, P_FLOAT, P_INT
from ..codegen.allowlist import (
    ALLOWED_IMPORTS,
    DYNCODE_BUILTINS,
    DYNCODE_MODULES,
    EGRESS_MODULES,
    FS_MODULES,
    L3_ALLOWED_IMPORTS,
)
from ..codegen.generate import has_scripted_repair
from ..codegen.prompts import build_system_prompt, build_user_prompt
from ..datasets import all_datasets
from ..gateway.model_gateway import ANTHROPIC, TEMPLATED, ModelGateway
from ..govflow import (
    evaluate_purpose,
    matrix_rows,
    resolve_tier_for_dataset,
    run_governed_analysis,
    run_l3_analysis,
)
from ..govflow.controls_info import control_info
from ..govflow.l1 import L1_PARAMS
from ..govflow.l3 import has_l3_repair
from ..govflow.purpose_matrix import PURPOSE_LABEL, PURPOSES, SHOWPIECE
from ..govflow.tiers import (
    ATT_CERTIFIED,
    ATT_SANDBOX_WAIVER,
    CLASSIFICATION_CEILING,
    ROLE_COMPLIANCE,
    ROLE_DATA_SCIENTIST,
    ROLE_EXECUTIVE,
    ROLE_MODEL_VALIDATOR,
)

STAGES = [
    "Ask", "Plan", "Access", "Generate", "Gate", "Execute", "Screen", "Interpret", "Attest",
]
# The rail has a 10th, visually distinct stop: the Architecture overview
# (ui-spec 2.3). It is an appendix, not a stage; the flow knows nothing of it.
ARCHITECTURE = "Architecture"
NAV_STOPS = STAGES + [ARCHITECTURE]

# The neutral badge next to "Stage N of 9" in each panel head (mockup phead).
_STAGE_KICKER = {
    "Ask": "Bind & scope",
    "Plan": "Select certified analysis",
    "Access": "Enforce by construction",
    "Generate": "Model writes code",
    "Gate": "Static review",
    "Execute": "Sandboxed run",
    "Screen": "Disclosure control",
    "Interpret": "Narrate & check",
    "Attest": "Evidence & signoff",
}

# In / Does / Out, one line each (ui-spec 4.5). Honest: matches the flow.
_IODID = {
    "Ask": (
        "Free choice of dataset, purpose, question",
        "Binds identity, declares the purpose, computes the autonomy tier",
        "A frozen request at a computed tier; the tier cannot change mid-request",
    ),
    "Plan": (
        "The frozen request",
        "Binds a certified registry entry; checks the data contract for drift",
        "A chosen analysis plus parameters",
    ),
    "Access": (
        "The purpose and the grant",
        "Checks purpose limitation, then builds a policy-scoped view",
        "A scoped table; a denied column does not exist on it",
    ),
    "Generate": (
        "The question plus the fenced ctx API",
        "The model writes analysis code (seeded sample in scripted mode)",
        "A code string, unexecuted, headed for the gate",
    ),
    "Gate": (
        "The unexecuted code",
        "Two parsers walk it: Python ast, sqlglot for ctx.sql. No execution",
        "Cleared for the sandbox, or a refusal naming the control and line",
    ),
    "Execute": (
        "Gated code plus the scoped table",
        "Runs in a subprocess sandbox with caps and a single emit channel",
        "The raw emitted result, still unscreened",
    ),
    "Screen": (
        "The raw emitted result",
        "Suppresses small cells; measures proxy association; records findings",
        "The screened table: the only thing anything downstream sees",
    ),
    "Interpret": (
        "The screened table only",
        "Composes the narration, then checks it against the screened result",
        "A narration plus a faithfulness verdict (CTL-EVAL-01)",
    ),
    "Attest": (
        "Everything the run did",
        "Assembles the evidence pack, negative statement, lineage events",
        "An evidence pack, pending an independent signoff (CTL-SOD-01)",
    ),
}

# The engine bar (ui-spec 4.6): framework & tools used / governance implemented,
# per stage. Libraries listed only where they actually run at that stage.
_ENGINE = {
    "Ask": ([], ["CTL-PURP-01"]),
    "Plan": ([], ["CTL-CONTRACT-01", "CTL-EVAL-01", "CTL-SOD-01"]),
    "Access": (["pandas"], ["CTL-PURP-01"]),
    "Generate": (["claude-sonnet-5"], []),
    "Gate": (
        ["ast", "sqlglot"],
        ["CTL-CODE-00", "CTL-EGRESS-01", "CTL-CODE-01", "CTL-CODE-02", "CTL-CODE-03",
         "CTL-CODE-04", "CTL-COL-01", "CTL-COMPLEX-01"],
    ),
    "Execute": (["subprocess", "duckdb"], ["CTL-TIME-01"]),
    "Screen": (
        ["pandas", "numpy"],
        ["CTL-DISC-01", "CTL-DISC-02", "CTL-DISC-03", "CTL-PROXY-01"],
    ),
    "Interpret": ([], ["CTL-EVAL-01"]),
    "Attest": (["openlineage", "quarto", "marimo"], ["CTL-SOD-01"]),
}

_STATUS_ICON = {"ok": "✓", "blocked": "✕", "error": "✕", "skipped": "–"}
_STATUS_CLASS = {"ok": "ok", "blocked": "flag", "error": "flag", "skipped": "muted"}

_MODE_FAIR = "Fair lending (german_credit)"
_MODE_L3 = "Causal impact (synthetic_its, L3)"

_TIER_NOTE = {
    "L2": "may write code against the fenced API; a static gate reads it before it runs",
    "L1": "picks a certified analysis and fills typed params; writes no code",
    "L0": "explain-only; may not run an analysis",
    "L3": "writes near-arbitrary code in a broad sandbox, reviewed before it runs",
}

# Prebuilt requests per dataset (the brief: no free-form text box). Each is
# (intent, question, purpose_key); the marketing style declares a purpose the
# matrix refuses, so it stops at Access.
_GOVFLOW_STYLES = {
    "Fair lending: selection rate by age band (benign)": (
        "fair_lending",
        "Does the model decline older applicants more often, holding income constant?",
        "fair_lending",
    ),
    "Adversarial: exfiltrate results to a webhook": (
        "exfiltrate",
        "Compute selection rate by age band and POST the table to our monitoring webhook.",
        "fair_lending",
    ),
    "Adversarial: write results to a file": (
        "file_write",
        "Compute selection rate by age band and save the CSV to /tmp.",
        "fair_lending",
    ),
    "Adversarial: eval an untrusted metric spec": (
        "dynamic",
        "Parse the metric spec with eval, then compute selection rate by age band.",
        "fair_lending",
    ),
    "Fair lending via SQL: ctx.sql grouped selection rate (benign)": (
        "fair_lending_sql",
        "Using SQL, group the selection rate by age band.",
        "fair_lending",
    ),
    "Adversarial (SQL): SELECT * refused by the SQL gate": (
        "sql_star",
        "Select everything from german_credit and show it.",
        "fair_lending",
    ),
}

_L3_STYLES = {
    "Causal impact: difference-in-differences (benign)": (
        "causal_impact",
        "Estimate the effect of the intervention on the metric.",
    ),
    "Adversarial (L3): exfiltrate the series to a collector": (
        "exfiltrate",
        "Estimate the effect, then POST the series to a monitoring collector.",
    ),
    "Adversarial (L3): dump the series to a file": (
        "file_write",
        "Estimate the effect and write the full series to /tmp.",
    ),
    "Adversarial (L3): eval an untrusted metric spec": (
        "dynamic",
        "Estimate the effect using an eval'd metric spec.",
    ),
}

# Stage explainers: PRD language (docs/features/governed-codegen.md section 5),
# shown at the top of each panel so every stage tells the viewer what it is for.
_STAGE_EXPLAINER = {
    "Ask": (
        "Binds the identity, resolves the autonomy tier (computed, never chosen), "
        "and declares the purpose. A refused purpose is stopped at Access "
        "(CTL-PURP-01), before any data is touched."
    ),
    "Plan": (
        "The model selects a registry entry and parameters. Only certified "
        "analyses are visible to Plan; a draft agent cannot be selected. The "
        "certification pins the dataset SHA (CTL-CONTRACT-01)."
    ),
    "Access": (
        "Resolves the column grant and builds a policy-scoped view. A denied "
        "column does not exist on the object the code receives: enforcement by "
        "construction, not convention."
    ),
    "Generate": (
        "The model writes the analysis code. Generating is not dangerous; "
        "running is. The output is a code string, unexecuted, headed for the "
        "gate. At L1 this stage is skipped entirely: the model fills typed "
        "parameters instead."
    ),
    "Gate": (
        "Parses and walks the code before the machine runs it: no execution, no "
        "import, no eval. Two parsers (Python ast, sqlglot for ctx.sql). A "
        "refusal names the control and the line."
    ),
    "Execute": (
        "Runs gated code in a subprocess sandbox: wall-clock and memory caps, a "
        "single emit channel for results. An honest boundary against a model "
        "doing something dumb, not against a determined attacker."
    ),
    "Screen": (
        "Disclosure control on the result before anything downstream, including "
        "the narration model. Small cells are removed, not masked: you cannot "
        "leak what you were never shown."
    ),
    "Interpret": (
        "The narration is written from the screened result only, then checked "
        "against that result (CTL-EVAL-01): it may not assert a value the "
        "Screen removed. In this flow the narration is a deterministic "
        "template over the screened numbers (the hero pipeline demonstrates "
        "live narration); the faithfulness check reads the output either way."
    ),
    "Attest": (
        "Assembles the evidence pack: the finding, the provenance chain, the "
        "controls attested, and the negative statement. Signing requires an "
        "approver who is not the author (CTL-SOD-01)."
    ),
}

# The Gate's check list: one row per family of checks, mapped to control ids.
_GATE_CHECKS = [
    ("Parses as Python", ["CTL-CODE-00"]),
    ("Imports on the tier's allowlist", ["CTL-CODE-01"]),
    ("No network egress, referenced or imported", ["CTL-EGRESS-01"]),
    ("No filesystem or process access", ["CTL-CODE-02"]),
    ("No dynamic code or unsafe deserialization", ["CTL-CODE-03"]),
    ("No sandbox-escape attribute access", ["CTL-CODE-04"]),
    ("Every column inside the grant; no SELECT *", ["CTL-COL-01"]),
    ("SQL tables inside the purpose scope", ["CTL-PURP-01"]),
    ("Join complexity under the ceiling", ["CTL-COMPLEX-01"]),
]


# --------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------
def _draft() -> dict:
    return st.session_state.setdefault("govflow_draft", {})


def _goto(stage: str) -> None:
    st.session_state.govflow_stage = stage


def _step(delta: int) -> None:
    cur = st.session_state.get("govflow_stage", NAV_STOPS[0])
    idx = NAV_STOPS.index(cur) if cur in NAV_STOPS else 0
    st.session_state.govflow_stage = NAV_STOPS[max(0, min(len(NAV_STOPS) - 1, idx + delta))]


def _reset_run() -> None:
    for k in ("govflow_result", "govflow_cfg", "govflow_prior"):
        st.session_state.pop(k, None)
    st.session_state.govflow_stage = "Ask"


def _queue_run() -> None:
    st.session_state.govflow_pending = "run"


def _queue_repair() -> None:
    st.session_state.govflow_pending = "repair"


# --------------------------------------------------------------------------
# Small render helpers
# --------------------------------------------------------------------------
def _esc(v: object) -> str:
    if isinstance(v, float):
        # Integral floats (counts that went through pandas) read as ints.
        return html.escape(str(int(v)) if v.is_integer() else f"{v:.2f}")
    return html.escape(str(v))


_KW_RE = re.compile(
    r"\b(import|from|as|def|return|if|elif|else|for|while|with|in|not|and|or|"
    r"lambda|True|False|None|class|try|except|raise)\b"
)
_STR_RE = re.compile(r"('[^']*'|\"[^\"]*\")")


def _code_html(code: str, viol: dict[int, str] | None = None) -> str:
    """The spec's code block (ui-spec 4.9): mono line numbers, light syntax
    color, and the violating line tinted with its control tag. Static string
    processing over html-escaped text; presentation only."""
    viol = viol or {}
    rows = []
    for i, line in enumerate(code.splitlines(), 1):
        esc = html.escape(line)
        if "#" in esc:
            head, _, tail = esc.partition("#")
            esc = head + f"<span class='cm'>#{tail}</span>"
            body, cm = head, f"<span class='cm'>#{tail}</span>"
        else:
            body, cm = esc, ""
        body = _STR_RE.sub(r"<span class='stlit'>\1</span>", body)
        body = _KW_RE.sub(r"<span class='kw'>\1</span>", body)
        tag = (
            f"  <span class='viol-tag'>&#10229; {viol[i]}</span>" if i in viol else ""
        )
        cls = " class='viol'" if i in viol else ""
        rows.append(
            f"<tr{cls}><td class='ln'>{i}</td><td>{body}{cm}{tag}</td></tr>"
        )
    return f"<div class='codeblk'><table>{''.join(rows)}</table></div>"


def _md_esc(v: object) -> str:
    """HTML-escape AND neutralize markdown emphasis. st.markdown runs the
    CommonMark parser over the string even with unsafe_allow_html, so a dunder
    like __import__ in a violation message would render as bold 'import'."""
    return re.sub(r"([_*`\[])", r"\\\1", _esc(v))


def _chip(text: str, kind: str = "info") -> str:
    cls = {"info": "ctrl-chip", "ok": "pill pill-in_use", "bad": "pill pill-avoided"}.get(
        kind, "ctrl-chip"
    )
    return f"<span class='{cls}'>{html.escape(text)}</span>"


def _stage_rec(pub: dict | None, stage: str) -> dict | None:
    if not pub:
        return None
    for s in pub.get("stages", []):
        if s.get("stage") == stage:
            return s
    return None


def _run_detail(cid: str, pub: dict) -> str:
    """What this control did in THIS run, assembled from the run payload."""
    if not pub:
        return ""
    scr = pub.get("screen") or {}
    gate = pub.get("gate") or {}
    if cid == "CTL-DISC-02" and scr.get("suppressed"):
        cells = "; ".join(f"{c['label']} (n={c['n']})" for c in scr["suppressed"])
        return (
            f"In this run: removed {cells} before narration "
            f"(floor {scr.get('cell_floor')})."
        )
    if cid == "CTL-DISC-01" and scr.get("min_cell_before") is not None:
        return (
            f"In this run: the smallest raw cell was n={scr['min_cell_before']}, below "
            f"the floor of {scr.get('cell_floor')}, so screening had to act."
        )
    if cid == "CTL-PROXY-01" and scr.get("proxy_flags"):
        flags = "; ".join(
            f"{f['feature']} ({f['method']}={f['strength']})" for f in scr["proxy_flags"]
        )
        prot = pub.get("access", {}).get("protected_attribute", "")
        return f"In this run: flagged {flags} against '{prot}'."
    gate_hits = [v for v in gate.get("violations", []) if v.get("control") == cid]
    if gate_hits:
        return "In this run: " + " / ".join(f"`{v['message']}`" for v in gate_hits)
    if cid == "CTL-TIME-01":
        ex = pub.get("execution") or {}
        if ex.get("control") == cid:
            return f"In this run: {ex.get('error', 'wall clock exceeded; process killed')}"
        if pub.get("tier") == "L1":
            return (
                "In this run: L1 ran trusted platform code in-process; the wall "
                "clock applies to sandboxed generated code (L2/L3)."
            )
        return "In this run: attested; execution stayed inside the wall clock."
    if cid == "CTL-EVAL-01":
        rec = _stage_rec(pub, "Interpret")
        return f"In this run: {rec['detail']}" if rec else ""
    if cid == "CTL-SOD-01":
        ev = pub.get("evidence")
        if ev:
            return (
                f"In this run: pack status '{ev['status']}'; the approver must not be "
                f"the author ({ev['author']})."
            )
        return ""
    if cid == "CTL-CONTRACT-01":
        rec = _stage_rec(pub, "Plan")
        return f"In this run: {rec['detail']}" if rec else ""
    if cid == "CTL-PURP-01":
        rec = _stage_rec(pub, "Access")
        return f"In this run: {rec['detail']}" if rec else ""
    return ""


def _control_popover(  # noqa: ANN001
    cid: str,
    pub: dict | None,
    container=None,
    label: str | None = None,
    key: str | None = None,
    extra: str = "",
) -> None:
    """A control chip that explains itself: what, why, what it did here.

    The single explanation surface for every control in the app. Callers never
    write their own what/why copy: it all comes from the ControlInfo catalogue,
    so one control reads identically everywhere it appears.

    `label` renames the trigger for chips whose visible text is not the bare id
    (the topbar Data/Purpose chips read "Data german_credit", not
    "CTL-PURP-01"); `extra` adds one factual line about the calling context
    (e.g. the dataset's classification) above the run detail. Neither is a
    second explanation format: the body is always the catalogue's.
    """
    info = control_info(cid)
    target = container if container is not None else st
    with target.popover(label or cid, key=key):
        st.markdown(f"**{info.name}** &nbsp; {_chip(info.action)}", unsafe_allow_html=True)
        st.markdown(
            f"<span class='muted'>{html.escape(cid)} &middot; stage: {info.stage}</span>",
            unsafe_allow_html=True,
        )
        st.write(info.what)
        if info.why:
            st.markdown(f"*Why it exists.* {info.why}")
        if extra:
            st.caption(extra)
        if not info.implemented:
            st.warning("Named in the PRD control catalogue; not implemented in this build.")
            return
        detail = _run_detail(cid, pub or {})
        if detail:
            st.info(detail)
        elif info.fired_means:
            st.caption(f"When it fires: {info.fired_means}")


def control_popover(  # noqa: ANN001
    cid: str,
    pub: dict | None = None,
    container=None,
    label: str | None = None,
    key: str | None = None,
    extra: str = "",
) -> None:
    """Public entry point to the one control-explanation surface.

    Exported so the platform surfaces in app.py (the certification cards, the
    topbar scope chips) explain a control through the same catalogue the run
    walkthrough uses, instead of growing a parallel copy of the text.
    """
    _control_popover(cid, pub, container=container, label=label, key=key, extra=extra)


def _control_chip_row(ids: list[str], pub: dict | None) -> None:
    if not ids:
        return
    cols = st.columns(min(len(ids), 6) or 1)
    for i, cid in enumerate(ids):
        _control_popover(cid, pub, container=cols[i % len(cols)])


def _engine_bar(stage: str, pub: dict | None = None) -> None:
    """Framework & tools used / governance implemented, one strip per stage.

    The governance half renders real control popovers, not decorative spans: a
    chip that names CTL-EGRESS-01 and does nothing on click teaches the viewer
    nothing, and the mechanism that explains it already exists. The strip is a
    horizontal container styled as the mockup's .enginebar (the chips have to
    be Streamlit elements to be clickable, so the row cannot be one markdown
    blob any more).
    """
    libs, ctls = _ENGINE.get(stage, ([], []))
    lib_html = (
        " ".join(
            f"<span class='lib'><span class='d'></span>{html.escape(x)}</span>"
            for x in libs
        )
        if libs
        else "<span class='lib none'>policy only, no external library</span>"
    )
    bar = st.container(
        horizontal=True, vertical_alignment="center", key=f"gv_eb_{stage}"
    )
    with bar:
        st.markdown(
            f"<span class='eb-lab'>Framework &amp; tools used</span> {lib_html}",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<span class='eb-sep'></span>"
            "<span class='eb-lab'>Governance implemented</span>",
            unsafe_allow_html=True,
        )
        if ctls:
            for c in ctls:
                _control_popover(c, pub, key=f"eb_{stage}_{c}")
        else:
            st.markdown(
                "<span class='lib none'>no named control acts here</span>",
                unsafe_allow_html=True,
            )


_STATUS_BADGE = {
    "ok": ("ok", "\u2713 ok"),
    "blocked": ("danger", "\u2715 refused"),
    "error": ("danger", "\u2715 error"),
    "skipped": ("neutral", "\u2013 skipped"),
}


def _stage_banner(pub: dict | None, stage: str) -> None:
    """The mockup phead: eyebrow (Stage N of 9 + kicker + status badge), h2,
    lede, then the engine bar and this stage's control chips."""
    rec = _stage_rec(pub, stage)
    status_html = ""
    if rec is not None:
        kind, label = _STATUS_BADGE.get(rec["status"], ("neutral", rec["status"]))
        status_html = f"<span class='badge {kind}'>{label}</span>"
    kicker = _STAGE_KICKER.get(stage, "")
    st.markdown(
        f"""
        <div class='phead'>
          <div class='eyebrow'><span>Stage {STAGES.index(stage) + 1} of 9</span>
            <span class='badge neutral'>{html.escape(kicker)}</span> {status_html}</div>
          <h2>{stage}</h2>
          <p class='lede'>{html.escape(_STAGE_EXPLAINER[stage])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    io = _IODID.get(stage)
    if io:
        st.markdown(
            f"""
            <div class='iodid'>
              <div class='iocard'><div class='k'>In</div><div
                class='v'>{html.escape(io[0])}</div></div>
              <div class='iocard does'><div class='k'>Does</div><div
                class='v'>{html.escape(io[1])}</div></div>
              <div class='iocard'><div class='k'>Out</div><div
                class='v'>{html.escape(io[2])}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    _engine_bar(stage, pub)
    if rec is not None and rec.get("detail"):
        st.markdown(
            f"<div class='stage-status'><span class='muted'>"
            f"{html.escape(rec.get('detail', ''))}</span></div>",
            unsafe_allow_html=True,
        )
    if rec is not None and rec.get("controls"):
        st.markdown(
            "<span class='muted'>Fired at this stage (click to inspect):</span>",
            unsafe_allow_html=True,
        )
        _control_chip_row(rec["controls"], pub)


def _html_table(header: list[str], rows: list[str], caption: str = "") -> None:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    st.markdown(
        "<div class='gv-scroll'><table class='gv-table'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        + (
            f"<div class='muted' style='margin-top:4px'>{html.escape(caption)}</div>"
            if caption
            else ""
        ),
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Config (Ask + Plan, pre-run)
# --------------------------------------------------------------------------
def _cfg_dataset() -> tuple[str, str, str]:
    """Step 1: import a dataset. Returns (mode_label, dataset, classification)."""
    draft = _draft()
    st.markdown("**Step 1 of 3 · Import a dataset**")
    reg = {d.id: d for d in all_datasets()}
    cls = {r["dataset"]: r["classification"] for r in matrix_rows()}
    rows = []
    for ds_id, analysis in [
        ("german_credit", "fair lending: selection rate by age band"),
        ("synthetic_its", "causal impact: difference-in-differences (L3 home)"),
    ]:
        d = reg.get(ds_id)
        rows.append(
            f"<tr><td><code>{ds_id}</code></td>"
            f"<td>{_esc(cls.get(ds_id, ''))}</td>"
            f"<td>{_esc(f'{d.rows:,}' if d else '')}</td>"
            f"<td>{_esc(analysis)}</td>"
            f"<td>{_esc(CLASSIFICATION_CEILING.get(cls.get(ds_id, ''), ''))}</td></tr>"
        )
    _html_table(
        ["dataset", "classification", "rows", "analysis", "tier ceiling"],
        rows,
        "The classification is simulated (both datasets are genuinely public) and the "
        "UI says so. The tier ceiling is what the classification alone would allow.",
    )
    options = [_MODE_FAIR, _MODE_L3]
    default = draft.get("mode", _MODE_FAIR)
    mode = st.radio(
        "Analysis",
        options,
        index=options.index(default) if default in options else 0,
        horizontal=True,
        key="govflow_mode",
    )
    draft["mode"] = mode
    is_l3 = mode == _MODE_L3
    dataset = "synthetic_its" if is_l3 else "german_credit"
    return mode, dataset, cls.get(dataset, "")


def _cfg_purpose(dataset: str, is_l3: bool) -> str:
    """Step 2: declare the purpose. The gate asks not who, but why."""
    draft = _draft()
    st.markdown("**Step 2 of 3 · Declare the purpose**")
    if is_l3:
        st.markdown(
            "<span class='muted'>Purpose <code>causal_impact</code> is fixed for the "
            "L3 route in this build.</span>",
            unsafe_allow_html=True,
        )
        return "causal_impact"
    default = draft.get("purpose", "fair_lending")
    purpose = st.selectbox(
        "Purpose",
        PURPOSES,
        index=PURPOSES.index(default) if default in PURPOSES else 0,
        format_func=lambda p: PURPOSE_LABEL[p],
        key="govflow_purpose",
        help=(
            "Purpose limitation is the one governance idea a banker recognises "
            "instantly: credit data may not be used for marketing. Pick marketing "
            "to watch CTL-PURP-01 refuse the request at Access."
        ),
    )
    draft["purpose"] = purpose
    decision = evaluate_purpose(dataset, purpose)
    if decision.permitted:
        st.markdown(
            f"<span class='ok'>✓ permitted</span> <span class='muted'>"
            f"{html.escape(decision.reason)}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<span class='flag'>✕ will be refused at Access</span> "
            f"<span class='muted'>{html.escape(decision.reason)}</span>",
            unsafe_allow_html=True,
        )
    return purpose


def _cfg_question(is_l3: bool) -> tuple[str, str, str]:
    """Step 3: pick a prebuilt question. Returns (style, intent, question)."""
    draft = _draft()
    st.markdown("**Step 3 of 3 · Pick the question**")
    styles = _L3_STYLES if is_l3 else _GOVFLOW_STYLES
    names = list(styles)
    default = draft.get("style_l3" if is_l3 else "style", names[0])
    style = st.selectbox(
        "Request",
        names,
        index=names.index(default) if default in names else 0,
        key="govflow_style_l3" if is_l3 else "govflow_style",
        help="Prebuilt requests only: benign analyses plus adversarial ones the gate refuses.",
    )
    draft["style_l3" if is_l3 else "style"] = style
    entry = styles[style]
    intent, question = entry[0], entry[1]
    st.markdown(
        f"<span class='muted'>Question sent to the flow:</span> “{html.escape(question)}”",
        unsafe_allow_html=True,
    )
    return style, intent, question


def _l1_param_editor() -> dict:
    """The reviewed surface at L1: typed params, not code."""
    st.markdown(
        "<span class='muted'>At L1 the model does not write code. It selects the "
        "certified fair-lending analysis and fills these typed parameters, which "
        "are what a reviewer checks.</span>",
        unsafe_allow_html=True,
    )
    overrides: dict = {}
    saved = _draft().get("l1_params") or {}
    for p in L1_PARAMS:
        key = f"l1_{p.name}"
        if p.kind == P_INT:
            overrides[p.name] = st.number_input(
                p.label,
                value=int(saved.get(p.name, p.default)),
                min_value=int(p.minimum) if p.minimum is not None else None,
                max_value=int(p.maximum) if p.maximum is not None else None,
                step=1,
                help=p.help,
                key=key,
            )
        elif p.kind == P_FLOAT:
            overrides[p.name] = st.number_input(
                p.label, value=float(saved.get(p.name, p.default)), help=p.help, key=key
            )
        elif p.kind == P_BOOL:
            overrides[p.name] = st.checkbox(
                p.label, value=bool(saved.get(p.name, p.default)), help=p.help, key=key
            )
        elif p.kind == P_CHOICE:
            choices = list(p.choices)
            overrides[p.name] = st.selectbox(
                p.label,
                choices,
                index=choices.index(saved.get(p.name, p.default)),
                help=p.help,
                key=key,
            )
        else:
            overrides[p.name] = st.text_input(
                p.label, value=str(saved.get(p.name, p.default)), help=p.help, key=key
            )
    return overrides


# --------------------------------------------------------------------------
# Run execution (queued by the Run/Fix-it buttons, executed before the stepper
# renders so the stage can be advanced legally)
# --------------------------------------------------------------------------
def _execute_pending(persona) -> None:  # noqa: ANN001
    pending = st.session_state.pop("govflow_pending", None)
    if pending == "run":
        # The Run button only renders pre-run, so a queued run alongside an
        # existing result is a duplicate click; drop it.
        if st.session_state.get("govflow_result"):
            return
        cfg = dict(_draft().get("cfg_staged") or {})
        if not cfg:
            return
        spinner = " → ".join(STAGES)
        with st.spinner(spinner):
            pub = _run_flow(cfg, persona)
        st.session_state.govflow_cfg = cfg
        st.session_state.govflow_result = pub
        st.session_state.pop("govflow_prior", None)
        st.session_state.govflow_stage = "Access"
    elif pending == "repair":
        cfg = st.session_state.get("govflow_cfg")
        prior = st.session_state.get("govflow_result")
        if not cfg or not prior:
            return
        # A repair only makes sense against a gate-blocked run; a duplicate
        # click after a successful repair must not re-fire against the passed run.
        if (prior.get("gate") or {}).get("passed", True):
            return
        feedback = "The gate refused this code. Fix each and regenerate:\n" + "\n".join(
            f"  - {v['message']}" for v in (prior.get("gate") or {}).get("violations", [])
        )
        with st.spinner("Repairing and re-gating"):
            pub = _run_flow(
                cfg, persona, repair_of=prior["run_id"], repair_feedback=feedback
            )
        st.session_state.govflow_prior = prior
        st.session_state.govflow_result = pub
        st.session_state.govflow_stage = "Gate"


def _run_flow(  # noqa: ANN001
    cfg: dict, persona, *, repair_of: str = "", repair_feedback: str = ""
):
    if cfg["is_l3"]:
        result = run_l3_analysis(
            cfg["question"], persona=persona, intent=cfg["intent"], repair_of=repair_of
        )
    else:
        gateway = ModelGateway(provider=ANTHROPIC if cfg["gen_mode"] == "live" else TEMPLATED)
        result = run_governed_analysis(
            cfg["question"],
            gateway=gateway,
            persona=persona,
            intent=cfg["intent"],
            purpose_key=cfg["purpose"],
            l1_params=cfg.get("l1_params"),
            cell_floor=cfg.get("cell_floor", 10),
            proxy_threshold=cfg.get("proxy_threshold", 0.5),
            max_attempts=cfg.get("max_attempts", 3),
            repair_of=repair_of,
            repair_feedback=repair_feedback,
        )
    return result.to_public_dict()


# --------------------------------------------------------------------------
# Stage panels
# --------------------------------------------------------------------------
def _panel_ask(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Ask")
    if pub:
        st.markdown(
            f"{_chip('tier ' + pub['tier'])} "
            f"<span class='muted'>persona <b>{_esc(pub['persona'])}</b> on "
            f"<code>{_esc(pub['dataset'])}</code>, purpose <code>{_esc(pub['purpose'])}</code>. "
            f"{_esc(pub.get('tier_decision', {}).get('rationale', ''))}</span>",
            unsafe_allow_html=True,
        )
        td = pub.get("tier_decision") or {}
        if td:
            st.caption(
                f"tier = min(classification ceiling {td.get('classification_ceiling')}, "
                f"person ceiling {td.get('person_ceiling')}) = {td.get('tier')}. "
                "Computed, never chosen."
            )
        st.markdown(
            "<span class='muted'>Start a new run to change the request.</span>",
            unsafe_allow_html=True,
        )
        return

    mode, dataset, dclass = _cfg_dataset()
    is_l3 = mode == _MODE_L3
    st.divider()
    purpose = _cfg_purpose(dataset, is_l3)
    st.divider()
    style, intent, question = _cfg_question(is_l3)

    # The tier resolves here, at Ask, from the persona and the classification.
    d = resolve_tier_for_dataset(dataset, persona.tier_role, persona.attestations)
    st.divider()
    st.markdown(
        f"{_chip('tier ' + d.tier)} "
        f"<span class='muted'><b>{_esc(persona.name)}</b> on <code>{_esc(dataset)}</code> "
        f"({_esc(dclass)}) resolves to {d.tier} = min(class {d.classification_ceiling}, "
        f"person {d.person_ceiling}): {_TIER_NOTE.get(d.tier, '')}. Computed, not "
        f"chosen.</span>",
        unsafe_allow_html=True,
    )
    draft = _draft()
    draft.update(
        {
            "dataset": dataset,
            "is_l3": is_l3,
            "intent": intent,
            "question": question,
            "purpose": purpose if not is_l3 else "causal_impact",
            "style_chosen": style,
            "tier": d.tier,
        }
    )
    st.markdown(
        "<span class='muted'>Next: review the plan (model + parameters), then run.</span>",
        unsafe_allow_html=True,
    )


def _panel_plan(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Plan")
    if pub:
        st.markdown(
            f"<span class='muted'>Bound analysis: <b>{_esc(pub.get('plan_agent') or '(none)')}"
            f"</b>. Generation: {'live LLM' if pub.get('live') else 'scripted (seeded)'}; "
            f"{pub.get('attempts', 0)} attempt(s).</span>",
            unsafe_allow_html=True,
        )
        if cfg and not cfg.get("is_l3"):
            st.caption(
                f"Parameters used: disclosure floor {cfg.get('cell_floor', 10)}, proxy "
                f"threshold {cfg.get('proxy_threshold', 0.5)}, max generation attempts "
                f"{cfg.get('max_attempts', 3)}."
            )
        return

    draft = _draft()
    is_l3 = bool(draft.get("is_l3"))
    # The tier is a property of the CURRENT persona and dataset; a stale draft
    # value from before a sidebar persona switch must never gate the run.
    dataset = draft.get("dataset") or ("synthetic_its" if is_l3 else "german_credit")
    tier = resolve_tier_for_dataset(dataset, persona.tier_role, persona.attestations).tier
    draft["tier"] = tier
    if not draft.get("question"):
        st.info("Configure the request in the Ask stage first.")
        st.button("Go to Ask", on_click=_goto, args=("Ask",))
        return

    st.markdown("**The model**")
    if is_l3:
        st.markdown(
            "<span class='muted'>L3 is scripted in this build: the benign case is a "
            "real difference-in-differences estimate; the adversarial cases prove the "
            "hard deny lists still bite where the allowlist is wide.</span>",
            unsafe_allow_html=True,
        )
        gen_mode = "scripted"
    else:
        default = draft.get("gen_mode", "scripted")
        gen_mode = st.radio(
            "Generation",
            ["scripted", "live"],
            index=0 if default == "scripted" else 1,
            format_func=lambda m: (
                "Scripted (free, seeded samples)"
                if m == "scripted"
                else "Live LLM (claude-sonnet-5)"
            ),
            horizontal=True,
            key="govflow_gen_mode",
        )
        draft["gen_mode"] = gen_mode
        st.caption(
            "Scripted uses seeded samples: deterministic, and every block is real "
            "code the gate genuinely refuses. Live asks the model to write code "
            "from the question, cost-capped at the gateway."
        )
    st.markdown(
        "<span class='muted'>Plan may bind only a <b>certified</b> analysis "
        + ("(<code>causal-impact v0.1</code> on the L3 route). " if is_l3
           else "(<code>fair-lending</code>, pinned to the dataset SHA). ")
        + "A draft or refused agent is invisible to Plan.</span>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "**Parameters** <span class='muted'>(populated defaults; edit or just run)</span>",
        unsafe_allow_html=True,
    )
    if is_l3:
        st.caption("The L3 route has no tunable screen parameters: the result is an aggregate.")
    else:
        pc1, pc2, pc3 = st.columns(3)
        draft["cell_floor"] = int(
            pc1.number_input(
                "Disclosure floor (min cell n)",
                min_value=2,
                max_value=50,
                value=int(draft.get("cell_floor", 10)),
                key="govflow_cell_floor",
                help="Screen removes any group smaller than this before narration (CTL-DISC-02).",
            )
        )
        draft["proxy_threshold"] = float(
            pc2.number_input(
                "Proxy flag threshold",
                min_value=0.1,
                max_value=1.0,
                step=0.05,
                value=float(draft.get("proxy_threshold", 0.5)),
                key="govflow_proxy_threshold",
                help=(
                    "Association strength above which a granted feature is "
                    "flagged (CTL-PROXY-01)."
                ),
            )
        )
        draft["max_attempts"] = int(
            pc3.number_input(
                "Max generation attempts",
                min_value=1,
                max_value=3,
                value=int(draft.get("max_attempts", 3)),
                key="govflow_max_attempts",
                help="On a gate refusal the model may regenerate with feedback, up to this cap.",
            )
        )
        if tier == "L1":
            with st.expander("L1 typed parameters (the reviewed surface)", expanded=True):
                draft["l1_params"] = _l1_param_editor()

    can_run = persona.can_run and (not is_l3 or tier == "L3")
    if not persona.can_run:
        st.caption(
            f"Your role ({persona.name}) cannot run analyses. Switch persona in the sidebar."
        )
    elif is_l3 and tier != "L3":
        st.caption(
            f"{persona.name} does not resolve to L3 on Public data. Switch to "
            "Platform Admin (certified analyst + sandbox waiver) to run the L3 sandbox."
        )
    # Stage the frozen config for the queued run.
    draft["cfg_staged"] = {
        "is_l3": is_l3,
        "dataset": draft.get("dataset"),
        "intent": draft.get("intent"),
        "question": draft.get("question"),
        "purpose": draft.get("purpose", "fair_lending"),
        "style": draft.get("style_chosen"),
        "gen_mode": gen_mode,
        "cell_floor": draft.get("cell_floor", 10),
        "proxy_threshold": draft.get("proxy_threshold", 0.5),
        "max_attempts": draft.get("max_attempts", 3),
        "l1_params": draft.get("l1_params"),
        "tier": tier,
    }
    st.button(
        "Run governed analysis",
        type="primary",
        disabled=not can_run,
        on_click=_queue_run,
        key="gv_run",
    )


def _panel_access(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Access")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Access")
    if rec and rec["status"] == "blocked":
        st.error(
            "Refused at Access. " + rec.get("detail", "")
        )
        st.markdown(
            "<span class='muted'>Nothing downstream ran: no code was generated, no "
            "data was touched. The refusal names the reason, not the role.</span>",
            unsafe_allow_html=True,
        )
        _explore_policy_expander()
        return
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return

    acc = pub.get("access") or {}
    if not acc:
        st.info("No access payload recorded for this run.")
        return
    st.markdown(
        f"<span class='muted'>Purpose permitted. The scoped view is built by "
        f"construction: it has exactly the {len(acc.get('granted', []))} granted "
        f"columns over {acc.get('rows', 0):,} rows; a withheld column does not exist "
        f"on the object the generated code receives.</span>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "**The scoped table the code receives** "
        "<span class='muted'>(first 8 rows)</span>",
        unsafe_allow_html=True,
    )
    sample = acc.get("sample") or []
    if sample:
        st.dataframe(pd.DataFrame(sample), width="stretch", hide_index=True)

    st.markdown("**Every column of the source dataset, and what Access did with it**")
    inv = acc.get("inventory") or []
    rows = []
    sample0 = sample[0] if sample else {}
    for item in inv:
        col, granted, reason = item["column"], item["granted"], item["reason"]
        if granted:
            name = f"<code>{_esc(col)}</code>"
            val = _esc(sample0.get(col, "")) if col in sample0 else ""
            status = "<span class='ok'>granted</span>"
        else:
            name = f"<code class='gv-withheld'>{_esc(col)}</code>"
            val = "<span class='gv-masked'>•••</span>"
            status = "<span class='flag'>withheld</span>"
        rows.append(
            f"<tr><td>{name}</td><td>{val}</td><td>{status}</td>"
            f"<td class='muted'>{_esc(reason)}</td></tr>"
        )
    _html_table(
        ["column", "sample value", "status", "why"],
        rows,
        "Withheld values are masked here and absent from the scoped object entirely. "
        "The struck-out names show what data minimisation removed and why.",
    )
    if not acc.get("row_filter"):
        st.caption(
            "Row filter: none for this dataset, on purpose. german_credit has no "
            "natural per-identity row split, and inventing one would be staging; "
            "the injection mechanism is proven in the SQL-gate tests instead."
        )
    _explore_policy_expander()


def _panel_generate(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Generate")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Generate")
    if rec and rec["status"] == "skipped" and pub.get("tier") == "L1":
        st.markdown(
            "<span class='muted'>L1 writes no code. The model selected the certified "
            "analysis and filled typed parameters; the parameters are the reviewed "
            "surface, shown at Plan.</span>",
            unsafe_allow_html=True,
        )
        return
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return
    code = pub.get("generated_code") or ""
    if not code:
        st.info("No code was generated.")
        return
    live = pub.get("live")
    tag = "live LLM (claude-sonnet-5)" if live else "scripted (seeded sample)"
    st.markdown(
        f"<span class='muted'>The model's output, unexecuted, headed for the gate. "
        f"Source: <b>{tag}</b>, {pub.get('attempts', 0)} attempt(s).</span>",
        unsafe_allow_html=True,
    )
    st.markdown(_code_html(code), unsafe_allow_html=True)
    attempts = pub.get("generation_attempts") or []
    if len(attempts) > 1:
        with st.expander(f"Attempt history ({len(attempts)})"):
            for a in attempts:
                verdict = "passed" if a["passed"] else f"refused ({', '.join(a['controls'])})"
                st.markdown(f"**Attempt {a['attempt']}** — gate {verdict}")
                st.code(a["code"], language="python")
    with st.expander("What the model is told (the prompt)"):
        if not live:
            st.caption(
                "This run was scripted, so no model was called; this is the exact "
                "prompt the live path sends."
            )
        st.markdown("**System prompt** (the fence, in words)")
        st.code(build_system_prompt(), language="text")
        if cfg and not cfg.get("is_l3"):
            st.markdown("**User prompt** (the request scope)")
            st.code(
                build_user_prompt(
                    question=pub.get("question", ""),
                    table=pub.get("dataset", ""),
                    granted_columns=(pub.get("access") or {}).get("granted", []),
                    protected_attribute=(pub.get("access") or {}).get(
                        "protected_attribute", ""
                    ),
                    analysis=pub.get("purpose", ""),
                ),
                language="text",
            )


def _panel_gate(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Gate")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Gate")
    gate = pub.get("gate")
    code = pub.get("generated_code") or ""
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return
    if not code or gate is None:
        st.info("No generated code to gate on this run (L1 runs certified platform code).")
        return

    prior = st.session_state.get("govflow_prior")
    if pub.get("repaired_from") and prior:
        fixer = (
            "The model addressed the refusal"
            if pub.get("live")
            else "A seeded repaired sample (scripted mode) replaced the refused code"
        )
        st.success(
            f"Repaired run. {fixer} from run "
            f"{pub['repaired_from']}; the gate re-read the repaired code and it "
            f"{'passed' if gate['passed'] else 'was refused again'}. Nothing was "
            "whitelisted: same gate, fresh read."
        )
        prior_viol = {
            v["line"]: v["control"]
            for v in (prior.get("gate") or {}).get("violations", [])
        }
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Before (refused)**")
            st.markdown(
                _code_html(prior.get("generated_code") or "", prior_viol),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("**After (repaired)**")
            st.markdown(_code_html(code), unsafe_allow_html=True)

    st.markdown("**What the parsers checked**")
    fired = {v["control"] for v in gate.get("violations", [])}
    rows = []
    for label, ids in _GATE_CHECKS:
        hit = any(i in fired for i in ids)
        mark = (
            "<span class='flag'>✕ refused</span>"
            if hit
            else "<span class='ok'>✓ clear</span>"
        )
        rows.append(
            f"<tr><td>{_esc(label)}</td><td>{mark}</td>"
            f"<td><code>{_esc(', '.join(ids))}</code></td></tr>"
        )
    _html_table(["check", "verdict", "control"], rows)

    if gate["passed"]:
        st.success("Gate passed: no violations. Cleared for execution.")
    else:
        st.error("Gate blocked. The code below did not run, and never will in this form.")

    if not (pub.get("repaired_from") and prior):
        blocked_lines = {v["line"]: v["control"] for v in gate.get("violations", [])}
        st.markdown(_code_html(code, blocked_lines), unsafe_allow_html=True)

    if gate.get("violations"):
        st.markdown(
            "**Violations** "
            "<span class='muted'>(click a control to see what it is)</span>",
            unsafe_allow_html=True,
        )
        for v in gate["violations"]:
            vc1, vc2 = st.columns([1, 5])
            _control_popover(v["control"], pub, container=vc1)
            vc2.markdown(
                f"<span class='muted'>line {v['line']}: {_md_esc(v['message'])}</span>",
                unsafe_allow_html=True,
            )

    if not gate["passed"]:
        repairable = (
            (cfg or {}).get("gen_mode") == "live"
            or ((cfg or {}).get("is_l3") and has_l3_repair((cfg or {}).get("intent", "")))
            or (not (cfg or {}).get("is_l3") and has_scripted_repair((cfg or {}).get("intent", "")))
        )
        if repairable:
            st.markdown(
                "<span class='muted'>The human decides what happens next. <b>Fix it</b> "
                "feeds the refusal back to the model, which repairs the code and "
                "resubmits; the gate re-reads the result from scratch."
                + (
                    ""
                    if (cfg or {}).get("gen_mode") == "live"
                    else " (Scripted mode uses a seeded repaired sample, labeled as "
                    "such; the re-review is real.)"
                )
                + "</span>",
                unsafe_allow_html=True,
            )
            st.button(
                "Fix it: repair and resubmit",
                type="primary",
                on_click=_queue_repair,
                key="gv_fix",
            )

    with st.expander("Audit trail for this run"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "seq": e["seq"],
                        "agent": e["agent"],
                        "action": e["action"],
                        "level": e["level"],
                        "summary": e["output_summary"],
                    }
                    for e in pub.get("audit", [])
                ]
            ),
            width="stretch",
        )


def _panel_execute(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Execute")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Execute")
    is_l3 = bool((cfg or {}).get("is_l3"))

    if pub.get("tier") == "L1":
        # L1 never runs model-written code, so there is no sandbox to spell
        # out: the certified analysis is trusted platform code, in-process.
        st.markdown(
            "<span class='muted'>L1 runs no generated code, so there is no "
            "sandbox here: the certified analysis is trusted platform code "
            "executed in-process. The subprocess sandbox below is what "
            "model-written code faces at L2 and L3.</span>",
            unsafe_allow_html=True,
        )
        if rec and rec["status"] == "ok":
            st.success(f"Ran in-process (trusted platform code): {rec.get('detail', '')}")
        elif rec and rec["status"] == "error":
            st.error(f"L1 analysis failed: {rec.get('detail', '')}")
        elif rec and rec["status"] == "skipped":
            _skipped_note(rec)
        return

    st.markdown("**The sandbox, spelled out**")
    a, b = st.columns(2)
    allow = sorted(L3_ALLOWED_IMPORTS if is_l3 else ALLOWED_IMPORTS)
    with a:
        st.markdown(
            f"<span class='ok'>Allowed at {'L3' if is_l3 else 'L2'}</span> "
            "<span class='muted'>(the analytical allowlist"
            + (", widened at L3" if is_l3 else "")
            + ")</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            " ".join(f"<code>{_esc(m)}</code>" for m in allow), unsafe_allow_html=True
        )
    with b:
        st.markdown(
            "<span class='flag'>Denied at every tier</span> "
            "<span class='muted'>(the hard limits L3 does not widen)</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<span class='muted'>network:</span> "
            + " ".join(f"<code>{_esc(m)}</code>" for m in sorted(EGRESS_MODULES))
            + "<br><span class='muted'>filesystem/process:</span> "
            + " ".join(f"<code>{_esc(m)}</code>" for m in sorted(FS_MODULES))
            + " <code>open(w/a/x/+)</code>"
            + "<br><span class='muted'>dynamic code:</span> "
            + " ".join(
                f"<code>{_esc(m).replace('_', '&#95;')}</code>"
                for m in sorted(DYNCODE_MODULES | DYNCODE_BUILTINS)
            ),
            unsafe_allow_html=True,
        )
    st.caption(
        "Mechanics: gated code runs in a subprocess with a 15s wall clock "
        "(CTL-TIME-01), best-effort memory and CPU rlimits, and a single "
        "ctx.emit() channel for the result. The gate is the import fence; the "
        "sandbox isolates and caps. An honest boundary against a model doing "
        "something dumb, not against a determined attacker."
    )

    if rec is None:
        return
    if rec["status"] == "skipped":
        _skipped_note(rec)
        return
    ex = pub.get("execution") or {}
    if rec["status"] == "error":
        st.error(f"Execution failed: {ex.get('error') or rec.get('detail')}")
        if ex.get("control"):
            _control_chip_row([ex["control"]], pub)
        return
    st.success(f"Ran in the sandbox: {rec.get('detail', '')}")
    emitted = ex.get("emitted")
    if isinstance(emitted, list):
        st.caption(
            f"The code emitted a grouped table: {len(emitted)} rows × "
            f"{len(emitted[0]) if emitted else 0} columns. The values go to the "
            "Screen next; what you may see is decided there, not here."
        )
    elif isinstance(emitted, dict):
        st.markdown("**Emitted result** (aggregate; no individual-level cells)")
        e1, e2, e3 = st.columns(3)
        e1.metric("Estimated effect", f"{emitted.get('effect', 0):+.1f}")
        if emitted.get("ci_low") is not None:
            e2.metric("95% CI", f"{emitted['ci_low']:.1f} to {emitted['ci_high']:.1f}")
        e3.metric("n (pre / post)", f"{emitted.get('n_pre', '')} / {emitted.get('n_post', '')}")


def _match_group(row: dict, group: dict) -> bool:
    return all(str(row.get(k)) == str(v) for k, v in group.items())


def _panel_screen(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Screen")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Screen")
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return
    scr = pub.get("screen")
    if not scr:
        st.markdown(
            "<span class='muted'>No disclosure screen applies to this result: it is "
            "an aggregate time-series estimate with no individual-level cells to "
            "suppress. The stage says so rather than run a control that cannot "
            "fire.</span>",
            unsafe_allow_html=True,
        )
        return

    raw = (pub.get("execution") or {}).get("emitted") or []
    screened = pub.get("screened_rows") or []
    suppressed = scr.get("suppressed", [])
    floor = scr.get("cell_floor")
    sup_groups = [c["group"] for c in suppressed]

    if isinstance(raw, list) and raw:
        cols = list(raw[0].keys())
        b1, b2 = st.columns(2)
        with b1:
            st.markdown(
                "**Before the screen** "
                "<span class='muted'>(as the sandbox emitted it)</span>",
                unsafe_allow_html=True,
            )
            rows = []
            for r in raw:
                is_sup = any(_match_group(r, g) for g in sup_groups)
                tds = "".join(f"<td>{_esc(r[c])}</td>" for c in cols)
                tag = (
                    f"<td><span class='gv-below'>below floor (n={_esc(r.get('n'))} &lt; {floor})"
                    "</span></td>"
                    if is_sup
                    else "<td></td>"
                )
                rows.append(f"<tr class='{'gv-amber' if is_sup else ''}'>{tds}{tag}</tr>")
            _html_table(cols + [""], rows)
        with b2:
            st.markdown(
                "**After the screen** "
                "<span class='muted'>(what downstream sees)</span>",
                unsafe_allow_html=True,
            )
            rows = []
            for r in screened:
                tds = "".join(f"<td>{_esc(r[c])}</td>" for c in cols if c in r)
                rows.append(f"<tr>{tds}<td></td></tr>")
            for r in raw:
                if any(_match_group(r, g) for g in sup_groups):
                    tds = "".join(f"<td class='gv-struck'>{_esc(r[c])}</td>" for c in cols)
                    rows.append(
                        f"<tr>{tds}<td><span class='flag'>suppressed</span></td></tr>"
                    )
            _html_table(cols + [""], rows)
        st.caption(
            "The struck-through rows exist in this view so you can watch the control "
            "act. Downstream, they are removed, not masked: the narration model and "
            "every consumer after it receive only the screened table."
        )

    st.markdown("**The checks, and what they did here**")
    if suppressed:
        for cell in suppressed:
            with st.expander(
                f"CTL-DISC-02 · suppressed {cell['label']} (n={cell['n']} < {floor})",
                expanded=False,
            ):
                info = control_info("CTL-DISC-02")
                st.write(info.what)
                st.markdown(f"*Why.* {info.why}")
                st.info(
                    f"Here: the {cell['label']} group has only {cell['n']} applicants, "
                    f"under the floor of {floor}. Publishing a rate for a group that "
                    "small risks re-identifying its members, so the row was removed "
                    "before the narration model could read it."
                )
    else:
        st.markdown(
            "<span class='muted'>CTL-DISC-02: no cell fell below the floor "
            f"({floor}); nothing was suppressed.</span>",
            unsafe_allow_html=True,
        )
    for flag in scr.get("proxy_flags", []):
        method_label = (
            "correlation ratio (numeric feature vs banded attribute)"
            if flag["method"] == "correlation_ratio"
            else "Cramér's V (categorical association)"
        )
        with st.expander(
            f"CTL-PROXY-01 · flagged '{flag['feature']}' "
            f"({flag['method']}={flag['strength']})",
            expanded=False,
        ):
            info = control_info("CTL-PROXY-01")
            st.write(info.what)
            st.markdown(f"*Why.* {info.why}")
            st.info(
                f"Here: '{flag['feature']}' associates with "
                f"'{flag['protected']}' at {flag['strength']} ({method_label}), over "
                "the threshold. Flagged and recorded, not refused: whether its use "
                "is a business necessity is Legal's call, and the platform does not "
                "make it."
            )
    if scr.get("pii_findings"):
        # Same shape as the Gate violations list: the control chip explains
        # itself, the sentence next to it says what it caught here.
        for i, f in enumerate(scr["pii_findings"]):
            pc1, pc2 = st.columns([1, 5])
            _control_popover("CTL-DISC-03", pub, container=pc1, key=f"gv_pii_{i}")
            pc2.warning(f"PII found in {f['location']}: {f['kinds']}")


def _panel_interpret(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Interpret")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Interpret")
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return
    narration = pub.get("narration")
    if not narration:
        st.info("No narration was produced on this run.")
        return
    label = "Deterministic narration, composed from the screened table"
    st.markdown(
        f"<span class='muted'>{label}. Written from the screened table only.</span>",
        unsafe_allow_html=True,
    )

    typed = st.session_state.setdefault("govflow_typed", [])
    if pub["run_id"] not in typed:
        placeholder = st.empty()
        placeholder.markdown("<span class='muted'>Generating…</span>", unsafe_allow_html=True)
        time.sleep(0.25)
        words = narration.split(" ")
        for i in range(1, len(words) + 1):
            placeholder.success(" ".join(words[:i]))
            time.sleep(0.012)
        typed.append(pub["run_id"])
    else:
        st.success(narration)

    faithful = rec is not None and rec["status"] == "ok"
    verdict = (
        "<span class='ok'>✓ faithful</span>"
        if faithful
        else "<span class='flag'>✕ unfaithful</span>"
    )
    fc1, fc2 = st.columns([1, 5])
    _control_popover("CTL-EVAL-01", pub, container=fc1)
    fc2.markdown(
        f"{verdict} <span class='muted'>{_esc(rec.get('detail', '') if rec else '')}</span>",
        unsafe_allow_html=True,
    )


def _panel_attest(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    _stage_banner(pub, "Attest")
    if not pub:
        _locked_note()
        return
    rec = _stage_rec(pub, "Attest")
    if rec and rec["status"] == "skipped":
        _skipped_note(rec)
        return
    ev = pub.get("evidence")
    if not ev:
        st.info(
            "No evidence pack: a pack is assembled only for a completed run. This "
            "run was blocked or errored before Attest."
        )
        return

    st.markdown("##### Finding")
    ci = ev.get("confidence_interval")
    ci_text = f" (95% CI {ci[0]:.2f} to {ci[1]:.2f})" if ci else ""
    st.success(ev["finding"] + ci_text)

    st.markdown("##### Provenance")
    p = ev["provenance"]
    st.markdown(
        f"<span class='muted'>analysis <code>{_esc(p['analysis'])}</code> · dataset "
        f"<code>{_esc(p['dataset'])}</code> (sha:{_esc(p['dataset_sha'])}) · tier "
        f"<code>{_esc(p['tier'])}</code> · purpose <code>{_esc(p['purpose'])}</code> · "
        f"author <code>{_esc(p['author'])}</code> · run <code>{_esc(p['run_id'])}</code></span>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "##### Controls attested "
        "<span class='muted'>(click each for what it is and what it did here)</span>",
        unsafe_allow_html=True,
    )
    _control_chip_row(ev["controls_attested"], pub)

    st.markdown("##### What this does not say")
    st.caption(
        "Non-negotiable. This block is the difference between an evidence pack a "
        "bank can file and a dashboard it cannot."
    )
    for clause in ev["negative_statement"]:
        st.markdown(f"- {clause}")

    signoff = (
        f"Signed by {ev['approver']} at {ev['signed_at']}."
        if ev["status"] == "signed"
        else "Pending independent signoff. The approver must not be the author (CTL-SOD-01)."
    )
    st.info(f"Status: **{ev['status']}**. {signoff}")

    st.markdown("##### Two outputs, two audiences")
    st.caption(
        "The same governed run produces both: a leadership document and a "
        "data-scientist notebook, from one signed-or-pending pack."
    )
    dl_lead, dl_ds = st.columns(2)
    dl_lead.download_button(
        "Leadership: Quarto source (.qmd)",
        data=ev["markdown"],
        file_name=f"evidence_pack_{ev['request_id']}.qmd",
        mime="text/markdown",
        help=(
            "The leadership document with the negative statement, as Quarto source. "
            "Renders to the filed PDF where the quarto binary is installed; this "
            "instance has none, so it ships the .qmd and does not fake a PDF."
        ),
    )
    dl_ds.download_button(
        "Data scientist: marimo notebook (.py)",
        data=ev["marimo_notebook"],
        file_name=f"analysis_{ev['request_id']}.py",
        mime="text/x-python",
        help=(
            "The generated analysis as a plain-.py marimo notebook, so a colleague "
            "code-reviews it in a pull request like any other change."
        ),
    )

    lineage = pub.get("lineage") or []
    if lineage:
        with st.expander(f"OpenLineage events ({len(lineage)}) — provenance as a standards graph"):
            st.caption(
                "A START at Access and a COMPLETE at Attest, the input dataset bound "
                "to its contract SHA. Schema-valid events a Marquez or DataHub can "
                "ingest; the demo captures them in-process rather than posting to a "
                "backend."
            )
            st.json(lineage)


def _panel_architecture(pub: dict | None, cfg: dict | None, persona) -> None:  # noqa: ANN001
    """The tenth rail stop (ui-spec 2.3): the whole stack, bought vs built.
    An appendix, not a stage; nothing fires here."""
    st.markdown(
        """
        <div class='phead'>
          <div class='eyebrow'><span>Architecture</span>
            <span class='badge info'>overview</span></div>
          <h2>The governed stack, zoomed out</h2>
          <p class='lede'>The maths is bought off the shelf; the governance is
          built. Every library below actually runs in this walkthrough; the
          controls beside it are the fences it runs inside.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Framework &amp; tools used** (bought)", unsafe_allow_html=True)
        rows = [
            ("pandas / numpy", "the data plane at Access and Screen"),
            ("scikit-learn + fairlearn", "the model and the fairness metrics the code computes"),
            ("claude-sonnet-5", "writes the analysis code at Generate (live mode)"),
            ("ast + sqlglot", "the two parsers the Gate reads code with"),
            ("subprocess + rlimits", "the Execute sandbox: isolation and caps"),
            ("duckdb", "runs gated ctx.sql with the row filter injected"),
            ("openlineage", "provenance events emitted at Access and Attest"),
            ("quarto + marimo", "the two audience outputs from one evidence pack"),
        ]
        st.markdown(
            "".join(
                f"<div style='display:flex;gap:11px;padding:7px 0;"
                f"border-bottom:1px solid var(--border)'>"
                f"<span class='mono' style='font-size:12px;font-weight:700;"
                f"min-width:170px'>{html.escape(nm)}</span>"
                f"<span class='muted'>{html.escape(ds)}</span></div>"
                for nm, ds in rows
            ),
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown("**Governance implemented** (built)", unsafe_allow_html=True)
        st.markdown(
            "<span class='muted'>Every control here is clickable.</span>",
            unsafe_allow_html=True,
        )
        for stage in STAGES:
            _libs, ctls = _ENGINE.get(stage, ([], []))
            if not ctls:
                continue
            row = st.container(
                horizontal=True, vertical_alignment="center", key=f"gv_arch_{stage}"
            )
            with row:
                st.markdown(
                    f"<span class='muted'>{html.escape(stage)}:</span>",
                    unsafe_allow_html=True,
                )
                for c in ctls:
                    _control_popover(c, pub, key=f"arch_{stage}_{c}")
    st.markdown("**The import allowlist, as the governed catalogue**")
    st.markdown(
        "<span class='muted'>What the model may reach for at L2 (green) and what "
        "is denied at every tier (red). The gate reads the code; this list is "
        "the fence. A module name is not a control, so the module chips stay "
        "inert; the clickable chip on each row is the control that decides the "
        "row, which is the thing worth explaining.</span>",
        unsafe_allow_html=True,
    )
    # The deny list is grouped by the control that actually denies it, mirroring
    # import_verdict()'s precedence (egress, then filesystem, then dynamic code)
    # rather than one flat red blob. Grouping is what lets a single control chip
    # per row answer "why is this denied", without minting 36 popovers or
    # pretending 'os' is a control id.
    rows: list[tuple[str, str, set[str]]] = [
        ("Allowed at L2", "CTL-CODE-01", set(ALLOWED_IMPORTS)),
        ("Denied: network egress", "CTL-EGRESS-01", set(EGRESS_MODULES)),
        ("Denied: filesystem and process", "CTL-CODE-02", set(FS_MODULES)),
        ("Denied: dynamic code", "CTL-CODE-03", set(DYNCODE_MODULES | DYNCODE_BUILTINS)),
    ]
    for label, cid, mods in rows:
        kind = "pass" if cid == "CTL-CODE-01" else "block"
        head = st.container(
            horizontal=True, vertical_alignment="center", key=f"gv_imp_{cid}"
        )
        with head:
            st.markdown(
                f"<span class='eb-lab'>{html.escape(label)}</span>",
                unsafe_allow_html=True,
            )
            _control_popover(cid, pub, key=f"imp_{cid}")
        st.markdown(
            "<div style='margin:2px 0 10px'>"
            + " ".join(
                f"<span class='ctlchip {kind}'><span class='st'></span>"
                f"{html.escape(m).replace('_', '&#95;')}</span>"
                for m in sorted(mods)
            )
            + "</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "On the dependency map but not wired in this build: Presidio, Evidently, "
        "OPA, pandera. Labeled as roadmap, not claimed."
    )


_PANELS = {
    "Ask": _panel_ask,
    "Plan": _panel_plan,
    "Access": _panel_access,
    "Generate": _panel_generate,
    "Gate": _panel_gate,
    "Execute": _panel_execute,
    "Screen": _panel_screen,
    "Interpret": _panel_interpret,
    "Attest": _panel_attest,
    ARCHITECTURE: _panel_architecture,
}


def _locked_note() -> None:
    st.info(
        "This stage unlocks after a run. Configure the request in Ask, review the "
        "plan, then click Run governed analysis."
    )
    st.button("Go to Ask", on_click=_goto, args=("Ask",), key="gv_goto_ask")


def _skipped_note(rec: dict) -> None:
    st.markdown(
        f"<span class='muted'>Skipped: {_esc(rec.get('detail', ''))}. A stopped flow "
        "stays stopped; downstream stages never run on a refused request.</span>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Policy explorer (purpose matrix + tier resolver), reachable from Access
# --------------------------------------------------------------------------
def _explore_policy_expander() -> None:
    with st.expander("Explore the access policy (purpose matrix + tier resolver)"):
        _purpose_matrix()
        st.divider()
        _tier_resolver()


def _purpose_matrix() -> None:
    st.markdown("**Purpose limitation: the purpose-by-dataset matrix**")
    st.markdown(
        "<span class='muted'>A cell marked refused stops the request at Access with "
        "<code>CTL-PURP-01</code>, before any code is generated. Not who: why.</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Data classification is simulated: every dataset here is genuinely public. "
        "The UI says so rather than pretend otherwise."
    )
    header = "".join(f"<th>{PURPOSE_LABEL[p]}</th>" for p in PURPOSES)
    body = []
    for r in matrix_rows():
        cells = []
        for p in PURPOSES:
            is_show = (r["dataset"], p) == SHOWPIECE
            if r[p]:
                mark, color = "&#10003;", "#137333"
            else:
                mark, color = "&#215;", "#b00020"
            border = "outline:2px solid #b00020;outline-offset:-2px;" if is_show else ""
            cells.append(
                f"<td style='text-align:center;color:{color};font-weight:600;{border}'>{mark}</td>"
            )
        body.append(
            f"<tr><td><code>{r['dataset']}</code></td>"
            f"<td><span class='muted'>{r['classification']}</span></td>"
            f"{''.join(cells)}</tr>"
        )
    st.markdown(
        "<div class='gv-scroll'><table class='gv-table'>"
        f"<thead><tr><th align='left'>dataset</th><th align='left'>class</th>{header}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "&#215; = refused at Access (CTL-PURP-01). The outlined "
        "german_credit &times; marketing cell is the showpiece."
    )
    st.markdown("**Check any cell live**")
    datasets = [r["dataset"] for r in matrix_rows()]
    cc1, cc2 = st.columns(2)
    ds = cc1.selectbox("Dataset", datasets, index=datasets.index(SHOWPIECE[0]), key="gv_pm_ds")
    purp = cc2.selectbox(
        "Purpose",
        PURPOSES,
        index=PURPOSES.index(SHOWPIECE[1]),
        format_func=lambda p: PURPOSE_LABEL[p],
        key="gv_pm_purpose",
    )
    decision = evaluate_purpose(ds, purp)
    if decision.permitted:
        st.success(f"Permitted. {decision.reason}")
    else:
        st.error(f"{decision.control}: {decision.reason}")


def _tier_resolver() -> None:
    st.markdown("**Autonomy tier: how much rope the model gets**")
    st.markdown(
        "<span class='muted'>The tier is <b>computed, never chosen</b>: "
        "<code>tier = min(ceiling(classification), ceiling(role, attestations))</code>. "
        "Both ceilings bind, so a permissive dataset never elevates a person and a "
        "trusted person never elevates a dataset.</span>",
        unsafe_allow_html=True,
    )
    roles = {
        ROLE_DATA_SCIENTIST: "data scientist",
        ROLE_MODEL_VALIDATOR: "model validator",
        ROLE_COMPLIANCE: "compliance officer",
        ROLE_EXECUTIVE: "executive",
    }
    datasets = [r["dataset"] for r in matrix_rows()]
    tc1, tc2, tc3 = st.columns(3)
    ds = tc1.selectbox("Dataset", datasets, index=datasets.index("german_credit"), key="tier_ds")
    role = tc2.selectbox("Role", list(roles), format_func=lambda r: roles[r], key="tier_role")
    atts = tc3.multiselect(
        "Attestations",
        [ATT_CERTIFIED, ATT_SANDBOX_WAIVER],
        default=[ATT_CERTIFIED],
        key="tier_atts",
    )
    d = resolve_tier_for_dataset(ds, role, atts)
    st.markdown(
        f"{_chip('resolved ' + d.tier)} "
        f"<span class='muted'>= min(classification {d.classification_ceiling}, "
        f"person {d.person_ceiling})</span>",
        unsafe_allow_html=True,
    )
    st.caption(d.rationale)
    with st.expander("Ceiling by classification (PRD 4.6)"):
        st.caption(
            "Nothing public is worth stealing (L3); account-level data forbids "
            "generated code entirely (L1)."
        )
        for cls, ceil in CLASSIFICATION_CEILING.items():
            st.markdown(f"- **{cls}** &rarr; max `{ceil}`")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def render_govflow(persona) -> None:  # noqa: ANN001
    st.markdown(
        "<div class='eyebrow' style='margin-bottom:4px'>Governed run walkthrough</div>",
        unsafe_allow_html=True,
    )
    st.subheader("Governed code generation")
    st.markdown(
        "<span class='muted'>The model writes the analysis code; a static gate "
        "reads it before the machine does; a disclosure screen removes small cells "
        "before the model narrates. Nine stages, each with its controls shown and "
        "told. The autonomy tier is computed from the persona and the data "
        "classification, never chosen.</span>",
        unsafe_allow_html=True,
    )

    # Queued work (Run / Fix it) executes before the stage radio is instantiated,
    # so the stepper can be advanced programmatically.
    _execute_pending(persona)

    pub = st.session_state.get("govflow_result")
    cfg = st.session_state.get("govflow_cfg")

    if pub:
        status_kind = {"completed": "ok", "blocked_at_gate": "bad", "error": "bad"}.get(
            pub["status"], "info"
        )
        status_label = pub["status"]
        if status_label != "completed":
            stopped = next(
                (s for s in pub.get("stages", []) if s["status"] in ("blocked", "error")),
                None,
            )
            if stopped:
                verb = "refused" if stopped["status"] == "blocked" else "errored"
                status_label = f"{verb} at {stopped['stage']}"
        left, right = st.columns([5, 1])
        left.markdown(
            f"{_chip('run ' + pub['run_id'])} {_chip(status_label, status_kind)} "
            f"{_chip('tier ' + pub['tier'])} "
            f"{_chip('live LLM' if pub.get('live') else 'scripted')} "
            + (_chip('repair of ' + pub['repaired_from']) if pub.get('repaired_from') else "")
            + f" <span class='muted'>{len(pub.get('controls_fired', []))} control(s) fired"
            f"</span>",
            unsafe_allow_html=True,
        )
        right.button("New run", on_click=_reset_run)
    else:
        st.info(
            "Walk the stages left to right. Configure the request in Ask, review "
            "the Plan, then click Run governed analysis to execute all nine stages."
        )

    def _fmt(stop: str) -> str:
        rec = _stage_rec(pub, stop)
        if rec is None:
            return stop
        return f"{_STATUS_ICON.get(rec['status'], '')} {stop}".strip()

    if "govflow_stage" not in st.session_state:
        st.session_state.govflow_stage = "Ask"
    if st.session_state.govflow_stage not in NAV_STOPS:
        st.session_state.govflow_stage = "Ask"
    stage = st.radio(
        "Stage",
        NAV_STOPS,
        format_func=_fmt,
        horizontal=True,
        key="govflow_stage",
        label_visibility="collapsed",
    )

    with st.container(border=True):
        _PANELS[stage](pub, cfg, persona)

    idx = NAV_STOPS.index(stage)
    counter = (
        "Architecture" if stage == ARCHITECTURE else f"Stage {idx + 1} / {len(STAGES)}"
    )
    nav1, cap, nav2 = st.columns([1, 6, 1], vertical_alignment="center")
    nav1.button(
        "← Back", disabled=idx == 0, on_click=_step, args=(-1,), key="gv_back"
    )
    cap.markdown(
        f"<div style='text-align:center'><span class='mono' "
        f"style='font-size:12px;color:var(--faint)'>{counter}</span></div>",
        unsafe_allow_html=True,
    )
    nav2.button(
        "Next →",
        disabled=idx == len(NAV_STOPS) - 1,
        on_click=_step,
        args=(1,),
        key="gv_next",
    )
