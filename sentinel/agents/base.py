"""Agent base class and the shared dependency bundle.

Every agent action funnels through the harness: RBAC on column reads,
guardrails on tool calls, PII redaction before narration, audit events, and
cost accounting. Agents never touch data or tools except through these.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..gateway.model_gateway import Generation, ModelGateway
from ..harness.audit import AuditLog
from ..harness.cost import CostTracker
from ..harness.guardrails import Guardrails
from ..harness.pii import redact
from ..harness.rbac import RBAC
from ..ml.data import Dataset


@dataclass
class AgentDeps:
    dataset: Dataset
    audit: AuditLog
    rbac: RBAC
    guardrails: Guardrails
    gateway: ModelGateway
    cost: CostTracker


class Agent:
    id: str = "base"
    title: str = "Agent"

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps

    # -- harness-mediated helpers --------------------------------------

    def read_columns(self, columns: list[str]) -> list[str]:
        """Read columns through guardrails + RBAC; returns permitted subset."""
        return self.deps.guardrails.call(
            self.id, "read_columns", self.deps.rbac.enforce, self.id, columns
        )

    def use_tool(self, tool: str, fn: Callable[..., Any], *args: Any, **kw: Any) -> Any:
        return self.deps.guardrails.call(self.id, tool, fn, *args, **kw)

    def redact_text(self, text: str) -> str:
        """Scrub PII before any text would reach an LLM. Logs if it fires."""
        return redact(text, self.id, self.deps.audit)

    def narrate(self, step: str, context: dict[str, Any]) -> Generation:
        gen = self.deps.gateway.narrate(step, context)
        self.deps.cost.add_usage(gen.tokens, gen.cost_usd)
        return gen

    def log(self, action: str, **kw: Any):
        return self.deps.audit.record(self.id, action, **kw)

    def run(self, state) -> None:  # noqa: ANN001 - RunState (avoids import cycle)
        raise NotImplementedError
