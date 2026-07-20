---
id: screens
title: Screens
chapter: Screens
summary: Every screen in the sidebar and what it answers, the two drill-downs that are not nav items, and the tabs inside the Pipeline screen.
---

## How the app is laid out

The sidebar carries the screens in groups, with Help last. Nothing in the product routes through Help, so putting it above the Platform group would imply it is a step in a workflow rather than a reference.

Two drill-downs are deliberately not nav items: a dataset's contract, and a single run's audit detail. You reach a drill-down by opening a row, and the sidebar Back button returns you to the screen you came from.

## Overview

Overview is the command centre and the first screen a visitor lands on. Every number on Overview is live from the surface it links to, so a tile and its destination cannot disagree.

The Overview call to action names the dataset, the purpose and the autonomy tier your current persona resolves to, before you click it. Naming the tier in advance is what makes the tier feel computed rather than assigned after the fact.

## Run

Run is the nine-stage governed walkthrough and the centre of the product. The Run rail carries the nine stages plus the Architecture appendix, and once a run exists each stage marks itself clear, refused or skipped.

Ask on the Run screen is three explicit steps: confirm a dataset, declare a purpose, pick an analysis. After those steps Ask prints the tier arithmetic in full.

Plan on the Run screen binds a certified analysis, checks its data contract for drift, and offers scripted or live generation. Gate on the Run screen shows each static check with a verdict, highlights the offending line, and offers a Fix it button that resubmits the repaired code to the same gate.

Attest on the Run screen shows the evidence pack and its downloads: Quarto source for a leadership audience, and a marimo notebook for a data scientist.

## Pipeline and its tabs

Pipeline is the four-agent credit-risk pipeline and the evidence from one run of it. Pipeline is the older route in the product, and it is the only route with a human interrupt in the graph.

The Pipeline tab shows the LangGraph orchestration graph, the control envelope, and one card per step. The human gate lives on this tab, which is where an MRM Approver clears or rejects a run.

The Fairness tab shows the disparity ratio against its threshold and the selection rate by group. The Model Card tab renders an SR 11-7 style model-risk document generated from the run, exportable to PDF.

The Cost and KPIs tab shows tokens, dollars, cycle time, eval pass-rate, human overrides and the eval gate's verdict. The Gateway tab shows the model-gateway ledger: every call, its stakes, the tier it routed to, cache hits and cost.

## Analyses

Analyses is the analysis catalogue and its parameter surface. Each entry carries a contract line saying what it requires and the controls it runs under, the dataset picker offers only datasets whose capabilities satisfy that contract, and parameters render as typed widgets where a bad value raises an error rather than starting a run.

## Datasets

Datasets lists every registered dataset under its classification, with a data contract behind each row. The list shows classification, rows, tables, licence, the commercial-use flag and the onboarding state.

The classification cell on the Datasets list is clickable and explains the autonomy tier ceiling that classification sets. A contract opened from a row is metadata only and says so: schema, column dictionary with roles, relationships and coverage, with no cell values, no distributions and no samples. Metadata access and data access are two different grants.

## Registry

Registry holds inventories that are easy to confuse, so the screen separates them explicitly. The Models tab is what a run produced: one row per run that trained something, with AUC, disparity, fairness verdict and promotion status.

The Agents tab is the workers inside a run: the pipeline agents in run order, with the template, tools and RBAC scope each one has. The Analysis-agents tab is what a run is allowed to be: the certified unit that Plan binds, under a certification lifecycle, and it is not the same thing as the agents on the previous tab.

## Platform, Adoption and Audit Log

Adoption answers whether anyone is using the platform and whether the controls are getting less intrusive over time. Adoption shows total runs, promotion rate, human-override rate and template coverage, plus charts for agent utilization, runs per week and runs per dataset. The telemetry is seeded from runs that really executed and is labelled as seeded on the surface.

Audit Log is the one cross-run surface. Every other audit view in the app is scoped to a single run and dies with the session, which is what makes the ledger worth its own nav slot. Audit Log reads the record and cannot write to it; no action on the screen mutates anything.

Opening a row in the Audit Log gives a run's detail: the run replayed as the same nine stages, keeping ran, skipped and not-in-this-route apart. Events carry the stage they were emitted at, stamped at the call site rather than guessed from the action string.

The Audit Log obeys the access control it is about. Oversight roles read the whole ledger and the first line reads its own runs. The scope is announced on screen rather than silently applied, the filters can only narrow it, and the drill-down re-checks the entitlement, because otherwise a deep link would be the way around the check. Deep links of the form run equals an id open straight to a run's evidence, so a link pasted to a colleague resolves to the run.
