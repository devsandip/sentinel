"""The data catalogue publishes the contract and nothing under it.

The tests that matter here are the negative ones: the catalogue must not become
a data browser by accident. A schema carries no values, so nothing it returns
may be traceable to a row.
"""

from __future__ import annotations

import pandas as pd
import pytest

from sentinel.datasets import all_datasets, role_note, schema
from sentinel.datasets.catalog import ColumnDoc, DatasetSchema
from sentinel.datasets.contracts import ROLE_PII, ROLE_PROTECTED
from sentinel.datasets.loaders import local_path


def test_every_registered_dataset_publishes_a_schema():
    for spec in all_datasets():
        sch = schema(spec.id)
        assert sch.onboarded, f"{spec.id} is not onboarded"
        assert sch.tables, spec.id
        assert sch.n_columns > 0, spec.id


def test_table_count_matches_the_registry():
    for spec in all_datasets():
        assert len(schema(spec.id).tables) == spec.tables, spec.id


def test_the_schema_carries_no_values():
    """The contract is metadata. Nothing a schema exposes may be a cell.

    Checked against the real file: no string field of any ColumnDoc may equal a
    value from the dataset's first rows.
    """
    sch = schema("german_credit")
    head = pd.read_csv(local_path("german_credit"), nrows=25)
    values = {str(v) for v in head.to_numpy().ravel()}
    for col in sch.tables[0].columns:
        for field in (col.dtype, col.role, col.description):
            assert field not in values, f"{col.name} leaked a value: {field!r}"


def test_no_missingness_or_cardinality_on_the_contract():
    """Profile statistics are computed from values, so they belong to the
    governed profiling analysis, not to the catalogue."""
    forbidden = {"n_missing", "pct_missing", "n_unique", "top_value", "top_freq", "stats"}
    assert not forbidden & set(ColumnDoc.__dataclass_fields__)
    assert not forbidden & set(DatasetSchema.__dataclass_fields__)


def test_pii_columns_are_published_as_pii():
    """german_credit's synthetic PII is derived at load, not in the file. The
    catalogue still publishes it: an analyst meets those columns, and hiding
    the redaction control's own target would be the dishonest option."""
    cols = {c.name: c for c in schema("german_credit").tables[0].columns}
    for name in ("applicant_email", "applicant_ssn"):
        assert cols[name].derived
        assert cols[name].role == ROLE_PII
    assert cols["age_band"].role == ROLE_PROTECTED
    assert cols["age_band"].derived


def test_registry_column_roles_survive_into_the_catalogue():
    """A role pinned in the registry (what the contract matcher reads) must be
    the role the catalogue shows, or the two disagree in public."""
    for spec in all_datasets():
        sch = schema(spec.id)
        published = {c.name: c.role for t in sch.tables for c in t.columns}
        for col, role in spec.column_roles.items():
            if col in published and "." not in col:
                assert published[col] == role or published[col] in (ROLE_PII,), (
                    f"{spec.id}.{col}: registry says {role}, catalogue says "
                    f"{published[col]}"
                )


def test_berka_relationships_reference_real_tables_and_columns():
    sch = schema("berka")
    tables = {t.name: {c.name for c in t.columns} for t in sch.tables}
    assert sch.relationships
    for rel in sch.relationships:
        assert rel.from_table in tables, rel.label()
        assert rel.to_table in tables, rel.label()
        assert rel.from_column in tables[rel.from_table], rel.label()
        assert rel.to_column in tables[rel.to_table], rel.label()


def test_single_table_datasets_have_no_relationships():
    for spec in all_datasets():
        if spec.tables == 1:
            assert not schema(spec.id).relationships, spec.id


def test_documentation_coverage_is_reported_not_faked():
    """Coverage is a real fraction over real descriptions. lendingclub is the
    honest low-water mark: 152 columns, most of them undocumented, which is
    exactly why it is the data-quality dataset."""
    assert schema("german_credit").coverage == 1.0
    lc = schema("lendingclub")
    assert 0.0 < lc.coverage < 1.0
    assert lc.n_documented == sum(
        1 for t in lc.tables for c in t.columns if c.description
    )


def test_sensitive_columns_are_the_pii_and_protected_ones():
    sens = schema("german_credit").sensitive_columns()
    assert {c.name for c in sens} >= {
        "applicant_email",
        "applicant_ssn",
        "sex",
        "age_band",
        "personal_status_sex",
    }
    assert all(c.role in (ROLE_PII, ROLE_PROTECTED) for c in sens)


def test_unknown_dataset_raises():
    with pytest.raises(KeyError):
        schema("not_a_dataset")


def test_every_role_in_use_has_a_note():
    """The catalogue tells a reader what a role will cost them at Access. A
    role with no note is a chip that explains nothing."""
    for spec in all_datasets():
        for table in schema(spec.id).tables:
            for col in table.columns:
                assert role_note(col.role), f"{spec.id}.{col.name}: {col.role}"
