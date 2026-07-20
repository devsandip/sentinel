"""Seeded run history (unified-app-build.md H0).

An append-only JSONL store of completed runs at sentinel/data/seed_runs.jsonl,
committed like the dataset CSVs. Honesty rule (project value): every record in
the store was produced by actually executing the run via scripts/seed_runs.py;
the metrics are that execution's real outputs, never invented. Everything
rendered from the store is labeled seeded in the UI.

Each record carries two timestamps: `executed_at` is the real wall-clock time
the run executed; `demo_date` is the record's assigned position on the demo
timeline. The weekly adoption chart and the registry's created_at dates render
the demo timeline (the same convention the previous hand-labeled seed rows
used), while executed_at preserves the true provenance in the store itself.

A second committed store sits beside it: sentinel/data/seed_audit.jsonl, one
line per audit event across every seeded run. It exists because the per-run
JSONL the harness writes lands under runtime/, which is gitignored and excluded
from the deploy bundle, so on a fresh instance there is no event history at all.
The seeded event stream is the same AuditEvent payload the harness persists,
captured at seed time and committed like the dataset CSVs. Same honesty rule:
every event is one an actual execution emitted.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

SEED_RUNS_PATH = Path(__file__).resolve().parents[1] / "data" / "seed_runs.jsonl"
SEED_AUDIT_PATH = Path(__file__).resolve().parents[1] / "data" / "seed_audit.jsonl"

KIND_ANALYSIS = "analysis"
KIND_CREDIT_RISK = "credit_risk"
KIND_GOVFLOW = "govflow"
KIND_L3 = "l3"


@dataclass(frozen=True)
class SeedRun:
    run_kind: str  # analysis | credit_risk | govflow | l3
    run_id: str
    ref_id: str  # analysis spec id or orchestrator question id
    dataset_id: str
    params: dict = field(default_factory=dict)
    status: str = ""
    metrics: dict = field(default_factory=dict)  # real outputs of the execution
    controls_fired: list = field(default_factory=list)
    cost: dict | None = None
    executed_at: str = ""  # real execution timestamp (ISO)
    demo_date: str = ""  # demo-timeline date (ISO); drives weekly + display
    seeded: bool = True
    # Who ran it, and who signed it off. `actor` is the persona id the run was
    # executed as. `approver` is the persona id that decided at a human gate,
    # empty when the run kind has no gate or never reached one. Both are needed
    # by the audit log; neither was derivable from the aggregate record before.
    actor: str = ""
    approver: str = ""
    # Per-step records, normalized across the four step vocabularies to
    # {name, status, agent, controls}. The run kinds keep their own step names
    # (Ask/Plan/... for govflow, profiler/eda/... for credit_risk); only the
    # envelope is shared.
    steps: list = field(default_factory=list)
    # The SR 11-7 style model card, for the run kinds that train something.
    # Captured at seed time because it is generated from live run objects that
    # do not survive the process; without it the Registry could list a model
    # version and not show its documentation, which is the wrong way round for
    # a model inventory. None for the routes that produce no model.
    model_card: dict | None = None

    @property
    def week(self) -> str:
        """ISO week of the demo-timeline date, e.g. '2026-W28'."""
        d = datetime.fromisoformat(self.demo_date)
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SeedRun:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


_CACHE: dict[str, list[SeedRun]] = {}


def load_seed_runs(path: Path = SEED_RUNS_PATH) -> list[SeedRun]:
    """All seeded runs, oldest first. Cached per process; missing file = []."""
    key = str(path)
    if key not in _CACHE:
        records: list[SeedRun] = []
        if path.exists():
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(SeedRun.from_dict(json.loads(line)))
        _CACHE[key] = records
    return list(_CACHE[key])


def write_seed_runs(records: list[SeedRun], path: Path = SEED_RUNS_PATH) -> Path:
    """Rewrite the store (idempotent seeding: replace, never duplicate)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()) + "\n")
    _CACHE.pop(str(path), None)
    return path


_AUDIT_CACHE: dict[str, dict[str, list[dict]]] = {}


def load_seed_audit(path: Path = SEED_AUDIT_PATH) -> dict[str, list[dict]]:
    """Seeded audit events grouped by run_id, each group ordered by seq.

    Cached per process; a missing file yields {} rather than raising, so the
    app still renders on a checkout that has not been seeded.
    """
    key = str(path)
    if key not in _AUDIT_CACHE:
        by_run: dict[str, list[dict]] = {}
        if path.exists():
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        ev = json.loads(line)
                        by_run.setdefault(ev.get("run_id", ""), []).append(ev)
        for events in by_run.values():
            events.sort(key=lambda e: e.get("seq", 0))
        _AUDIT_CACHE[key] = by_run
    return {k: list(v) for k, v in _AUDIT_CACHE[key].items()}


def write_seed_audit(
    events_by_run: dict[str, list[dict]], path: Path = SEED_AUDIT_PATH
) -> Path:
    """Rewrite the seeded event store (idempotent: replace, never append)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for run_id in events_by_run:
            for ev in sorted(events_by_run[run_id], key=lambda e: e.get("seq", 0)):
                f.write(json.dumps(ev) + "\n")
    _AUDIT_CACHE.pop(str(path), None)
    return path


def credit_risk_runs() -> list[SeedRun]:
    return [r for r in load_seed_runs() if r.run_kind == KIND_CREDIT_RISK]


def seeded_weekly() -> list[tuple[str, int]]:
    """Run counts per ISO week of the demo timeline, oldest week first."""
    counts: dict[str, int] = {}
    for r in load_seed_runs():
        counts[r.week] = counts.get(r.week, 0) + 1
    return sorted(counts.items())


def seeded_by_dataset() -> list[tuple[str, int]]:
    """Run counts per dataset, most-run first then by id."""
    counts: dict[str, int] = {}
    for r in load_seed_runs():
        counts[r.dataset_id] = counts.get(r.dataset_id, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
