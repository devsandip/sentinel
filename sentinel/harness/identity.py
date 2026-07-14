"""Identity and personas (ideas.md item 9).

No real authentication: the UI selects a persona to demonstrate role-aware
governance. Personas carry capabilities (can_run, can_approve,
can_toggle_controls, read_only) loaded from config/personas.yaml. The point is
least privilege and segregation of duties: promotion authority at the human gate
belongs only to the MRM Approver (and Admin), the Auditor is read-only, and only
the Admin may toggle a control off in demo mode.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import load_personas


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    role: str
    can_run: bool
    can_approve: bool
    can_toggle_controls: bool
    read_only: bool
    description: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.role})"


def policy_version() -> str:
    return str(load_personas().get("policy_version", "unversioned"))


def all_personas() -> list[Persona]:
    return [
        Persona(
            id=p["id"],
            name=p["name"],
            role=p["role"],
            can_run=bool(p.get("can_run", False)),
            can_approve=bool(p.get("can_approve", False)),
            can_toggle_controls=bool(p.get("can_toggle_controls", False)),
            read_only=bool(p.get("read_only", False)),
            description=str(p.get("description", "")).strip(),
        )
        for p in load_personas()["personas"]
    ]


def get_persona(persona_id: str) -> Persona | None:
    for p in all_personas():
        if p.id == persona_id:
            return p
    return None


def default_persona() -> Persona:
    """The first-line persona: the first that can run (the Analyst)."""
    for p in all_personas():
        if p.can_run and not p.read_only:
            return p
    return all_personas()[0]


def ui_start_persona() -> Persona:
    """The persona the public UI starts on.

    A first-time visitor starts on an approver-capable role so a naive
    Run -> Approve completes end to end and reaches the model card, instead of
    dead-ending at the segregation-of-duties denial. The four-eyes control is
    still demonstrable: switch to the Data Scientist / Analyst and try to
    approve, and the denial fires and is logged.
    """
    for p in all_personas():
        if p.can_run and p.can_approve and not p.read_only:
            return p
    return default_persona()
