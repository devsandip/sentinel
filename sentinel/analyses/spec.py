"""Analysis specifications: an analysis is a declarative spec, not code.

An AnalysisSpec names a data contract, a list of typed parameters a user may
edit, and an ordered list of governed steps. The engine (engine.py) interprets
the spec: it checks the contract against the chosen dataset, then runs each step
through the same harness the credit-risk pipeline uses (audit, guardrails, RBAC,
cost, tracing). "Applies to any dataset" is really "any dataset that satisfies
the contract", validated before the run.

Two execution engines exist. ENGINE_LINEAR specs are read-only, non-promoting
analyses (profiling, feature engineering) the AnalysisEngine runs top to bottom.
ENGINE_CREDIT_RISK is the model-training pipeline with the human-approval gate;
that one is described here as a spec but executed by the LangGraph Orchestrator,
because it has a promotion decision the linear engine deliberately does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..datasets.contracts import DataContract, contract

ENGINE_LINEAR = "linear"
ENGINE_CREDIT_RISK = "credit_risk_graph"

# Parameter kinds the UI knows how to render and the spec knows how to coerce.
P_INT = "int"
P_FLOAT = "float"
P_BOOL = "bool"
P_CHOICE = "choice"
P_STR = "str"

_KINDS = {P_INT, P_FLOAT, P_BOOL, P_CHOICE, P_STR}


class ParamError(ValueError):
    """A parameter override failed validation (type, bound, or choice)."""


@dataclass(frozen=True)
class ParamSpec:
    """One editable parameter with a type, a default, and validation."""

    name: str
    label: str
    kind: str
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[Any, ...] = ()
    help: str = ""

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(f"unknown param kind {self.kind!r}")
        if self.kind == P_CHOICE and not self.choices:
            raise ValueError(f"choice param {self.name!r} needs choices")

    def coerce(self, value: Any) -> Any:
        """Validate and coerce a user-supplied value, or raise ParamError."""
        if value is None:
            return self.default
        try:
            if self.kind == P_INT:
                v: Any = int(value)
            elif self.kind == P_FLOAT:
                v = float(value)
            elif self.kind == P_BOOL:
                v = bool(value)
            elif self.kind == P_CHOICE:
                v = value
            else:
                v = str(value)
        except (TypeError, ValueError) as exc:
            raise ParamError(f"{self.name}: cannot parse {value!r} as {self.kind}") from exc

        if self.kind in (P_INT, P_FLOAT):
            if self.minimum is not None and v < self.minimum:
                raise ParamError(f"{self.name}: {v} below minimum {self.minimum}")
            if self.maximum is not None and v > self.maximum:
                raise ParamError(f"{self.name}: {v} above maximum {self.maximum}")
        if self.kind == P_CHOICE and v not in self.choices:
            raise ParamError(f"{self.name}: {v!r} not in {list(self.choices)}")
        return v

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "default": self.default,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "choices": list(self.choices),
            "help": self.help,
        }


@dataclass(frozen=True)
class StepSpec:
    """One governed step: an agent invoking one whitelisted tool.

    `agent` is the identity the harness scopes (guardrail allow-list + RBAC);
    `tool` is the whitelisted tool name the guardrail checks. `produces` names
    the output keys the step writes into the run's results, so the contract
    between steps is typed and inspectable.
    """

    id: str
    title: str
    agent: str
    tool: str
    description: str
    produces: tuple[str, ...] = ()
    gate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "agent": self.agent,
            "tool": self.tool,
            "description": self.description,
            "produces": list(self.produces),
            "gate": self.gate,
        }


@dataclass(frozen=True)
class AnalysisSpec:
    """A declarative analysis: contract + editable params + governed steps."""

    id: str
    name: str
    description: str
    engine: str
    requires: frozenset[str]  # capabilities the dataset must provide
    min_rows: int = 0
    default_dataset_id: str = ""
    params: tuple[ParamSpec, ...] = ()
    steps: tuple[StepSpec, ...] = ()
    outputs: tuple[str, ...] = ()  # declared result keys the UI renders
    controls: tuple[str, ...] = ("Audit", "RBAC", "Guardrails", "Contract")
    tags: tuple[str, ...] = ()

    def contract(self) -> DataContract:
        return contract(*sorted(self.requires), min_rows=self.min_rows)

    def param(self, name: str) -> ParamSpec | None:
        for p in self.params:
            if p.name == name:
                return p
        return None

    def resolve_params(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Merge user overrides onto defaults, validating each. Unknown keys raise."""
        overrides = dict(overrides or {})
        unknown = set(overrides) - {p.name for p in self.params}
        if unknown:
            raise ParamError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
        return {p.name: p.coerce(overrides.get(p.name)) for p in self.params}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "engine": self.engine,
            "requires": sorted(self.requires),
            "min_rows": self.min_rows,
            "default_dataset_id": self.default_dataset_id,
            "params": [p.to_dict() for p in self.params],
            "steps": [s.to_dict() for s in self.steps],
            "outputs": list(self.outputs),
            "controls": list(self.controls),
            "tags": list(self.tags),
        }


@dataclass
class StepRun:
    """The record of one executed step."""

    id: str
    title: str
    agent: str
    tool: str
    status: str
    summary: str
    produced: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "agent": self.agent,
            "tool": self.tool,
            "status": self.status,
            "summary": self.summary,
            "produced": list(self.produced),
        }
