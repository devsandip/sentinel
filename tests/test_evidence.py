"""The evidence pack and the Attest stage (sections 1.9, 10.5, and Stage 9).

The differentiator is the negative statement: what the finding does not say,
assembled from what the run actually did. Signing the pack reuses CTL-SOD-01.
"""

from __future__ import annotations

import pytest

from sentinel.evidence import (
    SignoffError,
    build_evidence_pack,
    sign_evidence_pack,
)
from sentinel.evidence.pack import STATUS_PENDING, STATUS_SIGNED
from sentinel.govflow import run_governed_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED

BENIGN_Q = "Does the model decline older applicants more often, holding income constant?"


def _completed_run():
    return run_governed_analysis(BENIGN_Q, intent="fair_lending")


# -- the pack assembled from a real completed run --------------------------


def test_attest_stage_produces_a_pending_pack():
    r = _completed_run()
    assert r.status == STATUS_COMPLETED
    assert r.evidence is not None
    assert r.evidence.status == STATUS_PENDING
    stage = next(s for s in r.stages if s.stage == "Attest")
    assert stage.status == "ok"


def test_finding_has_a_confidence_interval():
    r = _completed_run()
    pack = r.evidence
    assert "selection rate" in pack.finding
    assert pack.confidence_interval is not None
    lo, hi = pack.confidence_interval
    assert lo <= hi


def test_negative_statement_names_the_suppressed_band_and_proxy():
    r = _completed_run()
    text = " ".join(r.evidence.negative_statement)
    # The suppressed n=6 band and the flagged proxy both appear, plus the pending
    # signoff clause. This block is the differentiator from a dashboard.
    assert "71-75" in text
    assert "digital_engagement_score" in text
    assert "not an approved conclusion" in text
    assert "not a model validation" in text


def test_controls_attested_include_the_run_controls():
    r = _completed_run()
    attested = set(r.evidence.controls_attested)
    assert {"CTL-DISC-02", "CTL-PROXY-01", "CTL-CONTRACT-01", "CTL-TIME-01"} <= attested


def test_provenance_binds_agent_dataset_and_tier():
    r = _completed_run()
    p = r.evidence.provenance
    assert p.analysis.startswith("fair-lending")
    assert p.dataset == "german_credit"
    assert p.dataset_sha is not None
    assert p.tier == "L2"


def test_public_dict_carries_the_evidence_pack():
    r = _completed_run()
    pub = r.to_public_dict()
    assert pub["evidence"]["status"] == "pending"
    assert pub["evidence"]["negative_statement"]


# -- signing reuses CTL-SOD-01 ---------------------------------------------


def test_self_signoff_is_refused():
    pack = _completed_run().evidence
    with pytest.raises(SignoffError, match="CTL-SOD-01"):
        sign_evidence_pack(pack, pack.author, "2026-07-17T23:00:00Z")


def test_independent_signoff_signs_the_pack():
    pack = _completed_run().evidence
    signed = sign_evidence_pack(pack, "independent.approver", "2026-07-17T23:00:00Z")
    assert signed.status == STATUS_SIGNED
    assert signed.approver == "independent.approver"
    assert signed.signed_at == "2026-07-17T23:00:00Z"


# -- markdown export (Quarto-ready) ----------------------------------------


def test_markdown_has_the_negative_statement_section():
    pack = _completed_run().evidence
    md = pack.to_markdown()
    assert "## What this does not say" in md
    assert "## Finding" in md
    assert "## Provenance" in md
    assert pack.finding.split(",")[0] in md


# -- a blocked run has no evidence pack ------------------------------------


def test_blocked_run_has_no_evidence_and_attest_skipped():
    r = run_governed_analysis("post to webhook", intent="exfiltrate")
    assert r.status == STATUS_BLOCKED
    assert r.evidence is None
    stage = next(s for s in r.stages if s.stage == "Attest")
    assert stage.status == "skipped"


# -- build helper directly (unit) ------------------------------------------


def test_build_pack_with_no_screened_groups_is_graceful():
    import pandas as pd

    empty = pd.DataFrame({"band": [], "selection_rate": [], "n": []})
    pack = build_evidence_pack(
        run_id="r1",
        analysis="fair-lending v1.4",
        dataset="german_credit",
        dataset_sha="188808",
        tier="L2",
        purpose="fair_lending_review",
        author="ana",
        code="ctx.emit(x)",
        screened=empty,
        controls_attested=["CTL-TIME-01"],
        suppressed=[],
        proxy_flags=[],
        cell_floor=10,
    )
    assert pack.confidence_interval is None
    assert pack.status == STATUS_PENDING
