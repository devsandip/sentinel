# Platform buildout proposal

2026-07-13 18:21

Previous: [2026-07-13-1720-https-via-cloudfront-custom-domain.md](2026-07-13-1720-https-via-cloudfront-custom-domain.md)

The demo is live and stable, so the question shifted from "does it work" to "is
it enough." It is not. Sentinel today proves one governed analysis. The role it
targets is an AI platform PM inside a bank data-science org, and a platform PM is
judged on the paved road, not one workflow.

I wrote a wishlist into `docs/ideas.md`: 13 platform elements to fold in, plus
two lead asks (utilization metrics, a central asset repository). Model gateway,
RAG with a vector DB, orchestration, agent runtime, tools and MCP, memory,
guardrails, observability and evals, identity and RBAC, playbooks, agent
templates, design patterns, a model registry. The instruction to myself was
blunt: they need to make some sense, not a lot, and every one has to show its
work in the UI instead of running silently.

Claude read the whole codebase and came back with the right reframe. About half
of those 13 already exist here in embryo, because the original build made the
correct separation between the pipeline and the control plane. So this is not
bolting on features. It is maturing an architecture that already made the right
call. The pitch becomes: not one governed agent, but the platform that makes
every agent governed, auditable, and reusable.

The proposal lives at `docs/features/platform-buildout.md`. It grounds where
Sentinel is today, then works each of the 13 with current state, the design
question answered, two or more options, a recommendation, the show-your-work
surface, and effort. I reviewed it in the margins and we settled the open forks.

Decisions locked this session:

- Orchestration migrates to LangGraph. The graph stays static (fixed nodes and
  edges, a workflow, not an autonomous agent), so the inspectability story holds.
  Its interrupt primitive is the human gate; its checkpointer is the memory
  persistence. One mechanism, two wins, and a name the panel knows.
- The vector DB is real AWS: pgvector on a small RDS, not OpenSearch Serverless,
  because Serverless has a painful minimum. Roughly 12 to 15 dollars a month on
  top of the EB cost. The corpus is real public regulation (SR 11-7, Reg B, the
  four-fifths rule) plus synthetic internal standards we author and label as
  synthetic. No Citi confidential material.
- Observability and evals: OpenTelemetry, promptfoo, Ragas.
- Tools: a real, runnable MCP server, so an external agent inherits the controls.
- Prompts: versioned files and a registry now, plus Langfuse self-hosted at zero
  cost to show the managed-platform capability.
- Guardrails get per-agent control envelopes and a live on/off toggle. A reviewer
  flips a control off and watches the run break. Disabling a control is itself
  audited. This is the headline demo device: the controls prove they are
  load-bearing instead of asking the panel to take it on faith.
- Identity gets five personas (Analyst, Model Validator, MRM Approver, Auditor,
  Admin) and a role-aware approval gate.

The framing that ties it together: Sentinel is the paved road that takes a bank
data scientist from a question to a defensible, documented, approved analysis,
with the governance evidence produced as a byproduct. The bank bottleneck is not
the science. It is the documentation, the approval path, and the audit trail.
That is what the agents automate and the human still owns the decision at the
gate.

Phasing is A through D by signal per hour. A is platform framing (patterns,
playbooks, templates, the LangGraph DAG). B is the spine (identity, gateway as
control point, guardrail sectioning). C is new capability (RAG, MCP). D is
platform ops (memory, registry, OTel and evals, runtime, adoption). Starting
Phase A now.
