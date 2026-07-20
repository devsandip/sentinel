"""The Agent Templates screen: a blueprint you can edit, check and deploy.

Two views on one section. A list of the shipped templates plus whatever this
session has drafted, and a drill-down that is an editor, a validation panel and
a deploy footer stacked in that order. The drill-down shares the section with
the list, following the dataset contract rather than the audit run: the editor
belongs to this page, so the nav item should stay lit and the app's Back stack
should not be spent on it. The audit run earns its own section because it is
deep-linkable and is a different object; a template's editor is neither.

The validation panel deliberately reuses the Gate stage's language -- four
verdicts, a count of what each check judged, evidence chips for the constructs
it read (sentinel/codegen/gate.py). A reviewer who has read one panel can read
this one. It also means the two panels cannot drift apart in wording, since
`CheckReading` computes its own summary and neither screen keeps a copy.

The shipped templates are never mutated. Edits live in session state against a
per-template buffer, and Revert restores from the Python objects, so the five
blueprints and the coverage metric read off them stay exactly what the tests
assert. What you edit is a draft; Download gives you the artifact to commit.
"""

from __future__ import annotations

import html

import streamlit as st

from ..codegen.gate import CLEARED, NO_SUBJECT, NOT_ARMED, REFUSED
from ..platform.template_spec import (
    DEPLOY_BLOCKING,
    DeployRefused,
    SpecError,
    blocking,
    deploy,
    deployable,
    eval_check_ids,
    import_vocabulary,
    pattern_vocabulary,
    summary_of,
    to_yaml,
    tool_vocabulary,
    validate_text,
)
from ..platform.templates import AVAILABLE, LIVE, all_templates, get_template
from .tables import table_head, table_row, td

SECTION = "Agent Templates"


def _esc(v: object) -> str:
    return html.escape(str(v))


def _html_table(header: list[str], rows: list[str], caption: str = "") -> None:
    head = "".join(f"<th>{_esc(h)}</th>" for h in header)
    st.markdown(
        "<div class='gv-scroll'><table class='gv-table'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        + (f"<div class='muted' style='margin-top:4px'>{_esc(caption)}</div>" if caption else ""),
        unsafe_allow_html=True,
    )


_READ_STYLE = {
    CLEARED: ("cleared", "cleared"),
    REFUSED: ("refused", "refused"),
    NO_SUBJECT: ("none", "nothing to read"),
    NOT_ARMED: ("unarmed", "not armed"),
}

_STATUS_PILL = {
    LIVE: "<span class='pill pill-in_use'>live</span>",
    AVAILABLE: "<span class='pill pill-planned'>available</span>",
}
_DRAFT_PILL = "<span class='pill pill-planned'>session draft</span>"


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
def _buffers() -> dict[str, str]:
    """Per-template editor buffers. A template with no entry here has not been
    edited this session and renders from its Python object."""
    return st.session_state.setdefault("tpl_buf", {})


def _drafts() -> dict[str, str]:
    """Drafts saved off a template this session: draft id -> YAML."""
    return st.session_state.setdefault("tpl_drafts", {})


def _deploys() -> list[dict]:
    return st.session_state.setdefault("tpl_deploys", [])


def _source(template_id: str) -> str:
    """The YAML for a template id: the edited buffer, a saved draft, or the
    shipped blueprint rendered fresh."""
    buffers = _buffers()
    if template_id in buffers:
        return buffers[template_id]
    drafts = _drafts()
    if template_id in drafts:
        return drafts[template_id]
    t = get_template(template_id)
    return to_yaml(t) if t else ""


def _is_edited(template_id: str) -> bool:
    t = get_template(template_id)
    if t is None:
        return False
    return _buffers().get(template_id, to_yaml(t)) != to_yaml(t)


# --------------------------------------------------------------------------
# The list
# --------------------------------------------------------------------------
# The row carries a button, so it is built from st.columns rather than raw HTML
# (ui/tables.py exists for exactly this: a cell that holds the thing you click).
_COLS = (3.0, 2.0, 0.7, 1.9, 1.5, 1.3, 1.2)
_HEAD = ("template", "pattern", "tier", "declares", "state", "policy", "")


def _open(template_id: str) -> None:
    st.session_state["tpl_sel"] = template_id


def _close() -> None:
    st.session_state["tpl_sel"] = None


def render_agent_templates(persona) -> None:  # noqa: ANN001
    # The list is the screen; the editor is the detail. Same section, so the
    # sidebar nav item stays lit and Back is not spent on a drill-down that
    # belongs to this page (the dataset contract does the same).
    if st.session_state.get("tpl_sel"):
        _render_editor(st.session_state["tpl_sel"], persona)
        return
    st.subheader("Agent templates")
    st.markdown(
        "<span class='muted'>A template is a governed blueprint: the tool "
        "allow-list, the column grant, the purposes it may run under, the tier "
        "ceiling and the eval floor, declared in one document. Starting from one "
        "means a new agent inherits the controls instead of re-deriving them."
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span class='muted'>Every field names a value some other module owns, so "
        "editing is checkable rather than free text. <b>Policy checks</b> are the "
        "fence and a refusal blocks the deploy. <b>Certification gates</b> do not: "
        "they block <code>certified</code>, which is why all five ship unowned and "
        "deploy to draft.</span>",
        unsafe_allow_html=True,
    )

    table_head(_HEAD, _COLS, "tpl")
    for t in all_templates():
        _row(t.id, t.name, _STATUS_PILL.get(t.status, t.status), edited=_is_edited(t.id))
    for draft_id in _drafts():
        _row(draft_id, draft_id, _DRAFT_PILL, edited=False)

    st.caption(
        "Tier is the ceiling the template asks for; a run still resolves "
        "min(that, the data's classification ceiling, the person's ceiling). "
        "Policy counts only the checks that block a deploy, so a template can "
        "read clear here and still be nowhere near certified."
    )

    if _deploys():
        st.divider()
        st.markdown("### Deployed this session")
        st.markdown(
            "<span class='muted'>Each of these is a real draft in the "
            "certification registry, visible on the Registry screen under "
            "Analysis-agents. None of them is certified, and the gates below say "
            "what each is waiting on.</span>",
            unsafe_allow_html=True,
        )
        for d in reversed(_deploys()):
            st.code(d["report"], language="text")


def _row(tid: str, name: str, pill: str, edited: bool) -> None:
    cols = table_row(_COLS, f"tpl_{tid}")
    try:
        spec, checks = validate_text(_source(tid))
    except SpecError as exc:
        cols[0].markdown(
            f"<span class='td'><b>{_esc(name)}</b></span>"
            f"<span class='evline'>{_esc(tid)}</span>",
            unsafe_allow_html=True,
        )
        cols[1].markdown(
            f"<span class='ev no'>does not parse</span> "
            f"<span class='muted'>{_esc(exc)}</span>",
            unsafe_allow_html=True,
        )
        cols[6].button("Open", key=f"tplopen_{tid}", on_click=_open, args=(tid,),
                       use_container_width=True)
        return

    refused = blocking(checks)
    dataset = spec.dataset or "no dataset"
    cols[0].markdown(
        f"<span class='td'><b>{_esc(name)}</b></span>"
        f"<span class='evline'>{_esc(tid)} · {_esc(dataset)}</span>",
        unsafe_allow_html=True,
    )
    td(cols[1], spec.pattern)
    td(cols[2], spec.max_tier, mono=True)
    td(
        cols[3],
        f"{len(spec.tools)} tool{'' if len(spec.tools) == 1 else 's'}, "
        f"{len(spec.columns)} column{'' if len(spec.columns) == 1 else 's'}",
    )
    cols[4].markdown(
        pill + (" <span class='ev muted'>edited</span>" if edited else ""),
        unsafe_allow_html=True,
    )
    cols[5].markdown(
        f"<span class='ev no'>{len(refused)} refused</span>"
        if refused
        else "<span class='ev'>clear</span>",
        unsafe_allow_html=True,
    )
    cols[6].button(
        "Open",
        key=f"tplopen_{tid}",
        on_click=_open,
        args=(tid,),
        use_container_width=True,
        help="Edit the spec, see every check it is judged against, and deploy it "
        "as a draft.",
    )


# --------------------------------------------------------------------------
# The editor
# --------------------------------------------------------------------------
def _render_editor(tid: str, persona) -> None:  # noqa: ANN001
    t = get_template(tid)
    if t is None and tid not in _drafts():
        st.error(f"Unknown template {tid!r}.")
        st.button("Back to templates", on_click=_close, key="tplnosel")
        return

    st.button("Back to templates", on_click=_close, key="tplback")
    st.subheader(t.name if t else tid)
    edited = _is_edited(tid)
    st.markdown(
        (
            "<span class='muted'>Edited this session. The shipped blueprint is "
            "unchanged; Revert restores it.</span>"
            if edited
            else "<span class='muted'>The shipped blueprint, as authored.</span>"
        ),
        unsafe_allow_html=True,
    )

    source = _source(tid)
    try:
        spec, checks = validate_text(source)
    except SpecError as exc:
        spec, checks = None, []
        st.markdown(
            f"<div class='gvd block'><div class='h'>The document does not parse</div>"
            f"<div class='why'>{_esc(exc)}</div>"
            "<div class='then'>Nothing was checked: a document that will not parse "
            "cannot be reasoned about, which is the same order the code gate uses."
            "</div></div>",
            unsafe_allow_html=True,
        )

    if spec is not None:
        _declares_strip(spec)

    left, right = st.columns([2.1, 1], gap="medium")
    with left:
        st.markdown("**The spec**")
        new = st.text_area(
            "spec",
            value=source,
            height=560,
            key=f"tpltext_{tid}",
            label_visibility="collapsed",
        )
        if new != source:
            _buffers()[tid] = new
            st.rerun()
    with right:
        _reference(spec)

    b1, b2, _ = st.columns([1, 1, 2])
    if b1.button("Revert", key=f"tplrev_{tid}", disabled=not edited, use_container_width=True):
        _buffers().pop(tid, None)
        st.rerun()
    b2.download_button(
        "Download .yaml",
        data=source,
        file_name=f"{spec.id if spec else tid}.yaml",
        mime="application/x-yaml",
        key=f"tpldl_{tid}",
        use_container_width=True,
    )

    if spec is None:
        return

    st.divider()
    _validation(checks)
    st.divider()
    _deploy_footer(tid, spec, checks, persona)


def _declares_strip(spec) -> None:  # noqa: ANN001
    """What the document declares, before any verdict on it."""
    classification = spec.classification
    tiles = [
        ("pattern", spec.pattern or "none", "from the pattern catalog"),
        (
            "tier ceiling",
            spec.max_tier or "none",
            f"{classification} data" if classification else "no dataset to bound it",
        ),
        (
            "dataset",
            spec.dataset or "none",
            f"{classification}, simulated" if classification else "no contract declared",
        ),
        (
            "purposes",
            ", ".join(spec.purposes) or "none",
            "matrix columns it may run under",
        ),
        (
            "scope",
            f"{len(spec.tools)} tools, {len(spec.columns)} columns",
            f"{len(spec.imports)} imports at {spec.max_tier or '?'}",
        ),
        (
            "eval floor",
            f"{spec.eval_floor:g}" if spec.eval_floor is not None else "none",
            f"{len(spec.eval_hooks)} hooks declared",
        ),
    ]
    st.markdown("**What the template declares**")
    st.markdown(
        "<div class='gatein'>"
        + "".join(
            f"<div class='t'><div class='k'>{_esc(k)}</div>"
            f"<div class='v'>{_esc(v)}</div><div class='s'>{_esc(s)}</div></div>"
            for k, v, s in tiles
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _reference(spec) -> None:  # noqa: ANN001
    """The closed vocabularies, so the author is not guessing at legal values."""
    st.markdown("**Legal values**")
    st.markdown(
        "<span class='muted'>Read from the enforcing modules, not typed here.</span>",
        unsafe_allow_html=True,
    )
    tier = spec.max_tier if spec else "L2"
    with st.expander("tools", expanded=True):
        st.markdown(_chips(tool_vocabulary()), unsafe_allow_html=True)
        st.caption("agents.yaml, enforced per agent by guardrails")
    with st.expander(f"imports at {tier}"):
        if tier in ("L0", "L1"):
            st.markdown(
                f"<span class='muted'>{_esc(tier)} writes no code, so the list must "
                "be empty.</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(_chips(import_vocabulary(tier)), unsafe_allow_html=True)
        st.caption("codegen/allowlist.py")
    with st.expander("patterns"):
        st.markdown(_chips(pattern_vocabulary()), unsafe_allow_html=True)
        st.caption("platform/patterns.py")
    with st.expander("eval hooks that resolve today"):
        st.markdown(_chips(eval_check_ids()), unsafe_allow_html=True)
        st.caption("evals.yaml. A hook outside this list is a case still to write.")


def _chips(values) -> str:  # noqa: ANN001
    return "".join(f"<span class='ev muted'>{_esc(v)}</span>" for v in values)


def _validation(checks: list) -> None:
    refused = [c for c in checks if c.verdict == REFUSED]
    policy_refused = blocking(checks)
    gates_refused = [c for c in refused if c.key not in DEPLOY_BLOCKING]

    if policy_refused:
        head = f"Refused by {len(policy_refused)} policy check" + (
            "" if len(policy_refused) == 1 else "s"
        )
        why = (
            "This spec cannot be deployed. "
            + "; ".join(
                f"<b>{_esc(c.label)}</b>: "
                + ", ".join(f"<code>{_esc(o.subject)}</code>" for o in c.refusals)
                for c in policy_refused
            )
            + "."
        )
        then = (
            "A policy refusal is the fence. The same rules judge generated code at "
            "the Gate stage, read earlier here so an illegal blueprint never reaches "
            "the registry."
        )
        cls = "block"
    else:
        head = "Policy checks clear"
        why = (
            "Every check that gates a deploy is satisfied, so this spec can be "
            "registered as a draft."
        )
        then = "Nothing was executed to reach this verdict: the document was read, not run."
        cls = "pass"
    if gates_refused:
        then += (
            " "
            + str(len(gates_refused))
            + " certification gate"
            + ("" if len(gates_refused) == 1 else "s")
            + " still fail ("
            + ", ".join(_esc(c.label.lower()) for c in gates_refused)
            + "). Those block certified, not the draft."
        )
    st.markdown(
        f"<div class='gvd {cls}'><div class='h'>{_esc(head)}</div>"
        f"<div class='why'>{why}</div><div class='then'>{then}</div></div>",
        unsafe_allow_html=True,
    )

    cells = []
    for c in checks:
        cls, _word = _READ_STYLE.get(c.verdict, ("none", c.verdict))
        if c.verdict == NOT_ARMED:
            figure, unit = "n/a", "rule not supplied"
        elif c.verdict == NO_SUBJECT:
            figure, unit = "–", "nothing to read"
        else:
            figure = str(c.examined)
            unit = (
                "judged"
                if c.verdict == CLEARED
                else f"judged, {len(c.refusals)} refused"
            )
        ids = ", ".join(c.controls) or ("policy" if c.key in DEPLOY_BLOCKING else "gate")
        cells.append(
            f"<div class='cell {cls}'>"
            f"<div class='cid'><span class='d'></span>{_esc(ids)}</div>"
            f"<div class='nrow'><span class='n'>{_esc(figure)}</span>"
            f"<span class='nu'>{_esc(unit)}</span></div>"
            f"<div class='lab'>{_esc(c.label)}</div></div>"
        )
    st.markdown("**What each check read**")
    st.markdown(f"<div class='gateread'>{''.join(cells)}</div>", unsafe_allow_html=True)
    st.caption(
        "Four verdicts, and only two of them are verdicts on the document. "
        "'nothing to read' means the check was armed and found no subject; "
        "'not armed' means its rule was never supplied, which is a gap, not an assurance."
    )

    rows = []
    for c in checks:
        mark = {
            CLEARED: "<span class='ok'>✓ cleared</span>",
            REFUSED: "<span class='flag'>✕ refused</span>",
            NO_SUBJECT: "<span class='muted'>– no subject</span>",
            NOT_ARMED: "<span class='gv-below'>! not armed</span>",
        }.get(c.verdict, _esc(c.verdict))
        kind = "policy" if c.key in DEPLOY_BLOCKING else "certification gate"
        chips = "".join(
            f"<span class='ev{'' if o.allowed else ' no'}' "
            f"title='{_esc(o.reason)}'>{_esc(o.subject)}"
            + (f" <span style='opacity:.6'>L{o.line}</span>" if o.line else "")
            + "</span>"
            for o in c.items[:12]
        )
        if len(c.items) > 12:
            chips += f"<span class='ev muted'>+{len(c.items) - 12} more</span>"
        reasons = "".join(
            f"<div class='muted' style='margin-top:3px'>{_esc(o.subject)}: {_esc(o.reason)}</div>"
            for o in c.refusals[:4]
        )
        rows.append(
            f"<tr><td><b>{_esc(c.label)}</b><br>"
            f"<span class='evline'>{_esc(', '.join(c.controls) or kind)}</span></td>"
            f"<td>{mark}<div class='muted'>{_esc(summary_of(c))}</div>"
            + (f"<div>{chips}</div>" if chips else "")
            + reasons
            + f"</td><td><span class='muted'>reads {_esc(c.examines)}</span><br>"
            f"<span class='muted'>against {_esc(c.rule)}</span></td></tr>"
        )
    _html_table(["check", "what it read, and how it ruled", "the rule"], rows)


def _deploy_footer(tid: str, spec, checks: list, persona) -> None:  # noqa: ANN001
    st.markdown("### Deploy")
    ok = deployable(checks)
    st.markdown(
        "<span class='muted'>Deploy registers this spec as a <b>draft</b> in the "
        "certification registry, with the dataset's content SHA computed now and "
        "pinned into the contract. It appears on the Registry screen under "
        "Analysis-agents, and the four gates decide what it is allowed to become. "
        "This is the same thing <code>sentinel new-agent</code> does from the "
        "CLI.</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span class='muted'><b>What is simulated.</b> Nothing is written to disk "
        "and no process is started. An enterprise deployment would push the spec to "
        "the agent runtime from this point; the governance outcome above is real, "
        "the rollout is not.</span>",
        unsafe_allow_html=True,
    )

    author = getattr(persona, "id", None) or getattr(persona, "name", "unknown")
    c1, c2 = st.columns([1, 3])
    if c1.button(
        "Deploy as draft",
        key=f"tpldep_{tid}",
        type="primary",
        disabled=not ok,
        use_container_width=True,
    ):
        try:
            result = deploy(spec, checks, author=str(author))
        except DeployRefused as exc:
            st.error(str(exc))
        else:
            _deploys().append({"id": spec.id, "report": result.report()})
            st.success(
                f"{spec.id} v{spec.version} registered at "
                f"{result.decision.status}. {result.sha_note}."
            )
            st.code(result.report(), language="text")
    if not ok:
        c2.markdown(
            "<span class='muted'>Disabled: a policy check refused this spec. "
            "Fix the refusals above and it enables.</span>",
            unsafe_allow_html=True,
        )
    else:
        c2.markdown(
            f"<span class='muted'>Will register as <code>{_esc(spec.id)}</code> "
            f"v{_esc(spec.version)}, authored by <code>{_esc(author)}</code>.</span>",
            unsafe_allow_html=True,
        )
