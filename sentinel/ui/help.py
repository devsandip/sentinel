"""The other two Help screens: FAQ and Ask me.

The User Manual is the reference. These two are lookup surfaces over it, and
neither is allowed to become a second reference: the FAQ answers in a sentence
and routes to the chapter, and Ask me answers only from retrieved manual
passages and shows them.

Both screens jump into the manual by writing `manual_chapter` before navigating,
so "read the chapter" lands on the chapter rather than on the deck. `nav_to` is
injected the same way `render_manual` takes it, and for the same reason: `app.py`
imports this module, so importing back would be a cycle.
"""

from __future__ import annotations

import html

import streamlit as st

from sentinel.gateway.model_gateway import ANTHROPIC, TEMPLATED, ModelGateway
from sentinel.help import faq as faq_mod
from sentinel.help.ask import ANSWERED, IRRELEVANT, UNSUPPORTED, Answer, ask
from sentinel.help.corpus_loader import page_by_id

_HELP_CSS = """
    <style>
      .help-lede { color:var(--muted); font-size:14.5px; max-width:78ch;
        line-height:1.55; }
      .faq-a { color:var(--muted); font-size:14px; line-height:1.6;
        max-width:76ch; }
      .faq-src { font-family:var(--mono); font-size:11px; color:var(--faint);
        letter-spacing:.02em; margin-top:8px; }
      .ask-verdict { display:inline-block; font-family:var(--mono); font-size:10.5px;
        font-weight:700; letter-spacing:.09em; text-transform:uppercase;
        padding:2px 9px; border-radius:999px; margin-bottom:9px; }
      .ask-verdict.ok { color:var(--ok); background:var(--ok-soft);
        border:1px solid var(--ok-border); }
      .ask-verdict.no { color:var(--danger); background:var(--danger-soft);
        border:1px solid var(--danger-border); }
      .ask-verdict.warn { color:var(--warn); background:var(--warn-soft);
        border:1px solid var(--warn-border); }
      .ask-cite { border-left:2px solid var(--border); padding:2px 0 2px 12px;
        margin:10px 0; }
      .ask-cite .h { font-family:var(--mono); font-size:11px; color:var(--faint);
        letter-spacing:.02em; }
      .ask-cite .t { color:var(--muted); font-size:13px; line-height:1.55;
        margin-top:4px; max-width:76ch; }
      .ask-meta { font-family:var(--mono); font-size:11px; color:var(--faint);
        margin-top:10px; }
    </style>
"""


def _esc(v: object) -> str:
    return html.escape(str(v))


def _open_chapter(nav_to, page_id: str) -> None:  # noqa: ANN001
    """Jump to the manual chapter a corpus page renders.

    Called from the button's return value rather than from `on_click`: `nav_to`
    ends in `st.rerun()`, and a rerun inside a callback is a no-op that
    Streamlit warns about on the page.
    """
    page = page_by_id(page_id)
    if page is not None:
        st.session_state.manual_chapter = page.chapter
    nav_to("User Manual")


# --------------------------------------------------------------------------
# FAQ
# --------------------------------------------------------------------------
def render_faq(nav_to) -> None:  # noqa: ANN001
    """The FAQ screen: common questions, each routing to its chapter."""
    st.markdown(_HELP_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='eyebrow' style='margin-bottom:4px'>Help</div>",
        unsafe_allow_html=True,
    )
    st.subheader("FAQ")
    st.markdown(
        "<div class='help-lede'>The questions that come up in the first five "
        "minutes, answered in a sentence each. Every answer names the User "
        "Manual chapter that carries the long version, because the manual is "
        "the reference and this page is a shortcut into it. If your question "
        "is not here, ask it on Ask me.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    query = st.text_input(
        "Filter",
        placeholder="Filter questions, e.g. autonomy, approve, dataset",
        label_visibility="collapsed",
        key="faq_filter",
    ).strip().lower()

    shown = 0
    for topic, entries in faq_mod.topics():
        matching = [
            e
            for e in entries
            if not query or query in e.question.lower() or query in e.answer.lower()
        ]
        if not matching:
            continue
        st.markdown(
            f"<div class='eyebrow' style='margin:18px 0 6px 0'>{_esc(topic)}</div>",
            unsafe_allow_html=True,
        )
        for entry in matching:
            shown += 1
            page = page_by_id(entry.page_id)
            with st.expander(entry.question):
                st.markdown(
                    f"<div class='faq-a'>{_esc(entry.answer)}</div>",
                    unsafe_allow_html=True,
                )
                if page is not None:
                    st.markdown(
                        f"<div class='faq-src'>User Manual · "
                        f"{_esc(page.chapter)}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"Open the {page.chapter} chapter",
                        key=f"faq_go_{entry.page_id}_{shown}",
                    ):
                        _open_chapter(nav_to, entry.page_id)

    if shown == 0:
        st.info(
            f"No FAQ entry matches '{query}'. Ask me takes the question directly "
            "and answers it from the manual."
        )


# --------------------------------------------------------------------------
# Ask me
# --------------------------------------------------------------------------
_SUGGESTED = (
    "What are the nine stages?",
    "What does L2 let an agent do?",
    "Who can approve a run?",
    "What happens if a control fires?",
)

# The off-topic example is on the page on purpose. The relevance gate is a
# feature, and a feature nobody triggers reads as an absent one.
_OFF_TOPIC_DEMO = "Who is the PM of India?"

_VERDICT_CHIP = {
    ANSWERED: ("ok", "answered from the manual"),
    UNSUPPORTED: ("warn", "not covered by the manual"),
    IRRELEVANT: ("no", "refused: off topic"),
}


def _render_answer(answer: Answer, nav_to, turn: int) -> None:  # noqa: ANN001
    cls, label = _VERDICT_CHIP[answer.verdict]
    st.markdown(
        f"<span class='ask-verdict {cls}'>{_esc(label)}</span>",
        unsafe_allow_html=True,
    )
    st.write(answer.text)

    if answer.citations:
        with st.expander(
            f"{len(answer.citations)} manual passage"
            f"{'s' if len(answer.citations) != 1 else ''} used"
        ):
            for i, hit in enumerate(answer.citations):
                st.markdown(
                    f"<div class='ask-cite'><div class='h'>[{i + 1}] "
                    f"{_esc(hit.chunk.anchor)} · score {hit.score}</div>"
                    f"<div class='t'>{_esc(hit.chunk.text)}</div></div>",
                    unsafe_allow_html=True,
                )
            top = answer.citations[0].chunk
            if st.button(f"Open the {top.chapter} chapter", key=f"ask_go_{turn}"):
                _open_chapter(nav_to, top.page_id)

    bits = []
    bits.append("answer: live model" if answer.live else "answer: scripted (passages)")
    bits.append("gate: live model" if answer.gate_live else "gate: lexical")
    if answer.tokens:
        bits.append(f"{answer.tokens} tokens · ${answer.cost_usd:.4f}")
    st.markdown(
        f"<div class='ask-meta'>{_esc(' · '.join(bits))}</div>",
        unsafe_allow_html=True,
    )
    for note in answer.notes:
        st.caption(note)


def _submit(question: str) -> None:
    st.session_state.ask_pending = question


def render_ask(nav_to) -> None:  # noqa: ANN001
    """Ask me: a question answered from the manual, or refused."""
    st.markdown(_HELP_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='eyebrow' style='margin-bottom:4px'>Help</div>",
        unsafe_allow_html=True,
    )
    st.subheader("Ask me")
    st.markdown(
        "<div class='help-lede'>Ask a question about Sentinel and get an answer "
        "built only from the User Manual. Every question passes a relevance "
        "check first: anything that is not about this product is refused before "
        "an answer is attempted. A question that is about Sentinel but is not "
        "covered gets told so rather than guessed at, and every answer shows "
        "the passages it was written from.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    mode = st.radio(
        "Mode",
        ["scripted", "live"],
        format_func=lambda m: "Scripted (free)" if m == "scripted" else "Live LLM",
        horizontal=True,
        key="ask_mode",
        label_visibility="collapsed",
    )
    st.caption(
        "Scripted = retrieval only, no model, zero cost: the gate is a lexical "
        "relevance test and the answer is the ranked passages themselves. Live = "
        "a model both gates and writes, cost-capped, through the same gateway "
        "and ledger as every other call in the product."
    )

    history = st.session_state.setdefault("ask_history", [])

    if not history:
        st.markdown(
            "<div class='eyebrow' style='margin:16px 0 6px 0'>Try one</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(_SUGGESTED))
        for col, q in zip(cols, _SUGGESTED, strict=True):
            col.button(
                q, key=f"ask_sug_{q}", on_click=_submit, args=(q,), width="stretch"
            )
        st.button(
            f"Or watch the gate refuse one: “{_OFF_TOPIC_DEMO}”",
            key="ask_offtopic",
            on_click=_submit,
            args=(_OFF_TOPIC_DEMO,),
        )

    for turn, (question, answer) in enumerate(history):
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            _render_answer(answer, nav_to, turn)

    typed = st.chat_input("Ask a question about Sentinel")
    if typed:
        st.session_state.ask_pending = typed

    pending = st.session_state.pop("ask_pending", None)
    if pending:
        gateway = ModelGateway(provider=ANTHROPIC if mode == "live" else TEMPLATED)
        with st.spinner("Checking relevance, then reading the manual"):
            answer = ask(pending, gateway=gateway)
        history.append((pending, answer))
        st.rerun()

    if history:
        st.button("Clear", key="ask_clear", on_click=history.clear)
