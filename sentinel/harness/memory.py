"""Governed memory: short-term working context and long-term precedent (item 6).

Memory is a data-retention control, not a convenience. Two tiers:

- Short-term: the per-run working context (the orchestrator's `shared` dict and
  the LangGraph checkpoint). Ephemeral, discarded when the run ends.
- Long-term: persisted precedent — prior run outcomes that can inform a future
  run ("this question was last run on DATE; fairness FLAGGED"). Retained under a
  records-retention policy.

Each tier is labeled with its retention class so the UI can show what is kept and
for how long.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

RETENTION_EPHEMERAL = "ephemeral — discarded when the run ends"
RETENTION_PRECEDENT = "retained — prior outcomes inform future runs"
RETENTION_AUDIT = "7-year WORM retention (records-retention policy)"


@dataclass
class Precedent:
    question_id: str
    status: str
    disparity_ratio: float | None
    created_at: str
    seeded: bool = False

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "status": self.status,
            "disparity_ratio": self.disparity_ratio,
            "created_at": self.created_at,
            "seeded": self.seeded,
        }


# Long-term precedent store (process-level), seeded with labeled history.
_PRECEDENT: list[Precedent] = [
    Precedent("build_model", "promoted", 0.57, "2026-07-06T10:14:00+00:00", seeded=True),
    Precedent("fairness_age", "blocked", 0.52, "2026-07-09T15:40:00+00:00", seeded=True),
]


def record_precedent(
    question_id: str, status: str, disparity_ratio: float | None
) -> Precedent:
    entry = Precedent(
        question_id=question_id,
        status=status,
        disparity_ratio=disparity_ratio,
        created_at=datetime.now(UTC).isoformat(),
    )
    _PRECEDENT.append(entry)
    return entry


def precedents_for(question_id: str) -> list[Precedent]:
    """Prior outcomes for a question, newest first."""
    return [p for p in reversed(_PRECEDENT) if p.question_id == question_id]


def short_term_context(shared: dict) -> list[str]:
    """The working-context keys held for the current run (ephemeral)."""
    return sorted(shared.keys())
