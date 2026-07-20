"""The nine governance stages, as a shape every run kind can be read in.

The Run screen teaches one vocabulary: Ask, Plan, Access, Generate, Gate,
Execute, Screen, Interpret, Attest. That is the product's governance spine. An
auditor who has learned it once should be able to read *any* run in it, rather
than learning four unrelated step vocabularies (analysis has load/profile/
quality, credit_risk has profiler/eda/modeler/gate/validator, govflow and L3
have the nine).

So this module maps each run kind onto the nine, and the Audit Log renders that
shape for every run.

Three rules keep the mapping honest, because a normalization that invents
stages is worse than four vocabularies:

1. **A stage a route does not have is `NOT_IN_ROUTE`, never `ok` and never
   `skipped`.** They are three different facts. `ok` means it ran. `skipped`
   means the run reached the stage and declined to execute it. `NOT_IN_ROUTE`
   means this kind of run has no such stage at all: a linear analysis generates
   no code, so it has no Generate stage to skip.
2. **The native step names stay visible** under the canonical stage. Nothing is
   renamed away; the mapping is additive.
3. **Libraries are per route, not per stage alone.** govflow's Execute runs a
   subprocess sandbox over duckdb; credit_risk's Execute trains a scikit-learn
   model. Printing govflow's libraries against a credit-risk run would be a
   plain falsehood, so each route declares its own and they are grounded in
   what the modules actually import.
"""

from __future__ import annotations

from .run_history import KIND_ANALYSIS, KIND_CREDIT_RISK, KIND_GOVFLOW, KIND_L3

# The spine, in order. Same list and same spelling as sentinel/govflow/flow.py
# STAGES, because divergence between the Run screen and the Audit Log is the
# failure this module exists to avoid.
CANONICAL_STAGES = [
    "Ask", "Plan", "Access", "Generate", "Gate",
    "Execute", "Screen", "Interpret", "Attest",
]

# A fourth status alongside ok / blocked / skipped.
NOT_IN_ROUTE = "not_in_route"

# What each stage is for, in one line, so the screen can say what a stage means
# without the reader going to the Run screen.
STAGE_PURPOSE = {
    "Ask": "The request is stated, the purpose declared, and the autonomy tier resolved.",
    "Plan": "A certified agent is bound to the purpose and its data contract pinned.",
    "Access": "Data is scoped to the columns the purpose and role permit.",
    "Generate": "Code is produced against the fenced API.",
    "Gate": "The generated code is read statically before anything runs.",
    "Execute": "The analysis runs.",
    "Screen": "Outputs are checked for disclosure and proxy risk before anyone sees them.",
    "Interpret": "Results are narrated, and the narration is checked against them.",
    "Attest": "Evidence is assembled and signed off.",
}

# -- native step -> canonical stage ----------------------------------------
# Keyed on the step name each run kind actually records. Anything not listed
# for a kind is NOT_IN_ROUTE for that kind.

_ANALYSIS_MAP = {
    "Governed data access": "Access",
    "Profile columns": "Execute",
    "Quality expectation suite": "Screen",
    "Entity feature build": "Execute",
    "Leakage scan": "Screen",
}

_CREDIT_RISK_MAP = {
    "Data Profiler": "Execute",
    "EDA / Feature": "Execute",
    "Modeler": "Execute",
    "Validator": "Screen",
}

# govflow and L3 already are the nine stages.
_IDENTITY_MAP = {s: s for s in CANONICAL_STAGES}

_STEP_MAP = {
    KIND_ANALYSIS: _ANALYSIS_MAP,
    KIND_CREDIT_RISK: _CREDIT_RISK_MAP,
    KIND_GOVFLOW: _IDENTITY_MAP,
    KIND_L3: _IDENTITY_MAP,
}

# Stages a route performs but does not record as a discrete step. They are real
# (the code does the thing) and get a status from the run's own outcome, with a
# note saying where the evidence lives. Anything absent here AND absent from the
# step map is NOT_IN_ROUTE.
_IMPLICIT = {
    KIND_ANALYSIS: {
        "Ask": "The analysis and its dataset were chosen from the certified catalog.",
        "Plan": "The spec's typed parameters were resolved and validated before the run.",
        "Interpret": "Each step summarised its own result; there is no model narration.",
    },
    KIND_CREDIT_RISK: {
        "Ask": "A preset question was chosen; this route predates the tier ladder.",
        "Plan": "The pipeline is a statically compiled graph, not a per-run plan.",
        "Access": "RBAC mediates every column read; denials are recorded as events.",
        "Interpret": "Each agent narrated its own step.",
        "Attest": "The human promotion gate, the eval gate, and the model card.",
    },
}

# -- per-route libraries ----------------------------------------------------
# Grounded in what the modules on each path actually import. govflow and L3
# defer to sentinel.ui.govflow._ENGINE so the Audit Log and the Run screen
# cannot drift; the other two declare their own.

_ANALYSIS_LIBS = {
    "Access": ["pandas"],
    "Execute": ["pandas", "numpy"],
    "Screen": ["pandas", "numpy"],
}

_CREDIT_RISK_LIBS = {
    "Plan": ["langgraph"],
    "Execute": ["pandas", "numpy", "scikit-learn"],
    "Screen": ["fairlearn.metrics"],
    "Attest": ["fpdf2"],
}

_ROUTE_LIBS = {KIND_ANALYSIS: _ANALYSIS_LIBS, KIND_CREDIT_RISK: _CREDIT_RISK_LIBS}

# -- per-route governance ---------------------------------------------------
# The controls each stage arms on that route. For govflow/L3 this comes from
# _ENGINE. These two routes predate the CTL- catalogue, so they name the
# harness controls they actually run, which is what their events record.

_ANALYSIS_CONTROLS = {
    "Access": ["contract_check", "rbac"],
    "Execute": ["guardrails"],
    "Screen": ["quality_gate"],
}

_CREDIT_RISK_CONTROLS = {
    "Access": ["rbac"],
    "Execute": ["guardrails", "pii"],
    "Screen": ["pii", "fairness"],
    "Attest": ["human_gate", "eval_gate", "CTL-SOD-01"],
}

_ROUTE_CONTROLS = {
    KIND_ANALYSIS: _ANALYSIS_CONTROLS,
    KIND_CREDIT_RISK: _CREDIT_RISK_CONTROLS,
}


def _govflow_engine(stage: str) -> tuple[list[str], list[str]]:
    """The Run screen's own table, so the two surfaces cannot disagree."""
    from ..ui.govflow import _ENGINE

    libs, ctls = _ENGINE.get(stage, ([], []))
    return list(libs), list(ctls)


def stage_engine(run_kind: str, stage: str) -> tuple[list[str], list[str]]:
    """(libraries, controls) for one stage of one route."""
    if run_kind in (KIND_GOVFLOW, KIND_L3):
        return _govflow_engine(stage)
    return (
        list(_ROUTE_LIBS.get(run_kind, {}).get(stage, [])),
        list(_ROUTE_CONTROLS.get(run_kind, {}).get(stage, [])),
    )


def canonical_steps(run) -> list[dict]:  # noqa: ANN001
    """The run, read as the nine stages.

    Each entry: stage, purpose, status, the native steps folded into it (with
    their detail), the libraries that stage used on this route, and the
    controls it armed. `native` is empty for an implicit stage, and the whole
    entry is NOT_IN_ROUTE where the route has no such stage.
    """
    step_map = _STEP_MAP.get(run.run_kind, {})
    implicit = _IMPLICIT.get(run.run_kind, {})

    folded: dict[str, list[dict]] = {}
    for s in run.steps:
        target = step_map.get(str(s.get("name", "")))
        if target:
            folded.setdefault(target, []).append(s)

    out: list[dict] = []
    for stage in CANONICAL_STAGES:
        native = folded.get(stage, [])
        libs, ctls = stage_engine(run.run_kind, stage)
        if native:
            status = _fold_status([str(s.get("status", "")) for s in native])
            note = ""
        elif stage in implicit:
            # Real, but not recorded as its own step. A run that never got off
            # the ground did not perform it either, so inherit the outcome
            # rather than claiming a green tick.
            status = "ok" if not run.stopped_run else "skipped"
            note = implicit[stage]
        else:
            status = NOT_IN_ROUTE
            note = ""
        out.append(
            {
                "stage": stage,
                "purpose": STAGE_PURPOSE[stage],
                "status": status,
                "native": native,
                "note": note,
                "libraries": libs,
                "controls": ctls,
                # Controls that actually fired here, as opposed to armed.
                "fired": sorted(
                    {c for s in native for c in (s.get("controls") or [])}
                ),
            }
        )
    return out


def _fold_status(statuses: list[str]) -> str:
    """Several native steps in one stage: the worst outcome wins.

    A stage that contains both a completed step and a blocked one is a blocked
    stage. Reporting it green because two of three steps passed is exactly the
    kind of aggregation an audit surface must not do.
    """
    for bad in ("blocked", "error", "rejected"):
        if bad in statuses:
            return bad
    if "awaiting_approval" in statuses:
        return "awaiting_approval"
    if statuses and all(s == "skipped" for s in statuses):
        return "skipped"
    return "ok"
