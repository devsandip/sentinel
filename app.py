"""Sentinel — Streamlit UI (six tabs over the governed pipeline).

Run: uv run streamlit run app.py

The analysis underneath is always real. In scripted mode the step narration is
deterministic (labeled honestly); the Live LLM toggle routes narration through
a real model behind a cost cap.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from sentinel.datasets import all_datasets
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
from sentinel.platform.patterns import AVOIDED, IN_USE, PLANNED
from sentinel.platform.templates import AVAILABLE, LIVE
from sentinel.rag import corpus_summary

st.set_page_config(page_title="Sentinel — Governed Agentic Analysis", layout="wide")

ACCENT = "#1e50a0"

st.markdown(
    f"""
    <style>
      .stApp {{ background: #fafbfc; }}
      .sentinel-badge {{
        display:inline-block; background:{ACCENT}; color:white; font-weight:600;
        padding:2px 10px; border-radius:12px; font-size:0.8rem; margin-right:6px;
      }}
      .ctrl-chip {{
        display:inline-block; background:#eef2fb; color:{ACCENT}; font-weight:600;
        padding:2px 9px; border-radius:10px; font-size:0.75rem; margin-right:5px;
        border:1px solid #d5e0f5;
      }}
      .flag {{ color:#b3261e; font-weight:700; }}
      .ok {{ color:#1b7f3b; font-weight:700; }}
      .muted {{ color:#5f6b7a; font-size:0.85rem; }}
      .pill {{
        display:inline-block; padding:1px 9px; border-radius:10px;
        font-size:0.72rem; font-weight:700; margin-left:6px;
      }}
      .pill-in_use {{ background:#e3f4e9; color:#1b7f3b; border:1px solid #bfe3cc; }}
      .pill-planned {{ background:#eef2fb; color:{ACCENT}; border:1px solid #d5e0f5; }}
      .pill-avoided {{ background:#fdeceb; color:#b3261e; border:1px solid #f3ccc9; }}
    </style>
    """,
    unsafe_allow_html=True,
)

if "orch" not in st.session_state:
    st.session_state.orch = Orchestrator()
    st.session_state.run_id = None
orch: Orchestrator = st.session_state.orch


# --------------------------------------------------------------------------
# Header + controls
# --------------------------------------------------------------------------
def header() -> None:
    left, right = st.columns([3, 2])
    with left:
        st.title("Sentinel")
        st.markdown(
            "<span class='muted'>Governed agentic data science for a regulated "
            "bank. Pick a question, run a real analysis, watch the controls "
            "fire.</span>",
            unsafe_allow_html=True,
        )
    with right:
        chips = "".join(
            f"<span class='ctrl-chip'>{c}</span>"
            for c in ["PII", "RBAC", "Audit", "Human Gate", "Eval Gate"]
        )
        st.markdown(
            f"<div style='text-align:right;margin-top:18px'>"
            f"<span class='sentinel-badge'>Governance: ON</span><br>"
            f"<div style='margin-top:8px'>{chips}</div></div>",
            unsafe_allow_html=True,
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
            f"Your role ({persona.name}) is read-only and cannot run analyses. "
            "Switch to an Analyst or MRM Approver to run."
        )

    settings = _control_toggles(persona)

    if run_clicked:
        state = orch.start_run(
            qid, narration_mode=mode, controls=settings, actor=persona
        )
        st.session_state.run_id = state.run_id


def _control_toggles(persona) -> ControlSettings:
    """Admin-only panel to disable a control for the next run (demo device)."""
    if not persona.can_toggle_controls:
        return ControlSettings()
    with st.expander("Controls (Admin) — disable a control to prove it is real"):
        st.caption(
            "Turn a control off and re-run to watch the failure it prevents. "
            "Disabling a control is itself audited, and the run is marked "
            "UNGOVERNED. Demo only."
        )
        disabled = []
        for cid, name, desc, breaks in CONTROL_CATALOG:
            off = st.checkbox(
                f"Disable {name}",
                key=f"ctrl_off_{cid}",
                help=f"{desc} If off: {breaks}",
            )
            if off:
                disabled.append(cid)
                st.markdown(
                    f"<span class='muted'>&nbsp;&nbsp;→ {breaks}</span>",
                    unsafe_allow_html=True,
                )
        return from_disabled(disabled)


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
                "onboarded": "yes" if d.onboarded else "registered",
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch")
    st.caption(
        "'registered' datasets carry metadata + contract but are not downloaded "
        "yet; the onboard script flips them to 'onboarded'. 'flagged' commercial "
        "status means the license restricts commercial use and the platform blocks it."
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
    b.metric("Promotion rate", f"{int(m['promotion_rate'] * 100)}%")
    c.metric("Human-override rate", f"{int(m['override_rate'] * 100)}%")
    d.metric("Template coverage", f"{int(m['template_coverage'] * 100)}%")

    st.markdown("**Agent utilization** (invocations across all runs)")
    st.bar_chart(
        pd.DataFrame(
            {"invocations": m["per_agent_invocations"]}
        )
    )

    st.markdown("**Runs per week** (seeded demo history)")
    wk = pd.DataFrame(m["weekly"], columns=["week", "runs"]).set_index("week")
    st.bar_chart(wk)
    st.caption(
        "Seeded weekly history is labeled demo telemetry; the totals above include "
        "live runs completed this session. Enterprise: this view reads the "
        "platform's real run store."
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


header()
st.divider()

section = st.sidebar.radio(
    "Section",
    ["Run analysis", "Platform", "Datasets", "Registry", "Adoption"],
    index=0,
)
st.sidebar.divider()
persona = persona_picker()

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
