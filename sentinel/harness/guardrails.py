"""Tool allow-list guardrails.

Agents may only invoke tools on their allow-list (from agents.yaml). Any
other tool call is blocked and logged. This is the sandbox boundary: the
demo executes no arbitrary code, only these named, whitelisted tools.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..config import load_agents
from .audit import LEVEL_BLOCKED, AuditLog
from .controls import ALL_ENABLED, CONTROL_GUARDRAILS, ControlSettings


class ToolNotAllowed(Exception):
    pass


class Guardrails:
    def __init__(
        self,
        audit: AuditLog,
        registry: dict | None = None,
        controls: ControlSettings = ALL_ENABLED,
    ) -> None:
        self._audit = audit
        self._controls = controls
        agents = (registry or load_agents())["agents"]
        self._allowed: dict[str, set[str]] = {
            a["id"]: set(a.get("tools", [])) for a in agents
        }

    def is_allowed(self, agent: str, tool: str) -> bool:
        return tool in self._allowed.get(agent, set())

    def call(
        self, agent: str, tool: str, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        # If guardrails are disabled for the run (demo toggle), skip the
        # allow-list check. The disabling itself is audited at run start.
        if not self._controls.is_enabled(CONTROL_GUARDRAILS):
            return fn(*args, **kwargs)
        if not self.is_allowed(agent, tool):
            self._audit.record(
                agent=agent,
                action="tool_blocked",
                level=LEVEL_BLOCKED,
                inputs_summary=f"attempted tool '{tool}'",
                output_summary=f"Tool '{tool}' not on allow-list for {agent}",
                extra={"allowed_tools": sorted(self._allowed.get(agent, set()))},
            )
            raise ToolNotAllowed(f"{agent} may not call {tool}")
        return fn(*args, **kwargs)
