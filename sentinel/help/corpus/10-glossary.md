---
id: glossary
title: Glossary
chapter: Glossary
summary: The terms Sentinel uses in a specific way, one short paragraph each, in alphabetical order.
---

## Terms

Attestation is a property a person holds beyond their role, such as certified_analyst or sandbox_waiver. Attestations raise the person ceiling in the autonomy tier arithmetic and never the data ceiling, so no attestation can make confidential data behave like public data.

Armed describes a control that was consulted at a stage on this run. Armed is not the same as fired: a gate event records that the control was reached, not that it said no, and treating every gate event as a refusal inflates the refusal count.

Autonomy tier is how much freedom the model gets on a request, on the ladder L0, L1, L2, L3. The autonomy tier is computed as the lower of the data ceiling and the person ceiling, resolved at Ask, and frozen for the rest of the run.

Certified analysis is a registry entry that passes every certification gate. Only certified entries are visible at Plan. Certification status is computed rather than stored, so an entry that loses a required gate stops being certified the moment it does.

Control is a named, testable rule that can refuse. Every control has an id, a stage it acts at, and exactly one of four actions: refuses, flags, suppresses or logs.

Data contract is the match between what an analysis needs, in capabilities, columns and minimum rows, and what a dataset provides, plus the dataset fingerprint the analysis was certified against. A data contract is metadata only and publishes no cell values.

Data classification is the level assigned to a dataset: Public, Internal, Restricted or Confidential. Data classification sets the ceiling on the autonomy tier any request against that dataset can reach, and the classification in this build is simulated because every registered dataset is genuinely public.

Declared, not implemented describes a control id that appears in the design with no code behind it. A declared control is badged as such in the Controls chapter, is never rendered as a live control, and can never appear on a run.

Disclosure floor is the minimum cell count below which a group is removed from the output rather than masked. The Architecture chapter of the User Manual prints the enforced floor, read from the disclosure module.

Evidence pack is the filed artifact of a run: the finding, the provenance chain, the controls attested, and the negative statement. An evidence pack ships pending until somebody who is not the author signs it.

Faithfulness floor is the score an analysis's eval suite must reach before it can be certified. The Architecture chapter of the User Manual prints the enforced floor, read from the certification module.

Fenced API is the only surface generated code may touch: ctx.table, ctx.sql, ctx.param and ctx.emit. The fenced API hands out no dataset handle, no network access and no filesystem access.

Fired describes a control that acted on this run, by refusing, suppressing, flagging or logging something concrete. Fired is the stricter word, and the Audit Log counts fired rather than armed.

Four-eyes means author is not approver, enforced by CTL-SOD-01 at signoff and at certification. There is no quorum in this build and no dual control; four-eyes here is a single independent signature.

Governed run is one request carried through all nine stages, with every control consulted and every consultation recorded. A governed run survives the session, because the ledger persists it.

Negative statement is the section of the evidence pack that says what the finding does not say. The negative statement is assembled from what the run actually did rather than written by hand.

Not in route describes a stage that a given kind of run has no equivalent for at all. Not in route is distinct from skipped: a linear analysis generates no code, so it has no Generate stage to skip, and recording it as skipped would be a small lie.

Proxy is a permitted column that statistically reconstructs a protected one, measured by Cramer's V or the correlation ratio. A proxy is flagged rather than refused, because whether the feature is a business necessity is Legal's call rather than the platform's.

Purpose limitation means a dataset carries a list of permitted purposes, and a request with the wrong purpose is refused before any code is written. Purpose limitation gates on why rather than on who, so the same analyst on a permitted purpose would be allowed.

Refusal is a control that said no. A refusal is distinct from a consultation, and the Audit Log separates a control that stopped a run from one that withheld something and let the run continue.

Scoped table is the policy-filtered view that Access builds. A denied column does not exist on the scoped table, so downstream code cannot reference it even by accident.

Seeded describes demo telemetry from runs that actually executed, committed to the repo so the record survives a deploy. Every seeded row is labelled as seeded on the surface that shows it.

Skipped describes a stage the run reached and declined to execute, which is what happens to the stages after a refusal. Skipped is neither ok nor not in route, and the three are kept apart deliberately.

Stage is one of the nine governance stages: Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret and Attest. Every run is readable in those stages regardless of the route it took.

Static gate is the pair of parsers that read generated code before anything runs, using ast for Python and sqlglot for SQL. The static gate never executes what it reads, and a refusal names the control and the line.

Ungoverned run is a run where an admin disabled a control. The disabling is itself audited and the run is banner-marked, so an ungoverned run is not a governed result and cannot be presented as one.

Withheld describes a control that removed something from the output and allowed the run to continue, as opposed to stopping it. The Audit Log's filter splits stopped from withheld on exactly that line.
