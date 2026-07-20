"""The Adoption screen: run volume and promotion rate over the seeded history."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import pandas as pd
import streamlit as st

from sentinel.platform import (
    adoption_metrics,
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
