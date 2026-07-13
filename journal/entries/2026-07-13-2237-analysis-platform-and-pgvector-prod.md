# Analysis platform first slice, and pgvector live in prod

Date: 2026-07-13 22:37
Previous: [2026-07-13-2005-aws-vector-store-provisioned.md](2026-07-13-2005-aws-vector-store-provisioned.md)

Sentinel stopped being one governed pipeline tonight. It is now a governed
analysis platform with a declarative engine and more than one analysis.

The core idea: an analysis is a spec, not code. An `AnalysisSpec` names a data
contract, a set of typed and bounded parameters a user can edit, and an ordered
list of governed steps. A linear engine interprets the spec. It checks the
contract against the chosen dataset first, then runs each step through the same
harness as the hero pipeline: the guardrail allow-list scopes every tool call,
RBAC filters restricted columns, the audit log records every step, cost is
tracked, and each step is an OpenTelemetry span. The contract check and the
per-step guardrail are themselves controls. An analysis cannot run on a dataset
it does not fit, and a step cannot call a tool it is not scoped for. I proved
both: a feature-engineering run on a non-relational dataset blocks before any
step executes, and a mis-scoped step is blocked and audited.

Two analyses ship on the engine. Data profiling and quality triage runs on any
tabular dataset: a dependency-free profiler plus a declarative expectation suite
that gates on blocking failures like excess missingness or a degenerate target.
Relational feature engineering runs on the Berka bank tables: per-account
aggregates and RFM features built only from transactions dated on or before the
loan date, so no post-outcome information leaks in. A separate leakage scan then
verifies the feature set independently, structurally and by correlation. On
Berka the scan comes back clean, max correlation 0.24, which is the window guard
doing its job.

The credit-risk pipeline is described as a spec too, so the catalog is unified,
but it still runs in the LangGraph orchestrator. It promotes a model and pauses
at the human approval gate, and the linear engine deliberately does neither.
That split is the honest line: read-only analyses run in the engine; anything
that promotes keeps the gate.

The whole thing has a UI. A new Analyses section shows the catalog, a
contract-matched dataset picker, editable parameters, and the governed result:
contract check, per-step trace, the profile or quality or feature or leakage
output, and the audit trail as evidence.

Second thing tonight: the RAG vector store now runs on real AWS in prod, not
just locally. I gave the Elastic Beanstalk instance role a least-privilege
policy (read the RDS-managed secret, invoke exactly the Titan embedding model),
added the pgvector extra to the deploy, and set the store to pgvector in the
environment. Retrieval has a runtime fallback: if RDS or Bedrock is unreachable,
it drops to the local index so the public link never breaks. I verified the real
path end to end against the same prod RDS: a Reg B query embeds through Bedrock,
the pgvector nearest-neighbor search returns the right passages, and the backend
reports pgvector, not the fallback.

All of it is in prod. I deployed, waited for green, and checked the live site:
health ok, TLS with the http-to-https redirect, WebSocket 101, the hero pipeline
runs to the gate with real numbers (AUC 0.8018), and the new profiling analysis
runs to completion on the deployed instance. 126 tests pass, ruff clean.

Deployed SHA: 7f3ccb4. Live at https://sentinel.sandip.dev.
