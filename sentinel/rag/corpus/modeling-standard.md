---
id: modeling-standard
title: Internal modeling standard (illustrative)
source: "Sentinel synthetic internal standard — not a real bank document"
provenance: synthetic
citation: "Internal Modeling Standard (illustrative)"
---

NOTE: This is a synthetic, illustrative standard authored for the demo. It stands
in for a confidential internal modeling standard. It is not a real Citi document.

Every model must ship with a model card documenting purpose, data lineage,
methodology, performance, fairness, limitations, and governance, consistent with
SR 11-7 documentation expectations.

A baseline model must clear an eval gate of golden checks before promotion:
performance above a floor, a complete confusion matrix, a fairness assessment with
a disparity ratio, exclusion of protected attributes from features, and a complete
model card. A model that fails any check is blocked from promotion.

Promotion requires an independent human approver with the authority to accept the
model risk. The developer of a model may not approve its promotion.
