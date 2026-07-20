"""The Registry screen: three inventories under one heading.

Models are what a run produces, agents are workers inside a run, and
analysis-agents are what a run is allowed to be. The screen says so, because
the person who commissioned this build could not tell them apart when one
subtitle covered all three."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import streamlit as st

from sentinel.harness.model_card import ModelCard, render_markdown, render_pdf
from sentinel.platform import (
    agent_registry,
    model_versions,
)
from sentinel.platform.certification import CertificationError, assign_validator
from sentinel.platform.certification import all_entries as cert_entries
from sentinel.platform.certification import evaluate as evaluate_cert
from sentinel.ui.govflow import (
    control_popover,
)
from sentinel.ui.tables import table_head, table_row, td


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
