"""The data catalogue: schema and dictionary, without the data.

A bank's analysts do not discover data by opening it. They browse a catalogue
(Collibra, Alation, a Glue/Unity metastore) that publishes *metadata* -- tables,
columns, types, roles, descriptions, relationships, lineage, ownership -- to a
far wider audience than the data itself. You read the catalogue to decide what
to request; you declare a purpose to get the values. Metadata access and data
access are two different grants, and conflating them is the mistake this module
exists to avoid.

So this module publishes the contract and nothing under it:

  * column names, types, roles, and descriptions -- yes,
  * table row counts and foreign keys -- yes,
  * cell values, distributions, top values, missingness, samples -- no.

Missingness and cardinality look like metadata but are computed *from* values;
they are profile outputs, and profiling is a governed analysis (`data_profiling`
in the analysis catalog) that runs under a declared purpose. The line this
module draws: the catalogue knows the shape, the profile knows the contents, and
only the profile is data access.

Types are inferred by reading a bounded head of the file (`_DTYPE_SAMPLE_ROWS`).
That is the platform touching the file to build metadata, which is not a
disclosure to the reader: no value read that way reaches the page.

Documentation coverage is reported rather than smoothed over. An undocumented
column says so, and the coverage percentage is a catalogue-completeness metric
in its own right -- the same metric a data-governance office reports on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from .contracts import (
    ROLE_ENTITY_ID,
    ROLE_FEATURE,
    ROLE_OUTCOME,
    ROLE_PII,
    ROLE_PROTECTED,
    ROLE_TARGET,
    ROLE_TIMESTAMP,
    ROLE_TREATMENT,
)
from .loaders import available, local_dir, local_path
from .registry import get_dataset

# Rows read to infer a column's type. Bounded on purpose: type inference is a
# metadata build step, not a scan, and lendingclub is 152 columns wide.
_DTYPE_SAMPLE_ROWS = 200

# How a pandas dtype is presented. The catalogue publishes a logical type, not
# numpy's storage type: "object" tells an analyst nothing.
_DTYPE_LABEL = {
    "object": "string",
    "str": "string",
    "int64": "integer",
    "float64": "decimal",
    "bool": "boolean",
    "datetime64[ns]": "timestamp",
}


@dataclass(frozen=True)
class ColumnDoc:
    """One column of the contract. `description` empty means undocumented, and
    the catalogue says so rather than inventing a description."""

    name: str
    dtype: str
    role: str = ROLE_FEATURE
    description: str = ""
    derived: bool = False  # produced at load time, not present in the file

    @property
    def documented(self) -> bool:
        return bool(self.description)


@dataclass(frozen=True)
class TableDoc:
    name: str
    description: str
    rows: int
    columns: list[ColumnDoc] = field(default_factory=list)


@dataclass(frozen=True)
class Relationship:
    """A foreign key between two tables, as the catalogue publishes it."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str  # "many-to-one" | "one-to-one"
    note: str = ""

    def label(self) -> str:
        return (
            f"{self.from_table}.{self.from_column} -> "
            f"{self.to_table}.{self.to_column}"
        )


@dataclass(frozen=True)
class DatasetSchema:
    dataset_id: str
    tables: list[TableDoc]
    relationships: list[Relationship]
    onboarded: bool

    @property
    def n_columns(self) -> int:
        return sum(len(t.columns) for t in self.tables)

    @property
    def n_documented(self) -> int:
        return sum(1 for t in self.tables for c in t.columns if c.documented)

    @property
    def coverage(self) -> float:
        """Share of columns carrying a description. A governance metric, not a
        vanity one: an undocumented column is a column nobody can request
        responsibly."""
        return self.n_documented / self.n_columns if self.n_columns else 0.0

    def sensitive_columns(self) -> list[ColumnDoc]:
        """Columns a purpose has to justify by name: PII and protected
        attributes."""
        return [
            c
            for t in self.tables
            for c in t.columns
            if c.role in (ROLE_PII, ROLE_PROTECTED)
        ]


# ---------------------------------------------------------------------------
# Table descriptions
# ---------------------------------------------------------------------------
# Single-table datasets use the sentinel table name "" (the dataset is the
# table); relational ones key by table name.

_TABLE_DOCS: dict[str, dict[str, str]] = {
    "german_credit": {
        "": "One row per loan applicant, with the credit decision outcome. The "
        "anchor dataset for the fair-lending route."
    },
    "uci_taiwan_credit": {
        "": "One row per credit-card client, with six months of repayment and "
        "billing history and a next-month default flag."
    },
    "ulb_fraud": {
        "": "One row per card transaction over two days, PCA-anonymised by the "
        "publisher before release."
    },
    "hillstrom": {
        "": "One row per customer in a three-arm email randomised trial, with "
        "the arm assigned and the outcomes observed."
    },
    "lendingclub": {
        "": "One row per funded loan, as LendingClub published it. Wide, "
        "inconsistently populated, and heavy with post-origination columns "
        "that leak the outcome; that is why it is the data-quality dataset."
    },
    "uci_bank_marketing": {
        "": "One row per contact attempt in a term-deposit campaign, with "
        "macroeconomic context at the time of the call."
    },
    "synthetic_its": {
        "": "One row per day: a metric series with a known effect injected "
        "from day 250, plus an untreated control series."
    },
    "berka": {
        "account": "The account, its home district, and its statement frequency.",
        "client": "The individual, with birth-derived demographics.",
        "disp": "Disposition: the many-to-many bridge between clients and "
        "accounts, marking who owns an account and who merely operates it.",
        "card": "Credit cards issued against a disposition.",
        "loan": "Loans granted on an account, with the repayment status.",
        "order": "Standing payment orders leaving an account.",
        "trans": "Transactions on an account. The deep table; the feature-"
        "engineering surface.",
        "district": "Demographic and economic attributes of a district.",
    },
}


# ---------------------------------------------------------------------------
# Column dictionary
# ---------------------------------------------------------------------------
# Keyed dataset -> column (single-table) or dataset -> "table.column"
# (relational). A missing entry is an undocumented column, reported as such.

_COLUMN_DOCS: dict[str, dict[str, str]] = {
    "german_credit": {
        "checking_status": "Status of the existing checking account, as a coded band (A11-A14).",
        "duration_months": "Term of the requested credit, in months.",
        "credit_history": "Coded repayment history on prior credits (A30-A34).",
        "purpose": "Coded purpose of the credit (car, furniture, education, business...).",
        "credit_amount": "Amount of credit requested, in Deutsche Marks.",
        "savings_status": "Savings account or bonds balance, as a coded band (A61-A65).",
        "employment_since": "Length of current employment, as a coded band (A71-A75).",
        "installment_rate": "Instalment as a percentage of disposable income (1-4).",
        "personal_status_sex": "Coded personal status combined with sex (A91-A95). The "
        "source of the derived sex attribute, which is why it is protected.",
        "other_debtors": "Co-applicants or guarantors on the credit (A101-A103).",
        "residence_since": "Years at the present residence.",
        "property_type": "Most valuable property owned, coded (A121-A124).",
        "age_years": "Applicant age in years. The source of the derived age band.",
        "other_installment_plans": "Instalment plans held elsewhere (bank, stores, none).",
        "housing": "Housing tenure: rent, own, or free (A151-A153).",
        "existing_credits": "Number of existing credits at this bank.",
        "job": "Coded job category and skill level (A171-A174).",
        "num_dependents": "Number of dependants the applicant maintains.",
        "telephone": "Whether a telephone is registered to the applicant.",
        "foreign_worker": "Whether the applicant is a foreign worker (A201/A202).",
        "credit_risk": "The published outcome label, 'good' or 'bad'. Only the derived "
        "0/1 target is granted to an analysis.",
        # Derived at load (sentinel/ml/data.py).
        "y": "Derived 0/1 target: 1 when credit_risk is 'bad' (defaulted).",
        "sex": "Derived from personal_status_sex per the UCI codebook. A protected "
        "attribute, excluded from model features.",
        "age_band": "Derived band over age_years. The fair-lending axis; banding is the "
        "minimisation, so the analysis never sees a raw age.",
        "foreign_worker_label": "Readable form of foreign_worker.",
        "applicant_email": "Synthetic email, injected at load. German Credit carries "
        "almost no PII; this column exists so the redaction control has a real target.",
        "applicant_ssn": "Synthetic national ID, injected at load. Same purpose as "
        "applicant_email: it is what CTL-PII-01 redacts.",
    },
    "uci_taiwan_credit": {
        "LIMIT_BAL": "Credit limit granted, in New Taiwan dollars, including family credit.",
        "SEX": "Client sex (1 male, 2 female). Protected attribute.",
        "EDUCATION": "Education level (1 graduate school ... 4 other).",
        "MARRIAGE": "Marital status (1 married, 2 single, 3 other).",
        "AGE": "Client age in years. Protected attribute.",
        "PAY_0": "Repayment status in the most recent month (-1 paid duly, 1-9 months delayed).",
        "PAY_2": "Repayment status one month earlier.",
        "PAY_3": "Repayment status two months earlier.",
        "PAY_4": "Repayment status three months earlier.",
        "PAY_5": "Repayment status four months earlier.",
        "PAY_6": "Repayment status five months earlier.",
        "BILL_AMT1": "Bill statement amount, most recent month.",
        "BILL_AMT2": "Bill statement amount, one month earlier.",
        "BILL_AMT3": "Bill statement amount, two months earlier.",
        "BILL_AMT4": "Bill statement amount, three months earlier.",
        "BILL_AMT5": "Bill statement amount, four months earlier.",
        "BILL_AMT6": "Bill statement amount, five months earlier.",
        "PAY_AMT1": "Amount paid, most recent month.",
        "PAY_AMT2": "Amount paid, one month earlier.",
        "PAY_AMT3": "Amount paid, two months earlier.",
        "PAY_AMT4": "Amount paid, three months earlier.",
        "PAY_AMT5": "Amount paid, four months earlier.",
        "PAY_AMT6": "Amount paid, five months earlier.",
        "default_payment_next_month": "Target: 1 if the client defaults next month.",
    },
    "hillstrom": {
        "recency": "Months since the customer's last purchase.",
        "history_segment": "Banded prior spend, as the publisher segmented it.",
        "history": "Actual dollars spent in the past year.",
        "mens": "1 if the customer bought men's merchandise in the past year.",
        "womens": "1 if the customer bought women's merchandise in the past year.",
        "zip_code": "Coarse location class: urban, suburban, or rural.",
        "newbie": "1 if the customer was acquired in the past twelve months.",
        "channel": "Channel the customer previously purchased through.",
        "segment": "Randomised arm: men's email, women's email, or no email. The "
        "treatment assignment, and the reason this dataset supports causal claims.",
        "visit": "1 if the customer visited the site in the two weeks after the send.",
        "conversion": "1 if the customer purchased in the two weeks after the send.",
        "spend": "Dollars spent in the two weeks after the send.",
    },
    "synthetic_its": {
        "date": "Daily time axis over one year.",
        "intervention": "0 before the injected change, 1 from day 250. The treatment flag.",
        "control": "An untreated comparison series, for a difference-in-differences read.",
        "metric": "The observed daily metric. A +12 effect is injected from day 250, so "
        "the ground truth is known and a causal estimate can be scored against it.",
    },
    "uci_bank_marketing": {
        "age": "Client age in years.",
        "job": "Job category.",
        "marital": "Marital status.",
        "education": "Education level.",
        "default": "Whether the client has credit in default.",
        "housing": "Whether the client has a housing loan.",
        "loan": "Whether the client has a personal loan.",
        "contact": "Contact channel for this campaign: cellular or telephone.",
        "month": "Month of last contact.",
        "day_of_week": "Weekday of last contact.",
        "duration": "Call duration in seconds. Leaks the outcome (a zero-second call never "
        "subscribes) and is dropped before modeling.",
        "campaign": "Contacts made to this client during this campaign.",
        "pdays": "Days since the client was last contacted in a prior campaign; 999 means never.",
        "previous": "Contacts made to this client before this campaign.",
        "poutcome": "Outcome of the previous campaign.",
        "emp.var.rate": "Employment variation rate, quarterly macro indicator.",
        "cons.price.idx": "Consumer price index, monthly.",
        "cons.conf.idx": "Consumer confidence index, monthly.",
        "euribor3m": "Three-month Euribor rate, daily.",
        "nr.employed": "Number of employees, quarterly macro indicator.",
        "y": "Target: whether the client subscribed to the term deposit.",
    },
    "ulb_fraud": {
        # V1..V28 are documented programmatically below; the publisher released
        # them as unlabelled principal components and describing them
        # individually would be invention.
        "Amount": "Transaction amount. One of two columns the publisher left untransformed.",
        "Class": "Target: 1 for a fraudulent transaction. Roughly 0.17 percent positive.",
    },
    "lendingclub": {
        "id": "Loan listing identifier.",
        "member_id": "Borrower identifier, blanked by the publisher in later releases.",
        "loan_amnt": "Amount the borrower applied for.",
        "funded_amnt": "Amount actually committed to the loan.",
        "term": "Loan term: 36 or 60 months.",
        "int_rate": "Interest rate on the loan.",
        "installment": "Monthly payment owed.",
        "grade": "LendingClub's assigned credit grade, A through G.",
        "sub_grade": "Finer grade within the letter grade.",
        "emp_title": "Free-text job title supplied by the borrower. Unnormalised and "
        "high-cardinality; a data-quality problem and a re-identification risk.",
        "emp_length": "Years employed, capped at 10+.",
        "home_ownership": "Housing tenure reported at application.",
        "annual_inc": "Self-reported annual income.",
        "verification_status": "Whether income was verified by LendingClub.",
        "issue_d": "Month the loan was funded.",
        "loan_status": "Current status of the loan. Post-origination: it is the outcome, "
        "not a feature.",
        "purpose": "Borrower-stated purpose of the loan.",
        "title": "Borrower-supplied free-text loan title. Overlaps purpose, inconsistently.",
        "zip_code": "First three digits of the borrower's postcode. Quasi-identifier.",
        "addr_state": "Borrower's state.",
        "dti": "Debt-to-income ratio, excluding mortgage.",
        "delinq_2yrs": "Delinquencies over 30 days in the past two years.",
        "earliest_cr_line": "Month the borrower's first credit line was opened.",
        "fico_range_low": "Lower bound of the FICO band at origination.",
        "fico_range_high": "Upper bound of the FICO band at origination.",
        "inq_last_6mths": "Credit inquiries in the past six months.",
        "open_acc": "Open credit lines in the borrower's file.",
        "pub_rec": "Derogatory public records.",
        "revol_bal": "Total revolving balance.",
        "revol_util": "Revolving line utilisation rate.",
        "total_acc": "Total credit lines ever held.",
        "out_prncp": "Remaining outstanding principal. Post-origination.",
        "total_pymnt": "Payments received to date. Post-origination.",
        "recoveries": "Post-charge-off gross recovery. Post-origination, and a direct "
        "outcome leak if modelled as a feature.",
        "last_pymnt_d": "Month of the last payment received. Post-origination.",
        "policy_code": "1 for publicly available products, 2 for products not offered publicly.",
        "application_type": "Individual or joint application.",
        "hardship_flag": "Whether the borrower is on a hardship plan. Post-origination.",
        "debt_settlement_flag": "Whether the borrower settled the debt. Post-origination.",
        "year": "Issue year, added on onboarding to make the sample stratification visible.",
    },
    "berka": {
        "account.account_id": "Account identifier. The join key most tables hang off.",
        "account.district_id": "District the account is held in.",
        "account.frequency": "Statement issuance frequency.",
        "account.date": "Account opening date (YYMMDD).",
        "client.client_id": "Client identifier.",
        "client.birth_number": "Encoded birth date and sex: females carry +50 on the month. "
        "A quasi-identifier, and the source of both derived demographics.",
        "client.district_id": "District the client lives in.",
        "client.birth_year": "Birth year decoded from birth_number.",
        "client.gender": "Sex decoded from the month offset in birth_number. Protected attribute.",
        "client.age_1999": "Age at the dataset's 1999 cut-off.",
        "client.age_band": "Banded age. The fairness axis, banded rather than raw.",
        "disp.disp_id": "Disposition identifier.",
        "disp.client_id": "Client on this disposition.",
        "disp.account_id": "Account on this disposition.",
        "disp.type": "OWNER or DISPONENT. Only an owner may order a permanent payment; "
        "the distinction is an entitlement, not a label.",
        "card.card_id": "Card identifier.",
        "card.disp_id": "Disposition the card was issued against.",
        "card.type": "Card class: junior, classic, or gold.",
        "card.issued": "Issue date.",
        "loan.loan_id": "Loan identifier.",
        "loan.account_id": "Account the loan is granted on.",
        "loan.date": "Date the loan was granted.",
        "loan.amount": "Loan amount.",
        "loan.duration": "Loan term in months.",
        "loan.payments": "Monthly payment.",
        "loan.status": "A/B/C/D: finished or running, contract met or in default.",
        "loan.default": "Derived 0/1 target: 1 for statuses B and D (in default).",
        "order.order_id": "Standing order identifier.",
        "order.account_id": "Account the order debits.",
        "order.bank_to": "Recipient bank code.",
        "order.account_to": "Recipient account number.",
        "order.amount": "Debited amount.",
        "order.k_symbol": "Characterisation: household, insurance, loan payment, leasing.",
        "trans.trans_id": "Transaction identifier.",
        "trans.account_id": "Account the transaction belongs to.",
        "trans.date": "Transaction date.",
        "trans.type": "Credit or withdrawal.",
        "trans.operation": "Mode: card withdrawal, cash, remittance to or from another bank.",
        "trans.amount": "Transaction amount.",
        "trans.balance": "Balance after the transaction.",
        "trans.k_symbol": "Characterisation: interest credited, sanction interest, "
        "household, pension, statement payment.",
        "trans.bank": "Counterparty bank code.",
        "trans.account": "Counterparty account number.",
        "district.A1": "District code. The key account and client join to.",
        "district.A2": "District name.",
        "district.A3": "Region.",
        "district.A4": "Inhabitants.",
        "district.A5": "Municipalities under 499 inhabitants.",
        "district.A6": "Municipalities 500-1999.",
        "district.A7": "Municipalities 2000-9999.",
        "district.A8": "Municipalities over 10000.",
        "district.A9": "Cities in the district.",
        "district.A10": "Ratio of urban inhabitants.",
        "district.A11": "Average salary.",
        "district.A12": "Unemployment rate, 1995.",
        "district.A13": "Unemployment rate, 1996.",
        "district.A14": "Entrepreneurs per 1000 inhabitants.",
        "district.A15": "Crimes committed, 1995.",
        "district.A16": "Crimes committed, 1996.",
    },
}

# The 28 anonymised components of ulb_fraud. Written as a loop because the
# publisher genuinely did not disclose what they are; one honest sentence
# repeated beats 28 invented ones.
for _i in range(1, 29):
    _COLUMN_DOCS["ulb_fraud"][f"V{_i}"] = (
        f"Principal component {_i} of the undisclosed original features. The "
        "publisher PCA-transformed everything except Amount and time before release."
    )


# ---------------------------------------------------------------------------
# Column roles beyond what the registry pins
# ---------------------------------------------------------------------------
# registry.DatasetSpec.column_roles carries the roles the contract matcher needs
# (target, protected, treatment, entity id). The catalogue adds the rest: PII,
# timestamps, and the outcome columns, so a reader can see at a glance which
# columns a purpose will have to justify.

_EXTRA_ROLES: dict[str, dict[str, str]] = {
    "german_credit": {
        "applicant_email": ROLE_PII,
        "applicant_ssn": ROLE_PII,
        "sex": ROLE_PROTECTED,
        "age_band": ROLE_PROTECTED,
        "foreign_worker": ROLE_PROTECTED,
        "foreign_worker_label": ROLE_PROTECTED,
        "y": ROLE_TARGET,
    },
    "uci_taiwan_credit": {},
    "hillstrom": {
        "zip_code": ROLE_PROTECTED,
        "visit": ROLE_OUTCOME,
    },
    "synthetic_its": {"metric": ROLE_OUTCOME},
    "uci_bank_marketing": {
        "age": ROLE_PROTECTED,
        "marital": ROLE_PROTECTED,
        "job": ROLE_PROTECTED,
        "education": ROLE_PROTECTED,
    },
    "lendingclub": {
        "id": ROLE_ENTITY_ID,
        "member_id": ROLE_PII,
        "emp_title": ROLE_PII,
        "zip_code": ROLE_PII,
        "addr_state": ROLE_PROTECTED,
        "url": ROLE_PII,
        "desc": ROLE_PII,
        "loan_status": ROLE_TARGET,
        "issue_d": ROLE_TIMESTAMP,
    },
    "ulb_fraud": {},
    "berka": {
        "account.account_id": ROLE_ENTITY_ID,
        "account.date": ROLE_TIMESTAMP,
        "client.client_id": ROLE_ENTITY_ID,
        "client.birth_number": ROLE_PII,
        "client.gender": ROLE_PROTECTED,
        "client.age_band": ROLE_PROTECTED,
        "client.age_1999": ROLE_PROTECTED,
        "client.birth_year": ROLE_PROTECTED,
        "disp.disp_id": ROLE_ENTITY_ID,
        "card.card_id": ROLE_ENTITY_ID,
        "card.issued": ROLE_TIMESTAMP,
        "loan.loan_id": ROLE_ENTITY_ID,
        "loan.date": ROLE_TIMESTAMP,
        "loan.default": ROLE_TARGET,
        "order.order_id": ROLE_ENTITY_ID,
        "order.account_to": ROLE_PII,
        "trans.trans_id": ROLE_ENTITY_ID,
        "trans.date": ROLE_TIMESTAMP,
        "trans.account": ROLE_PII,
    },
}


# ---------------------------------------------------------------------------
# Columns derived at load time
# ---------------------------------------------------------------------------
# These are not in the file. They are produced by the loader (sentinel/ml/data.py
# for german_credit, the onboard script for berka) and they are the columns an
# analysis actually meets, so the catalogue publishes them and marks them
# derived. Two of german_credit's are synthetic PII that exist purely to give
# the redaction control something real to redact; hiding them would be the
# dishonest option.

_DERIVED: dict[str, dict[str, str]] = {
    "german_credit": {
        "y": "integer",
        "sex": "string",
        "age_band": "string",
        "foreign_worker_label": "string",
        "applicant_email": "string",
        "applicant_ssn": "string",
    },
}


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

_RELATIONSHIPS: dict[str, list[Relationship]] = {
    "berka": [
        Relationship("disp", "client_id", "client", "client_id", "many-to-one",
                     "the bridge: a client may hold several dispositions"),
        Relationship("disp", "account_id", "account", "account_id", "many-to-one",
                     "the bridge: an account may be operated by several clients"),
        Relationship("account", "district_id", "district", "A1", "many-to-one"),
        Relationship("client", "district_id", "district", "A1", "many-to-one"),
        Relationship("card", "disp_id", "disp", "disp_id", "one-to-one"),
        Relationship("loan", "account_id", "account", "account_id", "many-to-one",
                     "at most one loan per account in this dataset"),
        Relationship("order", "account_id", "account", "account_id", "many-to-one"),
        Relationship("trans", "account_id", "account", "account_id", "many-to-one",
                     "the deep side: the transaction table carries the row volume"),
    ],
}


# ---------------------------------------------------------------------------
# Building the schema
# ---------------------------------------------------------------------------


def _label_dtype(dtype: object) -> str:
    return _DTYPE_LABEL.get(str(dtype), str(dtype))


def _read_head(path) -> tuple[pd.DataFrame, int]:  # noqa: ANN001
    """The bounded head used for type inference, plus the file's row count.

    The row count is a line count, not a read: no value leaves this function.
    """
    head = pd.read_csv(path, nrows=_DTYPE_SAMPLE_ROWS)
    with path.open("rb") as fh:
        rows = max(sum(1 for _ in fh) - 1, 0)
    return head, rows


def _columns_for(
    dataset_id: str, table: str, head: pd.DataFrame, registry_roles: dict[str, str]
) -> list[ColumnDoc]:
    docs = _COLUMN_DOCS.get(dataset_id, {})
    extra = _EXTRA_ROLES.get(dataset_id, {})
    out: list[ColumnDoc] = []
    for name in head.columns:
        key = f"{table}.{name}" if table else name
        role = extra.get(key) or registry_roles.get(name) or ROLE_FEATURE
        out.append(
            ColumnDoc(
                name=name,
                dtype=_label_dtype(head[name].dtype),
                role=role,
                description=docs.get(key, ""),
            )
        )
    # Derived columns are appended in declaration order, after the file's own.
    for name, dtype in _DERIVED.get(dataset_id, {}).items():
        role = extra.get(name) or registry_roles.get(name) or ROLE_FEATURE
        out.append(
            ColumnDoc(
                name=name,
                dtype=dtype,
                role=role,
                description=docs.get(name, ""),
                derived=True,
            )
        )
    return out


@lru_cache(maxsize=32)
def schema(dataset_id: str) -> DatasetSchema:
    """The published contract for one dataset: tables, columns, types, roles,
    descriptions, and foreign keys. No values.

    Returns an empty schema (onboarded=False) when the dataset is registered but
    its local file is not present, rather than raising: the catalogue entry
    exists whether or not the data has landed, which is the point of a
    catalogue.
    """
    spec = get_dataset(dataset_id)
    if spec is None:
        raise KeyError(f"unknown dataset {dataset_id!r}")
    rels = _RELATIONSHIPS.get(dataset_id, [])
    if not available(dataset_id):
        return DatasetSchema(dataset_id, [], rels, onboarded=False)

    table_docs = _TABLE_DOCS.get(dataset_id, {})
    tables: list[TableDoc] = []
    if spec.tables > 1:
        for path in sorted(local_dir(dataset_id).glob("*.csv")):
            head, rows = _read_head(path)
            tables.append(
                TableDoc(
                    name=path.stem,
                    description=table_docs.get(path.stem, ""),
                    rows=rows,
                    columns=_columns_for(dataset_id, path.stem, head, spec.column_roles),
                )
            )
    else:
        head, rows = _read_head(local_path(dataset_id))
        tables.append(
            TableDoc(
                name=dataset_id,
                description=table_docs.get("", ""),
                rows=rows,
                columns=_columns_for(dataset_id, "", head, spec.column_roles),
            )
        )
    return DatasetSchema(dataset_id, tables, rels, onboarded=True)


def role_note(role: str) -> str:
    """Why a role matters at Access, in one line. The catalogue's job is to tell
    a reader what a column will cost them to request."""
    return {
        ROLE_TARGET: "the modelled outcome; granted to analyses that model it",
        ROLE_PROTECTED: "protected attribute; granted only to a purpose whose axis it is",
        ROLE_PII: "personally identifying; never granted, and redacted before any "
        "text reaches a model (CTL-PII-01)",
        ROLE_TREATMENT: "experiment arm; the assignment a causal claim rests on",
        ROLE_OUTCOME: "measured outcome of the experiment",
        ROLE_TIMESTAMP: "time axis; also the window a purpose may be limited to",
        ROLE_ENTITY_ID: "join key; identifies an entity, so it carries linkage risk",
        ROLE_FEATURE: "ordinary model input",
    }.get(role, "")
