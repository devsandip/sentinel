"""The FAQ: the questions a visitor asks in the first five minutes.

Each entry is a short answer plus the corpus page that carries the long one, so
the FAQ is a routing surface rather than a third place a fact about the product
lives. `page_id` resolves against the corpus at load time; an entry citing a
page that does not exist raises rather than rendering a dead link.

The numbers rule applies here as it does to the corpus. An answer names the
control or the cap and sends the reader to the chapter that prints the enforced
value. No answer on this page states a tunable number.
"""

from __future__ import annotations

from dataclasses import dataclass

from .corpus_loader import page_by_id


@dataclass(frozen=True)
class FaqEntry:
    topic: str
    question: str
    answer: str
    page_id: str


FAQ_ENTRIES: tuple[FaqEntry, ...] = (
    # -- Getting oriented --------------------------------------------------
    FaqEntry(
        topic="Getting oriented",
        question="What is Sentinel?",
        answer=(
            "A governed agentic data-science platform, built around the question of "
            "how a bank lets agents touch regulated data without losing the audit "
            "trail. Every run declares a purpose, resolves an autonomy tier, has its "
            "data scoped to that purpose, and leaves evidence behind."
        ),
        page_id="overview",
    ),
    FaqEntry(
        topic="Getting oriented",
        question="Is the analysis real, or is this a mock-up?",
        answer=(
            "The analysis is real. What is scripted by default is the step narration, "
            "which comes from deterministic templates rather than a model so the "
            "public link costs nothing to run. The interface labels which of the two "
            "you are looking at, and the Live LLM toggle switches it."
        ),
        page_id="overview",
    ),
    FaqEntry(
        topic="Getting oriented",
        question="Where do I start?",
        answer=(
            "Open the User Manual and read the presentation, then the Quick start "
            "chapter, which is the click-by-click path to a governed run. If you would "
            "rather see it work first, go to Run and step through the stages."
        ),
        page_id="quick-start",
    ),
    FaqEntry(
        topic="Getting oriented",
        question="There used to be a Pipeline screen. Where did it go?",
        answer=(
            "Its tabs moved into the stages that own the question they answer: the "
            "gateway ledger at Generate, the emitted result at Execute, the "
            "disparity ratio at Interpret, the model card in the Registry. Cost "
            "became run-header chips. Four were dropped, because this route does "
            "no retrieval, keeps no precedent and emits no traces, so those panels "
            "would render empty forever. Its runs are still in the Audit Log."
        ),
        page_id="screens",
    ),
    # -- Governance concepts ----------------------------------------------
    FaqEntry(
        topic="Governance concepts",
        question="What are the nine stages?",
        answer=(
            "Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret, Attest. "
            "It is one vocabulary for reading any run, so an auditor learns it once "
            "instead of learning a different step list for every kind of run."
        ),
        page_id="nine-stages",
    ),
    FaqEntry(
        topic="Governance concepts",
        question="What is the difference between not in route, skipped, and blocked?",
        answer=(
            "Three different facts, never collapsed into one. Not in route means this "
            "kind of run has no such stage at all. Skipped means the run reached the "
            "stage and declined to execute it. Blocked means the stage ran and stopped "
            "the run."
        ),
        page_id="nine-stages",
    ),
    FaqEntry(
        topic="Governance concepts",
        question="What is an autonomy tier, and what changes between L1 and L2?",
        answer=(
            "The tier is resolved from your role, the attestations you hold, and the "
            "classification of the data, and the lowest of those ceilings wins. At L1 "
            "the agent picks a certified analysis and fills typed parameters. At L2 it "
            "may write code against the fenced API. The Autonomy levels chapter walks "
            "the ladder and prints the ceilings."
        ),
        page_id="autonomy-levels",
    ),
    FaqEntry(
        topic="Governance concepts",
        question="What is a control, and what does it mean when one fires?",
        answer=(
            "A control is a named check that acts at a specific stage and can refuse. "
            "Armed means the stage had the control in force. Fired means the control "
            "actually tripped on this run. A stage arming several checks and tripping "
            "none is the normal case, and is not a refusal."
        ),
        page_id="controls",
    ),
    FaqEntry(
        topic="Governance concepts",
        question="Why do some controls render dashed in the catalogue?",
        answer=(
            "Those are declared but not implemented. The Controls chapter styles an id "
            "dashed whenever it is absent from the implemented set, so a control cannot "
            "be presented as enforcement it is not. A control that gains an "
            "implementation changes appearance there with no edit to the manual."
        ),
        page_id="controls",
    ),
    FaqEntry(
        topic="Governance concepts",
        question="Who can approve a run, and why not the person who ran it?",
        answer=(
            "Promotion authority sits with the MRM Approver, and that persona cannot "
            "run. Keeping the two disjoint means the signature on a promotion is never "
            "the author's own, which is what segregation of duties means here."
        ),
        page_id="roles-and-access",
    ),
    # -- Using the product -------------------------------------------------
    FaqEntry(
        topic="Using the product",
        question="Why can I see a dataset's schema but not its rows?",
        answer=(
            "Access is scoped by purpose and by role, at column level. Some datasets "
            "publish a contract, the column roles and the classification without "
            "publishing the data. The Data chapter covers what a contract does and "
            "does not put on the page."
        ),
        page_id="data",
    ),
    FaqEntry(
        topic="Using the product",
        question="What does the purpose matrix decide?",
        answer=(
            "It maps a declared purpose against a data classification and returns what "
            "that combination permits. Declaring a purpose at the Ask stage is what "
            "makes the later access scoping decidable rather than discretionary."
        ),
        page_id="roles-and-access",
    ),
    FaqEntry(
        topic="Using the product",
        question="What does the Audit Log's 'caught' column mean?",
        answer=(
            "It names the controls that actually fired on that run. Opening a row "
            "drills into the run read in the nine stages, with the native step names "
            "kept visible under each canonical stage."
        ),
        page_id="screens",
    ),
    FaqEntry(
        topic="Using the product",
        question="Do my runs persist?",
        answer=(
            "No. Live runs write to a runtime directory that is excluded from version "
            "control and from the deploy bundle, so a restart leaves the seeded history "
            "alone. The Architecture chapter covers deployment."
        ),
        page_id="architecture",
    ),
    FaqEntry(
        topic="Using the product",
        question="Can I switch personas mid-session?",
        answer=(
            "Yes. The persona switcher is in the topbar, and the interface re-resolves "
            "what you may do as soon as you change it. Switching to the Auditor is the "
            "quickest way to see a read-only surface."
        ),
        page_id="roles-and-access",
    ),
    # -- Ask me ------------------------------------------------------------
    FaqEntry(
        topic="About Ask me",
        question="How does Ask me decide what it will answer?",
        answer=(
            "Two stages. First a relevance gate decides whether the question is about "
            "Sentinel at all, and refuses outright if it is not. Only then does it "
            "retrieve manual passages and answer from them. A question that is on "
            "topic but not covered gets told so rather than guessed at."
        ),
        page_id="overview",
    ),
    FaqEntry(
        topic="About Ask me",
        question="Can Ask me tell me something the manual does not say?",
        answer=(
            "No, by construction. The answer is written only from retrieved passages, "
            "and every answer shows the passages it used. In scripted mode no model "
            "writes anything at all and you get the ranked passages directly."
        ),
        page_id="overview",
    ),
)


def validate() -> None:
    """Fail loudly if an entry cites a corpus page that does not exist."""
    missing = sorted({e.page_id for e in FAQ_ENTRIES if page_by_id(e.page_id) is None})
    if missing:
        raise ValueError(f"FAQ entries cite unknown corpus pages: {missing}")


def topics() -> list[tuple[str, list[FaqEntry]]]:
    """FAQ entries grouped by topic, in first-seen order."""
    validate()
    grouped: dict[str, list[FaqEntry]] = {}
    for entry in FAQ_ENTRIES:
        grouped.setdefault(entry.topic, []).append(entry)
    return list(grouped.items())
