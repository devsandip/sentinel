"""Role-based access control over dataset columns.

Each agent has an allow-list of columns (from rbac.yaml). Requests for
columns outside the allow-list, or for globally restricted columns, are
denied and logged to the audit trail. Returns the permitted subset so the
agent proceeds on what it is allowed to see.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import load_rbac
from .audit import LEVEL_BLOCKED, AuditLog


@dataclass
class AccessDecision:
    agent: str
    requested: list[str]
    allowed: list[str]
    denied: list[str]


class RBAC:
    def __init__(self, audit: AuditLog, policy: dict | None = None) -> None:
        self._audit = audit
        self._policy = policy or load_rbac()
        self._restricted = set(self._policy.get("restricted_columns", []))
        self._agents = self._policy.get("agents", {})

    def _allowed_for(self, agent: str) -> set[str] | None:
        """Return the allow-set, or None meaning 'all non-restricted'."""
        entry = self._agents.get(agent, {})
        allow = entry.get("allow", [])
        if allow == ["*"] or allow == "*":
            return None
        return set(allow)

    def check(self, agent: str, columns: list[str]) -> AccessDecision:
        allow_set = self._allowed_for(agent)
        allowed, denied = [], []
        for col in columns:
            restricted = col in self._restricted
            not_allowed = allow_set is not None and col not in allow_set
            if restricted or not_allowed:
                denied.append(col)
            else:
                allowed.append(col)
        return AccessDecision(agent, list(columns), allowed, denied)

    def enforce(self, agent: str, columns: list[str]) -> list[str]:
        """Log any denials and return the permitted columns."""
        decision = self.check(agent, columns)
        if decision.denied:
            self._audit.record(
                agent=agent,
                action="rbac_access_denied",
                level=LEVEL_BLOCKED,
                inputs_summary=f"requested {len(columns)} columns",
                data_touched=decision.denied,
                output_summary=(
                    f"Denied access to {len(decision.denied)} column(s): "
                    f"{', '.join(decision.denied)}"
                ),
                extra={"allowed_count": len(decision.allowed)},
            )
        return decision.allowed
