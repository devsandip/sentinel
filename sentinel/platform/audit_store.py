"""Cross-run audit reader (docs/features/audit-log.md section 5c).

Every other audit surface in Sentinel is scoped to one run and dies with the
session. This is the only reader that spans runs, and it is what the Audit Log
screen renders.

Two sources, unioned:

- the committed seed stores, sentinel/data/seed_runs.jsonl (one aggregate
  record per run) and sentinel/data/seed_audit.jsonl (the per-event stream);
- live runs from this process, whose events the harness has already written to
  runtime/audit/<run_id>.jsonl.

The runtime directory is gitignored and excluded from the deploy bundle, so on
a fresh instance the second source is empty and the screen renders the seeded
history alone. That is the intended behaviour, not a degraded mode: seeded runs
are the durable record, live runs are a session's own additions.

Status normalization deserves a note. The four run kinds carry four unrelated
status vocabularies with no shared base class, so this module maps them onto
three outcomes: OK, REFUSED, AWAITING. The map is deliberately explicit rather
than a prefix rule, because govflow's 'blocked_at_gate' is a lie whenever the
block happened at Ask, and a rule that reads the constant would repeat it.
Where an event stream is available, `stopped_at` reads the run's own step
records instead, so the screen can name the real stage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..harness.audit import LEVEL_BLOCKED, LEVEL_REDACTION, RUNTIME_DIR
from ..harness.identity import Persona
from .run_history import (
    KIND_CREDIT_RISK,
    SeedRun,
    load_seed_audit,
    load_seed_runs,
)

# The three outcomes the screen renders. Anything unmapped is treated as
# REFUSED rather than OK: an unrecognized status is not evidence of success.
OUTCOME_OK = "ok"
OUTCOME_REFUSED = "refused"
OUTCOME_AWAITING = "awaiting"

# Explicit, per source vocabulary. Adding a status constant anywhere without
# adding it here is a test failure, not a silent default.
_STATUS_MAP: dict[str, str] = {
    # analysis (sentinel/analyses/engine.py)
    "completed": OUTCOME_OK,
    "blocked": OUTCOME_REFUSED,
    # credit_risk (sentinel/orchestrator.py, plus the seeder's rename)
    "promoted": OUTCOME_OK,
    "running": OUTCOME_AWAITING,
    "awaiting_approval": OUTCOME_AWAITING,
    "rejected": OUTCOME_REFUSED,
    # govflow / l3 (sentinel/govflow/flow.py, l3.py)
    "blocked_at_gate": OUTCOME_REFUSED,
    "error": OUTCOME_REFUSED,
}

ORIGIN_SEEDED = "seeded"
ORIGIN_LIVE = "live"


@dataclass(frozen=True)
class AuditRun:
    """One run as the Audit Log screen needs it: the record plus its events."""

    run_id: str
    run_kind: str
    ref_id: str
    dataset_id: str
    status: str  # the raw status, kept verbatim
    outcome: str  # OUTCOME_*
    actor: str
    approver: str
    origin: str  # seeded | live
    when: str  # demo_date for seeded runs, executed_at for live ones
    controls_fired: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    # -- refusal accounting -------------------------------------------------

    @property
    def blocked_events(self) -> list[dict]:
        return [e for e in self.events if e.get("level") == LEVEL_BLOCKED]

    @property
    def caught_events(self) -> list[dict]:
        """Events where something was actually refused or withheld.

        Two levels, and only two. `blocked` is a refusal: a column denied, a
        run stopped, an approval turned down. `redaction` is a withholding: a
        value removed before it reached a model.

        `gate` is deliberately excluded. A gate event records that a control
        was consulted, not that it said no: `eval_gate` at 6/6 passed and
        `approval_decision` APPROVED are both gate-level and both mean the run
        was allowed to proceed. Counting them as refusals inflates every
        number on the screen and credits controls with stopping things they
        waved through. Where a gate does refuse, it writes `blocked` instead
        (`approval_denied`, `gate_block`, `tier_block`).
        """
        return [
            e
            for e in self.events
            if e.get("level") in (LEVEL_BLOCKED, LEVEL_REDACTION)
        ]

    @property
    def has_refusal(self) -> bool:
        """True when a control refused or withheld something on this run.

        Falls back to controls_fired when no event stream is available, so a
        seeded run without events is not silently reported as clean. That
        fallback is coarser than the event path, because controls_fired mixes
        gate passes in; it is the honest best available when events are gone.
        """
        if self.events:
            return bool(self.caught_events)
        return bool(self.controls_fired)

    @property
    def refusal_controls(self) -> list[str]:
        """What refused or withheld something, read from the event record.

        `controls_fired` is not usable on its own for two independent reasons.
        It over-reports: the seeder builds it from blocked, redaction AND gate
        levels, so a passing eval gate lands in it. And it under-reports:
        govflow only accumulates CTL- ids raised at Gate and Screen, so a run
        refused at Ask by the tier gate carries an empty list while its events
        plainly record a tier_block. Reading caught_events fixes both, and a
        test asserts no refused run ever renders with nothing here.

        Falls back to the action string where no control id was stamped, which
        is honest: that is genuinely all the record holds.

        CTL- ids from controls_fired are then unioned back in. That list is
        govflow's own account of the controls it raised, and it can name one
        the events do not: the Screen stage suppresses a cell under CTL-DISC-01
        but stamps CTL-DISC-02 on the event. The union is safe precisely
        because the gate-pass pollution is all bare action strings
        (approval_requested, eval_gate) and never a CTL- id.
        """
        found: list[str] = []
        for e in self.caught_events:
            ctl = (e.get("extra") or {}).get("control") or e.get("action", "")
            if ctl and ctl not in found:
                found.append(str(ctl))
        extra = self.controls_fired if not self.events else [
            c for c in self.controls_fired if c.startswith("CTL-")
        ]
        found.extend(c for c in extra if c not in found)
        return found

    @property
    def stopped_run(self) -> bool:
        """The run ended at a control rather than completing."""
        return self.outcome in (OUTCOME_REFUSED, OUTCOME_AWAITING)

    @property
    def stopped_at(self) -> str:
        """The step or stage where the run ended, read from its own records.

        Each kind names its own halt: analysis and govflow use blocked/error,
        credit_risk rewrites the gate step to 'rejected', and a run refused at
        the gate stays 'awaiting_approval' because it was never resolved.
        """
        for s in self.steps:
            if s.get("status") in ("blocked", "error", "rejected", "awaiting_approval"):
                return str(s.get("name", ""))
        return ""

    @property
    def has_events(self) -> bool:
        """Whether an event trail was persisted at all.

        Distinct from has_refusal: 'nothing was refused' and 'no trail exists'
        are different statements and the screen must not conflate them.
        """
        return bool(self.events)

    @property
    def seq_gaps(self) -> list[int]:
        """Missing sequence numbers within the run, if any.

        The only tamper evidence available today: seq is monotonic per run and
        assigned by AuditLog.record, so a hole means a line went missing. This
        is not a hash chain and must not be presented as one.
        """
        if not self.events:
            return []
        seqs = {int(e.get("seq", -1)) for e in self.events}
        return [n for n in range(max(seqs) + 1) if n not in seqs]

    @property
    def reached_gate(self) -> bool:
        """The run reached a human promotion gate."""
        return any(e.get("action") == "approval_requested" for e in self.events)

    @property
    def four_eyes(self) -> bool:
        """Signed by someone other than the author.

        A self-approval refused by CTL-SOD-01 is not coverage: `approver` is
        read off the decision event, which a refusal never writes.
        """
        return bool(self.approver) and self.approver != self.actor


def normalize_status(status: str) -> str:
    return _STATUS_MAP.get(status, OUTCOME_REFUSED)


def _from_seed(rec: SeedRun, events: list[dict]) -> AuditRun:
    return AuditRun(
        run_id=rec.run_id,
        run_kind=rec.run_kind,
        ref_id=rec.ref_id,
        dataset_id=rec.dataset_id,
        status=rec.status,
        outcome=normalize_status(rec.status),
        actor=rec.actor,
        approver=rec.approver,
        origin=ORIGIN_SEEDED,
        when=rec.demo_date or rec.executed_at,
        controls_fired=list(rec.controls_fired),
        steps=list(rec.steps),
        events=events,
        metrics=dict(rec.metrics),
    )


def _read_runtime_events(run_id: str, runtime_dir: Path) -> list[dict]:
    path = runtime_dir / f"{run_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    events.sort(key=lambda e: e.get("seq", 0))
    return events


def audit_runs(
    live: list[AuditRun] | None = None,
    *,
    runtime_dir: Path = RUNTIME_DIR,
) -> list[AuditRun]:
    """Every run on file, newest first.

    Seeded runs come from the committed stores. Live runs are passed in by the
    caller (the app knows its own session's runs); their events are read back
    from the runtime JSONL the harness wrote.
    """
    seeded_events = load_seed_audit()
    runs = [_from_seed(r, seeded_events.get(r.run_id, [])) for r in load_seed_runs()]
    for r in live or []:
        events = r.events or _read_runtime_events(r.run_id, runtime_dir)
        runs.append(
            AuditRun(**{**r.__dict__, "events": events, "origin": ORIGIN_LIVE})
        )
    return sorted(runs, key=lambda r: r.when, reverse=True)


def visible_runs(runs: list[AuditRun], persona: Persona | None) -> list[AuditRun]:
    """The runs one persona is entitled to read.

    Oversight roles (second line, third line, platform) read everything; the
    first line reads its own runs only. The entitlement is declared per persona
    in config/personas.yaml, not decided here by role-name matching, so adding
    a persona is a config change and not a code change.

    Default deny: an unidentified viewer sees nothing. That is the awkward
    answer rather than the convenient one, and it is the right one for an
    access check. The caller always has a persona, because the app resolves it
    before it renders anything.

    Scoping the ledger by identity necessarily scopes the KPI tiles computed
    over it, so the screen must say which set it is counting. A first line
    analyst reading "3 runs logged" while 24 exist is misled unless told.
    """
    if persona is None:
        return []
    if persona.can_view_all_runs:
        return list(runs)
    return [r for r in runs if r.actor == persona.id]


def summary(runs: list[AuditRun]) -> dict[str, Any]:
    """The four KPI tiles, computed once so the screen and its test agree."""
    gated = [r for r in runs if r.reached_gate or r.run_kind == KIND_CREDIT_RISK]
    refused = [r for r in runs if r.has_refusal]
    stopped = [r for r in refused if r.stopped_run]
    # Coverage, not refusal: an eval gate that fired and passed is a control
    # that fired. So this deliberately uses the broad controls_fired list,
    # unlike the refusal tiles above, which read caught_events only.
    controls: set[str] = set()
    for r in runs:
        controls.update(r.controls_fired)
        for e in r.events:
            ctl = (e.get("extra") or {}).get("control")
            if ctl:
                controls.add(str(ctl))
    return {
        "runs": len(runs),
        "live_runs": sum(1 for r in runs if r.origin == ORIGIN_LIVE),
        "events": sum(len(r.events) for r in runs),
        "runs_without_events": sum(1 for r in runs if not r.has_events),
        "refused": len(refused),
        "stopped": len(stopped),
        # Refusals recorded on a run that still finished: a column denied, a
        # cell suppressed, a value redacted.
        "withheld": len(refused) - len(stopped),
        "gated": len(gated),
        "four_eyes": sum(1 for r in gated if r.four_eyes),
        "controls_fired": sorted(controls),
    }
