"""Cost + KPI tracker.

Accumulates tokens and dollar cost (both 0 in templated narration mode),
wall-clock cycle time, eval pass-rate, and human-override count. Feeds the
Cost & KPIs tab. Timing uses an injectable clock so it is testable.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostTracker:
    narration_mode: str = "templated"
    tokens: int = 0
    cost_usd: float = 0.0
    human_overrides: int = 0
    approvals: int = 0
    rejections: int = 0
    eval_pass_rate: float = 0.0
    _clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    _start: float | None = field(default=None, repr=False)
    _elapsed: float = 0.0

    def start(self) -> None:
        self._start = self._clock()

    def stop(self) -> None:
        if self._start is not None:
            self._elapsed = self._clock() - self._start
            self._start = None

    def add_usage(self, tokens: int, cost: float) -> None:
        self.tokens += int(tokens)
        self.cost_usd = round(self.cost_usd + float(cost), 6)

    def record_decision(self, approved: bool) -> None:
        # Any human decision at the gate counts as a human override event.
        self.human_overrides += 1
        if approved:
            self.approvals += 1
        else:
            self.rejections += 1

    def set_eval_pass_rate(self, rate: float) -> None:
        self.eval_pass_rate = round(float(rate), 4)

    @property
    def cycle_time_s(self) -> float:
        if self._start is not None:
            return round(self._clock() - self._start, 3)
        return round(self._elapsed, 3)

    def snapshot(self) -> dict[str, Any]:
        return {
            "narration_mode": self.narration_mode,
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
            "cycle_time_s": self.cycle_time_s,
            "eval_pass_rate": self.eval_pass_rate,
            "human_overrides": self.human_overrides,
            "approvals": self.approvals,
            "rejections": self.rejections,
        }
