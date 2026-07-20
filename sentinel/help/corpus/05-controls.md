---
id: controls
title: Controls
chapter: Controls
summary: What a control is, the CTL id scheme, which family acts at which stage, the four actions, armed versus fired, and enforced versus declared.
---

## What a control is

A control is a named, testable rule that can refuse. Every control has an id, the stage it acts at, and exactly one of four actions. Wherever the app shows a control chip, that chip is clickable and says what the control is and what its firing means.

## The four actions

Refuses means the run stops and nothing downstream executes. A refusal names the control and, where the refusal came from reading code, the line that caused it.

Suppresses means the control removes something from the output and the run continues. Small-cell suppression is the canonical example: the group is gone from the result, and everything after that point sees only what survived.

Logs means the control records that a condition held and the run continues unchanged. Flags means the control records a finding for a human and the run continues. Flag is used where the judgement is not the platform's to make, such as whether a permitted feature acting as a proxy is a business necessity.

## The id scheme

Control ids are prefixed CTL and named by family, so the id tells you the concern before you look it up. CTL-TIER-01 is the autonomy tier gate. CTL-CONTRACT-01 is data-contract drift. CTL-PURP-01 is purpose limitation, and CTL-PURP-02 is the column-scope variant of the same idea.

The CTL-CODE family is the static gate on generated Python. CTL-CODE-00 refuses code that does not parse. CTL-CODE-01 enforces the import allowlist. CTL-CODE-02 refuses filesystem and process access. CTL-CODE-03 refuses dynamic code and unsafe deserialization. CTL-CODE-04 refuses attribute access that walks the object graph out of the sandbox.

CTL-EGRESS-01 refuses any reference to a network module at all. CTL-COL-01 requires every column the code touches to be inside the purpose's grant, which is what catches a SELECT star passed through ctx.sql. CTL-COMPLEX-01 refuses SQL that exceeds the query complexity ceiling or joins without an explicit ON or USING condition; the Architecture chapter of the User Manual prints the enforced join ceiling.

The CTL-DISC family acts on outputs. CTL-DISC-01 logs that the raw grouped output breached the disclosure floor. CTL-DISC-02 suppresses groups below the floor. CTL-DISC-03 flags PII found in output text. CTL-DISC-04 is the target-leakage flag. CTL-PROXY-01 flags a granted feature that statistically reconstructs a protected one.

CTL-TIME-01 refuses at Execute when the sandbox exceeds its wall clock. CTL-EVAL-01 flags narration that is not faithful to the screened result. CTL-SOD-01 refuses when the signer is the author. CTL-RBAC-01 and CTL-RBAC-02 cover column denial and row filtering at Access. CTL-INJECT-01 screens instruction-shaped text in data-derived model context. CTL-COST-01 stops live model calls over the spend cap. CTL-LIN-01 blocks attestation on an incomplete lineage chain. CTL-PII-01 redacts PII before text reaches model context.

## Which family acts where

Ask carries the tier gate. Plan carries the data-contract check. Access carries purpose limitation and the RBAC controls. Generate carries no enforced control at all, deliberately, because writing code is not running code.

Gate carries the whole static-analysis family: the parse check, the import allowlist, the filesystem and process ban, the dynamic-code ban, the sandbox-escape ban, the egress ban, the column grant and the complexity ceiling. Gate is where the largest cluster of refusals lives, because Gate is the last point before code meets data.

## Armed versus fired

Armed means a control was consulted at a stage, which the run records regardless of outcome. Fired means the control acted: it refused, suppressed, flagged or logged something concrete about this run.

A gate event means the control was armed, not that it said no. A passing eval gate and an approved human decision are both gate events, and neither is a refusal. Reading a gate event as a refusal inflates the refusal count and makes a clean run look like a caught one.

The Audit Log splits stopped from withheld on exactly this line. A control that ended a run is stopped. A control that removed something from the output and let the run continue is withheld. A control that was merely consulted is neither, and the screen's filters keep the three apart.

## Enforced versus declared

Some control ids are enforced in this build and some are declared but not implemented. The difference is deliberate and visible: an id that appears in the design but has no code behind it is listed as declared, is never rendered as a live control, and can never appear on a run.

## The switchable controls

A small set of harness controls on the credit-risk pipeline can be switched off, and they are the only ones with a switch. Those controls are RBAC, PII redaction, guardrails, the eval gate and the human gate. Each carries a plain statement of what breaks without it, which is the reason the switch exists at all: the demo can show what a control is load-bearing for.

Turning a control off is itself a governed act. Only the Platform Admin can do it, the disabling is written to the audit log before the run starts, and the run is banner-marked UNGOVERNED everywhere it appears afterwards.

The audit log itself has no switch. The audit log is listed alongside the switchable controls in the Controls popover so that its absence from the switchable set is visible rather than silent. An unaudited run is not a run.

## Two refusals people conflate

Authority and segregation of duties are two different refusals at the promotion gate, and they are easy to conflate. Approval tests promotion authority before it tests segregation of duties, so an analyst who tries to self-approve is refused for lacking promotion authority and never reaches CTL-SOD-01 at all. Only an author who already holds promotion authority exercises the four-eyes control itself.