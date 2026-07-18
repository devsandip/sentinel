"""Identity and personas (ideas.md item 9).

No real authentication: the UI selects a persona to demonstrate role-aware
governance. Personas carry capabilities (can_run, can_approve,
can_toggle_controls, read_only) loaded from config/personas.yaml. The point is
least privilege and segregation of duties: run authority and promotion authority
are held by disjoint personas, so an approver is never the author of the run it
signs off. Promotion authority at the human gate belongs only to the MRM
Approver, the second line never runs, the Auditor is read-only, and only the
Admin may toggle a control off in demo mode.
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
    # Autonomy tier inputs (governed-codegen 4.6). tier_role maps the display
    # persona to a resolution role (data_scientist, model_validator, ...) and
    # attestations are the credentials that lift a data scientist above L1.
    tier_role: str = ""
    attestations: tuple[str, ...] = ()

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
            tier_role=str(p.get("tier_role", "")),
            attestations=tuple(p.get("attestations", []) or []),
        )
        for p in load_personas()["personas"]
    ]


def get_persona(persona_id: str) -> Persona | None:
    for p in all_personas():
        if p.id == persona_id:
            return p
    return None


def default_persona() -> Persona:
    """The persona the UI starts on: the first that can run (the Analyst)."""
    for p in all_personas():
        if p.can_run and not p.read_only:
            return p
    return all_personas()[0]
