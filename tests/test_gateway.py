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
