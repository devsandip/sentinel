"""Dataset registry (analysis-platform.md, first-slice step 2).

The onboarded-dataset inventory. Each DatasetSpec carries provenance, license (+
a commercial-use flag the governance layer enforces), the capabilities it
provides, and a role for known columns. Seeded from the verified inventory in
docs/features/datasets.md. `onboarded` is True once the data is available
locally; the onboard script flips it by producing the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    CAP_PROTECTED,
    CAP_RELATIONAL,
    CAP_TABULAR,
    CAP_TARGET,
    CAP_TIMESERIES,
    CAP_TREATMENT,
    ROLE_ENTITY_ID,
    ROLE_PROTECTED,
    ROLE_TARGET,
    ROLE_TIMESTAMP,
    ROLE_TREATMENT,
)


@dataclass(frozen=True)
class DatasetSpec:
    id: str
    name: str
    source_url: str
    license: str
    commercial_ok: bool  # governance blocks commercial use when False
    rows: int
    tables: int
    provides: frozenset[str]  # capabilities (see contracts.py)
    column_roles: dict[str, str] = field(default_factory=dict)
    onboarded: bool = False  # is the data available locally?
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_url": self.source_url,
            "license": self.license,
            "commercial_ok": self.commercial_ok,
            "rows": self.rows,
            "tables": self.tables,
            "provides": sorted(self.provides),
            "onboarded": self.onboarded,
            "notes": self.notes,
        }


# The verified inventory. german_credit is onboarded (ships with the repo); the
# rest are registered with metadata + contracts and flip to onboarded when the
# onboard script produces their local file.
DATASETS: list[DatasetSpec] = [
    DatasetSpec(
        id="german_credit",
        name="UCI Statlog German Credit",
        source_url="https://archive.ics.uci.edu/static/public/144/statlog+german+credit+data.zip",
        license="CC BY 4.0",
        commercial_ok=True,
        rows=1000,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TARGET, CAP_PROTECTED}),
        column_roles={
            # Raw columns present in german_credit.csv; the modeling loader
            # derives y/sex/age_band and injects synthetic PII at load time.
            "credit_risk": ROLE_TARGET,
            "personal_status_sex": ROLE_PROTECTED,
            "age_years": ROLE_PROTECTED,
        },
        onboarded=True,
        notes="The anchor dataset; ships with the repo. Modeling loader derives "
        "sex/age_band and injects synthetic PII to demonstrate redaction.",
    ),
    DatasetSpec(
        id="uci_taiwan_credit",
        name="UCI Default of Credit Card Clients (Taiwan)",
        source_url="https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip",
        license="CC BY 4.0",
        commercial_ok=True,
        rows=30000,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TARGET, CAP_PROTECTED}),
        column_roles={
            "default_payment_next_month": ROLE_TARGET,
            "SEX": ROLE_PROTECTED,
            "AGE": ROLE_PROTECTED,
        },
        notes="Clean CC BY 4.0; SEX/AGE as columns. Credit-fairness primary.",
    ),
    DatasetSpec(
        id="berka",
        name="PKDD'99 Financial (Berka, Czech bank)",
        source_url="https://raw.githubusercontent.com/jlacko/berka-dataset/master/",
        license="No formal license (research/education)",
        commercial_ok=False,
        rows=1090086,
        tables=8,
        provides=frozenset({CAP_TABULAR, CAP_RELATIONAL, CAP_TARGET, CAP_PROTECTED}),
        column_roles={
            "default": ROLE_TARGET,  # loan.status B/D
            "gender": ROLE_PROTECTED,  # derived from client.birth_number
            "age_band": ROLE_PROTECTED,
            "account_id": ROLE_ENTITY_ID,
        },
        notes="Relational backbone: 8 tables + FKs + M:N bridge (jlacko mirror, "
        "faithful original). Feature-eng primary; onboarded as a sample of "
        "loan-holding accounts with full transaction depth. gender/age_band "
        "derived from birth_number.",
    ),
    DatasetSpec(
        id="hillstrom",
        name="Hillstrom MineThatData email",
        source_url="https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz",
        license="No formal license (permissive by practice)",
        commercial_ok=False,
        rows=64000,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TREATMENT}),
        column_roles={"segment": ROLE_TREATMENT, "spend": "outcome", "conversion": "outcome"},
        notes="RCT: 3 arms + visit/conversion/spend. Experiment primary.",
    ),
    DatasetSpec(
        id="ulb_fraud",
        name="ULB Credit Card Fraud (OpenML 1597)",
        source_url="https://www.openml.org/data/v1/download/1673544/creditcard.arff",
        license="DbCL 1.0",
        commercial_ok=True,
        rows=284807,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TARGET}),
        column_roles={"Class": ROLE_TARGET},
        notes="PCA-anonymized fraud label. Fraud detection primary.",
    ),
    DatasetSpec(
        id="lendingclub",
        name="LendingClub 2007-2018 (messy)",
        source_url="https://bigblue.depaul.edu/jlee141/econdata/LendingClub_LoanData/LC_Loan_sample_2016.csv",
        license="DePaul mirror unlicensed; Zenodo copy CC BY 4.0",
        commercial_ok=False,
        rows=2260000,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TARGET}),
        notes="Canonical messy finance table. Data-quality triage primary; sampled on onboard.",
    ),
    DatasetSpec(
        id="uci_bank_marketing",
        name="UCI Bank Marketing",
        source_url="https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
        license="CC BY 4.0",
        commercial_ok=True,
        rows=41188,
        tables=1,
        provides=frozenset({CAP_TABULAR, CAP_TARGET}),
        column_roles={"y": ROLE_TARGET},
        notes="Term-deposit campaign. Marketing/propensity primary. Drop 'duration' (leakage).",
    ),
    DatasetSpec(
        id="synthetic_its",
        name="Semi-synthetic interrupted time series",
        source_url="(generated) labeled injected effect",
        license="Apache-2.0 / MIT (generated)",
        commercial_ok=True,
        rows=365,
        tables=1,
        provides=frozenset({CAP_TIMESERIES, CAP_TREATMENT}),
        column_roles={"date": ROLE_TIMESTAMP, "intervention": ROLE_TREATMENT},
        onboarded=True,
        notes="Fully synthetic: a daily metric with a known +12 effect injected from "
        "day 250. Ground truth is known, so it validates causal-impact analysis. The "
        "only Public-class dataset, and the only legal home for the L3 sandbox.",
    ),
]

DATASETS_BY_ID: dict[str, DatasetSpec] = {d.id: d for d in DATASETS}


def all_datasets() -> list[DatasetSpec]:
    return list(DATASETS)


def get_dataset(dataset_id: str) -> DatasetSpec | None:
    return DATASETS_BY_ID.get(dataset_id)


def onboarded_datasets() -> list[DatasetSpec]:
    return [d for d in DATASETS if d.onboarded]
