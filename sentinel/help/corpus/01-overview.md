---
id: overview
title: Overview
chapter: Presentation
summary: What Sentinel is, what it deliberately is not, the pipeline plane versus the control plane, and how the manual chapters fit together.
---

## What Sentinel is

Sentinel is a governed agentic analysis platform. A model writes the analysis code, a static gate reads that code before any machine executes it, a disclosure screen removes small cells before the model is allowed to describe the result, and what comes out is an evidence pack that somebody other than the author signs. Governance is the product here; the machine learning underneath is deliberately simple.

Most agentic AI stalls at the demo, and not because the model cannot do the analysis. It stalls because nobody can show a second line of defence what the agent actually did. Sentinel is the harness that answers that question, built alongside the pipeline rather than bolted on afterwards.

Sentinel runs a real analysis with real metrics and real fairness numbers computed live from the data. Sentinel lets a model write code at the L2 and L3 autonomy tiers, against a fenced API that hands out no dataset handle, no network and no filesystem. Sentinel refuses out loud, so every refusal names the control that fired and the line of code that caused it. Sentinel keeps the record, so every run is replayable as the same nine governance stages across sessions and across deploys.

A Sentinel run ends in evidence rather than a chart. The evidence pack carries the finding, its provenance, the controls attested, and a negative statement saying what the finding does not say.

## What Sentinel deliberately is not

Sentinel is not a model zoo. The machine learning is a logistic-regression baseline on purpose, because the interesting part of the build is the control plane and a fancier model would only obscure it.

Sentinel is not a staged demo. The controls that fire, fire on real code with real violations. Nothing is seeded to look like a refusal, and the adversarial analyses in the Ask dropdown are genuine code that genuinely breaks a rule.

Sentinel is not dual control. Four-eyes in this build means author is not approver, enforced by CTL-SOD-01, and that is a single independent signature. There is no quorum, no approver list and no pending-second-signature state, and the product says so rather than implying one.

Sentinel is not a hardened sandbox. Execute is a subprocess with resource limits, an honest boundary against a model doing something dumb rather than a defence against a determined attacker. Real isolation is named as a gap rather than implied to be closed.

## The two planes

The pipeline plane is what does the work. On the credit-risk route the pipeline plane is a LangGraph StateGraph with a fixed topology, running a Profiler, an EDA and feature step, a Modeler, a human gate and a Validator. The human gate is a real interrupt rather than a flag: the graph stops there and resumes on a Command.

The control plane is what decides the pipeline may. The control plane carries purpose limitation, tier resolution, RBAC, the static gate, the sandbox, the disclosure screen, the faithfulness check and segregation of duties. Each of those is a named, testable rule that can refuse, and nothing reaches data, a tool or a model without passing through the control plane first.

Read the architecture arrows carefully, because the control plane is not a step in the pipeline. The control plane wraps every step of the pipeline. An agent cannot read a column, call a tool or send text to a model except through the harness, which is why the audit log is complete by construction rather than by discipline.

At L2 and L3 the work the pipeline plane does is code the model wrote. At L1 the work is a certified analysis with typed parameters, and the reviewed surface becomes those parameters rather than the code.

## How the chapters fit together

The Presentation chapter is the deck: the whole product at slide altitude, covering what it does, the two planes, the nine steps, the autonomy ladder, the governance catalogue, the bought-versus-built stack, the roles and a map of the screens. Every chapter after the Presentation is the reference that the deck points at.

Read Quick start if you want to know what to click and in what order to see a governed run end to end. Read The nine stages for what each stage is for and which controls act there. Read Autonomy levels for the tier arithmetic, the import allowlists and the sandbox caps, which are printed there from the modules that enforce them.

Read Controls for the full catalogue: every control id, its stage, its single action, and what firing means. Read Screens for every screen in the sidebar and where the retired Pipeline screen's tabs went. Read Roles and access for the personas, column-level RBAC and the purpose matrix. Read Data for the registered datasets, the classification levels and what a data contract publishes. Read Architecture for the module map and deployment, and Glossary for the words this product uses in a specific way.

## Why the numbers are not in this corpus

Every number the User Manual prints is read from the module that enforces it, so the manual cannot quietly fall out of step with the product. This corpus is prose written alongside the manual, which makes it a second source of truth, so it names things rather than restating their values. Where a cap, a floor, a ceiling or a count matters, the paragraph names the control and points you at the chapter of the User Manual that prints the live figure.

Sentinel has already paid for the alternative twice: an import allowlist that named packages installed nowhere, and an Execute panel whose stated wall clock had not matched the enforced one for several versions. A manual that asserts a number the code has since changed is worse than no manual at all.
