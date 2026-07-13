"""Loaders + availability for onboarded datasets.

A dataset is *available* when its local file exists under sentinel/data/. The
onboard script (scripts/onboard_datasets.py) produces those files. `load_frame`
returns the raw DataFrame for a single-table dataset; relational datasets (Berka)
will load a dict of frames once onboarded.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class NotOnboarded(RuntimeError):
    """Raised when a dataset's local file is not present yet."""


def local_path(dataset_id: str) -> Path:
    # german_credit ships as german_credit.csv; onboarded sets follow <id>.csv.
    return DATA_DIR / f"{dataset_id}.csv"


def available(dataset_id: str) -> bool:
    return local_path(dataset_id).exists()


def load_frame(dataset_id: str) -> pd.DataFrame:
    path = local_path(dataset_id)
    if not path.exists():
        raise NotOnboarded(
            f"{dataset_id} is registered but not onboarded. Run "
            f"`uv run python scripts/onboard_datasets.py {dataset_id}`."
        )
    return pd.read_csv(path)
