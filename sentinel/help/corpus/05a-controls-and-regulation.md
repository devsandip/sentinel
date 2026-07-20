---
id: controls-and-regulation
title: Controls and regulation
chapter: Controls and regulation
summary: What each control answers to, the regime families behind the catalogue, why the app says answers to rather than complies with, and where the forward-looking frameworks sit.
---

## What the regulation line is

Every control in the catalogue carries a line naming the regime it answers to and the principle within that regime. The line lives on the control itself, so it appears wherever the control does: the Gate panel, the Audit Log drill-down, the Registry headers, and the manual. There is one catalogue and one explanation, not a separate document that drifts away from the code.

A control with no external driver says so in as many words rather than leaving the line empty. A blank would read as an oversight. Saying the control is an internal operational one is a decision, and it is legible as a decision.

Ask the Controls and regulation chapter of the manual for the current list. It reads the catalogue live, so a control added tomorrow appears there without anyone editing prose.

## Answers to, not complies with

The app never says a run is compliant, and this is deliberate rather than modest. Compliance is a determination a firm's own second and third lines of defence make against their own written policy, on systems with authenticated users and a real model inventory. This build has none of those things. What it can honestly say is that a given control serves a given principle, which is a claim about design rather than a claim about status.

The Audit Log carries a caption saying the same thing about its own limits. That caption is load-bearing for the credibility of everything else on screen.

## Model risk management

SR 11-7 is the US Federal Reserve and OCC supervisory guidance on model risk management. PRA SS1/23 is its UK counterpart. Both are the driver behind the controls that concern independence, documentation and monitoring.

The strongest single example is segregation of duties. SR 11-7 asks for independence between model development and model validation. Most implementations satisfy that with a role check. Sentinel compares identities instead, which is the stricter reading: an administrator who authored a run cannot approve it either, because the check is on who they are rather than on what they are allowed to do.

## Fair lending

ECOA and Regulation B, together with the disparate-impact doctrine, drive the fairness and proxy controls.

The central fair-lending failure mode is not using a protected attribute directly. It is using a feature that correlates with one. That is why proxy discovery exists, and why it flags rather than refuses. Whether a correlated feature has a business necessity is a Legal and Compliance judgment, not a platform judgment. A platform that refused on correlation alone would be wrong on the law and would be switched off within a week. The purpose of the control is that nobody afterwards gets to say they did not know.

## Purpose limitation and data protection

GDPR Article 5 purpose limitation, FCRA permissible purpose for credit data specifically, and the GLBA Safeguards Rule for access controls sit behind the purpose matrix, the column grants and the redaction controls.

The purpose refusal is the one governance idea a banker recognises instantly. Credit-decision data may not be repurposed for marketing. The refusal wording makes the legal distinction explicit: the request is refused because the reason is wrong, not because the role lacks permission.

## Statistical disclosure control

This family has no banking regulator behind it. It comes from official statistics practice, the conventions the national statistical agencies use when publishing aggregate numbers, and it is the standard answer to re-identification risk in grouped output.

It is worth knowing precisely because most AI systems have never heard of it. A minimum cell size before an aggregate may be published, suppression applied upstream of anything that could describe the result, and an explicit on-screen note that suppression occurred, are all ordinary practice in that world and rare in this one.

## Operational and technology risk

No single citation covers this family. It is the space that SOX change control, third-party and tool risk, and a firm's own secure-SDLC standards occupy. The static gate's refusals mostly live here: no network egress, no filesystem writes, no dynamic evaluation, no unbounded query shapes, and caps on what a sandboxed process may consume.

## Data lineage

BCBS 239 sets principles for risk data aggregation and reporting. The lineage events and the dataset fingerprint pin answer to it. A run against changed data is a different run, and the drift control makes it say so rather than letting a certification quietly stop meaning anything.

## Where this is heading

Three frameworks are worth naming because they are the direction of travel, not because this build implements them.

The EU AI Act treats creditworthiness assessment of natural persons as high-risk under Annex III. The obligations that follow map onto things already on screen: data governance, technical documentation, automatic logging, and human oversight. One terminology note matters here. The Act requires technical documentation and instructions for use. It does not mandate model cards. That phrase is a research-paper convention with no legal standing, and the binding driver for a bank is SR 11-7's documentation requirement, which is what the card is already shaped like.

The NIST AI RMF offers vocabulary rather than obligation, organised as Govern, Map, Measure and Manage. A control catalogue is a Manage artifact.

ISO/IEC 42001 covers AI management systems and is the certification track a bank eventually wants. Nothing here attempts it.
