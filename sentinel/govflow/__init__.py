"""The governed analysis flow: Ask -> Access -> Generate -> Gate -> Execute ->
Screen -> Interpret (docs/features/governed-codegen.md sections 1 and 5).

This is the v1 vertical slice wired end to end. It reuses the codegen gate, the
sandbox, and the disclosure screen built alongside it, and it is what the two
Streamlit screens (Console and Gate) drive. The tier is frozen at L2, the persona
is the first-line analyst, the dataset is german_credit, and the purpose is
fair_lending_review.
"""

from __future__ import annotations

from .flow import GovernedRunResult, StageRecord, run_governed_analysis

__all__ = ["GovernedRunResult", "StageRecord", "run_governed_analysis"]
