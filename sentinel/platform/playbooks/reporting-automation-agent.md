---
id: reporting-automation-agent
title: Stand up a reporting-automation agent
jtbd: >
  As an analytics team, replace a recurring manual reporting task with a governed
  agent that assembles the report, cites its sources, and routes anomalies to a
  human, without leaking data or skipping review.
pattern: prompt_chaining
status: template
implemented_by: not yet built; use the data-analysis and retrieval-QA templates
---

# Playbook: Stand up a reporting-automation agent

A common first platform use case: a recurring report (risk, portfolio, ops) that
a person assembles by hand every week. Automate the assembly, keep the judgment.

## Job to be done

Turn a recurring manual report into a governed agent run: pull the numbers,
ground the commentary in source documents, flag anomalies for a human, and emit
the report plus an audit trail.

## Recommended architecture pattern

**Prompt chaining** for the fixed assembly steps, with a **routing** step that
sends anomalies to a human and routine sections straight through. Retrieval grounds
the commentary so claims cite a source.

## Data-classification checklist

- [ ] Classify every input feed; confirm the agent's RBAC scope covers only what
      the report needs.
- [ ] Confirm no PII enters the narrative; redaction on before any text reaches a
      model.
- [ ] Confirm source documents used for grounding are approved for this audience.

## Prompt and eval scaffolding

- Versioned prompt templates per report section.
- Evals: numeric reconciliation checks (totals tie out), groundedness scoring on
  the commentary (Ragas), and a freshness check on the source data.

## Human-in-the-loop requirements

- Anomalies above a threshold pause for human review before the report is issued.
- Sign-off recorded with the acting identity.

## Model-risk sign-off path

- Lower risk than a predictive model, but still: a named owner approves the report
  template and the eval thresholds before first issue.

## Cost and latency budget

- Batch, off-peak; cache retrieval embeddings for the fixed corpus.
- Budget the live-model spend per report and cap it centrally at the gateway.

## Launch checklist

- [ ] Input feeds classified and RBAC scoped.
- [ ] Reconciliation and groundedness evals in place.
- [ ] Anomaly threshold and routing rule set.
- [ ] Report owner assigned and template approved.
