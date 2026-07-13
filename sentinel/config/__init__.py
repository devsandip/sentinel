"""Config loaders for the governance harness and agents."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent


def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


@cache
def load_rbac() -> dict[str, Any]:
    return _load("rbac.yaml")


@cache
def load_questions() -> dict[str, Any]:
    return _load("questions.yaml")


@cache
def load_evals() -> dict[str, Any]:
    return _load("evals.yaml")


@cache
def load_agents() -> dict[str, Any]:
    return _load("agents.yaml")
