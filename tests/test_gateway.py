"""Tests for the model gateway: routing, caching, and the ledger (item 1)."""

from __future__ import annotations

import sentinel.gateway.model_gateway as gw
from sentinel.gateway.model_gateway import (
    ANTHROPIC,
    TEMPLATED,
    TIER_CAPABLE,
    TIER_CHEAP,
    TIER_TEMPLATED,
    ModelGateway,
)


def _fresh_cache():
    gw._RESPONSE_CACHE.clear()


def test_templated_call_is_free_and_logged():
    _fresh_cache()
    g = ModelGateway(provider=TEMPLATED)
    gen = g.narrate("profiler", {"n_rows": 1000})
    assert gen.cost_usd == 0.0 and not gen.live
    assert len(g.ledger) == 1
    row = g.ledger[0]
    assert row.routed_tier == TIER_TEMPLATED
    assert row.cache == "miss"


def test_routing_classifies_stakes():
    _fresh_cache()
    # In live mode the router picks tiers by stakes (no call is executed here;
    # we inspect the routing decision directly).
    g = ModelGateway(provider=ANTHROPIC)
    stakes_low, tier_low, _ = g._route("profiler")
    stakes_hi, tier_hi, model_hi = g._route("summary")
    assert stakes_low == "low" and tier_low == TIER_CHEAP
    assert stakes_hi == "elevated" and tier_hi == TIER_CAPABLE
    assert "sonnet" in model_hi  # capable model


def test_cache_hit_on_identical_call():
    _fresh_cache()
    g = ModelGateway(provider=TEMPLATED)
    g.narrate("profiler", {"n_rows": 1000})
    g.narrate("profiler", {"n_rows": 1000})  # identical -> hit
    assert [r.cache for r in g.ledger] == ["miss", "hit"]


def test_cache_is_process_level_across_gateways():
    _fresh_cache()
    ModelGateway(provider=TEMPLATED).narrate("eda", {"protected_attribute": "age_band"})
    g2 = ModelGateway(provider=TEMPLATED)
    g2.narrate("eda", {"protected_attribute": "age_band"})
    assert g2.ledger[0].cache == "hit"


def test_cumulative_cap_bounds_total_spend_across_gateways():
    """The cap is a process-global ceiling, not a per-run budget: once total
    live spend reaches it, further live calls fall back to scripted."""
    _fresh_cache()
    gw.reset_process_live_spend()
    # Each live call "costs" $0.60; cap at $1.00 allows one, blocks the rest.
    def fake_call(self, step, context, model):  # noqa: ANN001
        return ("live text", 100, 0.60)

    g1 = ModelGateway(provider=ANTHROPIC, monthly_cap_usd=1.0)
    g1._call_live = fake_call.__get__(g1, ModelGateway)
    first = g1.narrate("profiler", {"n": 1})
    assert first.live and first.cost_usd == 0.60

    # A brand-new gateway (new run) shares the process-global spend.
    g2 = ModelGateway(provider=ANTHROPIC, monthly_cap_usd=1.0)
    g2._call_live = fake_call.__get__(g2, ModelGateway)
    second = g2.narrate("eda", {"n": 2})  # cumulative 0.60 < 1.0 -> allowed
    assert second.live
    third = g2.narrate("modeler", {"n": 3})  # cumulative 1.20 >= 1.0 -> blocked
    assert not third.live and third.fell_back
    assert "cap" in third.fallback_reason
    assert gw.process_live_spent_usd() >= 1.0
    gw.reset_process_live_spend()


def test_ledger_dicts_shape():
    _fresh_cache()
    g = ModelGateway(provider=TEMPLATED)
    g.narrate("modeler", {"auc": 0.78})
    d = g.ledger_dicts()[0]
    assert set(d) >= {
        "call_kind",
        "stakes",
        "routed_tier",
        "routed_model",
        "cache",
        "policy",
        "cost_usd",
    }
    assert d["stakes"] == "elevated"  # modeler is elevated-stakes
