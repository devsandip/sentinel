"""Dataset registry + data contracts for the analysis platform.

  contracts - column roles + capabilities + DataContract matching
  registry  - the onboarded-dataset inventory (DatasetSpec), with license +
              contract + column classification
"""

from __future__ import annotations

from .contracts import (
    ALL_CAPABILITIES,
    ALL_ROLES,
    DataContract,
    contract,
)
from .registry import (
    DATASETS,
    DatasetSpec,
    all_datasets,
    get_dataset,
    onboarded_datasets,
)

__all__ = [
    "ALL_CAPABILITIES",
    "ALL_ROLES",
    "DataContract",
    "contract",
    "DATASETS",
    "DatasetSpec",
    "all_datasets",
    "get_dataset",
    "onboarded_datasets",
]
