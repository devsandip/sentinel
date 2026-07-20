"""Dataset registry + data contracts for the analysis platform.

  contracts - column roles + capabilities + DataContract matching
  registry  - the onboarded-dataset inventory (DatasetSpec), with license +
              contract + column classification
"""

from __future__ import annotations

from .catalog import (
    ColumnDoc,
    DatasetSchema,
    Relationship,
    TableDoc,
    role_note,
    schema,
)
from .contracts import (
    ALL_CAPABILITIES,
    ALL_ROLES,
    DataContract,
    contract,
)
from .loaders import NotOnboarded, available, load_frame, load_tables, local_path
from .registry import (
    DATASETS,
    DatasetSpec,
    all_datasets,
    get_dataset,
)

__all__ = [
    "ALL_CAPABILITIES",
    "ALL_ROLES",
    "ColumnDoc",
    "DataContract",
    "DatasetSchema",
    "Relationship",
    "TableDoc",
    "contract",
    "role_note",
    "schema",
    "DATASETS",
    "DatasetSpec",
    "all_datasets",
    "get_dataset",
    "available",
    "load_frame",
    "load_tables",
    "local_path",
    "NotOnboarded",
]
