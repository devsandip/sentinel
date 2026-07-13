"""Orchestrator: a LangGraph workflow over the agent pipeline.

Profiler -> EDA -> Modeler, then an interrupt for human approval, then either
Validator -> finalize or a rejection. The graph is statically defined (fixed
nodes and edges), so it stays a workflow, not an autonomous agent: an examiner
can read the path. LangGraph gives us three things a bespoke state machine did
not: a named framework, an `interrupt()` primitive that is exactly the human
gate, and a checkpointer that persists state across the pause.

Design note: the heavy RunState (with its live harness handles) lives in the
Orchestrator's run store, keyed by run_id. The LangGraph state carries only the
run_id and the approval decision, so the checkpointer never has to serialize a
file handle. Nodes look the RunState up and mutate it in place; the graph owns
sequencing and the gate, the agents own the work.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

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


class GraphState(TypedDict):
    """LangGraph's own state: intentionally tiny and serializable.

    The RunState (with live harness handles) is kept out of here so the
    checkpointer never has to serialize a file handle.
    """

    run_id: str
    approved: bool | None


class Orchestrator:
    """Owns the run store and a compiled LangGraph workflow over the pipeline."""

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    # -- lookups -------------------------------------------------------

    def questions(self) -> list[dict[str, Any]]:
        return load_questions()["questions"]

    def get_run(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    # -- graph definition ----------------------------------------------

    def _build_graph(self):
        builder = StateGraph(GraphState)
        builder.add_node("profiler", self._profiler_node)
        builder.add_node("eda", self._eda_node)
        builder.add_node("modeler", self._modeler_node)
        builder.add_node("approval", self._approval_node)
        builder.add_node("validator", self._validator_node)
        builder.add_node("rejected", self._rejected_node)

        builder.add_edge(START, "profiler")
        builder.add_edge("profiler", "eda")
        builder.add_edge("eda", "modeler")
        builder.add_edge("modeler", "approval")
        builder.add_conditional_edges(
            "approval",
            self._route_after_approval,
            {"approved": "validator", "rejected": "rejected"},
        )
        builder.add_edge("validator", END)
        builder.add_edge("rejected", END)
        return builder.compile(checkpointer=self._checkpointer)

    def graph_dot(self) -> str:
        """DOT of the actual compiled graph, for the UI. The gate and terminal
        nodes are highlighted; conditional edges (the approve/reject branch) are
        dashed. Generated from the real graph so it cannot drift from the code.
        """
        g = self._graph.get_graph()
        label = {"__start__": "START", "__end__": "END"}
        styles = {
            "approval": 'label="human gate\\n(interrupt)", fillcolor="#fdeceb", color="#b3261e"',
            "validator": 'fillcolor="#e3f4e9", color="#1b7f3b"',
            "rejected": 'fillcolor="#fdeceb", color="#b3261e"',
            "__start__": 'shape=circle, fillcolor="#ffffff"',
            "__end__": 'shape=doublecircle, fillcolor="#ffffff"',
        }
        lines = [
            "digraph pipeline {",
            "  rankdir=LR;",
            '  node [shape=box, style="rounded,filled", fontname="Helvetica", '
            'fillcolor="#eef2fb", color="#1e50a0"];',
        ]
        for n in g.nodes:
            attrs = styles.get(n, "")
            lbl = label.get(n)
            parts = [p for p in (f'label="{lbl}"' if lbl else "", attrs) if p]
            suffix = f" [{', '.join(parts)}]" if parts else ""
            lines.append(f'  "{n}"{suffix};')
        for e in g.edges:
            dashed = " [style=dashed]" if getattr(e, "conditional", False) else ""
            lines.append(f'  "{e.source}" -> "{e.target}"{dashed};')
        lines.append("}")
        return "\n".join(lines)

    # -- graph nodes (sequencing only; agents own the work) ------------

    def _profiler_node(self, state: GraphState) -> dict:
        rs = self._runs[state["run_id"]]
        ProfilerAgent(rs.deps).run(rs)
        return {}

    def _eda_node(self, state: GraphState) -> dict:
        rs = self._runs[state["run_id"]]
        EDAAgent(rs.deps).run(rs)
        return {}

    def _modeler_node(self, state: GraphState) -> dict:
        rs = self._runs[state["run_id"]]
        ModelerAgent(rs.deps).run(rs)  # sets status -> awaiting_approval
        return {}

    def _approval_node(self, state: GraphState) -> dict:
        """The human gate. interrupt() pauses here until approve() resumes."""
        rs = self._runs[state["run_id"]]
        decision = interrupt({"gate": "human_approval", "run_id": rs.run_id})
        approved = bool(decision)
        rs.deps.cost.record_decision(approved)
        rs.deps.audit.record(
            agent="human_reviewer",
            action="approval_decision",
            level="gate",
            output_summary=("APPROVED" if approved else "REJECTED") + " at model gate",
        )
        return {"approved": approved}

    def _route_after_approval(self, state: GraphState) -> str:
        return "approved" if state["approved"] else "rejected"

    def _validator_node(self, state: GraphState) -> dict:
        rs = self._runs[state["run_id"]]
        deps = rs.deps
        for step in rs.steps:
            if step.status == STATUS_AWAITING:
                step.status = "approved"

        ValidatorAgent(deps).run(rs)
        eval_report = rs.shared["eval_report"]
        rs.status = STATUS_COMPLETED if eval_report.promoted else STATUS_BLOCKED

        # Final summary narration through the gateway.
        result = rs.shared["model_result"]
        fairness = rs.shared["fairness"]
        summary = deps.gateway.narrate(
            "summary",
            {
                "auc": result.metrics["auc"],
                "fairness_verdict": (
                    "within tolerance" if fairness.passes else "FLAGGED for review"
                ),
                "promotion_state": ("allowed" if eval_report.promoted else "BLOCKED"),
            },
        )
        deps.cost.add_usage(summary.tokens, summary.cost_usd)
        rs.shared["summary_narration"] = summary.text

        deps.cost.stop()
        deps.audit.record(
            agent="orchestrator",
            action="run_ended",
            output_summary=(
                f"status={rs.status}; "
                f"promotion={'allowed' if eval_report.promoted else 'blocked'}"
            ),
        )
        return {}

    def _rejected_node(self, state: GraphState) -> dict:
        rs = self._runs[state["run_id"]]
        for step in rs.steps:
            if step.status == STATUS_AWAITING:
                step.status = "rejected"
        rs.status = STATUS_REJECTED
        rs.deps.cost.stop()
        rs.deps.audit.record(
            agent="orchestrator",
            action="run_ended",
            output_summary="Run stopped by human rejection; no promotion.",
        )
        return {}

    # -- public API (unchanged surface) --------------------------------

    def _config(self, run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

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

        # Runs profiler -> eda -> modeler, then pauses at the approval interrupt.
        self._graph.invoke(
            {"run_id": run_id, "approved": None}, self._config(run_id)
        )
        return state

    def approve(self, run_id: str, approved: bool) -> RunState:
        state = self._runs[run_id]
        assert state.deps is not None
        # Resume the graph from the approval interrupt with the human decision.
        self._graph.invoke(Command(resume=approved), self._config(run_id))
        return state

    # -- helpers -------------------------------------------------------

    def _resolve_question(self, question_id: str) -> dict[str, Any]:
        for q in load_questions()["questions"]:
            if q["id"] == question_id:
                return q
        raise ValueError(f"unknown question id: {question_id}")
