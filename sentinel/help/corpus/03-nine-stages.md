---
id: nine-stages
title: The nine stages
chapter: The nine stages
summary: Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret and Attest, what each is for, which controls act there, and how not-in-route differs from skipped and blocked.
---

## The spine

The nine governance stages are Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret and Attest, in that order. Every governed run passes through all nine, and a run that is refused records the remaining stages as skipped rather than pretending they ran.

## Ask

Ask states the request, declares the purpose, and resolves the autonomy tier. The tier is computed here from the data's classification and the person's attestations, and then frozen for the rest of the run. Nobody chooses the tier and it cannot be raised later in the run.

CTL-TIER-01 acts at Ask and refuses an operation that exceeds the resolved autonomy tier. The gate sits in the flow rather than in the user interface, so a caller that bypasses the Run screen still lands on CTL-TIER-01. Firing means the resolved tier was outside the runnable range, so the run was refused at Ask and the remaining stages were recorded as skipped.

## Plan

Plan binds a certified agent to the declared purpose and pins its data contract, and CTL-CONTRACT-01 refuses here when the pinned dataset fingerprint no longer matches. Only certified analyses are visible at Plan, and certification is computed rather than stored, so an entry that loses a required gate stops being certified the moment it does.

## Access

Access scopes the data to the columns the purpose and the role permit. A denied column is not masked, it is absent: the scoped table simply does not have the column, so no downstream stage can reference it by accident.

CTL-PURP-01 acts at Access and enforces purpose limitation. Each dataset carries a list of permitted purposes, and a request whose declared purpose is not on that list is refused before a single line of code is generated. Purpose limitation is not a permissions gap, so the same analyst with the same role on the same data would be allowed under a permitted purpose.

## Generate

Generate produces code against the fenced API. Nothing is dangerous yet at Generate, because generating code is not running code, and no named control acts at this stage.

## Gate

Gate reads the generated code statically before anything runs. Two parsers read the code and neither executes it: Python's ast for the Python half, and sqlglot for anything passed to ctx.sql. A refusal at Gate names the control and the line.

The controls at Gate are CTL-CODE-00 for code that does not parse, CTL-CODE-01 for the import allowlist, CTL-CODE-02 for filesystem and process access, CTL-CODE-03 for dynamic code and unsafe deserialization, CTL-CODE-04 for sandbox-escape attribute access, CTL-EGRESS-01 for network egress, CTL-COL-01 for column grants, and CTL-COMPLEX-01 for query complexity. Each refuses, which means the run stops and nothing downstream executes.

## Execute

Execute runs the analysis in a subprocess sandbox with a wall clock, a memory cap and one channel out, which is ctx.emit. The sandbox is an honest boundary against a model doing something dumb, not a defence against a determined attacker, and the product states it that way everywhere.

CTL-TIME-01 acts at Execute and refuses when the sandbox subprocess exceeds its wall-clock cap. The Autonomy levels chapter of the User Manual prints the enforced wall clock and memory ceiling, read from the sandbox module itself, so ask that chapter for the live values rather than trusting a number written in prose.

## Screen

Screen checks outputs for disclosure and proxy risk before anyone sees them. Small cells are removed rather than masked, on the principle that you cannot leak a number you were never shown, and the model that writes the narration sits downstream of this line.

CTL-DISC-01 logs that the raw grouped output breached the disclosure floor. CTL-DISC-02 suppresses any group below the floor. CTL-DISC-03 flags PII found in output text. CTL-PROXY-01 flags a permitted feature that reconstructs a protected one, measured by statistical association, and it flags rather than refuses because business necessity is Legal's call rather than the platform's.

## Interpret

Interpret narrates the result and checks the narration against the screened table. Asserting a value for a band that Screen removed is exactly what the faithfulness check catches, because the narration may only describe what survived the disclosure screen.

CTL-EVAL-01 acts at Interpret and flags narration that is not faithful to the screened result. Flagging records a finding for a human and lets the run continue, because the judgement about a borderline sentence is not the platform's to make.

## Attest

Attest assembles the evidence and takes it to signoff. The pack ships pending: signing requires somebody who is not the author, and the negative statement is assembled from what the run actually did rather than written by hand.

CTL-SOD-01 acts at Attest and refuses when the person signing a run, an evidence pack or a certification is the person who authored it. Four-eyes in this build is a single independent signature, and there is no quorum anywhere in the product.

## Not in route, skipped, and blocked

Not in route, skipped and blocked are three different facts, and the Audit Log keeps them apart deliberately. A normalization that invents stages is worse than several unrelated step vocabularies, so the mapping refuses to fill gaps with a green tick.

A stage that ran and passed is ok. A stage that is skipped means the run reached that stage and declined to execute it, which is what happens to the stages after a refusal. A stage that is not in route means this kind of run has no such stage at all: a linear analysis generates no code, so it has no Generate stage to skip.

Blocked means a control refused at that stage. Where several native steps fold into one canonical stage, the worst outcome wins, so a stage containing both a completed step and a blocked one is a blocked stage. Reporting it green because most steps passed is exactly the kind of aggregation an audit surface must not do.