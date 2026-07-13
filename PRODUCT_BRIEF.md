# Sentinel — Product Brief

**Author:** Sandip
**Audience:** SVP hiring panel, bank data-science / agentic-AI platform
**One line:** A governed agentic data-science platform that makes AI analysis auditable, controllable, and shippable inside a regulated bank.

---

## 1. The problem

Banks want the productivity of agentic AI on their data-science work: profiling, modeling, validation, documentation. The blocker is not capability. It is governance. A model that a regulator cannot audit, that reads data it should not, that promotes itself without a human sign-off, or that ships without a fairness review and a model-risk document, cannot go to production in a bank. The result is that most agentic AI stalls at the demo stage.

The gap is not a better model. It is the harness around the model: the controls that make an autonomous analysis defensible to a second line of defense, an internal auditor, and an examiner.

## 2. The platform thesis

Treat governance as the product, not the paperwork. Build the agent pipeline and the control plane together, so every autonomous step is mediated by a control and emits an audit event. The ML underneath can be deliberately simple (a logistic-regression baseline here); the differentiation is that the same run produces the evidence a bank needs to trust it.

Sentinel demonstrates this with one dataset (UCI German Credit) and a four-agent pipeline (Profiler, EDA, Modeler, Validator) plus an orchestrator. The analysis is always real: metrics, fairness numbers, and the model card are computed live and change with the data and seed. The agent narration is scripted by default (zero cost, safe for a public link) and labeled honestly; a live-LLM toggle exists behind a cost cap. The point the demo makes is that the controls are real, visible, and load-bearing.

## 3. Governance controls mapped to bank KRAs

Each control is a small, named module. Every agent action flows through them.

| Control | What it does | Bank KRA it serves |
| --- | --- | --- |
| Audit log | Append-only, immutable JSONL of every agent action, denial, and decision | Auditability; examiner and internal-audit evidence; SR 11-7 outcomes analysis |
| RBAC | Per-agent column allow-list; out-of-policy reads blocked and logged | Least-privilege data access; data governance; segregation of duties |
| PII redaction | Regex detection and redaction before any text reaches an LLM | Data privacy (GLBA); prevents PII leakage into third-party models |
| Guardrails | Tool allow-list; no arbitrary code execution | Operational risk; controlled autonomy; third-party / tool risk |
| Human-in-the-loop gate | Pipeline pauses after the model is proposed; a person approves or rejects | Accountability; four-eyes control; model approval authority |
| Eval gate | Golden-set checks must pass before a model can be promoted | Change management; release control; conceptual soundness |
| Model card | SR 11-7-style model-risk document generated from the real run, exported to PDF | Model risk management; model inventory; validation evidence |
| Fairness review | Group metrics and a four-fifths disparity ratio; protected attribute excluded from features | Fair lending (ECOA/Reg B); responsible AI; reputational risk |
| Cost and KPI tracker | Tokens, dollars, cycle time, eval pass-rate, human-override count | Unit economics; run-cost control; operational reporting |

The design principle: a control is only credible if it can be seen firing. Sentinel forces two of them to fire on every run. The Profiler is denied a proxy-for-sex column (RBAC "access denied", logged), and an applicant email is scrubbed before narration (PII "redacted", logged). The age-band fairness check flags a real disparity (ratio 0.57 against a 0.8 threshold), so the Validator raises a genuine review item rather than a staged one.

## 4. The metric tree

North-star: **percent of agentic analyses that are promotable without rework** (governed throughput).

Decomposed:

- **Trust / quality**
  - Eval-gate pass-rate (share of runs clearing all golden checks)
  - Fairness pass-rate (share within the disparity threshold)
  - Human-override rate at the approval gate (lower over time as trust builds)
- **Control integrity**
  - Audit completeness (every step has an event; target 100 percent)
  - RBAC and PII events captured per run (control coverage)
- **Efficiency / cost**
  - Cycle time per analysis
  - Cost per run (0 in scripted mode; capped in live mode)
- **Adoption (platform stage)**
  - Analyses run per week; distinct question types; datasets onboarded

## 5. Prototype to enterprise platform

What is deliberately stubbed here, and how it hardens:

- **Data:** in-memory CSV and JSON files today. Enterprise: governed data access to the bank's warehouse, with RBAC driven by the existing entitlements system rather than a YAML file.
- **Model registry:** the model card is generated per run. Enterprise: cards write to the model inventory / MRM system (for example an internal registry), versioned, with lineage to the training data snapshot.
- **Eval gate:** a small golden set today. Enterprise: a curated, growing eval suite per model family, wired into CI so promotion is gated in the deployment pipeline, not just the UI.
- **Human gate:** a single Approve/Reject today. Enterprise: routed to the accountable approver by role, with SLA tracking and delegation.
- **Gateway:** provider-agnostic interface with templated and live providers. Enterprise: routes to the bank's approved model gateway, with the cost cap and rate limits enforced centrally, keys in a secrets manager.
- **Datasets and questions:** one dataset, four presets, designed to be config-extended. Enterprise: a catalog of question templates per line of business.

The architecture is the message: the pipeline and the control plane are separable modules, so the same harness wraps any future analysis. That is what turns a prototype into a platform.

## 6. Why this is the right artifact for the role

The job is not to prove that agents can do data science. It is to make agentic AI safe and shippable in a regulated bank. Sentinel is built so that every decision serves that one message: when in doubt, invest in the governance harness and its visibility, not in fancier ML. The model card, audit log, human gate, and fairness check are the product.
