# All thirteen platform items built

2026-07-13 19:49

Previous: [2026-07-13-1903-platform-phases-a-b-shipped.md](2026-07-13-1903-platform-phases-a-b-shipped.md)

Finished the platform buildout. All thirteen items from the proposal plus both
lead asks are built, tested, and on main. Sentinel is a governed platform demo
now, end to end.

The five items added since the last entry:

- RAG with citations. A curated corpus of real public regulation (SR 11-7, Reg B,
  the four-fifths rule) plus labeled synthetic internal standards. The fairness
  review retrieves and cites the four-fifths rule and Reg B instead of asserting
  them. Runs on a free local vector index; the AWS pgvector adapter is written but
  not provisioned, so no money was spent. A Knowledge tab shows the query, the
  retrieved passages with scores, and their provenance.
- A runnable MCP server. Four governed tools (profile_dataset, retrieve_policy,
  compute_fairness, get_audit_log) exposed over the Model Context Protocol. An
  external agent that connects inherits the controls: RBAC still denies the
  sex-proxy column, every call is audited. The governance travels with the tools.
- Memory. Short-term working context and long-term precedent, each labeled with a
  retention class. Prior outcomes are recorded and recalled per question.
- The agent runtime. A lifecycle boundary that instantiates each agent with its
  scoped deps and logs start and finish with the scope in effect.
- Observability. Real OpenTelemetry spans per agent and per gateway call, rendered
  as a trace tree. Plus promptfoo and Ragas eval suites in evals/, runnable with
  the named tools, honest about what they skip without a key.

Test count went from 36 at the start of the day to 100. Ruff clean throughout.
Every feature verified end to end through the app with AppTest, not just units.

The build is complete but not shipped. Two deliberate toggles remain, both
requiring a decision, not more code: provision the real AWS RDS pgvector store
for the vector DB (it runs on the local store today), and push or deploy the
platform build. The live app at sentinel.sandip.dev is still the pre-platform
version. I held both lines the whole way: no paid AWS was provisioned, nothing was
pushed or deployed.

Where this leaves the interview artifact: not one governed agent, but the platform
that makes every agent governed, auditable, and reusable. Ten run tabs, four
sidebar sections, a control toggle that proves the controls are load-bearing, a
model inventory, adoption metrics, cited compliance, a governed MCP surface, and
OpenTelemetry traces. The science stayed simple on purpose; the governance is the
product.
