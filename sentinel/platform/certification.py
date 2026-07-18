"""The certification lifecycle (section 11) and the analysis-agent registry.

An analysis-agent earns the right to run. It moves draft -> candidate ->
certified, and only a certified agent is visible to the Plan stage, so an
uncertified analysis cannot silently reach a user. Four gates stand between an
agent and `certified`:

  1. an eval suite exists and passes (faithfulness >= the floor)   -> CTL-EVAL-01
  2. the owner is assigned, and is a person, not a team
  3. a data contract is declared
  4. an independent validator signs, where validator != author     -> CTL-SOD-01

Gate 4 reuses the segregation-of-duties control from v0: an author cannot be the
validator of their own work, at certification time exactly as at approval time.

The status is computed from the gates, never stored, so a pill on the Registry
screen can never drift from the gate results behind it. The seeded registry holds
one certified agent (the golden-path fair-lending analysis) and one visibly
refused agent (cohort-retention v0.3), because everyone demos the happy path and
the refusal is the differentiator (section 10.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The catalogue controls this lifecycle reuses. Both are defined elsewhere:
# CTL-EVAL-01 is the narration-faithfulness control (govflow), applied here to the
# certification eval floor; CTL-SOD-01 is segregation of duties (v0).
CTL_EVAL_01 = "CTL-EVAL-01"
CTL_SOD_01 = "CTL-SOD-01"
# Data-contract drift (section 5, Stage 3): the dataset changed since the
# certification was granted, so the certification is evidence about a dataset
# that no longer exists. Checked at Access; see datasets/fingerprint.py.
CTL_CONTRACT_01 = "CTL-CONTRACT-01"

# Lifecycle states (section 11).
STATUS_DRAFT = "draft"
STATUS_CANDIDATE = "candidate"
STATUS_CERTIFIED = "certified"
STATUS_DEPRECATED = "deprecated"
STATUS_REFUSED = "refused"

FAITHFULNESS_FLOOR = 0.90


class CertificationError(Exception):
    """Raised when a certification action is itself refused (e.g. CTL-SOD-01)."""


def parse_contract(contract: str | None) -> tuple[str, str | None]:
    """Split a data contract 'dataset@sha:abc123' into (dataset_id, sha).

    A contract with no SHA returns (dataset_id, None); an empty contract returns
    ('', None). This is pure string parsing; the SHA is recomputed elsewhere.
    """
    if not contract:
        return "", None
    dataset, _, rest = contract.partition("@")
    sha = None
    if rest.startswith("sha:"):
        sha = rest[len("sha:"):] or None
    return dataset, sha


@dataclass(frozen=True)
class ContractCheck:
    """The data-contract drift verdict for one entry (CTL-CONTRACT-01)."""

    entry_id: str
    ok: bool
    drifted: bool
    certified_sha: str | None
    current_sha: str | None
    detail: str

    @property
    def control(self) -> str:
        return CTL_CONTRACT_01


def check_contract(
    entry: RegistryEntry, current_sha: str | None, note: str = ""
) -> ContractCheck:
    """Compare the entry's certified dataset SHA against the current SHA.

    Drift (a mismatch) fires CTL-CONTRACT-01: flag and require recertification
    rather than run silently on data the certification never covered. A dataset
    that cannot be fingerprinted (current_sha is None) is reported as
    unverifiable, not silently passed.
    """
    _, certified = parse_contract(entry.data_contract)
    if current_sha is None:
        return ContractCheck(
            entry.id, ok=False, drifted=False, certified_sha=certified,
            current_sha=None, detail=note or "dataset SHA could not be recomputed",
        )
    if certified is None:
        return ContractCheck(
            entry.id, ok=False, drifted=False, certified_sha=None,
            current_sha=current_sha, detail="no SHA declared in the data contract",
        )
    if certified == current_sha:
        return ContractCheck(
            entry.id, ok=True, drifted=False, certified_sha=certified,
            current_sha=current_sha, detail=f"contract SHA {certified} matches current data",
        )
    return ContractCheck(
        entry.id, ok=False, drifted=True, certified_sha=certified, current_sha=current_sha,
        detail=(
            f"CTL-CONTRACT-01: dataset drifted since certification "
            f"(certified {certified}, current {current_sha}); recertification required"
        ),
    )


@dataclass(frozen=True)
class GateCheck:
    """One certification gate: did it pass, and why or why not."""

    name: str
    passed: bool
    detail: str
    control: str | None = None  # set where the gate maps to a catalogue control


@dataclass
class RegistryEntry:
    """An analysis-agent in the registry (data model, section 12)."""

    id: str
    version: str
    author: str
    owner: str = "UNASSIGNED"
    owner_is_person: bool = False
    validator: str | None = None
    data_contract: str | None = None
    eval_suite_ref: str | None = None
    faithfulness: float | None = None
    last_evaluated: str | None = None
    certified_at: str | None = None
    deprecated: bool = False

    def label(self) -> str:
        return f"{self.id} v{self.version}"


def _gates(entry: RegistryEntry, floor: float) -> list[GateCheck]:
    """The four certification gates, evaluated against an entry."""
    eval_ran = entry.eval_suite_ref is not None and entry.faithfulness is not None
    eval_ok = eval_ran and entry.faithfulness >= floor  # type: ignore[operator]
    if not eval_ran:
        eval_detail = "no eval suite defined"
    elif eval_ok:
        eval_detail = f"faithfulness {entry.faithfulness:.2f} >= floor {floor:.2f}"
    else:
        eval_detail = f"faithfulness {entry.faithfulness:.2f} < floor {floor:.2f}"

    owner_ok = bool(entry.owner) and entry.owner != "UNASSIGNED" and entry.owner_is_person
    owner_detail = (
        f"owner {entry.owner!r} (a person)"
        if owner_ok
        else f"owner {entry.owner!r} is unassigned or not a person"
    )

    contract_ok = bool(entry.data_contract)
    contract_detail = (
        f"data contract {entry.data_contract}" if contract_ok else "no data contract declared"
    )

    independent = bool(entry.validator) and entry.validator != entry.author
    if not entry.validator:
        val_detail = "no validator assigned"
    elif entry.validator == entry.author:
        val_detail = f"validator {entry.validator!r} is the author (self-signoff refused)"
    else:
        val_detail = f"independent validator {entry.validator!r}"

    return [
        GateCheck("eval suite passes", eval_ok, eval_detail, CTL_EVAL_01),
        GateCheck("owner is a person", owner_ok, owner_detail),
        GateCheck("data contract declared", contract_ok, contract_detail),
        GateCheck("independent validator", independent, val_detail, CTL_SOD_01),
    ]


@dataclass(frozen=True)
class CertificationDecision:
    """Whether an entry can be certified, gate by gate."""

    entry_id: str
    status: str
    gates: list[GateCheck] = field(default_factory=list)

    @property
    def certifiable(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def blocking(self) -> list[GateCheck]:
        return [g for g in self.gates if not g.passed]

    def summary(self) -> str:
        if self.status == STATUS_CERTIFIED:
            return f"{self.entry_id}: certified (all gates pass)."
        reasons = "; ".join(f"{g.name}: {g.detail}" for g in self.blocking)
        return f"{self.entry_id}: {self.status} -- blocked on {reasons}"


def _status_from_gates(entry: RegistryEntry, gates: list[GateCheck]) -> str:
    by_name = {g.name: g for g in gates}
    if entry.deprecated:
        return STATUS_DEPRECATED
    if all(g.passed for g in gates):
        return STATUS_CERTIFIED
    eval_ran = entry.eval_suite_ref is not None and entry.faithfulness is not None
    if not eval_ran:
        return STATUS_DRAFT
    if not by_name["eval suite passes"].passed:
        # Evals ran and failed the floor: refused, not merely draft.
        return STATUS_REFUSED
    # Evals pass; awaiting owner / contract / validator.
    return STATUS_CANDIDATE


def evaluate(entry: RegistryEntry, floor: float = FAITHFULNESS_FLOOR) -> CertificationDecision:
    """Evaluate an entry against the four gates and compute its lifecycle status."""
    gates = _gates(entry, floor)
    return CertificationDecision(entry.id, _status_from_gates(entry, gates), gates)


def status_of(entry: RegistryEntry, floor: float = FAITHFULNESS_FLOOR) -> str:
    return evaluate(entry, floor).status


def assign_validator(
    entry: RegistryEntry, validator: str, floor: float = FAITHFULNESS_FLOOR
) -> CertificationDecision:
    """The Registry screen's action. Refuses a self-signoff (CTL-SOD-01), then
    sets the validator and returns the recomputed decision.

    Assigning an independent validator clears the SoD gate; it does not certify
    an entry whose other gates still fail (a low-faithfulness agent stays refused
    even with a valid validator). That layering is the honest part of the demo.
    """
    if validator == entry.author:
        raise CertificationError(
            f"CTL-SOD-01: validator {validator!r} is the author of {entry.label()}; "
            "self-signoff refused. Certification requires an independent validator."
        )
    entry.validator = validator
    return evaluate(entry, floor)


# -- The seeded registry ---------------------------------------------------
# One certified agent (the golden path) and one visibly refused agent.
_REGISTRY: list[RegistryEntry] = [
    RegistryEntry(
        id="fair-lending",
        version="1.4",
        author="priya.raman",
        owner="Dana Okafor",
        owner_is_person=True,
        validator="sam.mendes",
        # Pinned to the real content SHA of sentinel/data/german_credit.csv, so
        # the live contract check passes honestly (no drift on static data). If
        # the CSV ever changes, test_contract's pin test fails loudly.
        data_contract="german_credit@sha:188808",
        eval_suite_ref="evals/fair_lending.yaml",
        faithfulness=0.94,
        last_evaluated="2026-05-02",
        certified_at="2026-05-02",
    ),
    # The differentiator: refused on two independent grounds. Faithfulness is
    # below the floor (CTL-EVAL-01), and no independent validator is assigned
    # (validator is None; the author is also the owner), so the SoD gate fails
    # too (CTL-SOD-01). Contrast deposit-elasticity below, which passes its evals
    # and only awaits a validator.
    RegistryEntry(
        id="cohort-retention",
        version="0.3",
        author="priya.raman",
        owner="priya.raman",
        owner_is_person=True,
        validator=None,
        data_contract="berka@sha:9b0c2e",
        eval_suite_ref="evals/cohort_retention.yaml",
        faithfulness=0.72,
        last_evaluated="2026-07-10",
    ),
    # A candidate: evals pass and it has an owner and a contract, but no validator
    # has signed yet. Assigning an independent validator would certify it.
    RegistryEntry(
        id="deposit-elasticity",
        version="0.9",
        author="marcus.lee",
        owner="Dana Okafor",
        owner_is_person=True,
        validator=None,
        data_contract="berka@sha:9b0c2e",
        eval_suite_ref="evals/deposit_elasticity.yaml",
        faithfulness=0.91,
        last_evaluated="2026-07-14",
    ),
]


def all_entries() -> list[RegistryEntry]:
    return list(_REGISTRY)


def get_entry(entry_id: str) -> RegistryEntry | None:
    return next((e for e in _REGISTRY if e.id == entry_id), None)


def register(entry: RegistryEntry) -> RegistryEntry:
    """Add an entry to the registry (used by the scaffolding CLI, Slice C)."""
    _REGISTRY.append(entry)
    return entry


def plan_visible_entries(floor: float = FAITHFULNESS_FLOOR) -> list[RegistryEntry]:
    """Only certified agents are visible to the Plan stage (section 11). A draft,
    candidate, refused, or deprecated agent cannot be selected by the model."""
    return [e for e in _REGISTRY if status_of(e, floor) == STATUS_CERTIFIED]
