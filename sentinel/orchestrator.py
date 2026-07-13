"""Orchestrator: sequences the agent graph and manages the approval pause.

Plain Python state machine (no LangGraph): Profiler -> EDA -> Modeler, then
PAUSE for human approval, then Validator -> finalize. Every step emits audit
events through the shared harness, so the flow is fully inspectable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .agents.base import AgentDeps
from .agents.eda import EDAAgent
from .agents.modeler import ModelerAgent
from .agents.profiler import ProfilerAgent
from .agents.validator import ValidatorAgent
from .config import load_questions
from .gateway.model_gateway import ANTHROPIC, TEMPLATED, ModelGateway
from .harness.audit import AuditLog
from .harness.cost import CostTracker
from .harness.guardrails import Guardrails
from .harness.rbac import RBAC
from .ml.data import load_dataset

# The governance controls advertised in the header badge.
GOVERNANCE_CONTROLS = ["PII", "RBAC", "Audit", "Human Gate", "Eval Gate"]

STATUS_RUNNING = "running"
STATUS_AWAITING = "awaiting_approval"
STATUS_COMPLETED = "completed"
STATUS_REJECTED = "rejected"
STATUS_BLOCKED = "blocked"


@dataclass
class StepRecord:
    agent: str
    title: str
    status: str
    narration: str
    live: bool
    fell_back: bool
    fallback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "title": self.title,
            "status": self.status,
            "narration": self.narration,
            "live": self.live,
            "fell_back": self.fell_back,
            "fallback_reason": self.fallback_reason,
        }


@dataclass
class RunState:
    run_id: str
    question_id: str
    question_label: str
    dataset_id: str
    protected_attribute: str
    narration_mode: str  # "scripted" | "live"
    seed: int
    status: str = STATUS_RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    shared: dict[str, Any] = field(default_factory=dict)
    # Harness handles (not serialized).
    deps: AgentDeps | None = field(default=None, repr=False)

    def add_step(self, agent, status: str, generation) -> None:  # noqa: ANN001
        self.steps.append(
            StepRecord(
                agent=agent.id,
                title=agent.title,
                status=status,
                narration=generation.text,
                live=generation.live,
                fell_back=generation.fell_back,
                fallback_reason=generation.fallback_reason,
            )
        )

    @property
    def narration_is_live(self) -> bool:
        return any(s.live for s in self.steps)

    def to_public_dict(self) -> dict[str, Any]:
        payload = self.shared.get("payload", {})
        audit = self.deps.audit if self.deps else None
        cost = self.deps.cost if self.deps else None
        # Model metrics exist as soon as the Modeler runs (pre-approval); the
        # assembled payload (fairness, card, evals) only exists post-approval.
        model = payload.get("model")
        if model is None and "model_result" in self.shared:
            model = self.shared["model_result"].to_dict()
        return {
            "run_id": self.run_id,
            "question": {"id": self.question_id, "label": self.question_label},
            "dataset": self.dataset_id,
            "protected_attribute": self.protected_attribute,
            "narration_mode": self.narration_mode,
            "narration_label": (
                "live LLM reasoning"
                if self.narration_is_live
                else "scripted narration over a live analysis"
            ),
            "status": self.status,
            "governance_controls": GOVERNANCE_CONTROLS,
            "steps": [s.to_dict() for s in self.steps],
            "model": model,
            "summary_narration": self.shared.get("summary_narration"),
            "fairness": payload.get("fairness"),
            "model_card": payload.get("model_card"),
            "evals": payload.get("evals"),
            "audit": audit.as_dicts() if audit else [],
            "cost": cost.snapshot() if cost else {},
        }


def _provider_for(mode: str) -> str:
    return ANTHROPIC if mode == "live" else TEMPLATED


class Orchestrator:
    """Owns the in-memory run store and drives the state machine."""

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}

    # -- lookups -------------------------------------------------------

    def questions(self) -> list[dict[str, Any]]:
        return load_questions()["questions"]

    def get_run(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    # -- state machine -------------------------------------------------

    def start_run(
        self,
        question_id: str,
        narration_mode: str = "scripted",
        seed: int = 42,
    ) -> RunState:
        question = self._resolve_question(question_id)
        protected = question["protected_attribute"]
        run_id = uuid.uuid4().hex[:12]

        audit = AuditLog(run_id=run_id)
        cost = CostTracker(narration_mode=_provider_for(narration_mode))
        deps = AgentDeps(
            dataset=load_dataset(protected),
            audit=audit,
            rbac=RBAC(audit),
            guardrails=Guardrails(audit),
            gateway=ModelGateway(provider=_provider_for(narration_mode)),
            cost=cost,
        )
        state = RunState(
            run_id=run_id,
            question_id=question_id,
            question_label=question["label"],
            dataset_id=question["dataset"],
            protected_attribute=protected,
            narration_mode=narration_mode,
            seed=seed,
            deps=deps,
        )
        self._runs[run_id] = state

        cost.start()
        audit.record(
            agent="orchestrator",
            action="run_started",
            inputs_summary=f"question={question_id}, mode={narration_mode}",
            output_summary=f"controls active: {', '.join(GOVERNANCE_CONTROLS)}",
        )

        # Pre-approval agents, then pause.
        ProfilerAgent(deps).run(state)
        EDAAgent(deps).run(state)
        ModelerAgent(deps).run(state)  # sets status -> awaiting_approval
        return state

    def approve(self, run_id: str, approved: bool) -> RunState:
        state = self._runs[run_id]
        assert state.deps is not None
        deps = state.deps

        deps.cost.record_decision(approved)
        deps.audit.record(
            agent="human_reviewer",
            action="approval_decision",
            level="gate",
            output_summary=("APPROVED" if approved else "REJECTED") + " at model gate",
        )

        if not approved:
            # Mark the paused Modeler step as rejected.
            for step in state.steps:
                if step.status == STATUS_AWAITING:
                    step.status = "rejected"
            state.status = STATUS_REJECTED
            deps.cost.stop()
            deps.audit.record(
                agent="orchestrator",
                action="run_ended",
                output_summary="Run stopped by human rejection; no promotion.",
            )
            return state

        # Approved: mark the gate step done, run validation, finalize.
        for step in state.steps:
            if step.status == STATUS_AWAITING:
                step.status = "approved"

        ValidatorAgent(deps).run(state)
        eval_report = state.shared["eval_report"]
        state.status = STATUS_COMPLETED if eval_report.promoted else STATUS_BLOCKED

        # Final summary narration through the gateway.
        result = state.shared["model_result"]
        fairness = state.shared["fairness"]
        summary = deps.gateway.narrate(
            "summary",
            {
                "auc": result.metrics["auc"],
                "fairness_verdict": (
                    "within tolerance" if fairness.passes else "FLAGGED for review"
                ),
                "promotion_state": (
                    "allowed" if eval_report.promoted else "BLOCKED"
                ),
            },
        )
        deps.cost.add_usage(summary.tokens, summary.cost_usd)
        state.shared["summary_narration"] = summary.text

        deps.cost.stop()
        deps.audit.record(
            agent="orchestrator",
            action="run_ended",
            output_summary=(
                f"status={state.status}; "
                f"promotion={'allowed' if eval_report.promoted else 'blocked'}"
            ),
        )
        return state

    # -- helpers -------------------------------------------------------

    def _resolve_question(self, question_id: str) -> dict[str, Any]:
        for q in load_questions()["questions"]:
            if q["id"] == question_id:
                return q
        raise ValueError(f"unknown question id: {question_id}")
