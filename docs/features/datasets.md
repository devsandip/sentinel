# Dataset onboarding spec

**Purpose:** the verified inventory of public datasets for the governed
multi-analysis platform. Each analysis type has a data contract; this maps every
contract to at least one real, obtainable dataset.

**Hard constraint:** every dataset must download **without an account/login** (no
Kaggle logins). Obtainability below was verified against live sources, not
assumed. Licenses are recorded because Sentinel is a public demo and the
governance layer should carry the license as dataset metadata and block
commercial use where flagged.

---

## Recommendation matrix

| Analysis (data contract) | Dataset | No-account source | Shape | License |
| --- | --- | --- | --- | --- |
| Data discovery + relational feature engineering (multi-table + FKs) | **PKDD'99 Berka** (Czech bank) | raw GitHub TSVs: `raw.githubusercontent.com/dnoeth/1999_Czech_financial_dataset_Teradata/master/fin_{account,client,disp,order,trans,loan,card,district}.tsv` | 8 tables, 1.09M rows (trans 1.056M), real FKs + M:N bridge (`disp`) | No formal license; research/education, document provenance |
| Credit-risk modeling + fairness/bias audit (target + protected attr) | **UCI Default of Credit Card Clients (Taiwan)** | `archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip` | 30,000 rows, 1 table; `SEX`/age/education/marriage columns + default target | **CC BY 4.0** |
| Data profiling + quality triage (messy real table) | **LendingClub** (DePaul sample + Zenodo clean copy) | sample: `bigblue.depaul.edu/jlee141/econdata/LendingClub_LoanData/LC_Loan_sample_2016.csv`; license-clean: Zenodo record `11295916` | full ~2.26M × 152 cols; sample ~30-40k | DePaul mirror unlicensed; Zenodo copy **CC BY 4.0** |
| A/B test / experiment (treatment/control + outcomes) | **Hillstrom MineThatData** | `hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz` (canonical minethatdata URL fails TLS; use S3) | 64,000 rows, 3 randomized arms, visit/conversion/spend | No formal license; permissive by long practice |
| Causal impact (time series + intervention) | **Semi-synthetic ITS** + **California Prop 99** anchor | generate via `tfcausalimpact`; Prop 99: `raw.githubusercontent.com/synth-inference/synthdid/master/data/california_prop99.csv` (semicolon-delimited) | synthetic: arbitrary; Prop 99: ~1,209 rows (39 states × 31 yr) | Apache-2.0 / MIT (synthetic); BSD-3 (Prop 99) |
| Fraud / AML (transaction-level) | **ULB Credit Card Fraud** via **OpenML** (not Kaggle) | `openml.org/data/v1/download/1673544/creditcard.arff` (OpenML id 1597) | 284,807 rows, 1 table, PCA-anonymized + `Class` label | DbCL (commercial-safe) |
| Marketing / propensity (campaign response) | **UCI Bank Marketing** | `archive.ics.uci.edu/static/public/222/bank+marketing.zip` | ~41k rows, term-deposit campaign; **drop `duration` (leakage)** | **CC BY 4.0** |

---

## Minimal reuse set (5 downloads cover all 7 analyses)

Several datasets are multi-purpose, so onboard fewer than seven:

1. **Berka** — relational FE (#1); doubles into credit-fairness (#2, loan default + demographics) and fraud FE (#6, 1M-row transactions).
2. **UCI Taiwan credit** — credit-fairness (#2); secondary messy-EDA (#3, undocumented categories).
3. **LendingClub** — messy-EDA (#3).
4. **Hillstrom** — A/B (#4) and marketing uplift (#7).
5. **UCI Bank Marketing** — marketing/propensity (#7); a second fairness surface.

Two slots need dedicated adds that do not reuse: causal impact (#5) → semi-synthetic ITS + Prop 99; fraud detection (#6) → ULB via OpenML (Berka has no fraud label).

**True minimal onboard: 5 real downloads + 1 generator + 1 tiny real anchor (Prop 99).**

---

## Gated datasets avoided, with no-account substitutes

The operator cannot create accounts. Each gated option and its replacement:

| Gated | Gate | Use instead |
| --- | --- | --- |
| Home Credit Default Risk | Kaggle competition (login + rules) | **Berka** (GitHub TSV) |
| Give Me Some Credit | Kaggle | **OpenML id 45577** (`fetch_openml(data_id=45577)`) |
| Freddie Mac SFLLD | Clarity registration | **LendingClub DePaul mirror** |
| IEEE-CIS Fraud | Kaggle | **ULB via OpenML id 1597** |
| PaySim / Sparkov ready CSVs | Kaggle | run the open generators (adds a generation step) |
| Criteo Uplift | original URL dead + **CC BY-NC-SA (NonCommercial)** | **Hugging Face mirror** for R&D only; do not ship |
| Elliptic Bitcoin AML | Kaggle | PyG `EllipticBitcoinDataset` (auto-download) — license unresolved, pin before use |

---

## Why causal impact is semi-synthetic (not a shortcut)

Every real causal dataset shares one fatal property: the true counterfactual is
unobserved, so you can never verify the estimator recovered the real effect. For
a governed platform that must prove its causal pipeline is calibrated, that is
disqualifying. The semi-synthetic ITS is the only option with known ground truth
(you set the intervention date, effect, pre-period fit, and noise, then show the
estimate recovers the injected effect), it is PII-free and Apache/MIT, and a fixed
seed makes it a reproducible governance artifact. Ship it as the validation
harness; pair it with California Prop 99 as the real-world credibility anchor.

---

## Onboarding order (fastest + lowest legal risk first)

1. **UCI Taiwan credit** (CC BY 4.0, one file) — unlocks #2 + part of #3.
2. **UCI Bank Marketing** (CC BY 4.0, one file) — #7.
3. **Hillstrom** (443 KB) — #4 + #7.
4. **Berka** (8 tables, biggest ingest) — #1, doubles into #2/#6.
5. **ULB fraud** (OpenML) — #6.
6. **LendingClub** (large, messy) — #3.
7. **Semi-synthetic ITS + Prop 99** (zero-footprint) — #5.

After step 5, six of seven analyses are runnable on no-account,
commercially-safe-or-flagged sources.

---

## Governance metadata each dataset carries

Every onboarded dataset registers with: source URL, obtainability (no-account?),
**license** (and a commercial-use flag), row/table counts, the **data contract(s)**
it satisfies, PII/protected-attribute classification per column, and provenance
notes. The cleanest licenses (prefer these when a choice exists): UCI Taiwan, UCI
German, UCI Bank Marketing, Zenodo LendingClub, OxCGRT — all CC BY 4.0.
