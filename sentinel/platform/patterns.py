"""Agentic architecture pattern catalog (ideas.md item 12).

A curated, vetted catalog anchored on Anthropic's *Building Effective Agents*,
which draws the line between workflows (LLMs on predefined code paths,
predictable, preferred in regulated settings) and agents (LLMs directing their
own tool use). Each entry names where Sentinel uses the pattern, or why it is
deliberately avoided, so the catalog is not abstract theory but a map of this
codebase.

Status values:
  in_use   - Sentinel implements this today.
  planned  - on the platform buildout roadmap (see docs/features/platform-buildout.md).
  avoided  - deliberately not used, and the reason is itself the point.
"""

from __future__ import annotations

from dataclasses import dataclass

IN_USE = "in_use"
PLANNED = "planned"
AVOIDED = "avoided"


@dataclass(frozen=True)
class Pattern:
    id: str
    name: str
    summary: str
    where: str
    status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "where": self.where,
            "status": self.status,
        }


# The five workflow patterns from Building Effective Agents, plus the workflow/
# agent distinction that frames the whole catalog.
PATTERNS: list[Pattern] = [
    Pattern(
        id="prompt_chaining",
        name="Prompt chaining",
        summary=(
            "Decompose the task into a fixed sequence of steps, with programmatic "
            "gates between them. Predictable and inspectable."
        ),
        where=(
            "The core pipeline: Profiler to EDA to Modeler, then a human-approval "
            "gate, then Validator to finalize. The human gate and the eval gate "
            "are the programmatic checks between steps. This is Sentinel's backbone."
        ),
        status=IN_USE,
    ),
    Pattern(
        id="evaluator_optimizer",
        name="Evaluator-optimizer",
        summary=(
            "A generator proposes and a critic evaluates against clear criteria, "
            "looping until the criteria are met."
        ),
        where=(
            "The Modeler (generator) proposes a model; the eval gate (critic) "
            "checks it against golden criteria and blocks promotion on failure. "
            "Single-pass today; the loop can iterate as the eval suite grows."
        ),
        status=IN_USE,
    ),
    Pattern(
        id="routing",
        name="Routing",
        summary=(
            "Classify the input and send it to a specialized handler. Also routes "
            "easy calls to cheap models and hard calls to capable ones."
        ),
        where=(
            "The model gateway will classify each call by stakes and difficulty "
            "and route: trivial narration to a template, low-stakes narration to a "
            "cheap model, harder generation to a capable model. See item 1."
        ),
        status=PLANNED,
    ),
    Pattern(
        id="parallelization",
        name="Parallelization (sectioning / voting)",
        summary=(
            "Run independent subtasks in parallel (sectioning), or make multiple "
            "attempts and vote for higher confidence (voting)."
        ),
        where=(
            "Guardrail input/output screening runs as a separate instance from the "
            "core response (sectioning). Voting is available to raise confidence on "
            "guardrail and eval decisions. See item 7."
        ),
        status=PLANNED,
    ),
    Pattern(
        id="orchestrator_workers",
        name="Orchestrator-workers",
        summary=(
            "A central LLM dynamically decomposes a task and delegates to worker "
            "LLMs when the subtasks cannot be predicted in advance."
        ),
        where=(
            "Deliberately not used. Dynamic self-decomposition is the wrong default "
            "in a regulated setting: the control flow must be fixed and auditable, "
            "not decided at runtime by a model. Naming what we avoid, and why, is "
            "part of the governance argument."
        ),
        status=AVOIDED,
    ),
]

PATTERNS_BY_ID: dict[str, Pattern] = {p.id: p for p in PATTERNS}


def all_patterns() -> list[Pattern]:
    return list(PATTERNS)


def get_pattern(pattern_id: str) -> Pattern | None:
    return PATTERNS_BY_ID.get(pattern_id)
