"""Sentinel platform assets: the central repository of reusable governance assets.

This package is the "central platform assets" ideas.md asks for: AI Playbooks,
reusable agent templates, and the agentic architecture pattern catalog. Packaged
with the app, rendered in the Platform surface, and downloadable as a pack.

  patterns   - the agentic architecture pattern catalog (item 12)
  playbooks  - opinionated end-to-end use-case guides (item 10)
  templates  - parameterized starter agents with the harness pre-wired (item 11)
"""

from __future__ import annotations

from .patterns import PATTERNS, Pattern, all_patterns, get_pattern
from .playbooks import Playbook, get_playbook, load_playbooks

__all__ = [
    "PATTERNS",
    "Pattern",
    "all_patterns",
    "get_pattern",
    "Playbook",
    "load_playbooks",
    "get_playbook",
]
