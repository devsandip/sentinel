"""Dataset fingerprints for the data-contract drift control (CTL-CONTRACT-01).

A certification is evidence about a dataset as it was at a moment in time. If the
dataset changes after certification, the evidence is about a dataset that no
longer exists. The contract binds a registry entry to the dataset SHA at
certification (section 5, Stage 3); at Access we recompute the SHA and refuse to
run silently on drifted data.

Honest note (from the PRD): with static CSVs, drift cannot happen in this build,
so the control cannot legitimately fire in the live demo. It is right in
principle and unfalsifiable in practice here. The mechanism is real and its
mismatch path is proven in tests; the live status is "pinned, no drift possible
on static data". We do not manufacture a fake drift to show the control firing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..ml.data import DATA_PATH
from ..platform.certification import RegistryEntry, check_contract, parse_contract

# Datasets whose source bytes we can fingerprint. Only german_credit is exercised
# by the v2 govflow; others can be added as they are onboarded.
DATASET_PATHS: dict[str, Path] = {
    "german_credit": DATA_PATH,
}

SHA_PREFIX_LEN = 6


class FingerprintError(Exception):
    """Raised when a dataset cannot be fingerprinted (no known source path)."""


def dataset_sha(dataset_id: str, length: int = SHA_PREFIX_LEN) -> str:
    """A deterministic content hash of the dataset's source bytes.

    Hashing the raw file bytes (not the loaded DataFrame) keeps the fingerprint
    stable across runs and platforms, so an unchanged CSV always yields the same
    SHA and the contract check does not false-fire.
    """
    path = DATASET_PATHS.get(dataset_id)
    if path is None:
        raise FingerprintError(
            f"no source path registered for dataset {dataset_id!r}; "
            f"known: {sorted(DATASET_PATHS)}"
        )
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return digest[:length]


def live_contract_check(entry: RegistryEntry):
    """Recompute the dataset SHA and check it against the entry's contract.

    Returns the same ContractCheck the pure check produces. On a dataset we
    cannot fingerprint, the check is reported as unverifiable rather than passed.
    """
    dataset_id, _ = parse_contract(entry.data_contract)
    try:
        current = dataset_sha(dataset_id)
    except FingerprintError as ex:
        return check_contract(entry, current_sha=None, note=str(ex))
    return check_contract(entry, current_sha=current)
