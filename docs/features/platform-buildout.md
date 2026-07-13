# Sentinel Platform Buildout — Proposal

**Status:** proposal, awaiting review. Nothing here is built yet.
**Author:** drafted for Sandip, 2026-07-13.
**Source:** answers the 13 items and two lead asks in [docs/ideas.md](../ideas.md).

---

## 0. Who Sentinel serves (read this first)

*Answering the margin question: this role sits in the data science org. What
does Sentinel do for a bank data scientist, and which pain does it kill?*

**The user is a Citi data scientist** (credit risk, fraud, marketing, collections,
model validation), and their manager. Not a generic "AI user." That framing keeps
every feature honest: if it does not make a bank data scientist faster or their
work more defensible, it does not belong.

**The tasks Sentinel covers** are the standard bank data-science lifecycle:
data profiling and quality assessment, exploratory analysis and feature handling,
baseline model development (PD/credit-risk, fraud, propensity), fairness /
fair-lending analysis, and model-risk documentation. That maps one-to-one to the
four agents (Profiler, EDA, Modeler, Validator) plus the model card.

**The pain it addresses.** In a bank the science is rarely the hard part. The hard
part is everything around it:

1. **Documentation burden.** Data scientists spend a large share of their time
   writing model-risk docs, validation reports, and audit evidence (SR 11-7),
   not doing science. This is the number-one time sink.
2. **A slow, friction-heavy path to production.** MRM review, fair-lending
   sign-off, and data-access approvals mean models stall for months between
   notebook and deployment.
3. **Data-access risk.** Getting entitled access to sensitive columns is slow,
   and using the wrong column (a protected attribute, PII) is a compliance
   incident.
4. **Reproducibility and audit.** When an examiner asks "how was this built, on
   what data, who approved it," reconstructing the trail by hand is painful.
5. **No reuse.** Everyone rebuilds the same scaffolding (loaders, fairness checks,
   documentation) from a blank notebook. No paved road.

**What Sentinel does about it — automate, speed up, augment:**

- **Automates the governance evidence.** The audit trail, model card, fairness
  report, and eval results are generated as a byproduct of the run. The
  documentation that normally takes days falls out of the analysis for free. This
  is the single biggest win.
- **Speeds up notebook-to-defensible-analysis.** The agents do the rote
  scaffolding (profile, EDA, baseline, fairness, docs); the data scientist reviews
  and approves at the gate. Months of last-mile friction compress because the
  evidence and the controls are produced inline, not assembled after the fact.
- **Augments, does not replace.** The human data scientist stays in the loop and
  owns the promotion decision at the approval gate. Sentinel removes the toil and
  enforces the controls; the judgment stays with the person.
- **Enforces access and fairness by default.** RBAC means the analysis physically
  cannot read columns it should not; every run produces a fairness disparity
  check whether or not anyone remembered to ask for one.
- **Compounds through reuse.** New analyses start from a governed template and a
  playbook, not a blank file (items 10, 11).

One line for the panel: **Sentinel is the paved road that takes a Citi data
scientist from a question to a defensible, documented, approved analysis, with the
governance evidence produced automatically as a byproduct.** It targets the real
bank-DS bottleneck: the science is easy, the governance and documentation are what
take months.

### The reframe

Sentinel today is a **governed pipeline** demo: one four-agent analysis wrapped
in real controls. Your `ideas.md` list, taken together, asks for one thing:
turn it into a **governed platform** demo. The paved road that makes *any* agent
workflow governed by default.

That is the exact jump an SVP AI Platform PM is hired to make: adoption, reuse,
playbooks, central controls, a registry. It is also the honest framing, because
roughly half of your 13 items already exist here in embryo. The pitch shifts
from "here is one governed agent" to "here is the platform that makes every
agent governed, auditable, and reusable." For a Citi-style panel that is the
stronger story.

Two principles govern every option below:

1. **The public link stays free, safe, and honest.** Every new model-touching
   capability (embeddings, a guardrail screen, RAG) follows the pattern the
   gateway already uses: deterministic or local by default, real provider behind
   the existing live toggle, labeled truthfully in the UI. The one deliberate
   exception is the vector store (see item 2), where you have chosen to stand up
   real AWS.
2. **Show your work.** Nothing runs silently in the backend. Every component
   gets a visible surface where a reviewer watches it fire: a ledger, a citation
   trail, a trace tree, a registry row. If we cannot show it, we do not claim it.

---

## 1. Where Sentinel is today

Grounded in the actual code, not the README.

### Modules that exist

**Two margin questions answered:**

- **LangGraph — are we using it? No.** Today the orchestrator is a hand-written
  Python state machine (`orchestrator.py`), no framework. You want LangGraph in;
  I agree, and item 3 below is rewritten to adopt it. Short version: LangGraph
  does not cost us the "inspectable workflow" story, because its graph is
  statically defined (fixed nodes and edges, not an autonomous loop), and its
  built-in interrupt + checkpointer primitives map exactly onto our human-approval
  pause and the persistence we need for memory (item 6). It also gives us a name
  the panel recognizes.
- **How to store an agent's prompt (industry standard).** Prompts are versioned
  artifacts, not string literals in code. The standard is one of two levels:
  (1) **versioned template files** in the repo (a `prompts/` directory of Jinja or
  text templates, each with an id and a semantic version), loaded through a small
  prompt registry and stamped as `prompt_id@version` into the trace and audit
  record; or (2) a **managed prompt platform** (LangSmith Prompt Hub, Langfuse
  Prompt Management, PromptLayer, Humanloop) that adds runtime pull, A/B, and
  non-engineer editing. We will do (1) now — versioned files + a registry + the
  `prompt_version` audit field — and **also integrate a managed platform to
  demonstrate the capability**, at near-zero cost. Recommended: **Langfuse
  self-hosted (~$0**, Docker; Cloud has a free Hobby tier and a ~$29/mo Core tier),
  because it is vendor-neutral, can ingest our OpenTelemetry spans, and does prompt
  management without fighting the observability stack. **LangSmith** (free Developer
  tier, then ~$39/seat/mo) is the tighter LangGraph-native pairing and includes
  Prompt Hub, but it pulls us into the LangChain ecosystem and overlaps the
  OTel/promptfoo tracing we already chose, so it is the recorded alternative, not
  the default. Net added cost either way for the demo: **$0**. This ties to the
  agent-template work (item 11) and the enriched audit (item 9).

| Layer | File(s) | What it does today |
| --- | --- | --- |
| Orchestration | `sentinel/orchestrator.py` | Plain-Python state machine. Profiler → EDA → Modeler → **pause for human approval** → Validator → finalize. In-memory run store keyed by `run_id`. |
| Agents | `sentinel/agents/{base,profiler,eda,modeler,validator}.py` | Four agents + a base class. Every agent action funnels through the harness via `read_columns`, `use_tool`, `redact_text`, `narrate`, `log`. |
| Model gateway | `sentinel/gateway/model_gateway.py` | Provider-agnostic `narrate(step, context)`. `templated` (default, zero cost), `anthropic`, `openai`. Cost cap + graceful fallback. **Narration only, one model, no routing or cache.** |
| Audit | `sentinel/harness/audit.py` | Append-only, immutable `AuditEvent` records. In-memory + per-run JSONL under `runtime/audit/`. Levels: info, blocked, redaction, gate. |
| RBAC | `sentinel/harness/rbac.py` + `config/rbac.yaml` | Per-agent column allow-list. Out-of-policy or restricted reads are denied and logged. |
| Guardrails | `sentinel/harness/guardrails.py` + `config/agents.yaml` | Tool allow-list. Any tool not whitelisted for an agent is blocked and logged. This is the sandbox boundary. |
| PII | `sentinel/harness/pii.py` | Regex redaction before any text could reach an LLM; logs when it fires. |
| Eval gate | `sentinel/harness/eval_gate.py` + `config/evals.yaml` | Golden-set checks the final payload must pass before promotion. Failing check blocks promotion. |
| Model card | `sentinel/harness/model_card.py` | SR 11-7-style model-risk doc generated from the real run; exports to PDF. |
| Cost / KPI | `sentinel/harness/cost.py` | Tokens, dollars, cycle time, decision counts. |
| ML | `sentinel/ml/{data,pipeline,fairness}.py` | Real sklearn logistic regression, real metrics, four-fifths fairness ratio. |
| UI | `app.py` | Six Streamlit tabs: Pipeline, Results, Audit Log, Fairness, Model Card, Cost & KPIs. |
| Deploy | `deploy/aws/*` | Live on AWS: CloudFront (TLS) → Elastic Beanstalk `t3.small`. HTTPS at https://sentinel.sandip.dev. |

### The honest scorecard against the 13

- **Already real:** orchestration (#3), RBAC + audit (#9), guardrails as sandbox
  (#4, #7 in part), a gateway (#1 in skeleton), eval gate (part of #8).
- **Embryonic, needs surfacing:** memory (#6, the `shared` dict + JSONL are
  short/long-term memory with no policy or surface), design patterns (#12, they
  are used but unlabeled), registry (#13, the model card is a per-run artifact
  with no inventory).
- **Net new:** RAG + vector store (#2), tool registry + MCP (#5), playbooks (#10),
  agent templates (#11), OpenTelemetry + external evals (#8), identity/personas
  (#9 extension), adoption telemetry (lead ask).

The takeaway for the panel: we are not bolting on features, we are **maturing an
architecture that already made the right separations** (pipeline vs. control
plane). That is the platform thesis in your PRODUCT_BRIEF, made concrete.

---

## 2. Locked decisions (from review)

You have already chosen on three forks. Recorded here; alternatives still shown
in the item sections for context.

- **Vector store (item 2): stand up real AWS.** See the cost note below; the
  concrete recommendation is pgvector on a small RDS instance rather than
  OpenSearch Serverless, for cost reasons.
- **Evals + observability (item 8): OpenTelemetry + promptfoo + Ragas.**
- **Tools (item 5): a real, runnable MCP server**, not just a registry doc.
- **Orchestration (item 3): migrate to LangGraph** (interrupts for the human gate,
  checkpointer for memory, a renderable static DAG). Kept as a workflow, not an
  autonomous agent.
- **Prompts:** stored as versioned template files + a prompt registry, stamped as
  `prompt_id@version` into audit and traces (managed platforms named as the
  enterprise path).
- **Guardrails (item 7): agent-specific control envelopes + a live on/off toggle.**
  A reviewer (Admin persona) can disable a control and watch the run break;
  disabling is itself audited. This is the headline demo device.

---

## 3. The 13 items — current state, options, recommendation

Each item: what exists, your question answered, two or more options, a
recommendation, the show-your-work surface, and rough effort (S/M/L).

---

### Lead ask A — Adoption & utilization metrics

> "Track agent utilization: who is using what agent, how often, for how long,
> impact on productivity."

**Current:** `cost.py` tracks per-run tokens/dollars/cycle time. No cross-run
aggregation, no per-agent utilization, no adoption view. The PRODUCT_BRIEF
metric tree already names these metrics; they just are not computed.

**Options:**
- **A. Aggregate over the persisted run store** (recommended). Once runs persist
  (item 6/13), compute runs/week, per-agent invocation counts, mean cycle time
  per agent, template-reuse %, human-override rate, cost/run. Seed with labeled
  historical demo runs so the charts are not empty.
- **B. Live-only counters.** Track utilization only for the current session. Less
  convincing, no trend line, but zero persistence work.

**Recommend A.** **Surface:** a new **Adoption** tab (or a section in Cost &
KPIs): a per-agent utilization bar, a runs-over-time line, and the reuse/override
tiles. Everything labeled "seeded demo telemetry" where it is not from live runs.
**Effort:** M (depends on persistence landing first).

@claude: agreed with recommendation. 

---

### Lead ask B — Central asset repository (playbooks, templates, patterns)

Covered by items 10, 11, 12 below. The "central repository packaged with the
app" is a `platform/` directory (playbooks, templates, patterns catalog) plus a
**Platform** tab that renders it and a downloadable pack.

---

### Item 1 — Model gateway / LLM access layer

> "What problem will a gateway solve for this specific thing we are developing?"

**Current:** `ModelGateway.narrate()` exists but is thin: one model, one call
type (narration), no routing, no cache, no per-call policy. Honest answer to
your question: **today it solves almost nothing**, because there is only one
model and one kind of call. Its value only appears when there are many models
and many callers to govern centrally.

**So give it a real job.** In a bank the gateway is where multi-model access,
PII controls, and cost governance are centralized (Citi already fronts Gemini +
Claude; the gateway is what makes that multi-model access *governed*).

**Options:**
- **A. Gateway as the visible control point** (recommended). Add: (1) **model
  routing** — cheap narration routes to Haiku, "hard" reasoning (e.g., drafting
  the model-card limitations section) routes to Sonnet, and a rules path routes
  trivial calls to templated; (2) a **response cache** keyed on prompt hash for
  cost/latency; (3) **per-call policy** — PII pre-screen and cost-cap enforced in
  the gateway, not the caller. Every call writes a ledger row.
- **B. Keep it thin, document the enterprise version.** Leave the gateway as
  narration-only and describe routing/caching/policy as "enterprise hardening"
  in the brief. Cheaper, but weaker — you would be describing the central control
  point rather than showing it.

**Recommend A.** **Surface:** a **Gateway Ledger** panel: every call with the
model chosen, the routing reason ("classified as low-stakes narration → Haiku"),
tokens, cost, cache hit/miss, and policy actions applied. This is the single
clearest demonstration of "governed multi-model access." **Effort:** M.

@claude: agreed with option A

---

### Item 2 — RAG / retrieval + vector DB  *(decision: real AWS)*

> "Can we build a vector db? We can use AWS for this."

**Current:** none. Agents narrate from computed facts; nothing is retrieved or
cited.

**What it is supposed to do, concretely.** A vector DB is not the point; grounded
retrieval is. The point is that a bank data scientist's agents should reason from
the bank's own governing documents, not from the model's training memory. Right
now every compliance-flavored statement Sentinel makes (the four-fifths rule, "the
protected attribute was excluded per policy," the model-card governance section)
is a hardcoded assertion. That is exactly the kind of claim an examiner challenges
and a model can hallucinate. Retrieval replaces assertion with citation.

**The four capabilities it unlocks** (each maps to a data-scientist pain from
section 0):

1. **Policy-grounded documentation.** When the Validator flags the age disparity,
   it retrieves the actual passage from the fair-lending policy / Reg B / the
   four-fifths rule and writes *"flagged per Fair Lending Policy §3.2 (four-fifths
   rule), disparity 0.57 < 0.80"* with a citation, into the model card and audit.
   The auto-generated docs become defensible instead of generic. Kills pain #1.
2. **Precedent and reuse.** "Has a model like this been documented before?" The
   store holds prior model cards and decisions; the agent retrieves the closest
   precedent so the data scientist reuses prior reasoning instead of starting
   blank. Kills pain #5.
3. **Data-classification grounding.** Before touching a column, an agent retrieves
   its classification from the data dictionary / classification policy ("email is
   Confidential-PII → restricted"), so the RBAC decision is explained by policy,
   not just enforced by a YAML file. Reinforces pain #3.
4. **Standards-grounded methodology.** The model-card methodology and limitations
   sections cite the internal modeling standard and SR 11-7 expectations rather
   than asserting them.

**Corpus provenance (what is real vs. authored).** We do not use Citi's internal
policy documents; they are confidential and off-limits. We also do not use pure
dummy text. The corpus is a deliberate mix, and each item is labeled in the UI by
provenance:

- **Real, public regulatory text** — the compliance backbone, genuinely citeable:
  **SR 11-7** (Fed model-risk guidance), **ECOA / Regulation B** (eCFR), and the
  **four-fifths rule** (EEOC Uniform Guidelines). These are the passages the
  Validator actually cites, which is what makes the citation defensible rather than
  decorative.
- **Synthetic "internal" standards we author ourselves** — an internal
  data-classification policy and an internal modeling standard, standing in for the
  confidential Citi documents a real deployment would point at. Clearly marked as
  illustrative/synthetic so nothing is passed off as a real Citi document.
- **Prior model cards** — generated by Sentinel's own past runs (real artifacts).

The retrieval query is derived from run state (the flagged attribute, the column
being read), not free user text, which is why it stays cheap and safe on the
public link. Without this, "governed" means "controls fire"; with it, "governed"
also means "every claim traces to a source." That is the difference between a demo
that looks compliant and one an examiner would accept.

**Options for the store:**
- **A. Real AWS — pgvector on RDS** (recommended concrete form of your choice).
  A small Postgres (RDS `t4g.micro`, roughly $12–15/mo) with the `pgvector`
  extension. Embeddings via Amazon **Bedrock Titan Embeddings** (pay-per-token,
  fractions of a cent for a fixed small corpus; queries are derived from run
  state, not free text, so they can be precomputed and cached — near-zero live
  cost). Honest "real AWS vector DB" story at low cost.
- **B. Real AWS — OpenSearch Serverless / Bedrock Knowledge Bases.** The
  managed-RAG path. More "enterprise" on paper, but OpenSearch Serverless has a
  painful minimum (roughly $100+/mo for the minimum OCUs). Not worth it for a
  public demo unless you specifically want the managed-KB name.
- **C. Local vector index + AWS adapter.** Numpy cosine over a local index, free
  and deterministic, with a documented swappable AWS adapter. This was the
  keep-it-free option; you chose real AWS, so this becomes the fallback if the
  RDS cost is unwelcome.

**Recommend A (pgvector on RDS)** as the concrete realization of your "real AWS"
decision: it is genuinely AWS, genuinely a vector DB, and cheap. **Surface:** a
**Knowledge / Citations** panel showing the retrieval query, the top-k chunks
with similarity scores, and where each citation landed in the card/audit. Plus a
**Ragas** groundedness score (item 8) proving the citations actually support the
claims. **Effort:** L (RDS + pgvector + ingestion + embeddings + citation wiring
+ surface). Cost note to confirm: the ~$12–15/mo RDS charge is on top of the
current ~$15/mo EB.

---

### Item 3 — Orchestration layer

> "What kind of orchestration layer should we have? What problems will it solve?"

**Current:** already built — a plain-Python state machine with a human-approval
pause and per-step audit.

**Answer to your question, which is the selling point:** keep it a
**predefined-path workflow**, not an autonomous agent loop. Anthropic's *Building
Effective Agents* draws the line: workflows (LLMs on predefined code paths,
predictable) versus agents (LLMs directing their own tool use). **Regulated
settings prefer workflows** because control flow is deterministic and
inspectable — an examiner can read the state machine. The problems it solves:
enforceable gates (human + eval) at fixed points, complete audit coverage, and
no surprise autonomy.

**Decision: migrate to LangGraph** (you asked for it; I agree). The concern I had
originally — that a framework hides control flow — does not apply to LangGraph the
way it would to an autonomous-agent framework, because a LangGraph graph is
statically defined: fixed nodes and edges you can read and render. It stays a
workflow, not a self-directing agent. What we gain:

- **A named, recognizable framework** the panel knows, instead of a bespoke loop.
- **Interrupts** — LangGraph's `interrupt()` / human-in-the-loop primitive is a
  precise fit for our approval pause. The Modeler node interrupts, the graph waits,
  a human resumes it. This replaces the hand-rolled `awaiting_approval` state.
- **Checkpointing** — LangGraph's checkpointer persists graph state at every node
  transition, which is exactly the short/long-term memory persistence item 6 needs.
  One mechanism serves both.
- **A real, renderable DAG** — LangGraph can emit the graph, so the "fixed path"
  visualization is close to free.

What we keep: the human gate and eval gate remain explicit nodes; every node still
emits an audit event; the flow is still Profiler → EDA → Modeler → [interrupt for
approval] → Validator → finalize. The migration is mechanical, not a redesign.

**Alternatives (recorded, not chosen):** (B) keep the bespoke state machine and
add checkpointing + a DAG by hand — less code churn, but no framework name and we
rebuild what LangGraph gives us; (C) a heavier framework or autonomous-agent
runtime — rejected, it undercuts the deterministic-workflow message.

**Surface:** a rendered LangGraph DAG on the Pipeline tab with the gate nodes
highlighted, plus the "why a workflow, not an autonomous agent" callout. **Effort:**
M (the migration touches the orchestrator and the run store).

---

### Item 4 — Agent runtime / sandbox

> "How can we deploy an agent runtime or sandbox? What problems will it solve?"

**Current:** the sandbox already exists implicitly — guardrails' tool allow-list
plus RBAC mean agents execute no arbitrary code, only named whitelisted tools on
data they are entitled to.

**Answer:** formalize it as an `AgentRuntime` that owns agent lifecycle
(instantiation with scoped deps, tool binding, teardown) and records lifecycle
events to audit. The problem it solves: a single, inspectable boundary for "what
an agent is allowed to be and do," and a place the enterprise version maps to a
managed runtime (Bedrock AgentCore, Vertex Agent Engine, Azure AI Foundry).

**Options:**
- **A. Lightweight `AgentRuntime` wrapper** (recommended). A thin class that
  instantiates agents from the registry/templates, injects scoped deps, and logs
  `agent_started` / `agent_finished` with the tool scope and RBAC scope in
  effect. No new process isolation; the sandbox is the allow-lists.
- **B. Real process/container isolation.** Run each agent in a subprocess or
  container with seccomp/resource limits. Genuinely stronger sandboxing, but
  heavy and off-message for a governance-visibility demo.

**Recommend A.** **Surface:** lifecycle rows in the audit trail and a "runtime"
line per agent in the pipeline view (scopes in effect). **Effort:** S.

**Why each agent needs its own sandbox (the coherent story).** An agent is an
LLM-driven actor. If any agent could read any column and call any tool, then one
hallucination, one prompt injection, or one bug could read an SSN or train and
promote a model with no review. A sandbox is least privilege: it bounds the blast
radius of a single agent to exactly its job. That is a standard bank control, not
a demo affectation.

The reason it is *per-agent* is that the four agents do genuinely different jobs
requiring different data and tools, and — critically — the bank principle of
**segregation of duties** says the agent that builds a model must not be the agent
that clears it. Map it out:

| Agent | Job | Data scope (RBAC) | Tools | Deliberately cannot |
| --- | --- | --- | --- | --- |
| Profiler | Data-quality / class-balance assessment | Structural columns only; **denied** PII (email, SSN) and the sex-proxy column | `read_columns`, `profile_dataset` | train or promote a model; see PII/proxy |
| EDA / Feature | Distributions, correlations, feature handling | All non-restricted columns | `read_columns`, `profile_dataset` | train, validate, or promote |
| Modeler | Train the baseline, request approval | Features | `read_columns`, `train_model` | run its own fairness or eval gate (cannot grade its own homework) |
| Validator | Independent fairness + eval-gate review | Adds the **protected attribute** (age_band), which no other agent may see, and only for fairness | `read_columns`, `compute_fairness`, `run_eval_gate` | train or modify the model (cannot fix-then-pass) |

Two things fall out of that table and they are the whole point:

1. **Least privilege is real here, not cosmetic.** The Profiler is denied the
   sex-proxy column so a protected attribute cannot leak into the profiling
   narrative; only the Validator sees `age_band`, and only to measure fairness,
   never to train on it. Different jobs, different scopes.
2. **Segregation of duties is enforced by the sandboxes.** The Modeler can train
   but cannot validate; the Validator can validate but cannot train. This is
   exactly how a bank separates model development (first line) from model
   validation (second line / MRM). The sandbox is what makes that separation
   mechanical instead of a policy nobody checks.

**Honest scoping of the "runtime."** With four agents on one dataset, the sandbox
differences are modest but real, and they encode a genuine control. The
`AgentRuntime` is the thing that instantiates each agent with its least-privilege
scope and records it — it is capability scoping (data + tools) enforced by RBAC +
guardrails, not process isolation. I will not oversell it as a container jail. The
platform payoff is forward-looking: as you add agents and templates (items 11, 13),
the runtime is where every new agent inherits a least-privilege sandbox by default
instead of getting god-mode. Enterprise hardening (real process/network isolation)
is Bedrock AgentCore / a managed runtime, named as the next rung.

---

### Item 5 — Tool / API integration layer + MCP  *(decision: real MCP server)*

> "Can we build tools? What would they be? Any MCP we can build? Just a handful."

**Current:** "tools" are internal Python functions gated by the guardrail
allow-list. No typed specs, no external interface.

**Two moves:**
- **A. Typed tool registry** (foundation). Each tool declares name, description,
  input schema, required RBAC scope, and cost. The guardrail enforces the scope.
  This is the "governed connector" idea made concrete.
- **B. A real, runnable MCP server** (your choice). `sentinel-mcp` exposes a
  handful of the governed tools over MCP: `profile_dataset`, `retrieve_policy`
  (the RAG tool), `compute_fairness`, `get_audit_log`. Any external Claude or
  Gemini agent that connects **inherits the controls** — RBAC, audit, guardrails
  — for free. That is the strongest tangible artifact in the whole list: the
  governance travels with the tools.

**Recommend A + B** (B depends on A). **Surface:** a **Tools** tab listing each
tool's spec, scope, and invocation count; plus a short doc + a runnable command
for the MCP server, and ideally a recorded clip of an external agent driving
Sentinel through it. **Effort:** M (registry S, MCP server M).

@claude: agreed

---

### Item 6 — Memory (short + long term)

> "Can we justify short and long term memory? How will this be implemented?"

**Current:** short-term memory already exists as the per-run `shared` dict passed
between agents. Long-term exists as the per-run audit JSONL. Neither is labeled
as memory and there is no retention policy.

**Justification (the bank answer):** short-term = working context for one
analysis, ephemeral. Long-term = persisted run outcomes and precedent, retained
under policy (audit records kept for years per records-retention rules; working
context discarded). Governed memory is a data-retention control, not a
convenience.

**Options:**
- **A. Formalize both with a retention policy + a precedent store** (recommended).
  Short-term: the `shared` context, shown and then discarded. Long-term: persist
  each run's outcome (question, verdicts, override, cost) to SQLite or DynamoDB;
  add a small "precedent" lookup ("this question was last run on DATE; fairness
  FLAGGED; promotion BLOCKED"). Label each store with its retention class.
- **B. Persist only the audit JSONL to S3.** Minimal: keep what exists, ship it
  to durable storage with a lifecycle policy. Honest but thinner.

**Recommend A.** **Surface:** a **Memory** panel: what is in short-term context
now vs. what was written long-term, each tagged with a retention class (e.g.,
"audit: 7-year WORM", "run context: ephemeral"). **Effort:** M.

@claude: sure. agreed with recommendation

---

### Item 7 — Guardrails

> "What explicit guardrails should we build?"

**Current:** tool allow-list (sandbox) + PII redaction + RBAC. Solid input-data
controls; no screening of LLM prompts or outputs.

**Add the sectioning pattern.** Anthropic's guidance is to run
input/output screening as a **separate instance** from the core response. Concretely:
- **Input screen:** before any live gateway call, a cheap screen checks the
  prompt for PII leakage and prompt-injection markers.
- **Output screen:** before an LLM response is shown or logged, a second screen
  checks it for leaked PII and policy violations, with a refusal path.

**Options:**
- **A. Rules + a small separate model screen** (recommended). Deterministic rules
  for the free path (regex/keyword, injection heuristics), a cheap separate model
  instance behind the live toggle. Both log guardrail events.
- **B. Rules only.** Regex/keyword screens, no separate model. Cheaper, but
  misses the "separate model instance" story that a panel will recognize.

**Recommend A.** **Surface:** guardrail events in the audit trail (blocked /
redacted / refused) and a **Guardrails** readout summarizing screens run and
hits. **Effort:** M.

**Your three follow-ups — yes to all, and the third is the best demo device we
have.**

- **Agent-specific guardrails? Yes, and we partly have them.** RBAC and the tool
  allow-list are already per-agent. We extend that to a per-agent **control
  envelope**: each agent (or template) declares its RBAC scope, allowed tools, PII
  policy, and which input/output screens apply. So the Profiler can run under a
  stricter PII policy than the Validator, and a future high-risk agent can require
  the output screen while a low-risk one does not. Guardrails become configuration
  per role, which is exactly the "per-role guardrail configs" ask in item 9.
- **Display the guardrails around each run? Yes.** When an agent, tool, or analysis
  step runs, we render its **control envelope** right there in the pipeline view: a
  small framed panel around the step showing the active controls (RBAC scope,
  allowed tools, PII screen on/off, output screen on/off) and, after it runs, which
  ones fired (green = enforced clean, amber = fired/redacted, red = blocked). The
  guardrails are literally drawn around the work. This is "show your work" at its
  most direct.
- **Switch guardrails on/off? Yes — and this is the single most persuasive thing in
  the whole build.** A **Controls** panel lets a reviewer disable a specific
  guardrail for the next run, then watch the run break: turn off RBAC and the
  sex-proxy column leaks into profiling; turn off PII redaction and an applicant
  email reaches the narration; turn off the eval gate and a failing model promotes.
  It proves the controls are load-bearing, not decoration. Two design rules keep it
  honest and safe:
  1. **Disabling a control is itself audited.** The audit log records
     `control_disabled(control=RBAC, by=role, ts=...)`, so even switching a
     guardrail off leaves an immutable trace. Very bank.
  2. **Only the Admin persona can toggle** (ties to item 9 identity), and a loud
     banner marks any run with a disabled control as `UNGOVERNED — demo only`, so
     it can never be mistaken for a real governed run and never persists for other
     visitors.

  Net effect: a reviewer does not have to take "the controls are real" on faith;
  they can switch one off and see the failure it prevents. **Added effort:** S–M on
  top of the base guardrail work (the envelope UI + the toggle plumbing + the
  disable-audit event).

---

### Item 8 — Observability & evals  *(decision: OTel + promptfoo + Ragas)*

> "Every action, thought, and decision should be traceable and observable.
> Implement evals with a well-known tool."

**Current:** the audit log is already a decision trace. The eval gate is a
golden-set release control. No standard tracing format, no external eval suite.

**The stack (your choice):**
- **OpenTelemetry** — emit a span per agent step and per gateway call, nested
  under a run span. Export to console/file by default, OTLP endpoint optionally.
  This is the recognized tracing standard a panel will know.
- **promptfoo** — an offline eval suite over narration quality and routing
  decisions (assertions on the templated/live outputs). Keeps the in-run eval
  gate as the release control; promptfoo is the pre-release quality bench.
- **Ragas** — groundedness/faithfulness scoring for the RAG citations (item 2):
  proves retrieved passages actually support the claims.

**Options considered:** OTel + promptfoo + Ragas (chosen); OTel + Anthropic
Inspect (single-tool alternative); minimal in-house tracing (no new dep). Chosen
stack maximizes name-recognition for the panel.

**Surface:** a **Traces** view (span tree per run) and an **Evals** page (offline
promptfoo report + Ragas scores, with example rows). **Effort:** L (three tools,
though each integration is modest).

@claude : agreed

---

### Item 9 — Identity, RBAC & audit logging

> "Implement RBAC and audit log; perhaps create users. Suggest a few courses of
> action."

**Current:** RBAC (per-agent column allow-list) and audit both exist. No notion
of a human identity or role; the approval gate is a bare Approve/Reject with no
actor.

**The upgrade with teeth: identity + role-aware governance.**
- **Personas/roles:** Analyst, Model Validator, MRM Approver, Auditor, Admin. A
  persona picker at the top (no real auth — pick-a-persona, labeled honestly).
- **Role-aware gate:** only an **MRM Approver** can approve promotion; an
  **Auditor** is read-only; an **Analyst** can run but not promote. Per-role
  guardrail configs.
- **Enriched audit:** every event stamped with acting user + role + model_version
  + policy_version + redaction_action + timestamp (the SR 11-7 fields).

**Options:**
- **A. Persona picker + role-aware gate + enriched audit** (recommended).
  Everything above. Big visible upgrade, no real auth system.
- **B. Real auth (Cognito/OIDC).** Genuine sign-in. Authentic, but it breaks the
  "public, no-auth, click-to-run" demo and adds a login wall. Not recommended for
  the public link; mention as the enterprise path.

**Recommend A.** **Surface:** a persona badge showing current role and what it
can/cannot do; audit rows showing the acting identity + policy/model versions;
a denied-promotion event when a non-approver tries to promote. **Effort:** M.

@claude: agreed with Option A

---

### Item 10 — AI Playbooks

> "Create a few relevant AI playbooks and put them in a central repository,
> package it with the app."

**Current:** none. The PRODUCT_BRIEF has the governance thinking but no
opinionated end-to-end guides.

**Build 2–3 playbooks**, each following the full anatomy: target job-to-be-done,
recommended architecture pattern, data-classification checklist, prompt/eval
scaffolding, human-in-the-loop requirements, model-risk sign-off path,
cost/latency budget, launch checklist. Candidates:
1. "Build a governed credit-risk model" (the one Sentinel itself implements).
2. "Stand up a reporting-automation agent."
3. "Onboard a new dataset to the platform."

Playbooks encode governance-as-default: a builder complies by following the happy
path, not by reading policy PDFs.

**Options:**
- **A. Markdown playbooks + a Playbooks tab + the current run cites its playbook**
  (recommended). The live run shows "implementing Playbook: Governed Credit-Risk
  Model, step 4 of 8," so the playbook is not a static doc but the actual path.
- **B. Static docs only.** Write the playbooks, link them, done. Cheaper, less
  convincing.

**Recommend A.** **Surface:** a **Playbooks** tab rendering each guide, a
downloadable pack, and a "this run follows Playbook X" indicator on the pipeline.
**Effort:** M (mostly content).

@claude: agreed with your recommendation

---

### Item 11 — Reusable agent templates

> "Build some agent templates and an AI playbook."

**Current:** the four agents are hand-written subclasses. No parameterized
templates, no reuse metric.

**Build parameterized starter agents** with guardrails, logging, and evals
pre-wired: a retrieval-QA agent, a document-summarizer, a data-analysis agent.
A factory instantiates one from config with the harness wired in. Track the
**leverage metric**: % of agents built from a template vs. from scratch, and
hours saved per reuse — the single clearest signal the platform is compounding.

**Options:**
- **A. Config-driven templates + factory + reuse metric** (recommended). Show the
  four pipeline agents as instances derived from templates, plus the reuse tile.
- **B. Documented template patterns only.** Describe them without a working
  factory. Cheaper, weaker.

**Recommend A.** **Surface:** a **Templates** section in the Platform tab and a
reuse-metric tile in Adoption. **Effort:** M.

@claude: agreed with option A

---

### Item 12 — Agentic architectural design patterns

> "Are there relevant agentic architecture design patterns for this case?"

**Current:** Sentinel already uses several patterns; none are labeled.

**Map what exists to Anthropic's catalog** (nearly free, high thought-process
signal):
- **Prompt chaining** — the pipeline is fixed sequential steps with programmatic
  gates (human + eval). This is the backbone.
- **Routing** — the upgraded gateway routes by stakes/difficulty to
  cheap/capable/templated models (item 1).
- **Parallelization (sectioning / voting)** — the guardrail input/output screens
  as separate instances (item 7); voting is available for higher-confidence eval.
- **Evaluator-optimizer** — Modeler (generator) + eval gate (critic) is exactly
  this loop.
- **Orchestrator-worker** — noted as the pattern we deliberately do *not* use,
  because dynamic self-decomposition is the wrong default in a regulated setting.

**Options:**
- **A. Patterns catalog doc + in-UI labels** (recommended). A curated catalog in
  `platform/patterns/`, and each Sentinel component tagged with the pattern it
  implements and why.
- **B. Doc only.** Catalog without UI labels. Cheaper, misses the "show your
  work" payoff of pointing at a running component and naming its pattern.

**Recommend A.** **Surface:** a **Patterns** section that names each pattern, and
inline tags in the pipeline/gateway views. **Effort:** S (labeling + content).

@claude: agreed with option A

---

### Item 13 — Model / agent registry

> "We need this too."

**Current:** the model card is a per-run artifact. No inventory, no versioning of
models or agents.

**Build a registry** — the MRM "model inventory":
- **Model registry:** each trained model versioned, with its card, data lineage,
  eval status, fairness verdict, and promotion state (promoted / blocked /
  rejected). This is where the model card writes on promotion.
- **Agent registry:** each agent versioned, with its template lineage, tool
  scope, RBAC scope, and eval status.

**Options:**
- **A. Persisted registry (SQLite/DynamoDB) + a Registry tab** (recommended).
  Real records that accumulate across runs, wired to the eval gate and templates.
- **B. In-memory registry for the session.** Simpler, but resets each run and
  cannot show inventory growth over time.

**Recommend A.** **Surface:** a **Registry** tab listing model versions (status
badges from the eval gate) and agent versions (template lineage + reuse). Ties
directly to the MRM story in the PRODUCT_BRIEF. **Effort:** M.

@claude: agreed

---

## 4. Proposed phasing

Ordered by interview-signal-per-hour. Each phase is independently shippable and
leaves the demo in a coherent state.

**Phase A — Platform framing (cheapest, do first).**
Items 12 (patterns), 10 (playbooks), 11 (templates + reuse), 3 (orchestration
answer + DAG). Mostly content + labels + one Platform tab. Establishes the
platform narrative and produces the artifacts later phases reference.

**Phase B — The spine.**
Items 9 (identity/personas + role-aware gate + enriched audit), 1 (gateway as
control point + Gateway Ledger), 7 (guardrail sectioning). The governance core.

**Phase C — New capabilities.**
Items 2 (RAG + pgvector on RDS + citations), 5 (tool registry + MCP server).
The tangible new-capability artifacts; also where the AWS cost lands.

**Phase D — Platform ops.**
Items 6 (memory + retention), 13 (registry), 8 (OTel + promptfoo + Ragas), 4
(runtime), Adoption tab. The operational-maturity layer that ties runs together.

Dependencies: Adoption (lead ask A) needs persistence from Phase D; Ragas (8)
needs RAG (2); the reuse metric (11) needs the registry (13) to be fully honest,
though a session-local version works earlier.

---

## 5. Cost & risk notes

- **New recurring cost:** ~$12–15/mo for the RDS pgvector instance (item 2), on
  top of the current ~$15/mo EB. Bedrock embedding cost is negligible for a fixed
  small corpus. Confirm you want the standing RDS charge, or we precompute
  embeddings and pause the instance between demos.
- **Dependency weight:** promptfoo, Ragas, OpenTelemetry, and pgvector client add
  install surface. All dev/eval-time except the pgvector client and OTel runtime.
  We keep the public app's hot path free of live calls by default.
- **Scope risk:** this is a multi-day buildout. Phase A alone materially upgrades
  the interview story; we can stop after any phase.
- **Honesty risk:** personas are not real auth; seeded telemetry is not live
  usage; templated narration is not live reasoning. Every one of these stays
  labeled in the UI, as the current app already does.

---

## 6. Open questions for review

1. **RDS cost:** OK to add the standing ~$12–15/mo pgvector instance, or prefer
   precompute-and-pause (spin the DB up only for demos)?
2. **Phasing:** start with Phase A as recommended, or reorder?
3. **Personas:** the five roles above (Analyst, Model Validator, MRM Approver,
   Auditor, Admin) — right set, or adjust?
4. **Playbook set:** the three candidates in item 10 — right three, or swap one?
5. **MCP client for the demo:** do you want a recorded clip of an external agent
   driving Sentinel over MCP as part of the deliverable, or is the runnable
   server enough?

---

## 7. What ships (deliverables checklist)

When fully built, Sentinel gains:

- A **Platform** tab: playbooks, agent templates, patterns catalog (items 10–12).
- A persona picker + role-aware approval gate + enriched audit (item 9).
- A **Gateway Ledger** with model routing + caching + policy (item 1).
- Input/output **guardrail** sectioning, **per-agent control envelopes**, and a
  **live on/off toggle** that proves each control is load-bearing (item 7).
- **RAG** with real AWS pgvector + policy citations in the card and audit (item 2).
- A typed **tool registry** + a runnable **`sentinel-mcp`** server (item 5).
- Governed **memory** with a retention policy surface (item 6).
- A **model/agent registry** tab (item 13).
- **OpenTelemetry** traces + a **promptfoo**/**Ragas** evals page (item 8).
- A **LangGraph** orchestrator (interrupts for the human gate, checkpointer for
  memory) with a rendered **DAG** and the "workflow, not autonomous agent"
  argument (item 3), plus an `AgentRuntime` lifecycle boundary (item 4).
- Versioned **prompts** (`prompt_id@version` in audit + traces).
- An **Adoption** telemetry view (lead ask A).

All of it visible, all of it labeled, none of it silent.
