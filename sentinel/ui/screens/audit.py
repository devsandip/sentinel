"""The Audit Log: the one cross-run surface, and a single run's drill-down.

See docs/features/audit-log.md. Rows are entitlement-scoped by persona, and a
withheld run says that it exists rather than vanishing."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import html
import json

import pandas as pd
import streamlit as st

from sentinel.govflow.controls_info import control_info, implemented_ids
from sentinel.harness.identity import (
    get_persona,
    policy_version,
)
from sentinel.orchestrator import (
    STATUS_REJECTED,
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
from sentinel.platform.run_history import KIND_CREDIT_RISK
from sentinel.ui.govflow import (
    cls_label,
    control_popover,
    purpose_extra,
)
from sentinel.ui.shell import classification_of, nav_to
from sentinel.ui.tables import table_head, table_row, td

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
SECTION_AUDIT_RUN = "Audit Run"



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




def audit_open(run_id: str) -> None:
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
    nav_to(SECTION_AUDIT_RUN)




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
        nav_to("Audit Log")

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
                audit_open(r.run_id)
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
            classification = classification_of(r.dataset_id)
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
            audit_open(r.run_id)

    st.caption(
        "Newest first, fixed sort. Seeded rows carry the demo-timeline date; "
        "live rows carry real execution time. Click a run id to open it."
    )

    st.caption(
        "A run opens as its own screen. Sidebar Back returns here, and the "
        "address bar carries ?run=<id>, so a single run's evidence can be "
        "linked, bookmarked, or opened in a new browser tab."
    )
