"""Model and agent registry (ideas.md item 13).

The MRM "model inventory": every trained model is versioned with its metrics,
fairness verdict, and promotion status; every agent is versioned with its
template lineage and tool scope. In this demo the model registry is a
process-level store that accumulates as runs complete, seeded with a few labeled
historical entries so the inventory is not empty. An enterprise deployment would
persist to the bank's model-inventory system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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


# Process-level model inventory, seeded with labeled history.
_MODEL_REGISTRY: list[ModelVersion] = [
    ModelVersion(
        version="credit-lr-000001",
        question_id="build_model",
        auc=0.78,
        disparity_ratio=0.57,
        fairness_pass=False,
        status=STATUS_PROMOTED,
        created_at="2026-07-06T10:14:00+00:00",
        seeded=True,
    ),
    ModelVersion(
        version="credit-lr-000002",
        question_id="fairness_age",
        auc=0.71,
        disparity_ratio=0.52,
        fairness_pass=False,
        status=STATUS_BLOCKED,
        created_at="2026-07-09T15:40:00+00:00",
        seeded=True,
    ),
]


def register_model(
    run_id: str,
    question_id: str,
    auc: float | None,
    disparity_ratio: float | None,
    fairness_pass: bool | None,
    status: str,
    ungoverned: bool = False,
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
    )
    _MODEL_REGISTRY.append(entry)
    return entry


def model_versions() -> list[ModelVersion]:
    """Newest first."""
    return list(reversed(_MODEL_REGISTRY))


@dataclass
class AgentVersion:
    agent_id: str
    template: str
    version: str
    tools: list[str]
    rbac_scope: str
    eval_status: str

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "template": self.template,
            "version": self.version,
            "tools": ", ".join(self.tools),
            "rbac_scope": self.rbac_scope,
            "eval_status": self.eval_status,
        }


def agent_registry() -> list[AgentVersion]:
    """The live agents, versioned, with their template lineage and tool scope."""
    out = []
    for agent_id, template_id in AGENT_LINEAGE.items():
        t = get_template(template_id)
        out.append(
            AgentVersion(
                agent_id=agent_id,
                template=template_id,
                version="v1",
                tools=t.tools if t else [],
                rbac_scope=t.rbac_scope if t else "",
                eval_status="passing",
            )
        )
    return out
