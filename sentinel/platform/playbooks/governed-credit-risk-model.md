---
id: governed-credit-risk-model
title: Build a governed credit-risk model
jtbd: >
  As a bank data scientist, take a loan portfolio from a raw dataset to a
  documented, fairness-reviewed, human-approved credit-default model, with the
  audit evidence produced as a byproduct.
pattern: prompt_chaining
status: implemented
implemented_by: the live Sentinel pipeline
---

# Playbook: Build a governed credit-risk model

This is the playbook Sentinel itself implements. Every run is one execution of
the happy path below. Follow it and you comply by construction, not by reading
policy PDFs after the fact.

## Job to be done

Take a loan portfolio from a raw dataset to a credit-default model that a second
line of defense, an internal auditor, and an examiner would accept: documented,
fairness-reviewed, human-approved, and fully audited.

## Recommended architecture pattern

**Prompt chaining** (fixed sequential steps with programmatic gates). Profiler to
EDA to Modeler, a human-approval gate, then Validator. Not an autonomous agent
loop: the control flow is fixed and inspectable, which is what a regulated setting
requires.

## Data-classification checklist

- [ ] Confirm the dataset's classification (this portfolio: Confidential).
- [ ] Identify PII columns and confirm they are restricted from every agent
      (here: applicant email, applicant SSN).
- [ ] Identify protected attributes and proxies (here: age band, and
      personal_status_sex as a sex proxy). Confirm proxies are withheld from the
      Profiler and the protected attribute is excluded from model features.
- [ ] Confirm RBAC scopes per agent match least privilege before the run.

## Prompt and eval scaffolding

- Agent prompts are versioned templates (`prompt_id@version`), stamped into the
  audit trail.
- The eval gate runs a golden-set check on the final payload: AUC floor, accuracy
  present, confusion matrix complete, fairness section present, protected
  attribute excluded, model-card sections complete.
- Promotion is blocked if any golden check fails.

## Human-in-the-loop requirements

- The pipeline pauses after the Modeler proposes a model.
- An accountable approver (role: MRM Approver) reviews the proposed metrics and
  either approves or rejects. No model promotes without this decision.
- The decision is recorded to the audit trail with the acting identity and role.

## Model-risk sign-off path

1. Modeler proposes the model (first line of defense).
2. Validator runs the fairness review and eval gate (second line).
3. Model card generated (SR 11-7-style model-risk document).
4. MRM Approver signs off at the human gate.
5. Model and card written to the registry with promotion status.

## Cost and latency budget

- Scripted narration: zero external cost. Default for the public link.
- Live narration: capped (default 5 USD/month ceiling), with graceful fallback to
  scripted on cap breach or failure.
- Target cycle time per analysis: seconds, not minutes.

## Launch checklist

- [ ] RBAC scopes reviewed and least-privilege confirmed.
- [ ] Fairness threshold set and justified (four-fifths rule, 0.80).
- [ ] Eval golden set covers the promotion criteria.
- [ ] Human approver role assigned.
- [ ] Model card template current with SR 11-7 sections.
- [ ] Audit persistence and retention class confirmed.
