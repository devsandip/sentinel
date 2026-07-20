"""The agent-template spec: one YAML document, its checks, and the deploy path.

A template is only worth editing if editing it can be refused. This module is
what makes that true: it serializes an AgentTemplate to YAML, parses YAML back,
and checks the result against the modules that actually enforce each field --
the pattern catalog, the tool allow-list in agents.yaml, the codegen import
allow-list, the purpose matrix, the tier ladder, the column grant, the
certification gates. Nothing here keeps a second copy of a policy. Every check
names the module it read the rule from, so a policy change moves one file and
this follows.

**YAML, and why.** The config layer is already YAML (rbac, evals, personas,
questions, agents), and `sentinel new-agent` already writes an agent spec in
YAML (scaffold.py `_spec_yaml`). A JSON template would mean the CLI and the
screen emit different artifacts for the same object. The looseness YAML brings
is answered by the schema check below rather than by the format.

**Two kinds of check, and the difference matters.**

  Policy checks -- schema, pattern, tools, imports, purposes, tier, columns,
  contract -- are the fence. A refusal here blocks the deploy outright, because
  an illegal blueprint should not reach the registry at all.

  Certification gates -- evals, owner, signoff -- do not block the deploy. They
  block `certified`. A draft with no owner is exactly what `sentinel new-agent`
  registers today (scaffold.py), and pretending otherwise would make the CLI and
  the screen disagree about what a new agent looks like on its first day.

Collapsing those two would be the familiar mistake in a new place: a screen that
paints "not yet owned" the same red as "reaches for the network" is not telling
a reviewer which one is a policy violation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from typing import Any

import yaml

from ..codegen.allowlist import ALLOWED_IMPORTS, L3_ALLOWED_IMPORTS
from ..codegen.gate import NO_SUBJECT, CheckReading, Observation
from ..config import load_agents, load_evals
from ..datasets.fingerprint import dataset_sha
from ..datasets.registry import DATASETS_BY_ID
from ..govflow.access import FAIR_LENDING_GRANT
from ..govflow.purpose_matrix import (
    CTL_PURP_01,
    DATA_CLASSIFICATION,
    PURPOSES,
    evaluate_purpose,
    is_known,
)
from ..govflow.tiers import CLASSIFICATION_CEILING, TIERS
from .certification import (
    CTL_CONTRACT_01,
    CTL_EVAL_01,
    CTL_SOD_01,
    FAITHFULNESS_FLOOR,
    CertificationDecision,
    RegistryEntry,
    evaluate,
    get_entry,
    parse_contract,
    register,
)
from .patterns import PATTERNS_BY_ID
from .templates import UNASSIGNED, AgentTemplate

# The document's self-description. A `kind` and a `schema` cost two lines and
# buy the ability to change the shape later without guessing what an old
# document meant.
KIND = "agent_template"
SCHEMA = "v1"

# CTL-CODE-01 (import allow-list) and CTL-COL-01 (column grant) are the codegen
# gate's ids, reused here because the template declares the same things the
# generated code will be judged against. Checking them at authoring time is the
# same rule read earlier, not a second rule.
CTL_CODE_01 = "CTL-CODE-01"
CTL_COL_01 = "CTL-COL-01"
CTL_TIER_01 = "CTL-TIER-01"

# Check keys.
CHK_SCHEMA = "schema"
CHK_PATTERN = "pattern"
CHK_TOOLS = "tools"
CHK_IMPORTS = "imports"
CHK_PURPOSES = "purposes"
CHK_TIER = "tier"
CHK_COLUMNS = "columns"
CHK_CONTRACT = "contract"
CHK_EVALS = "evals"
CHK_OWNER = "owner"
CHK_SOD = "sod"

# The fence. A refusal in any of these blocks the deploy; the rest are
# certification gates, which block `certified` and nothing else.
DEPLOY_BLOCKING: frozenset[str] = frozenset(
    {
        CHK_SCHEMA,
        CHK_PATTERN,
        CHK_TOOLS,
        CHK_IMPORTS,
        CHK_PURPOSES,
        CHK_TIER,
        CHK_COLUMNS,
        CHK_CONTRACT,
    }
)

# Tiers that write no code, so an import list on them is a contradiction rather
# than a long list to check.
_NO_CODE_TIERS = frozenset({"L0", "L1"})

_RANK = {t: i for i, t in enumerate(TIERS)}

# The one purpose with a defined column grant in this build (access.py). Any
# other purpose leaves the column check unarmed, which is the honest reading:
# there is no grant to test the names against yet.
_PURPOSE_GRANTS: dict[str, tuple[str, ...]] = {
    "fair_lending": tuple(FAIR_LENDING_GRANT),
}

# Words that make an owner a group rather than a person. Certification gate 2
# wants a named individual: a queue cannot be asked why it signed.
_TEAM_WORDS = frozenset(
    {"team", "squad", "group", "guild", "pod", "chapter", "dept", "department",
     "org", "function", "unit", "desk", "office"}
)


class SpecError(ValueError):
    """The document is not YAML, or is not a mapping. Everything milder than
    this is a check refusal, so the panel does the explaining, not a traceback."""


# --------------------------------------------------------------------------
# Vocabularies (what the editor offers as reference chips)
# --------------------------------------------------------------------------
@cache
def tool_vocabulary() -> tuple[str, ...]:
    """Every tool any agent may call, from agents.yaml. Guardrails enforces the
    per-agent slice of this at run time; a template may not invent a name."""
    agents = load_agents().get("agents", []) or []
    return tuple(sorted({t for a in agents for t in (a.get("tools") or [])}))


@cache
def eval_check_ids() -> tuple[str, ...]:
    """Check ids the eval gate already implements (evals.yaml). A hook naming
    one of these resolves today; a hook naming anything else is a case someone
    still has to write, which is allowed but worth showing."""
    checks = load_evals().get("checks", []) or []
    return tuple(sorted({c.get("id", "") for c in checks if c.get("id")}))


def import_vocabulary(max_tier: str) -> tuple[str, ...]:
    """The allow-list that applies at a tier. L3 widens the analytical list; the
    deny lists do not move at any tier (allowlist.py)."""
    allowed = L3_ALLOWED_IMPORTS if max_tier == "L3" else ALLOWED_IMPORTS
    return tuple(sorted(allowed))


def pattern_vocabulary() -> tuple[str, ...]:
    return tuple(PATTERNS_BY_ID)


# --------------------------------------------------------------------------
# The document
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class TemplateSpec:
    """A parsed template document. Lenient by construction: a missing or
    wrong-typed field lands here as an empty value and is refused by a check
    that can explain itself, rather than raising on the way in."""

    id: str
    name: str
    version: str
    pattern: str
    purpose: str
    max_tier: str
    purposes: tuple[str, ...]
    contract: str | None
    columns: tuple[str, ...]
    tools: tuple[str, ...]
    imports: tuple[str, ...]
    eval_floor: float | None
    eval_hooks: tuple[str, ...]
    owner: str
    validator: str | None

    @property
    def dataset(self) -> str:
        """The dataset the contract names, or '' when none is declared."""
        return parse_contract(self.contract)[0]

    @property
    def classification(self) -> str | None:
        return DATA_CLASSIFICATION.get(self.dataset)


def _str(v: Any, default: str = "") -> str:
    return v if isinstance(v, str) else default


def _strs(v: Any) -> tuple[str, ...]:
    if not isinstance(v, list):
        return ()
    return tuple(x for x in v if isinstance(x, str))


def _mapping(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def from_doc(doc: dict) -> TemplateSpec:
    """Build a spec from a parsed document, tolerating anything malformed."""
    data = _mapping(doc.get("data"))
    evals = _mapping(doc.get("evals"))
    floor = evals.get("floor")
    contract = data.get("contract")
    validator = doc.get("validator")
    return TemplateSpec(
        id=_str(doc.get("id")),
        name=_str(doc.get("name")),
        version=_str(doc.get("version")),
        pattern=_str(doc.get("pattern")),
        purpose=_str(doc.get("purpose")),
        max_tier=_str(doc.get("max_tier")),
        purposes=_strs(data.get("purposes")),
        contract=contract if isinstance(contract, str) and contract else None,
        columns=_strs(data.get("columns")),
        tools=_strs(doc.get("tools")),
        imports=_strs(doc.get("imports")),
        eval_floor=float(floor) if isinstance(floor, (int, float)) else None,
        eval_hooks=_strs(evals.get("hooks")),
        owner=_str(doc.get("owner")),
        validator=validator if isinstance(validator, str) and validator else None,
    )


def parse_yaml(text: str) -> tuple[TemplateSpec, dict]:
    """Parse an editor buffer. Raises SpecError only when there is no document
    to check; everything else is a check's job."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SpecError(f"not valid YAML: {exc}") from exc
    if doc is None:
        raise SpecError("the document is empty")
    if not isinstance(doc, dict):
        raise SpecError(
            f"the document is a {type(doc).__name__}, not a mapping of fields"
        )
    return from_doc(doc), doc


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------
def _s(value: Any) -> str:
    """A scalar or flat list as unambiguous inline YAML.

    json.dumps emits a subset of YAML that PyYAML reads back identically, which
    sidesteps every quoting question a hand-rolled emitter would have to answer
    (a name with a colon, a version that looks like a float, a null)."""
    return json.dumps(value)


def _folded(text: str, indent: str = "  ", width: int = 72) -> str:
    """Prose as a folded block. `>-` joins the lines back with single spaces on
    parse, so the round trip is exact for text without deliberate line breaks."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return ">-\n" + "\n".join(indent + ln for ln in lines)


def to_yaml(t: AgentTemplate) -> str:
    """Render a template as the editable document.

    `status` is not emitted, and the schema check refuses it if someone adds it:
    certification.py computes status from the gates and never stores it, so a
    document carrying one would be asserting a verdict nobody reached."""
    return f"""# Agent template. Everything here is authored; status is not a field --
# certification.py computes it from the gates every time it is asked.
kind: {KIND}
schema: {SCHEMA}

id: {_s(t.id)}
name: {_s(t.name)}
version: {_s(t.version)}
pattern: {_s(t.pattern)}          # a pattern-catalog id (patterns.py)

purpose: {_folded(t.purpose)}

# The most autonomy an instance may ask for. The run still resolves
# min(this, classification ceiling, role ceiling), so this can only lower it.
max_tier: {_s(t.max_tier)}

data:
  # Purpose-matrix columns this template may run under (purpose_matrix.py).
  purposes: {_s(list(t.purposes))}
  # The dataset an instance binds to. The content SHA is pinned at deploy, not
  # here: a blueprint that pinned one would be claiming every instance runs
  # against today's file.
  contract: {_s(t.contract)}
  # The column grant. Checked against the purpose's grant where one is defined.
  columns: {_s(list(t.columns))}

# Tools the agent may call. Guardrails enforces this at run time; the names
# come from agents.yaml and cannot be invented here.
tools: {_s(list(t.tools))}

# Imports the generated code may use, at L2 and above. Checked against the
# codegen allow-list for the declared tier. Meaningless below L2, where no
# code is written at all.
imports: {_s(list(t.imports))}

evals:
  floor: {_s(t.eval_floor)}
  hooks: {_s(list(t.evals))}

# Certification gate 2: a named individual, not a queue.
owner: {_s(t.owner)}
# Certification gate 4 (CTL-SOD-01): must differ from the author.
validator: {_s(t.validator)}
"""


def _line_of(source: str, token: str) -> int:
    """The 1-based line a token first appears on, for evidence chips. 0 when it
    cannot be found, which the UI reads as 'no line to point at'."""
    if not token:
        return 0
    for i, line in enumerate(source.splitlines(), start=1):
        if token in line:
            return i
    return 0


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------
# Required keys and the type each must carry. `data` and `evals` are mappings
# with their own required keys, listed under them.
_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "kind": str,
    "schema": str,
    "id": str,
    "name": str,
    "version": str,
    "pattern": str,
    "purpose": str,
    "max_tier": str,
    "data": dict,
    "tools": list,
    "imports": list,
    "evals": dict,
    "owner": str,
}
# `validator` is required to be present but may be null, so it is typed
# separately from the rest.
_NULLABLE = {"validator"}
_DATA_KEYS: dict[str, type | tuple[type, ...]] = {"purposes": list, "columns": list}
_DATA_NULLABLE = {"contract"}
_EVAL_KEYS: dict[str, type | tuple[type, ...]] = {"floor": (int, float), "hooks": list}

# Keys a document must not carry, and why. Both are computed elsewhere, and a
# document asserting one would be claiming a verdict it cannot reach.
_REFUSED_KEYS = {
    "status": (
        "status is computed from the certification gates every time it is asked "
        "(certification.py) and is never stored; a document cannot assert one"
    ),
    "governance": (
        "the governance block is computed, not authored; it is rendered beside "
        "the editor and has no place in the document"
    ),
}


def _check_schema(doc: dict, source: str) -> CheckReading:
    items: list[Observation] = []

    def obs(subject: str, allowed: bool, reason: str) -> None:
        items.append(
            Observation(subject, _line_of(source, subject), allowed, reason,
                        "" if allowed else "schema")
        )

    for key, typ in _REQUIRED.items():
        if key not in doc:
            obs(key, False, "required key is missing")
        elif not isinstance(doc[key], typ):
            want = typ.__name__ if isinstance(typ, type) else "number"
            obs(key, False, f"must be a {want}, got {type(doc[key]).__name__}")
        else:
            obs(key, True, f"present, a {type(doc[key]).__name__}")

    for key in _NULLABLE:
        if key not in doc:
            obs(key, False, "required key is missing (may be null, may not be absent)")
        elif doc[key] is not None and not isinstance(doc[key], str):
            obs(key, False, f"must be a string or null, got {type(doc[key]).__name__}")
        else:
            obs(key, True, "present" + (" (null)" if doc[key] is None else ""))

    if isinstance(doc.get("kind"), str) and doc["kind"] != KIND:
        obs(doc["kind"], False, f"kind must be {KIND!r}")
    if isinstance(doc.get("schema"), str) and doc["schema"] != SCHEMA:
        obs(doc["schema"], False, f"this build reads schema {SCHEMA!r} only")

    data = doc.get("data")
    if isinstance(data, dict):
        for key, typ in _DATA_KEYS.items():
            if key not in data:
                obs(f"data.{key}", False, "required key is missing")
            elif not isinstance(data[key], typ):
                obs(f"data.{key}", False, f"must be a {typ.__name__}")
            else:
                obs(f"data.{key}", True, "present")
        for key in _DATA_NULLABLE:
            if key not in data:
                obs(f"data.{key}", False, "required key is missing (may be null)")
            elif data[key] is not None and not isinstance(data[key], str):
                obs(f"data.{key}", False, "must be a string or null")
            else:
                obs(f"data.{key}", True, "present")

    evals = doc.get("evals")
    if isinstance(evals, dict):
        for key, typ in _EVAL_KEYS.items():
            if key not in evals:
                obs(f"evals.{key}", False, "required key is missing")
            elif not isinstance(evals[key], typ):
                obs(f"evals.{key}", False, "wrong type")
            else:
                obs(f"evals.{key}", True, "present")

    known = set(_REQUIRED) | _NULLABLE
    for key in doc:
        if key in _REFUSED_KEYS:
            obs(key, False, _REFUSED_KEYS[key])
        elif key not in known:
            obs(key, False, "not a field in this schema (a typo reads as a new key)")

    return CheckReading(
        key=CHK_SCHEMA,
        label="Document schema",
        controls=(),
        examines="every key the document carries, and every key it should",
        rule=f"the {SCHEMA} agent-template schema; status and governance are "
        "computed, never authored",
        unit="key",
        examined=len(items),
        items=tuple(items),
    )


def _check_pattern(spec: TemplateSpec, source: str) -> CheckReading:
    items = ()
    if spec.pattern:
        known = spec.pattern in PATTERNS_BY_ID
        items = (
            Observation(
                spec.pattern,
                _line_of(source, spec.pattern),
                known,
                f"{PATTERNS_BY_ID[spec.pattern].name} in the catalog"
                if known
                else f"not a pattern id; the catalog holds {', '.join(PATTERNS_BY_ID)}",
                "" if known else "schema",
            ),
        )
    return CheckReading(
        key=CHK_PATTERN,
        label="Architecture pattern",
        controls=(),
        examines="the declared pattern",
        rule="the pattern catalog (patterns.py), anchored on Building Effective Agents",
        unit="pattern",
        examined=len(items),
        items=items,
    )


def _check_tools(spec: TemplateSpec, source: str) -> CheckReading:
    vocab = tool_vocabulary()
    items = tuple(
        Observation(
            t,
            _line_of(source, t),
            t in vocab,
            "on the tool allow-list" if t in vocab
            else "no agent in agents.yaml declares this tool, so guardrails would block it",
            "" if t in vocab else "guardrails",
        )
        for t in spec.tools
    )
    return CheckReading(
        key=CHK_TOOLS,
        label="Tool allow-list",
        controls=("guardrails",),
        examines="every tool the template pre-wires",
        rule="the union of tools declared in agents.yaml, which guardrails enforces per agent",
        unit="tool",
        examined=len(items),
        items=items,
    )


def _check_imports(spec: TemplateSpec, source: str) -> CheckReading:
    tier = spec.max_tier
    base = dict(
        key=CHK_IMPORTS,
        label="Import allow-list",
        controls=(CTL_CODE_01,),
        examines="every import the generated code may use",
        unit="import",
    )
    if tier in _NO_CODE_TIERS:
        # Not unarmed: the rule is known and it has something to say. An import
        # list at a tier that writes no code is a contradiction in the document,
        # not a check with nothing to read.
        items = tuple(
            Observation(
                m, _line_of(source, m), False,
                f"{tier} writes no code, so an import list here cannot mean anything",
                CTL_CODE_01,
            )
            for m in spec.imports
        )
        return CheckReading(
            **base,
            rule=f"{tier} writes no code (tiers.py), so the list must be empty",
            examined=len(items),
            items=items,
        )
    allowed = set(import_vocabulary(tier))
    items = tuple(
        Observation(
            m, _line_of(source, m), m in allowed,
            f"on the {tier} allow-list" if m in allowed
            else f"not on the {tier} allow-list (allowlist.py); the sandbox could not import it",
            "" if m in allowed else CTL_CODE_01,
        )
        for m in spec.imports
    )
    return CheckReading(
        **base,
        rule=f"the {tier} import allow-list in codegen/allowlist.py",
        examined=len(items),
        items=items,
    )


def _check_purposes(spec: TemplateSpec, source: str) -> CheckReading:
    dataset = spec.dataset
    base = dict(
        key=CHK_PURPOSES,
        label="Purpose limitation",
        controls=(CTL_PURP_01,),
        examines="every purpose the template may run under, against its dataset",
        unit="purpose",
    )
    if not dataset:
        return CheckReading(
            **base,
            rule="the purpose matrix needs a dataset; this document declares no contract",
            armed=False,
        )
    items: list[Observation] = []
    for p in spec.purposes:
        line = _line_of(source, p)
        if p not in PURPOSES:
            items.append(
                Observation(p, line, False,
                            f"not a purpose in the matrix; it holds {', '.join(PURPOSES)}",
                            CTL_PURP_01)
            )
        elif not is_known(dataset, p):
            items.append(
                Observation(p, line, False, f"no matrix cell for {dataset}", CTL_PURP_01)
            )
        else:
            d = evaluate_purpose(dataset, p)
            items.append(Observation(p, line, d.permitted, d.reason, d.control or ""))
    return CheckReading(
        **base,
        rule=f"the purpose-by-dataset matrix for {dataset} (purpose_matrix.py)",
        examined=len(items),
        items=tuple(items),
    )


def _check_tier(spec: TemplateSpec, source: str) -> CheckReading:
    base = dict(
        key=CHK_TIER,
        label="Autonomy ceiling",
        controls=(CTL_TIER_01,),
        examines="the tier this template may ask for",
        unit="tier",
    )
    line = _line_of(source, spec.max_tier)
    if spec.max_tier and spec.max_tier not in _RANK:
        return CheckReading(
            **base,
            rule=f"one of {', '.join(TIERS)} (tiers.py)",
            examined=1,
            items=(
                Observation(spec.max_tier, line, False,
                            f"not a tier; the ladder is {', '.join(TIERS)}", CTL_TIER_01),
            ),
        )
    classification = spec.classification
    if classification is None:
        return CheckReading(
            **base,
            rule="the ceiling comes from the dataset's classification; no dataset is declared",
            armed=False,
        )
    ceiling = CLASSIFICATION_CEILING[classification]
    ok = _RANK[spec.max_tier] <= _RANK[ceiling]
    reason = (
        f"{classification} data allows up to {ceiling}, and the template asks for "
        f"{spec.max_tier}"
        if ok
        else (
            f"{classification} data allows up to {ceiling}; asking for {spec.max_tier} "
            f"would raise a ceiling a template may only lower"
        )
    )
    return CheckReading(
        **base,
        rule=f"the {classification} ceiling of {ceiling} for {spec.dataset} (tiers.py)",
        examined=1,
        items=(Observation(spec.max_tier, line, ok, reason, "" if ok else CTL_TIER_01),),
    )


def _check_columns(spec: TemplateSpec, source: str) -> CheckReading:
    base = dict(
        key=CHK_COLUMNS,
        label="Column grant",
        controls=(CTL_COL_01,),
        examines="every column the template names",
        unit="column",
    )
    granted: set[str] = set()
    named: list[str] = []
    for p in spec.purposes:
        if p in _PURPOSE_GRANTS:
            granted.update(_PURPOSE_GRANTS[p])
            named.append(p)
    if not named:
        return CheckReading(
            **base,
            rule=(
                "no declared purpose has a column grant defined in this build "
                "(access.py defines fair_lending only), so there is nothing to test against"
            ),
            armed=False,
        )
    items = tuple(
        Observation(
            c, _line_of(source, c), c in granted,
            f"inside the {' + '.join(named)} grant" if c in granted
            else f"outside the {' + '.join(named)} grant; the scoped table would not carry it",
            "" if c in granted else CTL_COL_01,
        )
        for c in spec.columns
    )
    return CheckReading(
        **base,
        rule=f"the column grant for {' + '.join(named)} (govflow/access.py)",
        examined=len(items),
        items=items,
    )


def _check_contract(spec: TemplateSpec, source: str) -> CheckReading:
    base = dict(
        key=CHK_CONTRACT,
        label="Data contract",
        controls=(CTL_CONTRACT_01,),
        examines="the dataset the contract names",
        unit="contract",
    )
    if spec.contract is None:
        # Refused, not absent-and-fine: a template with no dataset cannot have
        # its purposes, tier or columns checked either, and three unarmed checks
        # downstream is what that costs.
        return CheckReading(
            **base,
            rule="a registered dataset id; the SHA is pinned at deploy",
            examined=1,
            items=(
                Observation(
                    "contract", _line_of(source, "contract"), False,
                    "no dataset declared, so purpose, tier and column checks have "
                    "nothing to read; certification gate 3 cannot pass",
                    CTL_CONTRACT_01,
                ),
            ),
        )
    dataset, sha = parse_contract(spec.contract)
    known = dataset in DATASETS_BY_ID
    reason = (
        f"{dataset} is registered ({DATA_CLASSIFICATION.get(dataset, 'unclassified')}); "
        "the content SHA is pinned at deploy"
        if known
        else f"{dataset!r} is not a registered dataset (datasets/registry.py)"
    )
    items = [Observation(dataset, _line_of(source, dataset), known, reason,
                         "" if known else CTL_CONTRACT_01)]
    if sha:
        items.append(
            Observation(
                f"sha:{sha}", _line_of(source, sha), False,
                "a template may not pin a content SHA: it is a fact about one "
                "snapshot, recomputed and written when an instance deploys",
                CTL_CONTRACT_01,
            )
        )
    return CheckReading(
        **base,
        rule="a registered dataset id, with no SHA pinned in the blueprint",
        examined=len(items),
        items=tuple(items),
    )


def _check_evals(spec: TemplateSpec, source: str) -> CheckReading:
    implemented = set(eval_check_ids())
    items: list[Observation] = []
    if spec.eval_floor is None:
        items.append(
            Observation("floor", _line_of(source, "floor"), False,
                        "no faithfulness floor declared", CTL_EVAL_01)
        )
    else:
        ok = spec.eval_floor >= FAITHFULNESS_FLOOR
        items.append(
            Observation(
                f"floor {spec.eval_floor:g}", _line_of(source, "floor"), ok,
                f"at or above the certification floor of {FAITHFULNESS_FLOOR:g}" if ok
                else f"below the certification floor of {FAITHFULNESS_FLOOR:g}; "
                     "a template cannot lower the bar its instances are certified against",
                "" if ok else CTL_EVAL_01,
            )
        )
    if not spec.eval_hooks:
        items.append(
            Observation("hooks", _line_of(source, "hooks"), False,
                        "no eval hooks declared; an empty suite cannot pass the gate",
                        CTL_EVAL_01)
        )
    for h in spec.eval_hooks:
        resolved = h in implemented
        items.append(
            Observation(
                h, _line_of(source, h), True,
                "resolves to a check the eval gate implements today (evals.yaml)"
                if resolved
                else "named, not yet implemented: the scaffold writes the suite empty "
                     "and the case has to be written before certification",
                "",
            )
        )
    return CheckReading(
        key=CHK_EVALS,
        label="Eval suite",
        controls=(CTL_EVAL_01,),
        examines="the faithfulness floor and every declared hook",
        rule=f"a floor at or above {FAITHFULNESS_FLOOR:g} and at least one hook "
        "(certification gate 1)",
        unit="declaration",
        examined=len(items),
        items=tuple(items),
    )


def _is_person(owner: str) -> bool:
    if not owner or owner == UNASSIGNED:
        return False
    return not any(w in _TEAM_WORDS for w in owner.lower().replace("-", " ").split())


def _check_owner(spec: TemplateSpec, source: str) -> CheckReading:
    owner = spec.owner
    line = _line_of(source, owner) if owner else _line_of(source, "owner")
    if not owner or owner == UNASSIGNED:
        reason = (
            "unassigned, which is what every shipped template carries: a blueprint "
            "cannot own the instances made from it. Name a person before certifying."
        )
        ok = False
    elif not _is_person(owner):
        reason = (
            "reads as a team rather than a person; a queue cannot be asked why it "
            "signed, which is the point of gate 2"
        )
        ok = False
    else:
        reason = "a named individual"
        ok = True
    return CheckReading(
        key=CHK_OWNER,
        label="Owner",
        controls=(),
        examines="the declared owner",
        rule="a named individual, not UNASSIGNED and not a team (certification gate 2)",
        unit="owner",
        examined=1,
        items=(Observation(owner or "(none)", line, ok, reason, "" if ok else "owner"),),
    )


def _check_sod(spec: TemplateSpec, source: str) -> CheckReading:
    v = spec.validator
    line = _line_of(source, v) if v else _line_of(source, "validator")
    if not v:
        ok, reason = False, (
            "no validator assigned; certification needs an independent signature "
            "and a template ships without one"
        )
    elif v == spec.owner:
        ok, reason = False, (
            f"{v!r} is also the owner. CTL-SOD-01 refuses a self-signoff at "
            "certification time exactly as it does at approval time"
        )
    else:
        ok, reason = True, f"independent of the owner ({spec.owner or 'unset'})"
    return CheckReading(
        key=CHK_SOD,
        label="Segregation of duties",
        controls=(CTL_SOD_01,),
        examines="the declared validator against the owner",
        rule="a validator who is not the author or the owner (certification gate 4)",
        unit="validator",
        examined=1,
        items=(Observation(v or "(none)", line, ok, reason, "" if ok else CTL_SOD_01),),
    )


def validate(spec: TemplateSpec, doc: dict, source: str = "") -> list[CheckReading]:
    """Every check, in the order the panel prints them: the fence first, the
    certification gates last."""
    return [
        _check_schema(doc, source),
        _check_pattern(spec, source),
        _check_tools(spec, source),
        _check_imports(spec, source),
        _check_contract(spec, source),
        _check_purposes(spec, source),
        _check_tier(spec, source),
        _check_columns(spec, source),
        _check_evals(spec, source),
        _check_owner(spec, source),
        _check_sod(spec, source),
    ]


def validate_text(text: str) -> tuple[TemplateSpec, list[CheckReading]]:
    """Parse and check an editor buffer in one call."""
    spec, doc = parse_yaml(text)
    return spec, validate(spec, doc, text)


def summary_of(check: CheckReading) -> str:
    """CheckReading.summary, with the one line that assumes it is reading code
    rewritten for a document. Everything else is the gate's own wording, because
    the check knows what its count means and no screen should re-guess it."""
    if check.verdict == NO_SUBJECT:
        return f"No {check.unit} declared, so there was nothing to judge."
    return check.summary


def blocking(checks: list[CheckReading]) -> list[CheckReading]:
    """The policy refusals that stop a deploy. A refused certification gate is
    absent here on purpose: it stops `certified`, not the draft."""
    return [c for c in checks if c.key in DEPLOY_BLOCKING and c.refusals]


def deployable(checks: list[CheckReading]) -> bool:
    return not blocking(checks)


# --------------------------------------------------------------------------
# Deploy
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class DeployResult:
    """What a deploy produced: a registry entry and the gates' verdict on it."""

    entry: RegistryEntry
    decision: CertificationDecision
    contract: str | None
    sha_note: str

    def report(self) -> str:
        """The same shape `sentinel new-agent` prints (scaffold.py), so the two
        paths to an agent read alike."""
        lines = [
            f"  registry {self.entry.id} v{self.entry.version} "
            f"status={self.decision.status} owner={self.entry.owner}"
        ]
        if self.contract:
            lines.append(f"  contract {self.contract}")
        if not self.decision.certifiable:
            lines.append("  note     status cannot reach 'certified' until:")
            for g in self.decision.blocking:
                lines.append(f"             - {g.name} (currently: {g.detail})")
        return "\n".join(lines)


class DeployRefused(Exception):
    """The deploy was refused: a policy check said no, or the id is taken."""


def deploy(spec: TemplateSpec, checks: list[CheckReading], author: str) -> DeployResult:
    """Register the spec as a draft analysis-agent.

    This is `certification.register` with the contract's SHA computed now, which
    is the honest binding: a certification is evidence about the data as it is at
    the moment it is granted, and CTL-CONTRACT-01 compares against it later.

    The entry lands at draft with no eval suite, exactly as the scaffolding CLI
    leaves one, because no cases have been written. Nothing is written to disk
    and no process starts; an enterprise deployment would push the spec to the
    agent runtime from here."""
    refused = blocking(checks)
    if refused:
        names = "; ".join(
            f"{c.label}: {', '.join(o.subject for o in c.refusals)}" for c in refused
        )
        raise DeployRefused(
            f"policy checks refused this spec, so it cannot reach the registry -- {names}"
        )
    if get_entry(spec.id) is not None:
        raise DeployRefused(
            f"{spec.id!r} is already in the registry. Change the id before deploying, "
            "or the two entries would be indistinguishable in the inventory."
        )

    dataset = spec.dataset
    sha: str | None = None
    note = "no dataset declared, so no SHA was pinned"
    if dataset:
        try:
            sha = dataset_sha(dataset)
            note = f"content SHA {sha} computed from {dataset} at deploy"
        except (FileNotFoundError, OSError, KeyError) as exc:
            note = (
                f"{dataset} could not be fingerprinted "
                f"({exc.__class__.__name__}), so no SHA was pinned"
            )
    contract = f"{dataset}@sha:{sha}" if sha else (dataset or None)

    entry = RegistryEntry(
        id=spec.id,
        version=spec.version,
        author=author,
        owner=spec.owner,
        owner_is_person=_is_person(spec.owner),
        validator=spec.validator,
        data_contract=contract,
        # No suite reference and no score: the scaffold writes the suite with no
        # cases, so gate 1 fails and the entry stays draft. Claiming a
        # faithfulness here would be inventing a measurement.
        eval_suite_ref=None,
        faithfulness=None,
    )
    register(entry)
    return DeployResult(entry, evaluate(entry), contract, note)
