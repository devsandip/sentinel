# Sentinel — portfolio page copy

The source text for https://sandip.dev/portfolio/Sentinel/. The HTML is a
rendering of this file. Edit here first.

---

## Hero

**Sentinel.**

A governed agentic data-science platform. A visitor picks a banking question,
hits Run, and watches a model write the analysis code, a static gate read that
code before the machine does, a sandbox execute it, and a disclosure screen strip
small cells out of the result before anything narrates it. Every step emits an
audit event. Several of the controls can refuse, and on a normal run at least two
of them do.

Live at **sentinel.sandip.dev**. Code at **github.com/devsandip/sentinel**.

---

## 1. What it is

Sentinel is a public, clickable demo of one idea: in a regulated bank, the
blocker on agentic AI is not capability, it is governance.

A model that a regulator cannot audit, that reads a column it should not, that
promotes itself without a human signature, or that ships without a fairness
review and a model-risk document, does not go to production in a bank. It stalls
at the demo. The gap is not a better model. It is the harness around the model:
the controls that make an autonomous analysis defensible to a second line of
defence, an internal auditor, and an examiner.

So Sentinel treats governance as the product rather than the paperwork. The
machine learning underneath is deliberately boring, a logistic-regression
baseline on a public credit dataset. What is not boring is that the same run
produces the evidence a bank would need to trust it: an append-only audit log, a
column-level access decision, a PII redaction, a human approval gate that the
author of the run cannot clear themselves, an eval gate, a fairness disparity
number, and a generated model card sized like an SR 11-7 document.

The analysis is always real. Metrics move with the dataset and the seed. The
narration is scripted by default so the public link costs about zero and cannot
be run up by a stranger, and the app says so on screen rather than implying live
reasoning it is not doing. A live-LLM path exists behind a hard spend cap.

**Why I built it.** I wanted an artifact, not a slide. The argument I care about
is that agentic AI in a bank is a controls problem, and the only convincing way
to make that argument is to build the controls and let someone click them.

---

## 2. Walkthrough

*(reserved slot: a YouTube walkthrough of a full run, start to signature)*

---

## 3. The architecture

### 3.1 The nine stages

A run is one vocabulary, used everywhere: **Ask, Plan, Access, Generate, Gate,
Execute, Screen, Interpret, Attest.** The stages are how the app is laid out, how
the audit log is indexed, and how the evidence pack is organised, because a
single reading order is the thing that makes a run explicable to someone who did
not write it.

| Stage | What happens | The control armed on it |
| --- | --- | --- |
| **Ask** | Persona, dataset, declared purpose, and a prebuilt request. No free-text prompt box on the public link. | The purpose matrix refuses a wrong-purpose request here, before a single token is spent. |
| **Plan** | Binds a certified analysis agent. Only certified entries are selectable. | Four certification gates, draft to candidate to certified. |
| **Access** | Builds the working table from granted columns and pins the dataset by SHA. | Column grants, the data contract, and the fingerprint pin. OpenLineage START. |
| **Generate** | The model writes the analysis code. | The gateway ledger and the cumulative spend cap sit here, because this is where money is spent. |
| **Gate** | A static read of the generated code before any machine reads it. Nine checks, four verdicts each. | Import allowlist, no dynamic code, no egress, must parse. A refusal feeds a regenerate loop up to a cap, then hands to a human. |
| **Execute** | A fresh subprocess per run. 15 second wall clock, 1024MB, no network, no filesystem. | The time and resource caps. |
| **Screen** | Small cells are removed from the result, and proxy discovery runs. | The disclosure floor at n under 10, applied upstream of the narration. |
| **Interpret** | The narration is built only from what survived the screen. | Faithfulness, measured, floor of 0.90. |
| **Attest** | The evidence pack is assembled and signed. | Segregation of duties. The approver cannot be the author. |

### 3.2 Four decisions that make it governance rather than logging

Most "governed AI" demos are a pipeline with a log next to it. These four are the
difference.

**Access enforces by construction, not by a check.** A denied column is not
filtered at read time. It is never put on the object the generated code receives.
There is no attribute to reach for, so there is no check to bypass, no rule to
get the order wrong on, and nothing for a clever prompt to argue with.

**The gate reads the code before the machine does.** It is a standard-library
`ast` walk. It never imports, evaluates, or runs what it is inspecting. Any SQL
literal is handed to a second parser (sqlglot), because a Python AST does not
understand SQL and a SQL parser does not analyse Python. The verdicts are four,
not two: cleared, refused, nothing to judge, and rule never supplied. That last
pair matters more than it looks. A control that was armed and found nothing is a
different fact from a control that was never configured, and collapsing them into
a green tick is how a control surface starts lying.

**The screen runs before the narration, and it removes rather than masks.** If a
cell is below the disclosure floor it is taken out of the frame, not blanked in
the display. The model that writes the interpretation never sees it, so it cannot
reason around it or infer it from a total.

**Segregation of duties is by identity, not by role.** SR 11-7 asks for
independence between development and validation. A role check satisfies that on
paper. Comparing identities is the stricter reading: a Platform Admin who started
a run cannot approve it either, even though their role says they may approve.

One more, in the other direction. **Proxy discovery flags and never refuses.**
Whether a correlated feature carries a business necessity is a Legal and
Compliance judgment, not a platform judgment. A platform that refused on
correlation alone would be wrong on the law and switched off inside a week. The
job of that control is that nobody afterwards gets to say they did not know.

### 3.3 The control catalogue

Twenty-six controls live in one catalogue. Twenty-three are enforced. Three are
declared in the design and not implemented in this build, and those render dashed
everywhere they appear rather than quietly counting as live.

Every control chip in the app resolves through that one catalogue, so a control
reads identically in the gate panel, the audit drill-down, the registry, and the
manual. Each entry names the regime it answers to:

| Regime | Principle | What answers to it |
| --- | --- | --- |
| SR 11-7 / PRA SS1/23 | Independence of validation from development | Segregation of duties on signing, narration faithfulness, the eval gate, the human promotion gate |
| ECOA / Regulation B | Disparate impact comes from what correlates with a protected attribute, not the attribute itself | Proxy discovery, which flags and never refuses |
| GDPR Article 5 / FCRA 604 | Purpose limitation and data minimisation | The purpose matrix, column scoping, PII controls |
| GLBA Safeguards Rule | Access control and containment | Column grants, no egress, no filesystem or process access |
| Statistical disclosure control | A minimum cell size before an aggregate may be published | The disclosure floor and small-cell suppression |
| SOX change control | Nothing runs that a reviewer has not read | The import allowlist, no dynamic code, code must parse |
| BCBS 239 | Risk data aggregation and lineage | The dataset fingerprint pin and OpenLineage events |

The wording is always **answers to**, never **complies with**. A control serves a
principle. Compliance is a determination a firm's own second and third lines make
against their own policy, on systems with authenticated users and a real model
inventory. This build has none of those, and it says so on screen.

### 3.4 Two routes, and only one of them has a screen

The nine-stage walkthrough is the live surface. Underneath it there is a second
route: a four-agent LangGraph pipeline (Profiler, EDA, Modeler, Validator) with a
real `interrupt()` human gate, a static topology, and a checkpointer. It produced
the credit-risk runs sitting in the audit log and the models in the registry.

It no longer has a screen of its own. That is a deliberate cut rather than an
omission, and the page says so because a visitor cannot click it.

The state split on that route is worth one line. The graph state carries the run
id and the approval flag and nothing else. The heavy run state, with live harness
handles in it, sits in the orchestrator's own store keyed by run id, so the
checkpointer never has to serialise a file handle.

### 3.5 The modules

The pipeline and the control plane are separable, which is the whole claim to
being a platform rather than a demo. Roughly 27,000 lines under `sentinel/`, with
8,000 more of tests.

- **`govflow/`** — the nine stages end to end, the autonomy tiers, the purpose
  matrix, the policy-scoped access build, and the single control catalogue.
- **`codegen/`** — the static gate (an `ast` walk), the SQL gate (sqlglot), the
  import allowlist, the result contract that is interpolated into the prompt and
  then enforced after execution, and a seeded corpus of real violations to test
  the gate against.
- **`sandbox/`** — parent-side spawn with a wall clock, a child entrypoint with
  resource limits, and a boot-time warm-up so the time cap measures the analysis
  rather than a cold import.
- **`harness/`** — the control plane: audit log, RBAC, PII, guardrails, eval
  gate, cost, model card, identity, OpenTelemetry tracing.
- **`platform/`** — certification, the model registry, the cross-run audit store,
  agent templates, playbooks, adoption metrics.
- **`disclosure/`** — small-cell suppression and the association measure behind
  proxy discovery.
- **`evidence/`** — the evidence pack, and the marimo and Quarto renderings of it.
- **`gateway/`, `ml/`, `datasets/`, `rag/`, `lineage/`, `analyses/`, `ui/`.**

### 3.6 Runtime

One `t3.small` Elastic Beanstalk instance, no load balancer, nginx in front of
Streamlit. CloudFront terminates TLS with an ACM certificate, Route 53 points at
it. Two idempotent CloudFormation stacks own the whole footprint, and two scripts
apply them.

The interesting part is the CloudFront cache policy, because it is where I was
wrong for a while. The distribution has two behaviours. The default one carries
the app with caching disabled and every viewer header forwarded, because the
Streamlit WebSocket needs the upgrade headers passed through untouched. `/static/*`
is separate, cached at the edge and compressed.

That split is not tidiness. Streamlit's front end is 61 files and 2.5MB,
content-hashed and immutable, and under the default behaviour every visitor
pulled all of it uncompressed off the small instance. That was the six seconds of
blank white on a cold load. It was not an Elastic Beanstalk cold start, which is
what I assumed first: time to first byte was under a second the whole time.
Compression needs both halves of that behaviour, because CloudFront compresses
what it caches, and the caching-disabled policy drops `Accept-Encoding` from the
cache key. Setting `Compress: true` alone does exactly nothing.

---

## 4. Build versus buy

The thesis that settles most of these: **the machine learning is bought off the
shelf, the governance is the product.** Anywhere a credible off-the-shelf
component exists, adopting it is more on-message than reimplementing it, because
the claim being made is "I can govern the tools a bank already uses," not "I can
rewrite them."

Two of these started as build decisions and I reversed them. Both reversals are
in the repo with dates.

| Decision | Call | Why |
| --- | --- | --- |
| Fairness metrics | **Buy** — fairlearn | Originally hand-rolled "for auditability". Reversed. If the pitch is that I govern off-the-shelf tools, hand-rolling the one metric a regulator cares most about undercuts it. Governing fairlearn is the stronger position. |
| Orchestration | **Buy** — LangGraph | Originally a plain Python state machine, which was right for a single-pipeline demo and wrong for a platform. LangGraph's graph is static, so it stays inspectable, and `interrupt()` plus a checkpointer are exactly the human gate and its pause. |
| The ML | **Buy** — scikit-learn | A logistic-regression baseline, on purpose. Reimplementing a classifier proves nothing relevant to the argument. |
| The frontend | **Buy** — Streamlit, over Next.js | One runtime, and load-bearingly so: the gate parses Python, the sandbox runs Python, the allowlist is Python imports, and fairlearn, statsmodels, DoWhy, lifelines, SHAP and sqlglot are Python-only. "Node entirely" means reimplementing fairlearn in TypeScript, which is the exact thing the thesis says not to do. "Node plus FastAPI" is a prioritisation trap: nobody hires an AI product lead for frontend engineering. The honest cost is a single process, in-memory session state, and no real auth. |
| The code gate | **Build** | Nothing off the shelf reads generated Python against a bank's policy and produces a per-check verdict a reviewer can read. It is 1,000 lines of stdlib `ast`. A gate tells you what was intended before it happens; a sandbox tells you what happened after. Both are needed, and this is the one that is demonstrable in a browser. |
| The SQL half of the gate | **Buy** — sqlglot | The Python AST does not understand SQL. sqlglot parses it and rewrites row filters into it. It parses and never executes. |
| The query engine | **Buy** — DuckDB | Replaced ad-hoc pandas so that generated SQL is a thing that can be gated and rewritten rather than string-matched. |
| Containment | **Build**, and stated as demo scope | A subprocess with resource limits. A serious sandbox needs gVisor or Firecracker. That is written down as a non-goal rather than glossed, because claiming a demo subprocess is production containment is the kind of thing a control surface should never do. |
| Provenance and tracing | **Buy the standards** — OpenLineage, OpenTelemetry | Emitting a schema-valid lineage event and a real span is worth more than a bespoke table, because the receiving side already exists in a bank. Captured in-process here, with no backend attached. |
| The document outputs | **Buy** — marimo, Quarto | Two audiences, two artifacts. A marimo notebook is plain `.py`, so a data scientist can review it in a pull request. The leadership view is a document that gets read once, forwarded, and filed, so Quarto serves it better than an app would. When the Quarto binary is absent, it writes the source and says so rather than faking a PDF. |
| Retrieval | **Both** | Locally a TF-IDF index, which is free, deterministic, and honestly labelled as lexical rather than dense. In production, RDS pgvector with Bedrock Titan embeddings behind the same interface, with a runtime fallback to the local one. |
| Hosting | **Buy** — Elastic Beanstalk and CloudFront | Amplify Hosting only runs JavaScript front ends and cannot hold a persistent Python server. Render and Fly both work, and `render.yaml` is still in the repo as a one-click alternative. AWS won because the deploy story is the one a bank will ask about. |
| Policy engine | **Not yet** | Policy is in-process. Externalising it to OPA needs a server and changes where the policy lives, not whether it exists. That is an architecture decision for a real deployment, not for a credibility artifact. It is on the dependency map, not claimed as built. |
| PII detection | **Not yet** | Regex today. Presidio is the intended replacement and is labelled on screen as on the dependency map and not wired in this build. I would rather ship a small honest control than a big implied one. |

The pattern underneath all of it: buy the thing a bank already recognises, build
the thing that is the argument, and label the gap where a component is roadmap
rather than reality.

---

## 5. Numbers

- **676 tests**, 51 test modules, 8,054 lines of test against roughly 27,000
  lines of source.
- **26 controls** in one catalogue. 23 enforced, 3 declared and drawn dashed.
- **9 stages**, 4 autonomy tiers, 6 personas, 8 datasets from 1,000 rows to 1.1
  million, 9 gate checks with 4 verdicts each.
- **14 allowlisted imports** at the default tier, 29 at the open tier. Egress,
  filesystem, process control and dynamic code are denied at every tier.
- **AUC 0.8018** on German Credit, seed 42. Fairness disparity ratio around 0.5
  to 0.57 against a 0.8 threshold, which flags. The number moves with data and
  seed, which is the point.
- **0 tokens and $0.0000** on a scripted run, 1.8 seconds end to end. Live mode
  is capped at $50 a month, process-global, so all public traffic shares one cap.
- One `t3.small`. Two CloudFormation stacks. 24 seeded runs and 249 audit events
  committed to the repo, every one of them produced by actually executing a run.

---

## 6. What it is not

Worth stating plainly, since the whole project is an argument about honesty in
control surfaces.

- No authentication. Personas are selectable, so segregation of duties is
  demonstrated rather than enforced against a real identity provider.
- Single process, in-memory session state. That is Streamlit's shape.
- The subprocess sandbox is demo-scope containment, not gVisor.
- Three of the twenty-six controls are declared and not implemented, and are
  drawn dashed wherever they appear.
- The four-agent LangGraph route is real and tested but has no screen, so a
  visitor cannot run it.
- Compliance is not claimed anywhere. Controls answer to principles. A firm's own
  second and third lines make compliance determinations, and this build has
  neither.
