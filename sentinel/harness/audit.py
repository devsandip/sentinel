"""Append-only audit log.

Every agent action, RBAC denial, PII redaction, and gate decision flows
through here. Events are immutable: once recorded they are never mutated,
only appended. Kept in memory for the UI and mirrored to a per-run JSONL file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parents[2] / "runtime" / "audit"

# Event levels drive UI treatment (a "blocked" or "redaction" event is styled
# differently from routine "info").
LEVEL_INFO = "info"
LEVEL_BLOCKED = "blocked"
LEVEL_REDACTION = "redaction"
LEVEL_GATE = "gate"


@dataclass(frozen=True)
class AuditEvent:
    run_id: str
    seq: int
    ts: str
    agent: str
    action: str
    level: str
    inputs_summary: str
    data_touched: list[str]
    output_summary: str
    tokens: int
    cost: float
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLog:
    """In-memory + JSONL append-only log for one run."""

    def __init__(self, run_id: str, persist: bool = True, clock=None) -> None:
        self.run_id = run_id
        self._events: list[AuditEvent] = []
        self._persist = persist
        # Injectable clock so tests are deterministic if needed.
        self._clock = clock or (lambda: datetime.now(UTC))
        if persist:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            self._path = RUNTIME_DIR / f"{run_id}.jsonl"
            # Fresh file per run; append-only thereafter.
            self._path.write_text("")

    def record(
        self,
        agent: str,
        action: str,
        *,
        level: str = LEVEL_INFO,
        inputs_summary: str = "",
        data_touched: list[str] | None = None,
        output_summary: str = "",
        tokens: int = 0,
        cost: float = 0.0,
        extra: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            run_id=self.run_id,
            seq=len(self._events),
            ts=self._clock().isoformat(),
            agent=agent,
            action=action,
            level=level,
            inputs_summary=inputs_summary,
            data_touched=list(data_touched or []),
            output_summary=output_summary,
            tokens=tokens,
            cost=round(float(cost), 6),
            extra=dict(extra or {}),
        )
        self._events.append(event)
        if self._persist:
            with open(self._path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        return event

    def events(self) -> list[AuditEvent]:
        # Return a copy so callers cannot mutate internal state.
        return list(self._events)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events]

    def count(self, level: str | None = None) -> int:
        if level is None:
            return len(self._events)
        return sum(1 for e in self._events if e.level == level)
