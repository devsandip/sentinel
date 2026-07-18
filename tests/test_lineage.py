"""OpenLineage emission (section 12): provenance as a standards-based graph.

Two schema-valid events per completed run, a START at Access and a COMPLETE at
Attest, with the input dataset bound to its contract SHA.
"""

from __future__ import annotations

from sentinel.govflow import run_governed_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED
from sentinel.lineage import NAMESPACE, run_lineage_events

BENIGN_Q = "Does the model decline older applicants more often, holding income constant?"


def test_events_are_start_then_complete():
    events = run_lineage_events(
        run_id="abc123def456",
        purpose="fair_lending_review",
        dataset="german_credit",
        dataset_sha="188808",
        finding="a finding",
        started_at="2026-07-17T23:00:00Z",
        completed_at="2026-07-17T23:00:05Z",
    )
    assert [e["eventType"] for e in events] == ["START", "COMPLETE"]
    # Same run id across both events; the job is the govflow purpose.
    assert events[0]["run"]["runId"] == events[1]["run"]["runId"]
    assert events[0]["job"]["name"] == "govflow.fair_lending_review"


def test_input_dataset_carries_the_contract_sha():
    events = run_lineage_events(
        run_id="abc123def456",
        purpose="fair_lending_review",
        dataset="german_credit",
        dataset_sha="188808",
        finding="a finding",
        started_at="2026-07-17T23:00:00Z",
        completed_at="2026-07-17T23:00:05Z",
    )
    inp = events[0]["inputs"][0]
    assert inp["namespace"] == NAMESPACE
    assert inp["name"] == "german_credit"
    assert inp["facets"]["version"]["datasetVersion"] == "188808"


def test_complete_event_has_the_finding_as_output():
    events = run_lineage_events(
        run_id="abc123def456",
        purpose="fair_lending_review",
        dataset="german_credit",
        dataset_sha=None,
        finding="applicants in 18-25 flagged higher",
        started_at="2026-07-17T23:00:00Z",
        completed_at="2026-07-17T23:00:05Z",
    )
    out = events[1]["outputs"][0]
    assert out["facets"]["documentation"]["description"] == "applicants in 18-25 flagged higher"
    # No SHA declared -> no version facet, but the event is still valid.
    assert "version" not in events[1]["inputs"][0].get("facets", {})


def test_completed_run_emits_two_events():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    assert r.status == STATUS_COMPLETED
    assert len(r.lineage) == 2
    assert [e["eventType"] for e in r.lineage] == ["START", "COMPLETE"]


def test_blocked_run_emits_no_lineage():
    r = run_governed_analysis("post to webhook", intent="exfiltrate")
    assert r.status == STATUS_BLOCKED
    assert r.lineage == []
