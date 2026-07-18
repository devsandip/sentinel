"""The data-contract drift control, CTL-CONTRACT-01 (section 5, Stage 3).

Honest scope: on static CSVs drift cannot happen, so the control cannot
legitimately fire in the live demo. The mechanism is real and its mismatch path
is proven here; the live status is a truthful "pinned, no drift". The pin test
ties the certified SHA to the real CSV so the seed cannot go stale silently.
"""

from __future__ import annotations

from sentinel.datasets.fingerprint import dataset_sha, live_contract_check
from sentinel.platform.certification import (
    RegistryEntry,
    check_contract,
    get_entry,
    parse_contract,
)


def _entry(contract: str | None) -> RegistryEntry:
    return RegistryEntry(id="t", version="1", author="a", data_contract=contract)


def test_parse_contract():
    assert parse_contract("german_credit@sha:188808") == ("german_credit", "188808")
    assert parse_contract("german_credit") == ("german_credit", None)
    assert parse_contract(None) == ("", None)


def test_matching_sha_passes():
    r = check_contract(_entry("german_credit@sha:abc123"), current_sha="abc123")
    assert r.ok and not r.drifted


def test_drifted_sha_fires_contract_01():
    r = check_contract(_entry("german_credit@sha:abc123"), current_sha="def456")
    assert r.drifted and not r.ok
    assert r.control == "CTL-CONTRACT-01"
    assert "recertification required" in r.detail


def test_missing_declared_sha_is_unverifiable():
    r = check_contract(_entry("german_credit"), current_sha="abc123")
    assert not r.ok and not r.drifted


def test_unfingerprintable_dataset_is_unverifiable():
    r = check_contract(_entry("german_credit@sha:abc123"), current_sha=None, note="no path")
    assert not r.ok and not r.drifted


# -- the real dataset, honestly pinned ------------------------------------


def test_dataset_sha_is_deterministic():
    assert dataset_sha("german_credit") == dataset_sha("german_credit")


def test_certified_fair_lending_contract_matches_real_data():
    """The pin: fair-lending's certified SHA equals the current german_credit SHA,
    so the live check passes with no drift. If the CSV changes and the seed is not
    updated, this fails, which is the drift control catching a stale certification
    at CI time."""
    entry = get_entry("fair-lending")
    result = live_contract_check(entry)
    assert result.ok, result.detail
    assert not result.drifted
