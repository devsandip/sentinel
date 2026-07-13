---
id: onboard-new-dataset
title: Onboard a new dataset to the platform
jtbd: >
  As a platform owner, add a new dataset so that any agent can use it under the
  same governance the platform already enforces, with no per-dataset special
  casing.
pattern: prompt_chaining
status: template
implemented_by: the config-extension path (rbac.yaml, questions.yaml)
---

# Playbook: Onboard a new dataset to the platform

The platform is only a platform if adding a dataset is configuration, not a
rewrite. This playbook is the paved road for onboarding one.

## Job to be done

Register a new dataset so the existing agents, controls, and surfaces work on it
unchanged, with classification and access set correctly from day one.

## Recommended architecture pattern

No new pattern. The existing **prompt-chaining** pipeline wraps the new dataset;
onboarding is a governance and configuration task, not an architecture change.

## Data-classification checklist

- [ ] Classify the dataset (Public / Internal / Confidential / Restricted).
- [ ] Enumerate PII columns; add them to the restricted list.
- [ ] Enumerate protected attributes and proxies; set exclusions and the
      fairness attribute.
- [ ] Define per-agent RBAC scopes (least privilege) in `rbac.yaml`.
- [ ] Record the data lineage (source, snapshot, owner) for the model card.

## Prompt and eval scaffolding

- Add preset questions in `questions.yaml` mapped to the dataset and its
  protected attribute.
- Extend the eval golden set if the dataset needs checks beyond the defaults.

## Human-in-the-loop requirements

- A data owner signs off on the classification and RBAC scopes before the dataset
  is usable.

## Model-risk sign-off path

- Data-governance sign-off on classification and access, before any model built on
  the dataset can be promoted.

## Cost and latency budget

- One-time onboarding cost; no recurring model spend from onboarding itself.

## Launch checklist

- [ ] Classification set and PII restricted.
- [ ] RBAC scopes defined and reviewed.
- [ ] Protected attributes and proxies handled.
- [ ] Preset questions added.
- [ ] Lineage recorded for the model card.
- [ ] Data owner sign-off captured.
