---
id: autonomy-levels
title: Autonomy levels
chapter: Autonomy levels
summary: The L0 to L3 ladder, how a tier is resolved from role, attestations and data classification, the min() ceiling arithmetic, the import allowlists, and the sandbox caps.
---

## The ladder

L0 is the lowest autonomy tier. At L0 the model explains finished numbers and writes no code and starts no run. L0 is where every role outside the first line lands, which includes the Model Validator, the MRM Approver and the Internal Auditor: they may read a finished run, they may not start one.

L1 is the tier where the model picks a certified analysis and fills in typed parameters. At L1 no code is written, so Generate and Gate are skipped, and the reviewed surface is the parameter set rather than a program. A bad parameter value raises an error instead of running.

L2 is the tier where the model writes code against the fenced ctx API. At L2 imports are restricted to an allowlist, and a static gate reads the code before it runs. L2 is the ordinary working tier for a certified analyst on data that permits it.

L3 is the tier where the model writes near-arbitrary code in a broader sandbox. L3 widens the import allowlist but keeps exactly the same deny list, and it requires a sandbox waiver attestation on top of certification. L3 is the only tier where the wider analytical libraries, including the causal inference stack, are reachable.

## The arithmetic

The autonomy tier is computed, never chosen. There is no autonomy dial anywhere in this product. The tier is the minimum of two ceilings: what the data's classification allows, and what the person and their attestations allow. The request lands at the lower of the two.

Both ceilings bind on purpose. A permissive dataset must not silently elevate a person, and a trusted person must not silently elevate a dataset. A certified analyst working on confidential data drops to L1 no matter how senior they are, and an uncertified analyst working on public data drops for the opposite reason.

The tier is resolved at Ask and frozen for the run. Nothing later in the run can raise it, and the gate that enforces it lives in the flow rather than in the user interface, so a caller that bypasses the screen still lands on CTL-TIER-01.

## The ceiling from the data

The data classification levels are Public, Internal, Restricted and Confidential, and each sets a ceiling on how much autonomy any request against that data may receive. Public data carries the highest ceiling and Confidential the lowest, because account-level data forbids generated code entirely and nothing public is worth stealing.

The Autonomy levels chapter of the User Manual prints the ceiling for each classification, and the datasets that carry it, read live from the tier module. Ask that chapter rather than this page for which classification permits which rung.

## The ceiling from the person

The person ceiling starts from the tier role rather than the display persona. Any non-analyst tier role, which covers model validators, compliance officers and executives, caps at L0. A data scientist with no attestation reaches L1.

Attestations raise the person ceiling and never the data ceiling. The certified_analyst attestation raises a data scientist to L2. The sandbox_waiver attestation, held on top of certification, raises them to L3. An attestation is a property a person holds beyond their role, and it is the only thing that moves the person ceiling.

## What the model may import

The import allowlist goes verbatim into the codegen system prompt, so every name on the allowlist is an instruction to the model to use that package. That is why a name on the list has to be installed in the environment that has to honour it, and why a test reconciles the list against what the production artifact actually installs.

L2 has an allowlist of analytical libraries. L3 adds further names to that list without removing anything, so L3 is a strict widening. The Autonomy levels chapter of the User Manual renders both lists as catalogues, read from the allowlist module, including which names L3 adds.

Deny is checked before allow, and that precedence is what makes L3 safe to widen. Adding names to the allowed set can never open a denied category, so an import of a network library reports CTL-EGRESS-01 at every tier including L3, rather than falling through to the allowlist check and being permitted.

Four deny categories hold at every tier. Network egress modules are denied under CTL-EGRESS-01. Filesystem and process modules are denied under CTL-CODE-02. Dynamic code and unsafe deserialization, which covers eval, exec, compile and the pickling modules, are denied under CTL-CODE-03. Attribute access that walks the object graph out of the sandbox is denied under CTL-CODE-04.

## The sandbox and its caps

The sandbox enforces a wall clock and a memory ceiling on every governed execution. The Autonomy levels chapter of the User Manual prints both enforced values, read from the sandbox module itself, along with the separate fallback the sandbox uses when a caller names no cap of its own. Exceeding the wall clock kills the process and fires CTL-TIME-01.

The only channel out of the sandbox is ctx.emit. A result that is not emitted does not exist, which means an analysis cannot smuggle a result out through a file, a socket or a print statement.

A warm-up subprocess pre-imports the allowlist at boot. Some allowlisted libraries cost a substantial amount of time to import cold, which would otherwise trip the wall clock on the first run of the day. An import grant is also a time budget, and the warm-up is how the platform pays it once rather than per run.

The sandbox is a subprocess with resource limits, not a container and not a jail, and the product states it that way on every surface. The hardening path is real isolation, and it is named as a gap rather than implied to be closed.
