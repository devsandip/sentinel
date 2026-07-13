"""Loaders + availability for onboarded datasets.

A dataset is *available* when its local file exists under sentinel/data/. The
onboard script (scripts/onboard_datasets.py) produces those files. `load_frame`
returns the raw DataFrame for a single-table dataset; relational datasets (Berka)
will load a dict of frames once onboarded.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .contracts import CAP_RELATIONAL
from .registry import get_dataset

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class NotOnboarded(RuntimeError):
    """Raised when a dataset's local file is not present yet."""


def _is_relational(dataset_id: str) -> bool:
    spec = get_dataset(dataset_id)
    return spec is not None and CAP_RELATIONAL in spec.provides


def local_path(dataset_id: str) -> Path:
    # german_credit ships as german_credit.csv; onboarded sets follow <id>.csv.
    return DATA_DIR / f"{dataset_id}.csv"


def local_dir(dataset_id: str) -> Path:
    # Relational datasets (Berka) land as a directory of per-table CSVs.
    return DATA_DIR / dataset_id


def available(dataset_id: str) -> bool:
    if _is_relational(dataset_id):
        d = local_dir(dataset_id)
        return d.is_dir() and any(d.glob("*.csv"))
    return local_path(dataset_id).exists()


def _not_onboarded(dataset_id: str) -> NotOnboarded:
    return NotOnboarded(
        f"{dataset_id} is registered but not onboarded. Run "
        f"`uv run python scripts/onboard_datasets.py {dataset_id}`."
    )


def load_frame(dataset_id: str) -> pd.DataFrame:
    """Single-table load. For relational datasets, use load_tables."""
    path = local_path(dataset_id)
    if not path.exists():
        raise _not_onboarded(dataset_id)
    return pd.read_csv(path)


def load_tables(dataset_id: str) -> dict[str, pd.DataFrame]:
    """Relational load: {table_name: frame} from the dataset's directory."""
    d = local_dir(dataset_id)
    if not (d.is_dir() and any(d.glob("*.csv"))):
        raise _not_onboarded(dataset_id)
    return {p.stem: pd.read_csv(p) for p in sorted(d.glob("*.csv"))}
