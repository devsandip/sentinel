"""Agent runtime (ideas.md item 4).

A thin runtime that owns agent lifecycle: it instantiates an agent with its
scoped dependencies, records lifecycle events (with the tool scope and RBAC scope
in effect), runs it, and records completion. It is the single inspectable
boundary for "what an agent is allowed to be and do."

Honest scoping: this is capability scoping (data + tools) enforced by RBAC and
the guardrail allow-list, recorded to audit. It is not process isolation. The
enterprise version maps to a managed runtime (Bedrock AgentCore, Vertex Agent
Engine, Azure AI Foundry) that adds real process and network isolation. The
platform payoff is that every agent instantiated through the runtime inherits a
least-privilege sandbox by default instead of god-mode.
"""

from __future__ import annotations

from ..harness.tracing import span
from ..platform.templates import get_template
from .base import Agent, AgentDeps


class AgentRuntime:
    """Instantiates agents and records their lifecycle to the audit trail."""

    def run(self, agent_cls: type[Agent], deps: AgentDeps, state) -> Agent:  # noqa: ANN001
        agent = agent_cls(deps)
        template = get_template(agent.template) if agent.template else None
        scope = ""
        if template:
            scope = (
                f" template={agent.template}; tools=[{', '.join(template.tools)}]; "
                f"rbac={template.rbac_scope}"
            )
        deps.audit.record(
            agent=agent.id,
            action="agent_started",
            output_summary=f"runtime instantiated {agent.title};{scope}",
        )
        with span(
            f"agent.{agent.id}",
            state.run_id,
            **{"agent.template": agent.template or "none"},
        ):
            agent.run(state)
        deps.audit.record(
            agent=agent.id,
            action="agent_finished",
            output_summary=f"{agent.title} lifecycle complete",
        )
        return agent
