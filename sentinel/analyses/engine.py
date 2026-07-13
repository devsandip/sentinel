"""Analysis engine: a governed interpreter for linear analysis specs.

Given an AnalysisSpec and a dataset, the engine (1) checks the dataset satisfies
the analysis's data contract, then (2) runs each step through the same harness
the credit-risk pipeline uses: the guardrail allow-list scopes every tool call,
RBAC filters restricted columns, the audit log records every step, cost is
tracked, and each step is an OpenTelemetry span. The contract check and the
per-step guardrail are governance controls, so an analysis cannot run on a
dataset it does not fit, and a step cannot call a tool it is not scoped for.

This engine runs ENGINE_LINEAR specs (read-only, non-promoting). The credit-risk
spec (with its human-approval gate and model promotion) is executed by the
LangGraph Orchestrator instead; the engine refuses it on purpose.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ..datasets import available, get_dataset, load_frame, load_tables
from ..datasets.registry import DatasetSpec
from ..harness.audit import LEVEL_BLOCKED, LEVEL_INFO, AuditLog
from ..harness.controls import ALL_ENABLED, ControlSettings
from ..harness.cost import CostTracker
from ..harness.guardrails import Guardrails, ToolNotAllowed
from ..harness.identity import Persona, policy_version
from ..harness.rbac import RBAC
from ..harness.tracing import span, spans_for
from .spec import ENGINE_LINEAR, AnalysisSpec, StepRun, StepSpec
from .tools import build_entity_features, leakage_scan, profile_frame, run_quality_checks

STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"


@dataclass
class _Ctx:
    """Mutable blackboard threaded through a run's steps."""

    spec: AnalysisSpec
    dataset_spec: DatasetSpec
    params: dict[str, Any]
    audit: AuditLog
    guardrails: Guardrails
    rbac: RBAC
    controls: ControlSettings
    frame: Any = None
    tables: Any = None
    roles: dict[str, list[str]] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)

    def p(self, name: str) -> Any:
        return self.params[name]

    def role_first(self, role: str) -> str | None:
        cols = self.roles.get(role, [])
        return cols[0] if cols else None


# -- step handlers (tool name -> callable) ---------------------------------
# Each returns a short human summary derived from the real output.


def _read_columns(ctx: _Ctx, agent: str, columns: list[str]) -> list[str]:
    """Exercise the guardrail (read_columns) + RBAC (restricted-column filter)."""
    return ctx.guardrails.call(agent, "read_columns", ctx.rbac.enforce, agent, columns)


def _h_load(ctx: _Ctx, step: StepSpec) -> str:
    ds = ctx.dataset_spec
    if ctx.tables is not None or _is_relational(ds):
        ctx.tables = load_tables(ds.id)
        rows = sum(len(t) for t in ctx.tables.values())
        summary = f"loaded {len(ctx.tables)} tables, {rows:,} rows from '{ds.id}'"
    else:
        ctx.frame = load_frame(ds.id)
        summary = f"loaded '{ds.id}': {len(ctx.frame):,} rows x {ctx.frame.shape[1]} cols"
    flagged = "" if ds.commercial_ok else "; commercial-use FLAGGED by license"
    ctx.audit.record(
        agent=step.agent,
        action="data_access",
        data_touched=[ds.id],
        inputs_summary=f"license={ds.license}; commercial_ok={ds.commercial_ok}",
        output_summary=summary + flagged,
    )
    return summary + flagged


def _h_profile(ctx: _Ctx, step: StepSpec) -> str:
    permitted = _read_columns(ctx, step.agent, list(ctx.frame.columns))
    df = ctx.frame[permitted]
    res = profile_frame(
        df,
        max_cardinality=ctx.p("max_cardinality"),
        sample_rows=ctx.p("sample_rows"),
        target=ctx.role_first("target"),
    )
    ctx.results["profile"] = res
    return res.headline


def _h_quality(ctx: _Ctx, step: StepSpec) -> str:
    permitted = _read_columns(ctx, step.agent, list(ctx.frame.columns))
    df = ctx.frame[permitted]
    res = run_quality_checks(
        df,
        missing_threshold=ctx.p("missing_threshold"),
        outlier_z=ctx.p("outlier_z"),
        key_columns=ctx.roles.get("entity_id", []),
        target=ctx.role_first("target"),
    )
    ctx.results["quality"] = res
    return res.headline


def _h_features(ctx: _Ctx, step: StepSpec) -> str:
    res = build_entity_features(
        ctx.tables,
        window_days=ctx.p("window_days"),
        include_rfm=ctx.p("include_rfm"),
        top_k=ctx.p("top_k"),
    )
    ctx.results["features"] = res
    ctx.frame = res.frame  # hand the feature frame to the leakage-scan step
    return res.headline


def _h_leakage(ctx: _Ctx, step: StepSpec) -> str:
    res = ctx.results["features"]
    rep = leakage_scan(
        res.frame,
        res.feature_names,
        res.target,
        corr_threshold=ctx.p("corr_threshold"),
    )
    ctx.results["leakage"] = rep
    return rep.headline


_HANDLERS = {
    "load_dataset_frames": _h_load,
    "profile_dataset": _h_profile,
    "run_quality_checks": _h_quality,
    "build_entity_features": _h_features,
    "leakage_scan": _h_leakage,
}


def _is_relational(ds: DatasetSpec) -> bool:
    from ..datasets.contracts import CAP_RELATIONAL

    return CAP_RELATIONAL in ds.provides


@dataclass
class AnalysisRun:
    run_id: str
    analysis_id: str
    analysis_name: str
    dataset_id: str
    params: dict[str, Any]
    status: str
    steps: list[StepRun]
    contract: dict[str, Any]
    results: dict[str, Any]
    audit: list[dict[str, Any]]
    cost: dict[str, Any]
    traces: list[dict[str, Any]]
    controls_disabled: list[str]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "analysis_id": self.analysis_id,
            "analysis_name": self.analysis_name,
            "dataset_id": self.dataset_id,
            "params": self.params,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "contract": self.contract,
            "results": self.results,
            "audit": self.audit,
            "cost": self.cost,
            "traces": self.traces,
            "controls_disabled": self.controls_disabled,
        }


class AnalysisEngine:
    """Runs a linear analysis spec against a dataset, under the harness."""

    def run(
        self,
        spec: AnalysisSpec,
        dataset_id: str,
        params: dict[str, Any] | None = None,
        *,
        controls: ControlSettings = ALL_ENABLED,
        actor: Persona | None = None,
    ) -> AnalysisRun:
        if spec.engine != ENGINE_LINEAR:
            raise ValueError(
                f"engine '{spec.engine}' is not run by AnalysisEngine "
                f"(the credit-risk graph runs in the Orchestrator)"
            )
        run_id = uuid.uuid4().hex[:12]
        resolved = spec.resolve_params(params)  # raises ParamError on bad input
        ds = get_dataset(dataset_id)

        audit = AuditLog(run_id=run_id, policy_version=policy_version())
        cost = CostTracker(narration_mode="templated")
        guardrails = Guardrails(audit, controls=controls)
        rbac = RBAC(audit, controls=controls)
        cost.start()

        audit.record(
            agent="analysis_engine",
            action="run_started",
            inputs_summary=f"analysis={spec.id}; dataset={dataset_id}",
            output_summary=f"params={resolved}",
            actor=actor.id if actor else "analysis_engine",
        )

        provides = set(ds.provides) if ds else set()
        rows = ds.rows if ds else 0
        ok, reasons = spec.contract().satisfied_by(provides, rows)
        onboarded = ds is not None and available(dataset_id)
        if not onboarded and ds is not None:
            ok = False
            reasons = reasons + [f"'{dataset_id}' is registered but not onboarded"]
        contract_info = {
            "ok": ok,
            "reasons": reasons,
            "requires": sorted(spec.requires),
            "provides": sorted(provides),
            "min_rows": spec.min_rows,
            "rows": rows,
        }
        audit.record(
            agent="analysis_engine",
            action="contract_check",
            level=LEVEL_INFO if ok else LEVEL_BLOCKED,
            output_summary=(
                "contract satisfied"
                if ok
                else "contract violation: " + "; ".join(reasons)
            ),
        )

        steps_run: list[StepRun] = []
        if not ok or ds is None:
            cost.stop()
            audit.record(
                agent="analysis_engine",
                action="run_ended",
                level=LEVEL_BLOCKED,
                output_summary="blocked before execution: contract not satisfied",
            )
            return self._assemble(
                run_id, spec, dataset_id, resolved, STATUS_BLOCKED,
                steps_run, contract_info, {}, audit, cost, controls,
            )

        ctx = _Ctx(
            spec=spec,
            dataset_spec=ds,
            params=resolved,
            audit=audit,
            guardrails=guardrails,
            rbac=rbac,
            controls=controls,
            roles=_invert_roles(ds),
        )
        if _is_relational(ds):
            ctx.tables = {}  # signal to _h_load to use the relational path

        status = STATUS_COMPLETED
        for step in spec.steps:
            audit.record(
                agent=step.agent, action="agent_started", output_summary=step.title
            )
            with span(f"analysis.{step.id}", run_id, **{"analysis.tool": step.tool}):
                try:
                    handler = _HANDLERS[step.tool]
                    summary = guardrails.call(step.agent, step.tool, handler, ctx, step)
                    step_status = "ok"
                except ToolNotAllowed as exc:
                    step_status, summary = "blocked", str(exc)
                except Exception as exc:  # noqa: BLE001 - surface as an audited failure
                    step_status, summary = "error", f"{type(exc).__name__}: {exc}"
            audit.record(
                agent=step.agent,
                action="agent_finished",
                level=LEVEL_INFO if step_status == "ok" else LEVEL_BLOCKED,
                output_summary=summary,
            )
            steps_run.append(
                StepRun(
                    id=step.id,
                    title=step.title,
                    agent=step.agent,
                    tool=step.tool,
                    status=step_status,
                    summary=summary,
                    produced=list(step.produces),
                )
            )
            if step_status != "ok":
                status = STATUS_BLOCKED
                break

        cost.stop()
        audit.record(
            agent="analysis_engine",
            action="run_ended",
            output_summary=f"status={status}; steps={len(steps_run)}",
        )
        public_results = {k: v.to_dict() for k, v in ctx.results.items()}
        return self._assemble(
            run_id, spec, dataset_id, resolved, status,
            steps_run, contract_info, public_results, audit, cost, controls,
        )

    @staticmethod
    def _assemble(  # noqa: PLR0913
        run_id, spec, dataset_id, params, status, steps, contract_info,
        results, audit, cost, controls,
    ) -> AnalysisRun:
        return AnalysisRun(
            run_id=run_id,
            analysis_id=spec.id,
            analysis_name=spec.name,
            dataset_id=dataset_id,
            params=params,
            status=status,
            steps=steps,
            contract=contract_info,
            results=results,
            audit=audit.as_dicts(),
            cost=cost.snapshot(),
            traces=spans_for(run_id),
            controls_disabled=controls.disabled_names(),
        )


def _invert_roles(ds: DatasetSpec) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for col, role in ds.column_roles.items():
        out.setdefault(role, []).append(col)
    return out
