"""Reusable agent templates (ideas.md item 11).

Parameterized starter agents with the governance harness pre-wired: a tool
allow-list, an RBAC scope, logging, and eval hooks. The point of a template is
leverage: a new agent starts from a governed blueprint, not a blank file, so it
inherits the controls by default.

Honesty note. Three of these templates have live running instances in the
current pipeline (the four pipeline agents realize three templates). Two more are
defined and available but not yet instantiated; they land with later phases
(retrieval-QA needs the RAG layer, item 2). We track template *coverage* of the
live agents, not a fabricated "built from template" percentage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LIVE = "live"  # the template has running instances in the pipeline
AVAILABLE = "available"  # defined and usable, not yet instantiated


@dataclass(frozen=True)
class AgentTemplate:
    id: str
    name: str
    purpose: str
    pattern: str  # references the pattern catalog id
    tools: list[str]  # pre-wired tool allow-list
    rbac_scope: str  # human-readable least-privilege scope
    evals: list[str]  # pre-wired eval hooks
    status: str
    realized_by: list[str] = field(default_factory=list)  # live agent ids

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "purpose": self.purpose,
            "pattern": self.pattern,
            "tools": list(self.tools),
            "rbac_scope": self.rbac_scope,
            "evals": list(self.evals),
            "status": self.status,
            "realized_by": list(self.realized_by),
        }


TEMPLATES: list[AgentTemplate] = [
    AgentTemplate(
        id="data_analysis",
        name="Data-analysis agent",
        purpose=(
            "Read permitted columns, profile or explore them, and narrate findings. "
            "The workhorse for profiling and EDA."
        ),
        pattern="prompt_chaining",
        tools=["read_columns", "profile_dataset"],
        rbac_scope="structural columns; PII and proxies withheld",
        evals=["no_pii_in_narration", "columns_within_scope"],
        status=LIVE,
        realized_by=["profiler", "eda"],
    ),
    AgentTemplate(
        id="modeling",
        name="Modeling agent",
        purpose=(
            "Train a baseline model on permitted features and request human "
            "approval before anything is promoted."
        ),
        pattern="evaluator_optimizer",
        tools=["read_columns", "train_model"],
        rbac_scope="features only; cannot validate its own model",
        evals=["auc_floor", "protected_excluded"],
        status=LIVE,
        realized_by=["modeler"],
    ),
    AgentTemplate(
        id="validation",
        name="Validation agent",
        purpose=(
            "Run an independent fairness review and the eval gate; flag disparities "
            "and block promotion on a failed check."
        ),
        pattern="evaluator_optimizer",
        tools=["read_columns", "compute_fairness", "run_eval_gate", "retrieve_policy"],
        rbac_scope="adds the protected attribute, for fairness only; cannot train",
        evals=["fairness_section_present", "eval_gate_complete"],
        status=LIVE,
        realized_by=["validator"],
    ),
    AgentTemplate(
        id="retrieval_qa",
        name="Retrieval-QA agent",
        purpose=(
            "Answer a scoped question grounded in the governed knowledge corpus, "
            "citing sources rather than asserting."
        ),
        pattern="prompt_chaining",
        tools=["read_columns", "retrieve_policy"],
        rbac_scope="corpus read; no dataset PII",
        evals=["groundedness", "citation_present"],
        status=AVAILABLE,  # lands with the RAG layer (item 2)
    ),
    AgentTemplate(
        id="document_summarizer",
        name="Document-summarizer agent",
        purpose=(
            "Summarize a document with PII redaction on before any text reaches a "
            "model, and log what was scrubbed."
        ),
        pattern="prompt_chaining",
        tools=["read_columns"],
        rbac_scope="document text only; redaction enforced",
        evals=["no_pii_in_output", "length_within_budget"],
        status=AVAILABLE,
    ),
]

TEMPLATES_BY_ID: dict[str, AgentTemplate] = {t.id: t for t in TEMPLATES}

# Which template each live pipeline agent realizes. Single source of truth for
# the coverage metric; the agent classes carry a matching `template` attribute
# (asserted in tests to stay in sync).
AGENT_LINEAGE: dict[str, str] = {
    "profiler": "data_analysis",
    "eda": "data_analysis",
    "modeler": "modeling",
    "validator": "validation",
}

# Illustrative, labeled as such in the UI: rough hours a builder saves by starting
# from a governed template instead of wiring the harness from scratch.
_HOURS_SAVED_PER_REUSE = 6


def all_templates() -> list[AgentTemplate]:
    return list(TEMPLATES)


def get_template(template_id: str) -> AgentTemplate | None:
    return TEMPLATES_BY_ID.get(template_id)


def reuse_metrics() -> dict[str, float | int]:
    """Coverage of the live agents by templates, plus an illustrative saving."""
    agents_total = len(AGENT_LINEAGE)
    agents_covered = sum(1 for t in AGENT_LINEAGE.values() if t in TEMPLATES_BY_ID)
    return {
        "templates_total": len(TEMPLATES),
        "templates_live": sum(1 for t in TEMPLATES if t.status == LIVE),
        "agents_total": agents_total,
        "agents_covered": agents_covered,
        "coverage_rate": round(agents_covered / agents_total, 3) if agents_total else 0.0,
        "est_hours_saved": agents_covered * _HOURS_SAVED_PER_REUSE,
    }
