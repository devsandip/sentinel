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

Sentinel demonstrates this as a nine-stage governed walkthrough: Ask, Plan, Access, Generate, Gate, Execute, Screen, Interpret, Attest. The model writes the analysis code, a static gate reads it before the machine does, a sandbox contains it, and a disclosure screen removes small cells before anything narrates the result. Every stage shows the controls armed on it, and each one can refuse.

The stages are the product's one vocabulary for reading a run, which is why they are also how the evidence is laid out: the gateway ledger sits at Generate because that is where tokens are spent, the raw emitted table at Execute because the screened one next door is what a control did to it, the disparity ratio at Interpret. What a run cost is a header chip, because no single stage owns it.

A second route, a four-agent LangGraph pipeline with an interrupt-based human gate, produced the credit-risk runs in the Audit Log and the models in the Registry. It no longer has a screen of its own. The analysis is real on both routes: metrics, fairness numbers and the model card are computed from the run and change with the data and seed. Generation is scripted by default (zero cost, safe for a public link) and labeled honestly; a live-LLM path exists behind a cost cap. The point the demo makes is that the controls are real, visible, and load-bearing.

## 3. Governance controls and the regulation each answers to

Each control is a named, testable rule that can refuse. They live in one catalogue (`sentinel/govflow/controls_info.py`), and every control chip in the app resolves through it, so a control reads identically in the Gate panel, the Audit Log drill-down, the Registry and the manual. Each entry names the regime it answers to and the principle within it. The manual's "Controls and regulation" chapter renders that catalogue live, which is why no count appears below: a table in a document goes stale the moment a control is added, and it goes stale silently.

The wording throughout is **answers to**, never **complies with**. A control serves a principle. Compliance is a determination a firm's own second and third lines make against their own policy, on systems with authenticated users and a real model inventory. This build has none of those, and the Audit Log says so on screen.

| Regime | Principle | Controls that answer to it |
| --- | --- | --- |
| SR 11-7 / PRA SS1/23 | Independence of validation from development; conceptual soundness; outcomes analysis | Segregation of duties on signing, narration faithfulness, the eval gate, the human promotion gate, target leakage (declared) |
| ECOA / Regulation B (12 CFR 1002) | Disparate impact: the failure mode is using what correlates with a protected attribute, not the attribute itself | Proxy discovery, which flags and never refuses |
| GDPR Article 5 / FCRA section 604 | Purpose limitation and permissible purpose; data minimisation | The purpose matrix, column scoping, PII controls in output text and in model context |
| GLBA Safeguards Rule (16 CFR 314) | Access control and containment | Column grants, no network egress, no filesystem or process access, RBAC and row filters (declared) |
| Statistical disclosure control | Minimum cell size before an aggregate may be published | The disclosure floor and small-cell suppression, applied upstream of the narration |
| SOX change control / secure SDLC | Nothing runs that a reviewer has not read | The import allowlist, no dynamic code, no sandbox escapes, code must parse |
| BCBS 239 | Risk data aggregation and lineage | The dataset fingerprint pin, OpenLineage events, lineage completeness (declared) |
| Internal operational | No external driver, stated as a decision rather than left blank | Wall-clock and resource caps, query complexity ceiling, spend cap, tool allowlist, injection screen |

Two design points are worth stating plainly.

**Segregation of duties is enforced by identity, not by role.** SR 11-7 asks for independence between development and validation. Most implementations satisfy that with a role check. Comparing identities is the stricter reading: a Platform Admin who authored a run cannot approve it either.

**Proxy discovery flags rather than refuses.** Whether a correlated feature carries a business necessity is a Legal and Compliance judgment, not a platform judgment. A platform that refused on correlation alone would be wrong on the law and switched off within a week. The job of the control is that nobody afterwards gets to say they did not know.

Forward-looking frameworks are named in the manual rather than claimed here. The EU AI Act treats creditworthiness assessment of natural persons as Annex III high-risk, and its Article 11 technical documentation requirement, not the phrase "model card", is what the model documentation in this build is shaped like.

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
