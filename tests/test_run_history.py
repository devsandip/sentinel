"""Tests for the seeded run-history store (unified-app-build H0-H2)."""

from __future__ import annotations

from sentinel.platform import model_versions
from sentinel.platform.run_history import (
    KIND_CREDIT_RISK,
    SEED_RUNS_PATH,
    SeedRun,
    load_seed_runs,
    seeded_by_dataset,
    seeded_weekly,
    write_seed_runs,
)


def _record(**overrides) -> SeedRun:
    base = dict(
        run_kind="analysis",
        run_id="abc123def456",
        ref_id="data_profiling",
        dataset_id="german_credit",
        params={"sample_rows": 5000},
        status="completed",
        metrics={"steps": 3},
        controls_fired=[],
        cost={"cost_usd": 0.0},
        executed_at="2026-07-19T09:30:00+00:00",
        demo_date="2026-07-08T10:00:00+00:00",
    )
    base.update(overrides)
    return SeedRun(**base)


def test_store_round_trip(tmp_path):
    path = tmp_path / "seed_runs.jsonl"
    records = [_record(), _record(run_id="ffff00001111", run_kind=KIND_CREDIT_RISK)]
    write_seed_runs(records, path)
    loaded = load_seed_runs(path)
    assert loaded == records
    # Rewriting replaces, never duplicates (idempotent seeding).
    write_seed_runs(records, path)
    assert len(load_seed_runs(path)) == 2


def test_week_derives_from_demo_date():
    assert _record(demo_date="2026-07-08T10:00:00+00:00").week == "2026-W28"
    assert _record(demo_date="2026-06-23T10:00:00+00:00").week == "2026-W26"


def test_committed_store_holds_the_executed_seed_plan():
    records = load_seed_runs()
    assert SEED_RUNS_PATH.exists(), "seed store missing; run scripts/seed_runs.py"
    assert len(records) >= 19
    # Honesty labels: every record is marked seeded and carries both the real
    # execution timestamp and its demo-timeline date.
    for r in records:
        assert r.seeded is True
        assert r.executed_at and r.demo_date
        assert r.status  # a real terminal status from the execution
    # H2 acceptance: at least 2 runs per registered dataset, 5 on the hero.
    per_ds = dict(seeded_by_dataset())
    assert per_ds["german_credit"] >= 5
    assert all(count >= 2 for count in per_ds.values())
    assert len(per_ds) == 8


def test_weekly_counts_cover_the_store():
    records = load_seed_runs()
    weekly = seeded_weekly()
    assert sum(n for _, n in weekly) == len(records)
    assert weekly == sorted(weekly)  # oldest week first


def test_credit_risk_seeds_fold_into_model_versions():
    seeded_rows = [m for m in model_versions() if m.seeded]
    credit_records = [r for r in load_seed_runs() if r.run_kind == KIND_CREDIT_RISK]
    assert len(seeded_rows) >= len(credit_records) >= 3
    by_version = {m.version: m for m in seeded_rows}
    for r in credit_records:
        row = by_version[f"credit-lr-{r.run_id[:6]}"]
        assert row.question_id == r.ref_id
        assert row.auc == r.metrics.get("auc")
        assert row.status == r.status
        assert row.created_at == r.demo_date
