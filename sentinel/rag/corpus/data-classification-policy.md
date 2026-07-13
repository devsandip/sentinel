---
id: data-classification-policy
title: Internal data-classification policy (illustrative)
source: "Sentinel synthetic internal standard — not a real bank document"
provenance: synthetic
citation: "Internal Data Classification Policy (illustrative)"
---

NOTE: This is a synthetic, illustrative standard authored for the demo. It stands
in for the confidential internal policy a real deployment would reference. It is
not a real Citi document.

Data is classified into four tiers: Public, Internal, Confidential, and
Restricted. Personally identifiable information (name, email, government
identifiers such as SSN) is Restricted and must not be used as a model feature or
exposed to a model in free text; it is redacted before any text reaches a model.

Protected attributes and their close proxies (for example, a field combining
personal status and sex) are Confidential and are excluded from model inputs. A
protected attribute may be read by an independent validation step solely to
measure fairness, never to train.

Access follows least privilege: each agent or user is granted only the columns
its role requires, and access to Restricted or out-of-scope columns is denied and
logged.
