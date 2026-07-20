---
id: roles-and-access
title: Roles and access
chapter: Roles & access
summary: The personas by name and their capability flags, column-level RBAC, the purpose matrix, and how segregation of duties is enforced.
---

## The personas

The Data Scientist, listed as Data Scientist / Analyst, is the first-line persona and the default identity for the Run walkthrough. The Data Scientist can run analyses, cannot approve them, cannot toggle controls, reads only its own runs in the audit ledger, holds the data_scientist tier role and carries the certified_analyst attestation.

The Junior Analyst is the uncertified first-line persona. The Junior Analyst can run analyses, cannot approve, cannot toggle controls, reads only its own runs, holds the data_scientist tier role and carries no attestations, which is why the same request that reaches L2 for the Data Scientist lands at L1 for the Junior Analyst.

The Model Validator is second-line model risk management. The Model Validator cannot run analyses and cannot approve them, reads every run in the ledger, and holds the model_validator tier role, which caps the person ceiling at L0.

The MRM Approver is second line with approval authority. The MRM Approver cannot run analyses, can approve them, reads every run, and holds the model_validator tier role. The MRM Approver is the persona that clears the human gate on the credit-risk pipeline.

The Internal Auditor is third line and read-only everywhere. The Internal Auditor cannot run, cannot approve, cannot toggle controls, reads every run, and holds the compliance_officer tier role. On the Run screen the Run button simply disappears for the Auditor, and CTL-TIER-01 refuses at Ask if the flow is reached another way.

The Platform Admin is the platform persona. The Platform Admin can run analyses, cannot approve them, is the only persona that can toggle a control, reads every run, holds the data_scientist tier role, and carries both the certified_analyst and sandbox_waiver attestations, which is what makes L3 reachable at all.

## The invariants

Run authority and promotion authority are disjoint by design. Nobody both runs an analysis and approves it, and that disjointness is the whole of four-eyes in this build. There is no quorum, no approver list and no dual control; a single independent signature is what the product claims and what it enforces.

Only the Platform Admin can switch a control off, and switching a control off is itself an audited act written to the log before the run starts. The run that follows is banner-marked UNGOVERNED on every surface it appears on.

The audit ledger is scoped by entitlement. Oversight roles read every run and the first line reads its own runs. The entitlement defaults to denied, because an access check that fails open is not a check.

## Column-level RBAC

Column-level RBAC means an agent sees only the columns its role grants, and a denial is a real event rather than a hypothetical. The synthetic PII columns, the applicant email and the applicant social security number, are denied to every agent always, without exception and at every tier.

The Profiler agent runs against an explicit allow-list of columns that omits the sex-proxy column. That omission is deliberate and it is what produces a real access-denied event on every single run of the credit pipeline, so the control is visibly live rather than theoretically available.

The EDA, Modeler and Validator agents receive all non-restricted columns. The Validator in particular needs the protected attribute, because computing fairness metrics without the protected attribute is not possible.

## The purpose matrix

Purpose limitation is the governance idea a banker recognises instantly: you may not use credit data for marketing. Not because the role lacks permission, but because the reason is wrong. The same analyst, same role, same data, on a permitted purpose would be allowed.

The purpose matrix pairs each dataset with each declared purpose and says allow or refuse. The declared purposes are fair lending review, credit risk modeling, fraud detection, marketing, data quality and causal inference. A refusal in the matrix is CTL-PURP-01 acting at Access, before a single line of code is generated.

The Roles and access chapter of the User Manual renders the purpose matrix as a table, with every dataset, its classification and its allow or refuse cell for each purpose, read live from the purpose module. Ask that chapter for the current matrix rather than assuming a pairing from memory.

## Segregation of duties

Segregation of duties is enforced by identity comparison rather than by convention. The run state records who started the run, and an approval attempt from that same identity is refused and recorded at blocked level naming CTL-SOD-01.

Two refusals live at the promotion gate and they are easy to conflate. Promotion authority is tested before segregation of duties, so an analyst attempting to self-approve is refused for lacking authority and never reaches CTL-SOD-01. Only an author who already holds promotion authority exercises the four-eyes control itself.

Rejection is unguarded in this build, and the product states it rather than hiding it. Both the role check and the segregation check are conditioned on the decision being an approval, so any persona can reject a run and terminate it, including the run's own author and the read-only Auditor.

The governed nine-stage route has no human gate at all. The interrupt belongs to the credit-risk pipeline, so the route with the most interesting refusals currently has the thinnest human accountability, and every evidence pack the product ships is pending a signature.

## Access policy version

The access policy carries a version string, stamped when the audit log is constructed, and every audit event carries it. Stamping the policy version on the event is what lets a reader of an old run know which rules were in force when it ran, rather than reading it against today's rules. The Roles and access chapter of the User Manual prints the current policy version.
