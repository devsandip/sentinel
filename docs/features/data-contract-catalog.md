# The data contract view (dataset catalogue)

**Branch:** `claude/governance-dataset-explore-df7cae`
**Status:** built
**Surface:** Governance > Datasets > Contract

## The question this answers

The Datasets surface listed eight rows of registry metadata and stopped there.
It proved the platform *has* an inventory, not that the inventory is worth
anything. The obvious fix is an "Explore this dataset" button that opens an EDA
view.

That button would break the demo's own argument.

## Why an EDA button violates the governance model

An explorer that shows values bypasses four controls the rest of the app spends
its time proving:

1. **Purpose limitation (CTL-PURP-01).** Access is gated on *why*, not only on
   who. An Explore button has no declared purpose, so it is data access with no
   reason attached. Six of the eight datasets are Restricted or Confidential.
2. **The autonomy ceiling.** The tier is computed as
   `min(ceiling(classification), ceiling(role, attestations))`. Confidential data
   caps at L1: pick a certified analysis, fill typed parameters, write no code.
   Free-form exploration of `berka` is above the ceiling by construction.
3. **The column grant (CTL-COL-01).** Access builds a scoped table, so a
   withheld column does not exist on the object the code receives. A view that
   renders every column re-materialises exactly what minimisation removed:
   `applicant_email`, `applicant_ssn`, `sex`, raw `age_years`.
4. **The disclosure screen (CTL-DISC-02).** Value counts and histograms are
   grouped counts, and cells below the k-anonymity floor are suppressed. An EDA
   grid emits small cells straight to the page.

A demo whose Governance section quietly hands out ungoverned data reads worse
than one with no drill-down at all.

## What was built instead

A **data contract** view: the catalogue layer, which is a real thing banks run
(Collibra, Alation, a Glue or Unity metastore) and which the platform was
missing. Metadata is published far more widely than data. You read the catalogue
to decide what to request; you declare a purpose to get values. Metadata access
and data access are two different grants.

Per dataset the contract publishes:

- provenance, license, classification, and the tier ceiling that classification
  sets;
- the purposes the matrix permits and refuses, read off the same
  `PURPOSE_MATRIX` that CTL-PURP-01 enforces;
- rows at source vs rows onboarded locally, where the onboard sampled;
- tables, with row counts and descriptions;
- foreign keys with cardinality, for the relational dataset;
- the column dictionary: name, logical type, role, description, and a
  `derived` tag for columns the loader produces rather than the file;
- a role legend saying what each role costs a requester at Access;
- documentation coverage as a bar and a fraction.

And it publishes nothing else. No values, no samples, no distributions, no
missingness, no cardinality, no top values.

## The line drawn

Missingness and cardinality *look* like metadata. They are computed from values,
so they are profile outputs, and profiling is already a governed analysis
(`data_profiling`, which loads under a license check, audits access, and gates
on blocking failures). The catalogue knows the shape; the profile knows the
contents; only the profile is data access. The page ends with two buttons that
route to those governed paths rather than shortcutting them.

Type inference reads a bounded head of each file (200 rows). That is the
platform touching the file to build metadata, not a disclosure: no value read
that way reaches the page, and `tests/test_catalog.py` asserts it by checking
every published string against the real first rows.

## Documentation coverage as a metric, not a cosmetic

`german_credit` is at 100 percent; `lendingclub` is at 26 percent of 152
columns. The gap is reported rather than smoothed over, because an undocumented
column is one nobody can request responsibly, and coverage is a metric a data
governance office actually reports. LendingClub being the worst-documented set
is the same fact that makes it the data-quality dataset.

## Files

- `sentinel/datasets/catalog.py` — the dictionary, roles beyond the registry's,
  derived-column declarations, foreign keys, and `schema()`.
- `app.py` — `render_dataset_contract()`, the per-row Contract button, and the
  `.dict` / `.role` / `.fk` / `.rleg` / `.cov` styles.
- `tests/test_catalog.py` — 12 tests, the load-bearing ones negative: no values
  on the contract, no profile statistics in the dataclasses, registry roles and
  catalogue roles agree, foreign keys reference real columns.

## Decisions

- **Button named "Contract", not "Explore".** The name has to promise what the
  page delivers. "Explore" promises values.
- **Derived columns are published, including the synthetic PII.** They are the
  columns an analysis actually meets, and hiding the redaction control's own
  target would be the dishonest option.
- **The column dictionary is one HTML table, not Streamlit rows.** LendingClub
  is 152 columns; a widget per row would crawl, and no cell here needs a
  popover.
- **The role consequence is a legend, not a per-row note.** Repeating "granted
  only to a purpose whose axis it is" on every protected column turns a
  dictionary into a lecture.
- **Foreign keys render as an edge list, not an ERD.** The relationships are the
  fact; a diagram would be decoration, and a hand-laid 8-node SVG would be
  fragile.
