# FAQ and Ask me

**Status:** built — two screens under Help, beside the User Manual
**Nav:** Help group: User Manual, FAQ, Ask me
**Owner surfaces:** `render_faq()` and `render_ask()` in `sentinel/ui/help.py`
**Logic:** `sentinel/help/` (corpus loader, retriever, relevance gate, answer)
**Doctrine:** the manual is the reference; these two are lookups over it

---

## 1. What this is

Two lookup surfaces beside the User Manual. The FAQ answers the questions a
visitor asks in the first five minutes, in a sentence each, and routes to the
chapter carrying the long version. Ask me takes a typed question and answers it
from the manual, or refuses.

The manual already answers everything on both screens. What it does not do is
answer a question phrased as a question. A reader who wants to know whether the
approver can also run has to know that the answer lives in Roles and access, and
a reader who does not know the product cannot know that. The FAQ is the index by
question rather than by subject, and Ask me is the same index with the phrasing
constraint removed.

---

## 2. Ask me: two stages, in this order

**Stage 1, the relevance gate.** Decide whether the question is about Sentinel
at all. "Who is the PM of India" is refused here, before retrieval, at the cost
of one cheap-tier call.

**Stage 2, the grounded answer.** Retrieve corpus passages, answer strictly from
them, and show them. If the passages do not contain the answer, the verdict is
`UNSUPPORTED` and the user is told so.

Gating before retrieval rather than after is the load-bearing choice. A model
handed five passages and an off-topic question will try to bridge the two, and
the bridge is where a confident falsehood gets built. Refusing first means the
answer stage is never asked to reconcile a question it has no business
answering.

Three verdicts, never collapsed into two. `IRRELEVANT` means the question is not
about this product. `UNSUPPORTED` means it is, and the manual does not cover it.
`ANSWERED` means the passages contained it. Collapsing the first two into a
single "cannot help" would hide the gap the second one is reporting, which is
the same reasoning that keeps `NOT_IN_ROUTE` distinct from `skipped` in the
audit stages.

### Both stages work with no model

Scripted mode is the public link's path: no key, no spend. The gate degrades to
a lexical relevance test over the same index the answer retrieves from, and the
answer degrades to the ranked passages, labeled as passages rather than dressed
up as prose. The screen prints which of the two ran, per turn, as
`answer: scripted (passages) · gate: lexical`.

A live call that fails or breaches the cost cap falls back to that same path,
and the fallback reason renders under the answer. A silent degradation would be
worse than a loud failure: the user would read retrieval output as a model's
reasoning.

### Every call goes through the gateway

`ModelGateway.complete()` is new, and is what both stages call. Narration is
templated by step and code generation has canned code to fall back to; neither
shape fits a question a visitor typed, so `complete()` takes the prompt and the
fallback text from the caller. Everything else is the existing machinery: stakes
classification (the gate is low, the answer is elevated), tier routing, the
response cache, the process-global cost cap, and a ledger row per call.

Help does not get a private path to a model, because nothing does. An Ask-me
call shows up in the Gateway ledger next to a modeler narration.

---

## 3. The corpus, and the cost of a second source of truth

The manual is `sentinel/ui/manual.py`, a screen. That is the right shape for a
reader and the wrong shape for retrieval, so `sentinel/help/corpus/` restates
its editorial content as markdown that can be chunked and ranked. Ten files, one
per chapter, frontmatter naming the chapter each renders.

This is a second source of truth, and it was chosen with that understood. The
alternative considered was extracting text from the manual at runtime by
rendering each chapter under a recording stand-in for `st`, which never drifts
but couples the corpus to whichever Streamlit primitives the manual happens to
use. The markdown corpus is simpler to read, simpler to edit, and simpler to
retrieve over.

**The fence around that decision is the numbers rule.** The manual's doctrine is
that every enforced number reads from the module that enforces it. Markdown
cannot read anything, so the corpus is not allowed to state one. A page names
the control or the cap and points at the chapter that prints the live value:
"the sandbox enforces a wall clock and a memory ceiling, and the Autonomy levels
chapter prints the enforced values."

`tests/test_help.py::test_corpus_states_no_enforced_number` scans every page for
the sandbox caps, the disclosure floor, and the counts of controls and personas,
reading each value live from the module that owns it. A page that retypes one
fails the build. The tier names L0 to L3 are exempt, being structural names
rather than tunable values.

A corpus that may not carry numbers can still go stale in its prose, but prose
drift degrades gracefully: a slightly dated description of what the Screens
chapter covers is a worse answer, not a false claim about what the sandbox
enforces.

---

## 4. Decisions

**Two nav items, not two chapters.** FAQ and Ask me sit beside User Manual in
the Help group rather than becoming chapters 11 and 12 on the manual's radio
rail. A chat pane inside a chapter rail is a cramped fit, and both surfaces are
worth addressing directly.

**The off-topic demo is a button on the page.** Ask me ships a button reading
"Or watch the gate refuse one", wired to the India question. The gate is the
feature, and a feature nobody triggers reads as an absent one.

**Answers cite passages, and the passages are visible.** Every answered turn
carries an expander listing the passages used, with their retrieval scores, and
a button into the chapter the top passage came from. An answer whose grounding
cannot be inspected is an assertion.

**The FAQ answers are capped.** `test_faq_answers_are_short` fails an entry over
seventy words. The FAQ routes; it does not become a third place a fact lives.

**`nav_to` is injected.** Same as `render_manual`, and for the same reason:
`app.py` imports `sentinel/ui/help.py`, so importing back would be a cycle. It
is what the FAQ's chapter buttons and Ask me's citation buttons use, and both
write `manual_chapter` before navigating so the jump lands on the chapter rather
than the deck.

---

## 5. Known gaps

- **The corpus is hand-written prose about a screen.** The numbers rule bounds
  what can go wrong, but a chapter that gains a section will not gain a corpus
  paragraph on its own. Adding a chapter without a corpus page fails
  `test_every_manual_chapter_is_covered`; editing one silently does not.
- **Retrieval is lexical.** TF-IDF over paragraphs, the same construction as the
  policy corpus in `sentinel/rag/store.py`. A question phrased entirely in
  synonyms of the manual's vocabulary can miss. The dense-embedding path exists
  in `sentinel/rag/` and is not wired here.
- **No conversation memory.** Each question is answered independently. A
  follow-up that says "and what about L3" carries no antecedent, so it retrieves
  on those words alone.
- **The scripted answer is passages, not prose.** That is honest, and it is not
  a good read. A visitor on the public link gets ranked paragraphs where a live
  visitor gets two sentences.
