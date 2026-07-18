"""Plain-language metadata for every governance control (the show-and-tell layer).

The brief (docs/more_ideas.md): a control chip that just names an id tells the
viewer nothing. Every place the UI shows a control, it should be able to say
what the control is, why it exists, and what firing means -- without the code
that enforces the control having to carry presentation text.

This module is data only: no streamlit, no enforcement. The enforcement lives
where it always did (gate, screen, flow, sandbox, pack); the ids here mirror
those modules and the PRD control catalogue (docs/features/governed-codegen.md
section 4.7: a control is "a named, testable rule that can refuse").

Doc-only ids from the PRD that have no implementation are included with
implemented=False so the UI can honestly distinguish "enforced here" from
"named in the design"; they are never rendered as live controls.
"""

from __future__ import annotations

from dataclasses import dataclass

# Action vocabulary: what the control does when it fires.
ACT_REFUSE = "refuses"
ACT_FLAG = "flags"
ACT_SUPPRESS = "suppresses"
ACT_LOG = "logs"


@dataclass(frozen=True)
class ControlInfo:
    id: str
    name: str
    stage: str  # the flow stage (or surface) where it acts
    action: str  # refuses | flags | suppresses | logs
    what: str  # what the rule is, in plain language
    why: str  # why it exists / the regulatory hook
    fired_means: str  # how to read this control appearing on a run
    implemented: bool = True


_INFOS: list[ControlInfo] = [
    # -- Access -----------------------------------------------------------
    ControlInfo(
        id="CTL-PURP-01",
        name="Purpose limitation",
        stage="Access",
        action=ACT_REFUSE,
        what=(
            "Each dataset carries a list of permitted purposes. A request whose "
            "declared purpose is not on the list is refused before any code is "
            "written; in SQL, a table outside the purpose's scope is refused the "
            "same way."
        ),
        why=(
            "The one governance idea a banker recognises instantly: you may not "
            "use credit data for marketing. Not because the role lacks "
            "permission -- because the reason is wrong. This gate asks not who, "
            "but why."
        ),
        fired_means=(
            "The dataset-by-purpose matrix refused this request at Access. "
            "Nothing downstream ran: no code was generated, no data was touched."
        ),
    ),
    ControlInfo(
        id="CTL-CONTRACT-01",
        name="Data-contract drift",
        stage="Plan",
        action=ACT_REFUSE,
        what=(
            "A certified analysis is pinned to the SHA of the dataset it was "
            "certified on. If the data has changed since certification, the run "
            "is refused and recertification is required."
        ),
        why=(
            "A certification is a claim about an analysis on specific data. "
            "Let the data drift silently and the certification is theatre."
        ),
        fired_means=(
            "The dataset no longer matches its certified fingerprint. On this "
            "build the CSVs are static, so this control passes pinned; the "
            "mechanism is proven in a test rather than staged in the demo."
        ),
    ),
    # -- Gate (the ast half) ---------------------------------------------
    ControlInfo(
        id="CTL-CODE-00",
        name="Code must parse",
        stage="Gate",
        action=ACT_REFUSE,
        what="Generated code that does not parse as Python is refused outright.",
        why=(
            "The gate reads code before the machine runs it. Code it cannot "
            "read, it cannot vouch for."
        ),
        fired_means="The generated code was not valid Python. It never ran.",
    ),
    ControlInfo(
        id="CTL-CODE-01",
        name="Import allowlist",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "Only a named list of analytical libraries may be imported (pandas, "
            "numpy, scipy.stats, fairlearn, statsmodels and peers at L2; whole "
            "scientific packages plus safe stdlib at L3). Anything else is "
            "refused by name."
        ),
        why=(
            "An allowlist inverts the burden of proof: a library is unusable "
            "until someone decided it is safe, not the other way round."
        ),
        fired_means=(
            "The code imported a module outside the tier's allowlist. It never ran."
        ),
    ),
    ControlInfo(
        id="CTL-CODE-02",
        name="No filesystem or process access",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "os, sys, subprocess, pathlib, shutil, tempfile, and open() in any "
            "write mode are refused at every tier, including L3."
        ),
        why=(
            "Generated code computes over the table it was granted. Writing "
            "files or spawning processes is exfiltration surface, not analysis."
        ),
        fired_means=(
            "The code tried to touch the filesystem or a process. It never ran."
        ),
    ),
    ControlInfo(
        id="CTL-CODE-03",
        name="No dynamic code",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "eval, exec, compile, __import__, importlib, pickle, marshal and "
            "ctypes are refused at every tier."
        ),
        why=(
            "Dynamic execution is the universal gate bypass: code the gate "
            "cannot read until it is already running. Deny it and the static "
            "read stays meaningful."
        ),
        fired_means=(
            "The code tried to build or run code at runtime (or deserialize "
            "untrusted bytes). It never ran."
        ),
    ),
    ControlInfo(
        id="CTL-CODE-04",
        name="No sandbox escapes",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "Attribute access that walks the object graph out of the sandbox "
            "(__globals__, __subclasses__, __mro__ and friends) is refused."
        ),
        why=(
            "Python's introspection lets code reach almost anything from almost "
            "anywhere. These dunders are the known escape hatches."
        ),
        fired_means="The code reached for an escape-hatch attribute. It never ran.",
    ),
    ControlInfo(
        id="CTL-EGRESS-01",
        name="No network egress",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "No network module may be referenced at all -- requests, urllib, "
            "socket, httpx and peers -- imported or not. Identical at L2 and L3."
        ),
        why=(
            "Data leaves a bank through the network. A hard, tier-independent "
            "deny is the only credible answer; there is no legitimate reason "
            "for a governed analysis to phone anywhere."
        ),
        fired_means=(
            "The code referenced a network module (the webhook case). The "
            "attempted egress was caught by reading the code; it never executed."
        ),
    ),
    ControlInfo(
        id="CTL-COL-01",
        name="Column grant",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "Every column the code touches must be in the purpose's grant. In "
            "SQL that also means no SELECT *, and the query must be a single "
            "static statement the gate can read."
        ),
        why=(
            "Access built a scoped table; the gate enforces the same grant in "
            "the code's own references, so an ungranted column is refused even "
            "as text."
        ),
        fired_means=(
            "The code referenced a column outside the grant (or used SELECT *). "
            "It never ran."
        ),
    ),
    ControlInfo(
        id="CTL-COMPLEX-01",
        name="Query complexity ceiling",
        stage="Gate",
        action=ACT_REFUSE,
        what=(
            "SQL joins need an explicit ON/USING condition and the join count "
            "is capped (default 2). Cartesian products are refused."
        ),
        why=(
            "Unconditioned joins are how a 1,000-row table becomes a million-row "
            "disclosure accident."
        ),
        fired_means="The SQL was too complex or joined without a condition.",
    ),
    # -- Execute ----------------------------------------------------------
    ControlInfo(
        id="CTL-TIME-01",
        name="Wall-clock cap",
        stage="Execute",
        action=ACT_REFUSE,
        what=(
            "The sandbox subprocess is killed when it exceeds its wall-clock "
            "budget; memory and CPU rlimits back it up best-effort."
        ),
        why=(
            "A runaway analysis is a denial-of-service on shared infrastructure. "
            "The cap turns it into a bounded failure."
        ),
        fired_means="Execution exceeded the wall clock and the process was killed.",
    ),
    # -- Screen -----------------------------------------------------------
    ControlInfo(
        id="CTL-DISC-01",
        name="Disclosure floor breached",
        stage="Screen",
        action=ACT_LOG,
        what=(
            "Records that the raw grouped output contained at least one cell "
            "below the disclosure floor, so screening had to act."
        ),
        why=(
            "The audit trail should show that the floor was needed, not only "
            "that it exists."
        ),
        fired_means=(
            "At least one group in the raw result was smaller than the floor. "
            "CTL-DISC-02 did the removal; this control is the record that it "
            "was necessary."
        ),
    ),
    ControlInfo(
        id="CTL-DISC-02",
        name="Small-cell suppression",
        stage="Screen",
        action=ACT_SUPPRESS,
        what=(
            "Any group with fewer members than the floor (default n < 10) is "
            "removed from the result before anything downstream -- including "
            "the narration model -- can see it."
        ),
        why=(
            "Small cells re-identify people. And you cannot leak what you were "
            "never shown: removal upstream of the model beats trusting the "
            "model to stay quiet."
        ),
        fired_means=(
            "A band fell below the floor and was removed. The narration was "
            "written from the screened table only, so it cannot assert anything "
            "about the removed band."
        ),
    ),
    ControlInfo(
        id="CTL-DISC-03",
        name="PII in output text",
        stage="Screen",
        action=ACT_FLAG,
        what=(
            "Output text can be scanned for PII, with findings recorded per "
            "location and kind."
        ),
        why="Results tables are not the only leak path; prose leaks too.",
        fired_means=(
            "PII patterns were found in an output text and recorded. On this "
            "build the governed flow routes no output text through the scan "
            "(the grouped table has none); the mechanism is proven in tests "
            "and by the pipeline's PII redaction rather than staged here."
        ),
    ),
    ControlInfo(
        id="CTL-PROXY-01",
        name="Proxy discovery",
        stage="Screen",
        action=ACT_FLAG,
        what=(
            "Measures the statistical association between each granted feature "
            "and the protected attribute. A feature over the threshold is "
            "flagged as a candidate proxy -- flagged, never refused."
        ),
        why=(
            "Proxy discrimination is the central problem in fair lending; it is "
            "why disparate impact exists as a legal test separate from disparate "
            "treatment. Whether a proxy is a business necessity is Legal's "
            "call, so the platform flags and records rather than deciding."
        ),
        fired_means=(
            "A granted feature associates strongly with the protected "
            "attribute. The finding is recorded for review; the run proceeds."
        ),
    ),
    # -- Interpret ---------------------------------------------------------
    ControlInfo(
        id="CTL-EVAL-01",
        name="Narration faithfulness",
        stage="Interpret",
        action=ACT_FLAG,
        what=(
            "The narration is checked against the screened result: it may not "
            "assert a value for a band the Screen removed."
        ),
        why=(
            "A model that narrates numbers it never saw is the failure mode "
            "this whole flow exists to prevent. The check is on the output, "
            "not on trust."
        ),
        fired_means=(
            "The narration referenced a suppressed band outside the explicit "
            "suppression note, and the Interpret stage was marked unfaithful."
        ),
    ),
    # -- Attest ------------------------------------------------------------
    ControlInfo(
        id="CTL-SOD-01",
        name="Segregation of duties",
        stage="Attest",
        action=ACT_REFUSE,
        what=(
            "The person who signs a run, evidence pack, or certification may "
            "not be its author. Self-signoff is refused and the refusal is "
            "audited."
        ),
        why=(
            "SR 11-7 requires independent validation; independence starts with "
            "the approver not being the author. This was a confirmed defect in "
            "an earlier build, which is exactly why it is enforced by identity "
            "comparison now, not by role."
        ),
        fired_means=(
            "A self-signoff was attempted and refused, or the pack is pending "
            "an approver who is not the author."
        ),
    ),
]

# -- Doc-only ids from the PRD (named in the design, not implemented) -----
_DOC_ONLY: list[ControlInfo] = [
    ControlInfo(
        id=cid,
        name=name,
        stage=stage,
        action=action,
        what=what,
        why="Named in the PRD control catalogue; not implemented in this build.",
        fired_means="Cannot fire: not implemented.",
        implemented=False,
    )
    for cid, name, stage, action, what in [
        ("CTL-RBAC-01", "Column denied by role", "Access", ACT_REFUSE,
         "A column the requester's role may not read is denied."),
        ("CTL-RBAC-02", "Row filter applied", "Access", ACT_LOG,
         "The identity's row filter is injected into every query."),
        ("CTL-PURP-02", "Column outside purpose scope", "Access", ACT_REFUSE,
         "A column outside the declared purpose's scope is denied."),
        ("CTL-TIER-01", "Operation exceeds tier", "Ask", ACT_REFUSE,
         "An operation beyond the resolved autonomy tier is refused."),
        ("CTL-INJECT-01", "Injection screen", "Generate", ACT_FLAG,
         "Instruction-shaped text in data-derived model context is screened."),
        ("CTL-COST-01", "Spend cap", "Execute", ACT_REFUSE,
         "Cumulative model spend over the cap stops further live calls."),
        ("CTL-DISC-04", "Target leakage", "Screen", ACT_FLAG,
         "A pre-decision feature set containing post-decision data is flagged."),
        ("CTL-LIN-01", "Lineage completeness", "Attest", ACT_REFUSE,
         "An incomplete lineage chain blocks attestation."),
        ("CTL-PII-01", "PII redaction", "any", ACT_SUPPRESS,
         "PII is redacted before text reaches model context."),
    ]
]

CONTROLS_INFO: dict[str, ControlInfo] = {c.id: c for c in _INFOS + _DOC_ONLY}

# The five toggleable harness controls (sentinel/harness/controls.py) use
# catalog ids, not CTL- ids. Give them the same treatment so the header chips
# can explain themselves.
CATALOG_INFO: dict[str, ControlInfo] = {
    "rbac": ControlInfo(
        id="rbac",
        name="RBAC",
        stage="pipeline",
        action=ACT_REFUSE,
        what=(
            "Per-agent column access control: each pipeline agent sees only the "
            "columns its role grants."
        ),
        why=(
            "Least privilege per agent. The Profiler has no business reading "
            "the sex-proxy column."
        ),
        fired_means=(
            "A column read was denied and logged. One denial fires on every "
            "hero-pipeline run by design, so the control is visibly live."
        ),
    ),
    "pii": ControlInfo(
        id="pii",
        name="PII redaction",
        stage="pipeline",
        action=ACT_SUPPRESS,
        what="PII is scrubbed from any text before it reaches a model.",
        why=(
            "Names, emails and SSNs have no business in a prompt. Redaction "
            "upstream beats trusting the model."
        ),
        fired_means=(
            "PII was found and redacted before narration. One redaction fires "
            "on every hero-pipeline run by design."
        ),
    ),
    "guardrails": ControlInfo(
        id="guardrails",
        name="Guardrails",
        stage="pipeline",
        action=ACT_REFUSE,
        what="Each agent may call only the tools on its allow-list.",
        why="An agent's blast radius is its tool list. Keep the list short.",
        fired_means="A tool call outside the allow-list was refused.",
    ),
    "eval_gate": ControlInfo(
        id="eval_gate",
        name="Eval gate",
        stage="pipeline",
        action=ACT_REFUSE,
        what="Golden-set checks must pass before a model can promote.",
        why=(
            "Promotion on vibes is how bad models reach production. The gate "
            "makes the checks a precondition, not a dashboard."
        ),
        fired_means="A golden check failed and promotion was blocked.",
    ),
    "human_gate": ControlInfo(
        id="human_gate",
        name="Human gate",
        stage="pipeline",
        action=ACT_REFUSE,
        what=(
            "The run pauses for a human decision before any model promotes; "
            "the approver may not be the author (CTL-SOD-01)."
        ),
        why=(
            "SR 11-7 model risk management: a person with promotion authority "
            "owns the decision, and the platform records who."
        ),
        fired_means="The run paused at the gate for an independent approval.",
    ),
    "audit": ControlInfo(
        id="audit",
        name="Audit log",
        stage="pipeline",
        action=ACT_LOG,
        what=(
            "Every agent action is appended to an audit log stamped with the "
            "acting identity and the policy version. Disabling a control is "
            "itself audited."
        ),
        why=(
            "The examiner's first question is 'show me'. Append-only, "
            "identity-stamped events are the answer."
        ),
        fired_means="Always on. Not toggleable: an unaudited run is not a run.",
    ),
}


def control_info(control_id: str) -> ControlInfo:
    """Look up a control by id; unknown ids get an honest placeholder."""
    info = CONTROLS_INFO.get(control_id) or CATALOG_INFO.get(control_id)
    if info is not None:
        return info
    return ControlInfo(
        id=control_id,
        name=control_id,
        stage="unknown",
        action=ACT_LOG,
        what="No registered description for this control id.",
        why="",
        fired_means="",
        implemented=False,
    )


def implemented_ids() -> list[str]:
    return [c.id for c in _INFOS]
