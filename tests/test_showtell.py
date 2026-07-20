"""The show-and-tell rework (docs/features/govflow-showtell.md).

Three claims under test: (1) to_public_dict grew the payloads the stepper UI
reads (execution, generation attempts, access inventory, tier decision) without
touching the pinned keys; (2) the Gate's "Fix it" repair path produces a run
that genuinely passes the same gate, linked to the blocked run it repairs;
(3) every control id the flow can fire has a registered plain-language entry.
"""

from __future__ import annotations

import pytest

from sentinel.codegen.gate import gate_code
from sentinel.codegen.generate import (
    _REPAIRED_CODE,
    _TEMPLATED_CODE,
    CodeGenRequest,
    _scripted_fallback,
    has_scripted_repair,
)
from sentinel.govflow import run_governed_analysis, run_l3_analysis
from sentinel.govflow.access import FAIR_LENDING_GRANT, column_inventory
from sentinel.govflow.controls_info import (
    CATALOG_INFO,
    CONTROLS_INFO,
    INTERNAL,
    control_info,
)
from sentinel.harness.controls import CONTROL_IDS
from sentinel.harness.identity import get_persona


# -- flow exposure ----------------------------------------------------------
def test_public_dict_grew_the_showtell_payloads():
    r = run_governed_analysis("selection rate by age band")
    pub = r.to_public_dict()
    # New keys exist alongside the pinned ones.
    for key in ("execution", "generation_attempts", "tier_decision", "access", "repaired_from"):
        assert key in pub
    # Execution is serialized, so the pre-screen result is reachable.
    assert pub["execution"]["ok"] is True
    assert isinstance(pub["execution"]["emitted"], list)
    assert len(pub["execution"]["emitted"]) >= len(pub["screened_rows"])
    # The tier decision explains itself.
    td = pub["tier_decision"]
    assert td["tier"] == pub["tier"]
    assert td["classification_ceiling"] and td["person_ceiling"] and td["rationale"]
    # Attempts carry the per-attempt gate verdicts.
    assert pub["generation_attempts"][0]["passed"] is True
    assert pub["repaired_from"] == ""


def test_access_payload_carries_the_column_inventory():
    r = run_governed_analysis("selection rate by age band")
    acc = r.to_public_dict()["access"]
    assert acc["granted"] == FAIR_LENDING_GRANT
    assert acc["rows"] == 1000
    assert len(acc["sample"]) == 8
    inv = {i["column"]: i for i in acc["inventory"]}
    # Granted and withheld columns are both present, each with a reason.
    assert inv["age_band"]["granted"] is True
    assert inv["applicant_ssn"]["granted"] is False
    assert "PII" in inv["applicant_ssn"]["reason"]
    assert inv["age_years"]["granted"] is False
    assert all(i["reason"] for i in acc["inventory"])


def test_column_inventory_covers_the_grant_and_the_frame():
    inv = column_inventory()
    cols = [i["column"] for i in inv]
    assert len(cols) == len(set(cols)), "no duplicate columns in the inventory"
    for granted_col in FAIR_LENDING_GRANT:
        assert granted_col in cols


def test_blocked_run_has_no_access_payload():
    r = run_governed_analysis("marketing", purpose_key="marketing")
    pub = r.to_public_dict()
    assert pub["status"] == "blocked_at_gate"
    assert pub["access"] == {}  # refused before the scoped view was built
    assert pub["execution"] is None


def test_l3_public_dict_exposes_the_emitted_effect():
    admin = get_persona("admin")
    r = run_l3_analysis("estimate the effect", persona=admin)
    pub = r.to_public_dict()
    assert pub["status"] == "completed"
    emitted = pub["execution"]["emitted"]
    assert isinstance(emitted, dict)
    assert "effect" in emitted and "ci_low" in emitted
    assert pub["access"]["granted"] == ["date", "intervention", "control", "metric"]


# -- the Fix it repair path -------------------------------------------------
def test_every_repaired_sample_passes_the_gate_its_original_failed():
    for intent, fixed in _REPAIRED_CODE.items():
        original = _TEMPLATED_CODE[intent]
        grant = FAIR_LENDING_GRANT
        blocked = gate_code(original, granted_columns=grant, allowed_tables=["german_credit"])
        repaired = gate_code(fixed, granted_columns=grant, allowed_tables=["german_credit"])
        assert not blocked.passed, f"{intent} original should be refused"
        assert repaired.passed, f"{intent} repair should pass: {repaired.refusal_summary()}"
        assert fixed != original


def test_scripted_fallback_honors_the_repair_flag():
    req = CodeGenRequest(question="q", intent="exfiltrate")
    assert "requests.post" in _scripted_fallback(req)
    req_fix = CodeGenRequest(question="q", intent="exfiltrate", repair=True)
    assert "requests.post" not in _scripted_fallback(req_fix)
    assert has_scripted_repair("exfiltrate")
    assert not has_scripted_repair("fair_lending")


def test_repair_run_completes_and_links_the_blocked_run():
    blocked = run_governed_analysis("exfiltrate", intent="exfiltrate")
    pub = blocked.to_public_dict()
    assert pub["status"] == "blocked_at_gate"
    feedback = blocked.gate.feedback_for_regeneration()
    repaired = run_governed_analysis(
        "exfiltrate",
        intent="exfiltrate",
        repair_of=pub["run_id"],
        repair_feedback=feedback,
    )
    rp = repaired.to_public_dict()
    assert rp["status"] == "completed"
    assert rp["repaired_from"] == pub["run_id"]
    # The repair request is on the audit trail.
    assert any(e["action"] == "repair_requested" for e in rp["audit"])
    # The repaired code passed the same gate, not a bypass.
    assert rp["gate"]["passed"] is True
    assert "requests.post" not in rp["generated_code"]


def test_l3_repair_run_completes_and_links_the_blocked_run():
    admin = get_persona("admin")
    blocked = run_l3_analysis("exfiltrate", persona=admin, intent="exfiltrate")
    pub = blocked.to_public_dict()
    assert pub["status"] == "blocked_at_gate"
    repaired = run_l3_analysis(
        "exfiltrate", persona=admin, intent="exfiltrate", repair_of=pub["run_id"]
    )
    rp = repaired.to_public_dict()
    assert rp["status"] == "completed"
    assert rp["repaired_from"] == pub["run_id"]
    assert any(e["action"] == "repair_requested" for e in rp["audit"])


def test_repair_of_an_unrepairable_l3_intent_is_a_no_op():
    admin = get_persona("admin")
    r = run_l3_analysis("benign", persona=admin, intent="causal_impact", repair_of="abc123")
    pub = r.to_public_dict()
    # Nothing to repair: the benign intent has no seeded repair, so the run is
    # a plain run and does not claim to be one.
    assert pub["repaired_from"] == ""


def test_repair_on_an_l1_persona_does_not_claim_the_linkage():
    """The L1 route never engages the repair machinery, so a repair request
    riding in (e.g. after a sidebar persona switch) must not stamp
    repaired_from or write a repair_requested record: the invariant is that
    the linkage exists iff the repair actually happened."""
    junior = get_persona("junior_analyst")
    r = run_governed_analysis(
        "exfiltrate",
        persona=junior,
        intent="exfiltrate",
        repair_of="deadbeef1234",
        repair_feedback="The gate refused this code.",
    )
    pub = r.to_public_dict()
    assert pub["tier"] == "L1"
    assert pub["repaired_from"] == ""
    assert not any(e["action"] == "repair_requested" for e in pub["audit"])


def test_stray_repair_of_on_a_plain_l2_run_is_a_no_op():
    """A repair_of with no feedback and no seeded repair (benign intent) is a
    plain run: no false audit record, no false linkage (the L3 contract)."""
    r = run_governed_analysis("benign", intent="fair_lending", repair_of="abc123")
    pub = r.to_public_dict()
    assert pub["status"] == "completed"
    assert pub["repaired_from"] == ""
    assert not any(e["action"] == "repair_requested" for e in pub["audit"])


def test_l3_tier_blocked_repair_does_not_claim_the_linkage():
    """A repair attempt by a persona that no longer resolves to L3 blocks at
    Ask; it repaired nothing and must not claim the linkage."""
    r = run_l3_analysis("exfiltrate", intent="exfiltrate", repair_of="abc123")
    pub = r.to_public_dict()
    assert pub["status"] == "blocked_at_gate"  # tier block uses the shared status
    assert pub["repaired_from"] == ""
    assert not any(e["action"] == "repair_requested" for e in pub["audit"])


# -- controls_info coverage -------------------------------------------------
# Every control id the flow modules can actually fire. Sourced from the
# controls inventory in the feature doc; if a new control lands, it belongs in
# this list AND in controls_info.
_FIREABLE = [
    "CTL-SOD-01",
    "CTL-EVAL-01",
    "CTL-CONTRACT-01",
    "CTL-DISC-01",
    "CTL-DISC-02",
    "CTL-DISC-03",
    "CTL-PROXY-01",
    "CTL-CODE-00",
    "CTL-CODE-01",
    "CTL-CODE-02",
    "CTL-CODE-03",
    "CTL-CODE-04",
    "CTL-EGRESS-01",
    "CTL-COL-01",
    "CTL-PURP-01",
    "CTL-COMPLEX-01",
    "CTL-TIME-01",
]


@pytest.mark.parametrize("cid", _FIREABLE)
def test_every_fireable_control_has_a_real_entry(cid):
    info = control_info(cid)
    assert info.implemented, f"{cid} must be marked implemented"
    assert info.what and info.why and info.fired_means
    assert info.action in ("refuses", "flags", "suppresses", "logs")


def test_catalog_controls_are_covered_too():
    for cid in CONTROL_IDS:
        assert cid in CATALOG_INFO, f"catalog control {cid} needs an entry"
        assert CATALOG_INFO[cid].what
    assert "audit" in CATALOG_INFO  # not toggleable, still explains itself


def test_doc_only_controls_are_marked_unimplemented():
    for cid in ("CTL-RBAC-01", "CTL-PURP-02", "CTL-INJECT-01"):
        assert cid in CONTROLS_INFO
        assert CONTROLS_INFO[cid].implemented is False


def test_tier_control_is_implemented_because_it_actually_refuses_runs():
    """CTL-TIER-01 was catalogued doc-only while flow.py was enforcing it.

    The Audit Log surfaced the contradiction: a seeded run is refused by this
    control at Ask, and its chip would have read "cannot fire: not implemented"
    beside the run it stopped. The catalogue was stale, not the code.
    """
    assert CONTROLS_INFO["CTL-TIER-01"].implemented is True

    from sentinel.platform.audit_store import audit_runs

    refused_at_ask = [r for r in audit_runs() if r.stopped_at == "Ask"]
    assert refused_at_ask, "expected a seeded run refused by the tier gate"
    assert any(
        e.get("action") == "tier_block"
        for r in refused_at_ask
        for e in r.events
    )


def test_every_control_names_the_regime_it_answers_to():
    """A control that cites no regime is a control nobody decided the basis for.

    Same shape as the guard that fails a gate check which lost its rule: the
    catalogue is the single explanation surface, so a blank here goes silently
    missing in the Gate panel, the Audit Log drill-down and the Registry headers
    at once. Controls with no external driver say INTERNAL in as many words, so
    silence never has to be read as either a gap or an oversight.
    """
    for cid, info in {**CONTROLS_INFO, **CATALOG_INFO}.items():
        assert info.regulation.strip(), (
            f"{cid} ships without a regulation line. Name the regime and the "
            f"principle, or set it to {INTERNAL!r} if there is no external "
            f"driver."
        )
        assert "complies" not in info.regulation.lower(), (
            f"{cid} says 'complies'. A control answers to a principle; "
            f"compliance is a determination a firm makes, not one this app can."
        )


def test_declared_controls_still_name_a_regime():
    """The doc-only entries share one `why`, so the regime is the only thing
    distinguishing what they would each be for. A blank would make the declared
    half of the catalogue indistinguishable from filler."""
    declared = [c for c in CONTROLS_INFO.values() if not c.implemented]
    assert declared, "expected doc-only controls in the catalogue"
    for info in declared:
        assert info.regulation.strip()


def test_unknown_control_gets_an_honest_placeholder():
    info = control_info("CTL-NOPE-99")
    assert info.implemented is False
    assert info.id == "CTL-NOPE-99"
