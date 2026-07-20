"""The governed analysis flow, wired end to end (sections 1 and 5).

Ask -> Access -> Generate -> Gate -> Execute -> Screen -> Interpret. Each stage
has a control that can refuse and an audit record. The flow stops where a control
stops it: a gate block never reaches Execute, and a suppressed cell never reaches
the narration. The narration is built from the screened numbers only, so it
cannot mention what the Screen removed (section 1.8).

v1 scope: tier frozen at L2, purpose fair_lending_review, dataset german_credit,
first-line analyst persona. Attest (Stage 9) and its evidence pack are later
slices; v1 ends at Interpret.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from ..codegen.gate import GateResult
from ..codegen.generate import (
    CodeGenRequest,
    GenerationOutcome,
    generate_and_gate,
    has_scripted_repair,
)
from ..datasets.fingerprint import FingerprintError, dataset_sha, live_contract_check
from ..disclosure import ScreenResult, screen
from ..evidence import EvidencePack, build_evidence_pack
from ..gateway.model_gateway import TEMPLATED, ModelGateway
from ..harness.audit import LEVEL_BLOCKED, LEVEL_GATE, AuditLog
from ..harness.identity import Persona, default_persona, policy_version
from ..lineage import run_lineage_events
from ..platform.certification import (
    CTL_CONTRACT_01,
    evaluate,
    get_entry,
    plan_visible_entries,
)
from ..sandbox import GOVFLOW_WALL_CLOCK_S, ExecutionResult, run_sandboxed
from .access import (
    DATASET_ID,
    FAIR_LENDING_GRANT,
    FAIR_LENDING_ROW_FILTER,
    PROTECTED_ATTRIBUTE,
    PROXY_CANDIDATES,
    build_scoped_table,
    column_inventory,
)
from .l1 import L1_ANALYSIS_ID, l1_code_descriptor, resolve_l1_params, run_l1_analysis
from .purpose_matrix import CTL_PURP_01, evaluate_purpose
from .tiers import resolve_tier_for_dataset

TIER_L2 = "L2"
PURPOSE = "fair_lending_review"  # the analysis/display label
PURPOSE_KEY = "fair_lending"  # the purpose-matrix key for this flow (PRD 4.4)
# The certified agent Plan binds for this purpose. Only certified agents are
# visible to Plan (section 11), so if this is not certified the flow refuses.
PLAN_AGENT_ID = "fair-lending"

STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked_at_gate"
STATUS_ERROR = "error"

CTL_EVAL_01 = "CTL-EVAL-01"

STAGES = [
    "Ask", "Plan", "Access", "Generate", "Gate", "Execute", "Screen", "Interpret", "Attest",
]


@dataclass
class StageRecord:
    stage: str
    status: str  # ok | blocked | error | skipped
    controls: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "controls": self.controls,
            "detail": self.detail,
        }


@dataclass
class GovernedRunResult:
    run_id: str
    question: str
    tier: str
    persona: str
    dataset: str
    purpose: str
    status: str
    stages: list[StageRecord]
    plan_agent: str = ""
    generated_code: str = ""
    gate: GateResult | None = None
    generation: GenerationOutcome | None = None
    execution: ExecutionResult | None = None
    screen: ScreenResult | None = None
    narration: str = ""
    evidence: EvidencePack | None = None
    lineage: list[dict] = field(default_factory=list)
    controls_fired: list[str] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)
    # Show-and-tell payloads (docs/features/govflow-showtell.md). Additive:
    # nothing above changes shape.
    tier_decision: dict[str, Any] = field(default_factory=dict)
    access: dict[str, Any] = field(default_factory=dict)
    # The blocked run this run repairs ("Fix it" at the Gate), if any.
    repaired_from: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "question": self.question,
            "tier": self.tier,
            "persona": self.persona,
            "dataset": self.dataset,
            "purpose": self.purpose,
            "status": self.status,
            "plan_agent": self.plan_agent,
            "stages": [s.to_dict() for s in self.stages],
            "generated_code": self.generated_code,
            "gate": self.gate.to_public_dict() if self.gate else None,
            "live": self.generation.live if self.generation else False,
            "attempts": self.generation.attempt_count if self.generation else 0,
            "screen": self.screen.to_dict() if self.screen else None,
            "screened_rows": (
                self.screen.screened.to_dict(orient="records") if self.screen else []
            ),
            "narration": self.narration,
            "evidence": self.evidence.to_public_dict() if self.evidence else None,
            "lineage": self.lineage,
            "controls_fired": self.controls_fired,
            "audit": self.audit,
            # Show-and-tell payloads (additive; the keys above are pinned by
            # tests and unchanged).
            "execution": self.execution.to_dict() if self.execution else None,
            "generation_attempts": [
                {
                    "attempt": a.attempt,
                    "live": a.codegen.live,
                    "passed": a.gate.passed,
                    "controls": a.gate.controls_fired,
                    "code": a.code,
                }
                for a in (self.generation.attempts if self.generation else [])
            ],
            "tier_decision": self.tier_decision,
            "access": self.access,
            "repaired_from": self.repaired_from,
        }


def _dedupe(seq: list[str]) -> list[str]:
    out: list[str] = []
    for s in seq:
        if s not in out:
            out.append(s)
    return out


def _band_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if c != "n" and not pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None


def _narrate(scr: ScreenResult) -> str:
    """Build a narration from the screened numbers only. It cannot reference a
    suppressed band because that band is not in the frame it reads."""
    df = scr.screened
    band_col = _band_column(df)
    if band_col is None or "selection_rate" not in df.columns or df.empty:
        return "The analysis produced a result with no comparable groups after screening."
    rates = df.set_index(band_col)["selection_rate"]
    hi_band, lo_band = rates.idxmax(), rates.idxmin()
    hi, lo = float(rates.max()), float(rates.min())
    ratio = (hi / lo) if lo > 0 else float("inf")
    lead = (
        f"Across age bands, applicants in {hi_band} are flagged at a "
        f"{hi:.2f} selection rate versus {lo:.2f} for {lo_band}"
    )
    if ratio != float("inf"):
        lead += f", a {ratio:.1f}x gap"
    tail = "."
    if scr.suppressed:
        removed = ", ".join(c.label() for c in scr.suppressed)
        tail = (
            f". Bands below the disclosure floor were suppressed before this "
            f"summary and are not reflected in it ({removed})."
        )
    return lead + tail


def _faithfulness(narration: str, scr: ScreenResult) -> tuple[bool, str]:
    """CTL-EVAL-01: the narration must not assert a value for a suppressed band.
    The suppression note names the band as removed, which is allowed; asserting a
    rate for it would not be. For v1 we check the band label does not appear
    outside the suppression clause."""
    for cell in scr.suppressed:
        label = str(next(iter(cell.group.values())))
        # Allowed only inside the explicit "suppressed" clause.
        before_clause = narration.split("suppressed", 1)[0]
        if label in before_clause:
            return False, f"narration references suppressed band {label!r}"
    return True, "narration grounded in screened result only"


def run_governed_analysis(
    question: str,
    *,
    gateway: ModelGateway | None = None,
    persona: Persona | None = None,
    intent: str = "fair_lending",
    audit: AuditLog | None = None,
    seed: int = 42,
    cell_floor: int = 10,
    proxy_threshold: float = 0.5,
    max_attempts: int = 3,
    purpose_key: str = PURPOSE_KEY,
    l1_params: dict[str, Any] | None = None,
    repair_of: str = "",
    repair_feedback: str = "",
) -> GovernedRunResult:
    """Run one question through the governed flow and return everything the UI
    needs. Scripted gateway by default (free, deterministic); pass a live gateway
    to generate with the model.

    ``purpose_key`` names the purpose-matrix cell (PRD 4.4) the request declares.
    It defaults to this flow's purpose (fair_lending); passing a purpose that the
    matrix refuses for german_credit (e.g. ``marketing``) is refused at Access
    with CTL-PURP-01 before any code is generated -- the showpiece refusal.

    The autonomy tier is computed from the persona and the dataset classification
    (PRD 4.6), never chosen. A certified analyst resolves to L2 and the model
    writes gated code; an uncertified analyst resolves to L1, where the model
    fills ``l1_params`` for a certified analysis and writes no code. A persona that
    resolves to L0 may not run.

    ``repair_of`` marks this run as the "Fix it" repair of an earlier
    gate-blocked run (its run id); ``repair_feedback`` carries that gate's
    refusal so the model can address it. The repair is a fresh governed run --
    same stages, same gate, fresh audit -- linked to the blocked one."""
    gateway = gateway or ModelGateway(provider=TEMPLATED)
    persona = persona or default_persona()
    run_id = uuid.uuid4().hex[:12]
    audit = audit or AuditLog(run_id=run_id, persist=False, policy_version=policy_version())
    tier_decision = resolve_tier_for_dataset(DATASET_ID, persona.tier_role, persona.attestations)
    tier = tier_decision.tier

    stages: list[StageRecord] = []
    controls: list[str] = []

    tier_info = {
        "tier": tier,
        "classification_ceiling": tier_decision.classification_ceiling,
        "person_ceiling": tier_decision.person_ceiling,
        "rationale": tier_decision.rationale,
    }

    def finish(status: str) -> GovernedRunResult:
        return GovernedRunResult(
            run_id=run_id,
            question=question,
            tier=tier,
            persona=persona.name,
            dataset=DATASET_ID,
            purpose=PURPOSE,
            status=status,
            stages=stages,
            plan_agent=plan_agent,
            generated_code=outcome.code if outcome else "",
            gate=outcome.gate if outcome else None,
            generation=outcome,
            execution=execution,
            screen=scr,
            narration=narration,
            evidence=evidence,
            lineage=lineage,
            controls_fired=_dedupe(controls),
            audit=audit.as_dicts(),
            tier_decision=tier_info,
            access=access_info,
            # Linked only when the repair machinery actually engaged (the L2
            # Generate branch); an L0/L1 route or an upstream block must not
            # claim a repair it never performed.
            repaired_from=repair_of if repair_engaged else "",
        )

    outcome: GenerationOutcome | None = None
    execution: ExecutionResult | None = None
    scr: ScreenResult | None = None
    narration = ""
    plan_agent = ""
    code_for_evidence = ""
    evidence: EvidencePack | None = None
    lineage: list[dict] = []
    access_info: dict[str, Any] = {}
    repair_engaged = False
    started_at = datetime.now(UTC).isoformat()

    # Stage 1: Ask -- bind identity, compute the autonomy tier (never chosen),
    # classify. The tier is min(class ceiling, person ceiling); see PRD 4.6.
    audit.record(
        agent="govflow",
        action="ask",
        stage="Ask",
        actor=persona.id,
        inputs_summary=f"purpose={PURPOSE}, dataset={DATASET_ID}",
        output_summary=f"tier resolved {tier}: {tier_decision.rationale}",
    )
    # A persona that resolves to L0 reads finished numbers; it may not run an
    # analysis. The tier gate enforces this, not just the persona's can_run flag.
    if tier not in ("L1", "L2", "L3"):
        detail = f"tier {tier} is explain-only (L0); {persona.name} may not run an analysis"
        audit.record(
            agent="govflow",
            action="tier_block",
            stage="Ask",
            level=LEVEL_BLOCKED,
            actor=persona.id,
            output_summary=detail,
        )
        stages.append(StageRecord("Ask", "blocked", detail=detail))
        for s in ("Plan", "Access", "Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
            stages.append(StageRecord(s, "skipped", detail="explain-only tier (L0)"))
        return finish(STATUS_BLOCKED)
    stages.append(
        StageRecord(
            "Ask",
            "ok",
            detail=(
                f"purpose={PURPOSE}, tier={tier} (computed: min(class "
                f"{tier_decision.classification_ceiling}, person "
                f"{tier_decision.person_ceiling})), persona={persona.name}"
            ),
        )
    )

    # Stage 2: Plan -- select a certified agent; only certified agents are visible
    # to Plan, so an uncertified analysis cannot silently reach a user.
    visible = {e.id: e for e in plan_visible_entries()}
    selected = visible.get(PLAN_AGENT_ID)
    if selected is None:
        entry = get_entry(PLAN_AGENT_ID)
        if entry is not None:
            decision = evaluate(entry)
            plan_controls = [g.control for g in decision.blocking if g.control]
            controls += plan_controls
            detail = (
                f"agent {PLAN_AGENT_ID} is {decision.status}; only certified agents "
                f"are visible to Plan"
            )
        else:
            plan_controls = []
            detail = f"no agent {PLAN_AGENT_ID!r} in the registry"
        audit.record(
            agent="govflow",
            action="plan_block",
            stage="Plan",
            level=LEVEL_BLOCKED,
            actor=persona.id,
            output_summary=detail,
        )
        stages.append(StageRecord("Plan", "blocked", controls=plan_controls, detail=detail))
        for s in ("Access", "Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
            stages.append(StageRecord(s, "skipped", detail="no certified agent to plan"))
        return finish(STATUS_BLOCKED)

    # The certification binds a dataset SHA; check for drift before running
    # (CTL-CONTRACT-01). On static data there is no drift, so this passes pinned.
    contract = live_contract_check(selected)
    if contract.drifted:
        controls.append(CTL_CONTRACT_01)
        audit.record(
            agent="govflow",
            action="plan_block",
            stage="Plan",
            level=LEVEL_BLOCKED,
            actor=persona.id,
            output_summary=contract.detail,
            extra={"control": CTL_CONTRACT_01},
        )
        stages.append(
            StageRecord("Plan", "blocked", controls=[CTL_CONTRACT_01], detail=contract.detail)
        )
        for s in ("Access", "Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
            stages.append(StageRecord(s, "skipped", detail="data contract drifted"))
        return finish(STATUS_BLOCKED)

    plan_agent = selected.label()
    audit.record(
        agent="govflow",
        action="plan",
        stage="Plan",
        actor=persona.id,
        output_summary=f"bound {plan_agent} (certified); contract {contract.detail}",
    )
    stages.append(
        StageRecord(
            "Plan",
            "ok",
            detail=f"bound {plan_agent} (certified); contract pinned, no drift",
        )
    )

    # Stage 3: Access -- purpose limitation first (CTL-PURP-01), then the grant.
    # The purpose gate asks not who but why: german_credit may be used for fair
    # lending, not for marketing. A refused purpose stops here, before any code is
    # generated. The refusal names the reason, not the role.
    purpose_decision = evaluate_purpose(DATASET_ID, purpose_key)
    if not purpose_decision.permitted:
        controls.append(CTL_PURP_01)
        audit.record(
            agent="govflow",
            action="access_block",
            stage="Access",
            level=LEVEL_BLOCKED,
            actor=persona.id,
            output_summary=purpose_decision.reason,
            extra={"control": CTL_PURP_01},
        )
        stages.append(
            StageRecord("Access", "blocked", controls=[CTL_PURP_01], detail=purpose_decision.reason)
        )
        for s in ("Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
            stages.append(StageRecord(s, "skipped", detail="purpose refused at Access"))
        return finish(STATUS_BLOCKED)

    # Permitted by the matrix, but this build wires only the fair_lending analysis
    # on german_credit. An honest stop that is not a policy refusal: a different
    # permitted purpose is allowed by policy but has no analysis here.
    if purpose_key != PURPOSE_KEY:
        detail = (
            f"{purpose_key} is permitted for {DATASET_ID} by the matrix, but no "
            f"analysis is wired for it in this build (only {PURPOSE_KEY})."
        )
        audit.record(
            agent="govflow",
            action="access_unwired",
            stage="Access",
            level=LEVEL_BLOCKED,
            actor=persona.id,
            output_summary=detail,
        )
        stages.append(StageRecord("Access", "blocked", detail=detail))
        for s in ("Generate", "Gate", "Execute", "Screen", "Interpret", "Attest"):
            stages.append(StageRecord(s, "skipped", detail="no analysis wired for this purpose"))
        return finish(STATUS_BLOCKED)

    scoped = build_scoped_table(seed=seed)
    access_info = {
        "granted": list(FAIR_LENDING_GRANT),
        "inventory": column_inventory(),
        "row_filter": FAIR_LENDING_ROW_FILTER,
        "rows": int(len(scoped)),
        "sample": scoped.head(8).to_dict(orient="records"),
        "protected_attribute": PROTECTED_ATTRIBUTE,
    }
    audit.record(
        agent="govflow",
        action="access",
        stage="Access",
        actor=persona.id,
        data_touched=FAIR_LENDING_GRANT,
        output_summary=(
            f"purpose {purpose_key} permitted; scoped view built: "
            f"{len(FAIR_LENDING_GRANT)} granted columns"
        ),
    )
    stages.append(
        StageRecord(
            "Access",
            "ok",
            detail=f"purpose {purpose_key} permitted; granted: {', '.join(FAIR_LENDING_GRANT)}",
        )
    )

    # Stages 4-6 branch on the resolved tier. At L2 the model writes code and the
    # gate reads it before the sandbox runs it. At L1 the model writes no code: it
    # selects a certified analysis and fills typed params, so there is nothing to
    # generate and nothing to statically gate, and the analysis runs in-process
    # because it is trusted platform code, not model-written.
    if tier == "L1":
        try:
            params = resolve_l1_params(l1_params)
        except ValueError as exc:
            audit.record(
                agent="l1",
                action="param_error",
                # Generate, not Plan: at L1 filling typed params is what the
                # model does *instead of* writing code, so it is that stage.
                stage="Generate",
                level=LEVEL_BLOCKED,
                actor=persona.id,
                output_summary=str(exc),
            )
            stages.append(StageRecord("Generate", "error", detail=str(exc)))
            for s in ("Gate", "Execute", "Screen", "Interpret", "Attest"):
                stages.append(StageRecord(s, "skipped", detail="invalid L1 parameters"))
            return finish(STATUS_ERROR)

        code_for_evidence = l1_code_descriptor(params)
        stages.append(
            StageRecord(
                "Generate",
                "skipped",
                detail=(
                    f"L1: the model selects the certified analysis {L1_ANALYSIS_ID!r} "
                    "and fills typed params; it writes no code."
                ),
            )
        )
        stages.append(
            StageRecord(
                "Gate",
                "skipped",
                detail="L1: no generated code to gate; the reviewed surface is the params.",
            )
        )
        audit.record(
            agent="l1",
            action="select_and_fill",
            stage="Generate",
            actor=persona.id,
            output_summary=f"certified analysis {L1_ANALYSIS_ID!r}, params {params}",
        )
        try:
            emitted = run_l1_analysis(scoped, params)
            execution = ExecutionResult(ok=True, emitted=emitted, has_emitted=True)
        except Exception as exc:  # noqa: BLE001 - report any analysis failure
            execution = ExecutionResult(ok=False, error=f"{type(exc).__name__}: {exc}")
            audit.record(
                agent="l1",
                action="analysis_error",
                stage="Execute",
                actor=persona.id,
                level=LEVEL_BLOCKED,
                output_summary=execution.error or "L1 analysis failed",
            )
            stages.append(StageRecord("Execute", "error", detail=execution.error or "failed"))
            for s in ("Screen", "Interpret", "Attest"):
                stages.append(StageRecord(s, "skipped", detail="L1 analysis failed"))
            return finish(STATUS_ERROR)
        stages.append(
            StageRecord(
                "Execute",
                "ok",
                detail=(
                    f"ran certified analysis {L1_ANALYSIS_ID!r} in-process with typed "
                    "params (trusted, not model-written)"
                ),
            )
        )
        audit.record(
            agent="l1",
            action="analysis_ok",
            stage="Execute",
            actor=persona.id,
            output_summary=f"certified analysis produced {len(emitted)} group(s)",
        )
    else:
        # L2: the model writes code, a static gate reads it, the sandbox runs it.
        # A repair engages only where there is something to repair with: live
        # feedback for the model, or a seeded repaired sample in scripted mode.
        # A stray repair_of on a plain run stays a plain run (the L3 contract).
        is_repair = bool(repair_feedback) or (
            bool(repair_of) and has_scripted_repair(intent)
        )
        request = CodeGenRequest(
            question=question,
            table=DATASET_ID,
            granted_columns=FAIR_LENDING_GRANT,
            protected_attribute=PROTECTED_ATTRIBUTE,
            analysis=PURPOSE,
            intent=intent,
            allowed_tables=[DATASET_ID],
            repair=is_repair,
        )
        if is_repair:
            repair_engaged = True
            audit.record(
                agent="govflow",
                action="repair_requested",
                stage="Generate",
                actor=persona.id,
                output_summary=(
                    f"Fix it: repair of gate-blocked run {repair_of or '(unknown)'}; "
                    + (
                        "the prior refusal is fed back to the model and the gate "
                        "re-reads the result"
                        if gateway.is_live
                        else "seeded repaired sample substituted and re-gated"
                    )
                ),
            )
        outcome = generate_and_gate(
            request, gateway, max_attempts=max_attempts, initial_feedback=repair_feedback
        )
        gen_detail = (
            f"{'live' if outcome.live else 'scripted'}, "
            f"{outcome.attempt_count} attempt(s)"
        )
        if is_repair:
            gen_detail += f"; repair of blocked run {repair_of or '(unknown)'}"
        stages.append(StageRecord("Generate", "ok", detail=gen_detail))

        if not outcome.gate.passed:
            controls += outcome.gate.controls_fired
            for v in outcome.gate.violations:
                audit.record(
                    agent="gate",
                    action="gate_block",
                    stage="Gate",
                    level=LEVEL_BLOCKED,
                    actor=persona.id,
                    output_summary=v.message,
                    extra={"control": v.control, "line": v.line},
                )
            stages.append(
                StageRecord(
                    "Gate",
                    "blocked",
                    controls=outcome.gate.controls_fired,
                    detail=outcome.gate.refusal_summary(),
                )
            )
            for s in ("Execute", "Screen", "Interpret", "Attest"):
                stages.append(StageRecord(s, "skipped", detail="upstream gate block"))
            return finish(STATUS_BLOCKED)

        audit.record(
            agent="gate",
            action="gate_pass",
            stage="Gate",
            actor=persona.id,
            level=LEVEL_GATE,
            output_summary=f"gate passed on attempt {outcome.attempt_count}",
        )
        stages.append(StageRecord("Gate", "ok", detail="no violations; cleared for execution"))

        # Execute in the sandbox. The grant and row filter back ctx.sql: the
        # runtime backstop for columns, and the injected identity filter.
        execution = run_sandboxed(
            outcome.code,
            tables={DATASET_ID: scoped},
            granted_columns=FAIR_LENDING_GRANT,
            row_filter_sql=FAIR_LENDING_ROW_FILTER,
            wall_clock_s=GOVFLOW_WALL_CLOCK_S,
        )
        if not execution.ok:
            ctl = [execution.control] if execution.control else []
            controls += ctl
            audit.record(
                agent="sandbox",
                action="execute_error",
                stage="Execute",
                actor=persona.id,
                level=LEVEL_BLOCKED,
                output_summary=execution.error or "execution failed",
                extra={"control": execution.control},
            )
            stages.append(
                StageRecord(
                    "Execute", "error", controls=ctl, detail=execution.error or "failed"
                )
            )
            for s in ("Screen", "Interpret", "Attest"):
                stages.append(StageRecord(s, "skipped", detail="execution failed"))
            return finish(STATUS_ERROR)

        emitted = execution.emitted
        if not isinstance(emitted, pd.DataFrame) or "n" not in emitted.columns:
            audit.record(
                agent="sandbox",
                action="execute_ok_bad_shape",
                stage="Execute",
                actor=persona.id,
                level=LEVEL_BLOCKED,
                output_summary="emitted result is not a grouped table with an 'n' column",
            )
            stages.append(
                StageRecord(
                    "Execute",
                    "error",
                    detail="emitted result must be a DataFrame with an 'n' count column",
                )
            )
            for s in ("Screen", "Interpret", "Attest"):
                stages.append(StageRecord(s, "skipped", detail="unusable result shape"))
            return finish(STATUS_ERROR)

        code_for_evidence = outcome.code
        stages.append(
            StageRecord("Execute", "ok", detail=f"ran in {execution.wall_clock_s:.2f}s")
        )
        audit.record(
            agent="sandbox",
            action="execute_ok",
            stage="Execute",
            actor=persona.id,
            output_summary=f"ran in {execution.wall_clock_s:.2f}s (no network, wall-clock capped)",
        )

    # Stage 7: Screen -- suppression, then proxy discovery.
    band_cols = [_band_column(emitted)] if _band_column(emitted) else None
    scr = screen(
        emitted,
        count_col="n",
        floor=cell_floor,
        group_cols=band_cols,
        scoped_table=scoped,
        protected=PROTECTED_ATTRIBUTE,
        granted_features=PROXY_CANDIDATES,
        proxy_threshold=proxy_threshold,
    )
    controls += scr.controls_fired
    for cell in scr.suppressed:
        audit.record(
            agent="screen",
            action="cell_suppressed",
            stage="Screen",
            actor=persona.id,
            level=LEVEL_BLOCKED,
            output_summary=f"suppressed cell {cell.label()} (n={cell.n} < {cell_floor})",
            extra={"control": "CTL-DISC-02"},
        )
    for flag in scr.proxy_flags:
        audit.record(
            agent="screen",
            action="proxy_flagged",
            stage="Screen",
            actor=persona.id,
            level=LEVEL_BLOCKED,
            output_summary=flag.message(),
            extra={"control": "CTL-PROXY-01"},
        )
    stages.append(
        StageRecord(
            "Screen",
            "ok",
            controls=scr.controls_fired,
            detail=(
                f"{len(scr.suppressed)} cell(s) suppressed, "
                f"{len(scr.proxy_flags)} proxy flag(s)"
            ),
        )
    )

    # Stage 8: Interpret -- narrate from screened numbers, then check faithfulness.
    narration = _narrate(scr)
    faithful, why = _faithfulness(narration, scr)
    eval_controls = [] if faithful else [CTL_EVAL_01]
    controls += eval_controls
    audit.record(
        agent="interpret",
        action="narration",
        stage="Interpret",
        actor=persona.id,
        output_summary=("faithful: " if faithful else "UNFAITHFUL: ") + why,
        extra={"control": CTL_EVAL_01, "passed": faithful},
    )
    stages.append(
        StageRecord(
            "Interpret",
            "ok" if faithful else "blocked",
            controls=eval_controls,
            detail=why,
        )
    )

    # Stage 9: Attest -- assemble the evidence pack. It ships pending: signing it
    # requires an approver who is not the author (CTL-SOD-01). Its differentiator
    # is the negative statement, built from what this run actually did.
    try:
        ds_sha = dataset_sha(DATASET_ID)
    except FingerprintError:
        ds_sha = None
    attested = _dedupe(
        controls + [CTL_CONTRACT_01, "CTL-TIME-01"] + ([CTL_EVAL_01] if faithful else [])
    )
    evidence = build_evidence_pack(
        run_id=run_id,
        analysis=plan_agent,
        dataset=DATASET_ID,
        dataset_sha=ds_sha,
        tier=tier,
        purpose=PURPOSE,
        author=persona.id,
        code=code_for_evidence,
        screened=scr.screened,
        controls_attested=attested,
        suppressed=scr.suppressed,
        proxy_flags=scr.proxy_flags,
        cell_floor=cell_floor,
    )
    # Emit the provenance chain as OpenLineage events: a START at Access and a
    # COMPLETE at Attest, the input dataset bound to its contract SHA.
    lineage = run_lineage_events(
        run_id=run_id,
        purpose=PURPOSE,
        dataset=DATASET_ID,
        dataset_sha=ds_sha,
        finding=evidence.finding,
        started_at=started_at,
        completed_at=datetime.now(UTC).isoformat(),
    )
    audit.record(
        agent="attest",
        action="evidence_pack",
        stage="Attest",
        actor=persona.id,
        output_summary=(
            f"evidence pack assembled (pending signoff); "
            f"{len(evidence.negative_statement)} negative-statement clause(s); "
            f"{len(lineage)} OpenLineage event(s) emitted"
        ),
    )
    stages.append(
        StageRecord(
            "Attest",
            "ok",
            detail="evidence pack assembled; pending independent signoff (CTL-SOD-01)",
        )
    )

    return finish(STATUS_COMPLETED)
