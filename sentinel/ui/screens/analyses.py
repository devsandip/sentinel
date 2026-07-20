"""The Analyses screen: the linear analysis engine's specs and their runs.

Read-only analyses with declared parameters. The credit-risk pipeline is not
here; it promotes a model and holds a human gate, so it stays in the
orchestrator."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
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


def _engine() -> AnalysisEngine:
    """One engine per browser session.

    It was a module-level singleton in `app.py`, which worked only because that
    file re-executes top to bottom on every rerun. A screen module is imported
    once, so the session-state read has to happen at call time."""
    if "analysis_engine" not in st.session_state:
        st.session_state.analysis_engine = AnalysisEngine()
        st.session_state.analysis_run = None
    return st.session_state.analysis_engine


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
            run = _engine().run(spec, dataset_id, overrides, actor=persona)
            st.session_state.analysis_run = run
        except ParamError as exc:
            st.error(f"Parameter error: {exc}")
            st.session_state.analysis_run = None

    run = st.session_state.get("analysis_run")
    if run is not None and run.analysis_id == spec.id:
        st.divider()
        _render_analysis_run(run.to_public_dict())
