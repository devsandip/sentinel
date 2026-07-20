---
id: screens
title: Screens
chapter: Screens
summary: Every screen in the sidebar and what it answers, the two drill-downs that are not nav items, and where the retired Pipeline screen's tabs went.
---

## How the app is laid out

The sidebar carries the screens in groups, with Help last. Nothing in the product routes through Help, so putting it above the Platform group would imply it is a step in a workflow rather than a reference.

Some drill-downs are deliberately not nav items: a dataset's contract, a single run's audit detail, and a template's editor. You reach a drill-down by opening a row, and the sidebar Back button returns you to the screen you came from.

## Overview

Overview is the command centre and the first screen a visitor lands on. Every number on Overview is live from the surface it links to, so a tile and its destination cannot disagree.

The Overview call to action names the dataset, the purpose and the autonomy tier your current persona resolves to, before you click it. Naming the tier in advance is what makes the tier feel computed rather than assigned after the fact.

## Run

Run is the nine-stage governed walkthrough and the centre of the product. The Run rail carries the nine stages, and once a run exists each stage marks itself clear, refused or skipped. Architecture is not a stage: it describes the platform rather than advancing a run, so it sits in the topbar next to Controls, reachable from every screen.

The Run header states the run id, its status, the tier, whether generation was scripted or live, and what the run cost: tokens, dollars and wall clock. An Audit trail button on the header opens that run in the Audit Log rather than rendering the event stream a second time inside a stage.

Ask on the Run screen is three explicit steps: confirm a dataset, declare a purpose, pick an analysis. After those steps Ask prints the tier arithmetic in full.

Plan on the Run screen binds a certified analysis, checks its data contract for drift, and offers scripted or live generation. Gate on the Run screen shows each static check with a verdict, highlights the offending line, and offers a Fix it button that resubmits the repaired code to the same gate.

Attest on the Run screen shows the evidence pack and its downloads: Quarto source for a leadership audience, and a marimo notebook for a data scientist.

## Where the Pipeline screen went

Pipeline was the four-agent credit-risk build and ten tabs of evidence from one run of it. The screen is retired. Its tabs were tested one at a time against a single question: does the surviving route produce the data, and does a stage own the question the tab answers?

Four moved into a stage. The gateway ledger is at Generate, which is where the tokens are spent; it shows every model call, its stakes, the tier it routed to, cache hits and cost, and it records the routing decision even in scripted mode where the call costs nothing. The emitted result is at Execute, shown raw before the Screen has removed anything, so the screened table next door reads as something a control acted on. The four-fifths disparity ratio is at Interpret, merged into the narration rather than given its own panel, because the result contract already forces every result to be a selection rate per group. The model card moved to the Registry, since a card documents a model and the Registry is the model inventory.

Two became header items. Tokens, dollars and cycle time are chips on the run header, because no single stage owns what a run cost. Architecture moved to the topbar.

One became a link. The audit trail opens the Audit Log's drill-down for that run instead of rendering the events a third time.

Four were dropped rather than moved. Knowledge and citations, memory and retention, and traces all describe things the nine-stage route does not do: it runs no retrieval, keeps no cross-run precedent, and emits no OpenTelemetry spans. Moving them would have produced a panel that renders an empty state on every run forever, which is a discard with extra steps. The eval-gate half of Cost and KPIs went the same way: it was the orchestrator's model-promotion gate, which is a different control from the Gate stage, and promotion machinery has no meaning without a model to promote.

The credit-risk runs themselves were not deleted. They are in the Audit Log, including the two that a control refused, and the orchestrator that produced them is still what the seeding script executes.

## Analyses

Analyses is the analysis catalogue and its parameter surface. Each entry carries a contract line saying what it requires and the controls it runs under, the dataset picker offers only datasets whose capabilities satisfy that contract, and parameters render as typed widgets where a bad value raises an error rather than starting a run.

## Datasets

Datasets lists every registered dataset under its classification, with a data contract behind each row. The list shows classification, rows, tables, licence, the commercial-use flag and the onboarding state.

The classification cell on the Datasets list is clickable and explains the autonomy tier ceiling that classification sets. A contract opened from a row is metadata only and says so: schema, column dictionary with roles, relationships and coverage, with no cell values, no distributions and no samples. Metadata access and data access are two different grants.

## Agent Templates

Agent Templates is the one screen where you author policy rather than read it. A template is a governed blueprint: the tool allow-list, the column grant, the purposes it may run under, the autonomy ceiling it asks for and the eval floor, all declared in one document. Starting an agent from a template means it inherits the controls instead of re-deriving them.

The spec is YAML, and it is the same format the scaffolding CLI writes, so the command line and the screen produce one artifact rather than two. Every field names a value that some other module owns: a purpose from the matrix, an import from the codegen allow-list, a tool from the agent config, a tier from the ladder. The legal values shown beside the editor are read from those modules, so the editor cannot offer something the enforcement would refuse.

Editing a template does not change the shipped blueprint. Edits live in your session against a buffer, Revert restores the original, and Download gives you the file to commit.

Two kinds of check run on every edit, and the screen keeps them apart. Policy checks are the fence: a refusal disables the deploy, because an illegal blueprint should not reach the registry at all. Certification gates are not the fence: they block a template from becoming certified, and they do not stop it being registered as a draft. That is why a shipped template can read clear on policy and still be a long way from certified.

Every shipped template ships without an owner, and that is the design rather than an omission. A blueprint cannot own the instances made from it, so the owner is named when someone deploys one. The scaffolding CLI registers a new agent unowned for the same reason.

The checks use the same four verdicts the Gate stage uses, and the distinction between them matters as much here. A check that was armed and found nothing to judge is not the same as a check whose rule was never supplied, and neither one is a pass. A template that declares no dataset leaves the purpose, tier and column checks with nothing to read, and the screen says so rather than painting them green.

Deploy registers the spec as a draft analysis-agent, with the dataset's content SHA computed at that moment and pinned into the contract. A template may not pin a SHA itself, because a SHA is a fact about one snapshot of a file and a blueprint that pinned one would be claiming every instance runs against today's data. The draft appears on the Registry screen under Analysis-agents and the certification gates decide what it is allowed to become. Nothing is written to disk and no process is started: an enterprise deployment would push the spec to the agent runtime from that point, so the governance outcome is real and the rollout is not.

## Registry

Registry holds inventories that are easy to confuse, so the screen separates them explicitly. The Models tab is what a run produced: one row per run that trained something, with AUC, disparity, fairness verdict and promotion status.

Each model row opens its own model card: an SR 11-7 style model-risk document generated from that run, exportable to PDF. A run that never cleared the human gate has no card, and the row says so rather than showing an empty one.

The Agents tab is the workers inside a run: the pipeline agents in run order, with the template, tools and RBAC scope each one has. The Analysis-agents tab is what a run is allowed to be: the certified unit that Plan binds, under a certification lifecycle, and it is not the same thing as the agents on the previous tab.

## Platform, Adoption and Audit Log

Adoption answers whether anyone is using the platform and whether the controls are getting less intrusive over time. Adoption shows total runs, promotion rate, human-override rate and template coverage, plus charts for agent utilization, runs per week and runs per dataset. The telemetry is seeded from runs that really executed and is labelled as seeded on the surface.

Audit Log is the one cross-run surface. Every other audit view in the app is scoped to a single run and dies with the session, which is what makes the ledger worth its own nav slot. Audit Log reads the record and cannot write to it; no action on the screen mutates anything.

Opening a row in the Audit Log gives a run's detail: the run replayed as the same nine stages, keeping ran, skipped and not-in-this-route apart. Events carry the stage they were emitted at, stamped at the call site rather than guessed from the action string.

The Audit Log obeys the access control it is about. Oversight roles read the whole ledger and the first line reads its own runs. The scope is announced on screen rather than silently applied, the filters can only narrow it, and the drill-down re-checks the entitlement, because otherwise a deep link would be the way around the check. Deep links of the form run equals an id open straight to a run's evidence, so a link pasted to a colleague resolves to the run.
