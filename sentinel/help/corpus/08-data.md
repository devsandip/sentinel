---
id: data
title: Data
chapter: Data
summary: The registered datasets by name, the data classification levels, column roles, and what a data contract publishes versus what it withholds.
---

## What a registered dataset carries

A registered dataset carries its provenance, its licence, a commercial-use flag the governance layer enforces, the capabilities it provides, and a role for every column it is known to have. An analysis declares what it needs, and the platform matches the two before a run rather than discovering the mismatch mid-flight.

Every dataset in the registry is genuinely public data. The classification assigned to each one is simulated for the purposes of the demo, and the product says so on its face rather than implying it holds real confidential material.

## The datasets by name

german_credit is the UCI Statlog German Credit dataset, and it is the anchor dataset that ships with the repo. german_credit provides a tabular shape, a target and protected attributes, with credit risk as the target role and the personal status and age columns as protected roles. Its modeling loader derives sex and age band, and injects synthetic PII so that redaction has something real to redact.

uci_taiwan_credit is the UCI Default of Credit Card Clients dataset from Taiwan. uci_taiwan_credit provides a tabular shape, a target and protected attributes, carrying sex and age as columns, and it is the primary dataset for credit fairness work.

berka is the PKDD'99 Financial dataset from a Czech bank, and it is the relational backbone of the registry. berka provides a relational shape across multiple tables with foreign keys and a many-to-many bridge, a target derived from loan status, and protected attributes for gender and age band derived from the client birth number. berka is the primary dataset for feature engineering.

hillstrom is the Hillstrom MineThatData email dataset, a real randomised controlled trial with treatment arms and visit, conversion and spend outcomes. hillstrom provides a tabular shape and a treatment role, and it is the primary dataset for experiment analysis.

ulb_fraud is the ULB Credit Card Fraud dataset, PCA-anonymized with a fraud label as its target. ulb_fraud provides a tabular shape and a target, and it is the primary dataset for fraud detection.

lendingclub is a LendingClub loan dataset and the canonical messy finance table in the registry. lendingclub provides a tabular shape and a target, and it is the primary dataset for data-quality triage. lendingclub is sampled at onboarding rather than loaded whole.

uci_bank_marketing is the UCI Bank Marketing dataset, a term-deposit campaign with a call outcome as its target. uci_bank_marketing provides a tabular shape and a target and is the primary dataset for marketing and propensity work. Its duration column is dropped because it leaks the outcome.

synthetic_its is a semi-synthetic interrupted time series: a daily metric with a known effect injected partway through the series. synthetic_its provides a tabular shape, a time series and a treatment role, with a timestamp column role and an intervention treatment role. Because the ground truth is known by construction, synthetic_its is what validates causal-impact analysis, and it is the only Public-class dataset, which makes it the only legal home for the L3 sandbox.

## Data classification

The data classification levels are Public, Internal, Restricted and Confidential. Classification is what sets the data half of the autonomy tier arithmetic, so a dataset's classification is the ceiling on how much freedom any request against it can receive.

synthetic_its is Public. hillstrom, lendingclub and uci_bank_marketing are Internal. uci_taiwan_credit and german_credit are Restricted. berka and ulb_fraud are Confidential, which is why a certified analyst working on ulb_fraud still lands at a lower tier than the same analyst on german_credit.

The Autonomy levels chapter of the User Manual prints the tier ceiling each classification permits, read from the tier module. The Datasets screen makes each classification cell clickable and explains the ceiling it sets, so the ceiling is reachable from the data rather than only from the policy.

## Column roles

A column role says what a column is for, so that a control can act on the role rather than on a hard-coded column name. The vocabulary of roles covers target, protected, treatment, outcome, timestamp, entity id, feature and PII.

## What a data contract publishes and withholds

A data contract publishes the schema and the column dictionary, a role for every column, the foreign keys and cardinality between tables, the row counts at source, the documentation coverage, and the dataset fingerprint the certified analysis was bound to.

A data contract withholds cell values, distributions and summary statistics, top values and most common categories, missingness rates, and sample rows of any size. Withholding those is what keeps a contract readable by somebody who has no grant on the data itself.

Metadata access and data access are two different grants, and the contract screen states that boundary on its own face rather than relying on the reader to notice. Reading a contract tells you what an analysis could do with a dataset. Reading a contract tells you nothing about the people in it.

## Contract drift

Contract drift is what happens when a dataset changes after an analysis was certified against it. A certified analysis pins the fingerprint of the dataset it was certified against, and if the current fingerprint differs, CTL-CONTRACT-01 refuses at Plan and the entry needs recertification before it can run again.

Contract drift cannot actually occur in this build, and the code says so. The datasets ship as static files committed to the repo, so the fingerprint does not move on its own. The control is wired and testable, and the condition that would trigger it does not arise here, which is stated rather than glossed over.
