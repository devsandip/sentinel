"""Model and agent registry (ideas.md item 13).

The MRM "model inventory": every trained model is versioned with its metrics,
fairness verdict, and promotion status; every agent is versioned with its
template lineage and tool scope. In this demo the model registry is a
process-level store that accumulates as runs complete, seeded from the executed
run history in sentinel/data/seed_runs.jsonl (every seed row came from a real
run; see run_history.py). An enterprise deployment would persist to the bank's
model-inventory system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .run_history import credit_risk_runs
from .templates import AGENT_LINEAGE, get_template

STATUS_PROMOTED = "promoted"
STATUS_BLOCKED = "blocked"
STATUS_REJECTED = "rejected"


@dataclass
class ModelVersion:
    version: str
    question_id: str
    auc: float | None
    disparity_ratio: float | None
    fairness_pass: bool | None
    status: str
    created_at: str
    ungoverned: bool = False
    seeded: bool = False
    # The run's model card, kept off to_dict(): the dict feeds the table cells
    # and a whole nested document in there would be carried by every caller
    # that only wants a number. The Registry reads it off the object.
    model_card: dict | None = None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "question_id": self.question_id,
            "auc": self.auc,
            "disparity_ratio": self.disparity_ratio,
            "fairness_pass": self.fairness_pass,
            "status": self.status,
            "created_at": self.created_at,
            "ungoverned": self.ungoverned,
            "seeded": self.seeded,
        }


def _seed_rows() -> list[ModelVersion]:
    """Fold the executed credit_risk seed records into ModelVersion rows."""
    rows: list[ModelVersion] = []
    for r in credit_risk_runs():
        rows.append(
            ModelVersion(
                version=f"credit-lr-{r.run_id[:6]}",
                question_id=r.ref_id,
                auc=r.metrics.get("auc"),
                disparity_ratio=r.metrics.get("disparity_ratio"),
                fairness_pass=r.metrics.get("fairness_pass"),
                status=r.status,
                created_at=r.demo_date,
                seeded=True,
                model_card=r.model_card,
            )
        )
    return rows


# Process-level model inventory, seeded once per process from the run-history
# store; live runs append on top via register_model.
_MODEL_REGISTRY: list[ModelVersion] = _seed_rows()


def register_model(
    run_id: str,
    question_id: str,
    auc: float | None,
    disparity_ratio: float | None,
    fairness_pass: bool | None,
    status: str,
    ungoverned: bool = False,
    model_card: dict | None = None,
) -> ModelVersion:
    entry = ModelVersion(
        version=f"credit-lr-{run_id[:6]}",
        question_id=question_id,
        auc=auc,
        disparity_ratio=disparity_ratio,
        fairness_pass=fairness_pass,
        status=status,
        created_at=datetime.now(UTC).isoformat(),
        ungoverned=ungoverned,
        # Carried so a live row and a seeded row are the same kind of thing.
        # Without it the Registry would show documentation for the models it
        # inherited and none for the ones it watched being made, which is the
        # wrong way round for an inventory.
        model_card=model_card,
    )
    _MODEL_REGISTRY.append(entry)
    return entry


def model_versions() -> list[ModelVersion]:
    """Newest first."""
    return list(reversed(_MODEL_REGISTRY))


@dataclass
class AgentVersion:
    agent_id: str
    title: str
    does: str
    template: str
    version: str
    tools: list[str]
    rbac_scope: str
    eval_status: str

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "title": self.title,
            "does": self.does,
            "template": self.template,
            "version": self.version,
            "tools": ", ".join(self.tools),
            "rbac_scope": self.rbac_scope,
            "eval_status": self.eval_status,
        }


def _agent_classes() -> dict[str, type]:
    """The live pipeline agent classes, keyed by id.

    Imported inside the function so the platform package stays importable
    without pulling in the ML stack; the registry is the only caller that
    needs the classes, and it needs them for `title`/`does` -- reading those
    off the class is what keeps the inventory honest about the running code.
    """
    from ..agents.eda import EDAAgent
    from ..agents.modeler import ModelerAgent
    from ..agents.profiler import ProfilerAgent
    from ..agents.validator import ValidatorAgent

    return {
        cls.id: cls for cls in (ProfilerAgent, EDAAgent, ModelerAgent, ValidatorAgent)
    }


def agent_registry() -> list[AgentVersion]:
    """The live agents, versioned, with what each one does, its template lineage,
    and its tool scope. Order follows the pipeline: profiler, eda, modeler,
    validator."""
    classes = _agent_classes()
    out = []
    for agent_id, template_id in AGENT_LINEAGE.items():
        t = get_template(template_id)
        cls = classes.get(agent_id)
        out.append(
            AgentVersion(
                agent_id=agent_id,
                title=getattr(cls, "title", agent_id),
                does=getattr(cls, "does", ""),
                template=template_id,
                version="v1",
                tools=t.tools if t else [],
                rbac_scope=t.rbac_scope if t else "",
                eval_status="passing",
            )
        )
    return out
