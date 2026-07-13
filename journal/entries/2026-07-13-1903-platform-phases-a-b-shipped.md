# Platform phases A and B shipped

2026-07-13 19:03

Previous: [2026-07-13-1821-platform-buildout-proposal.md](2026-07-13-1821-platform-buildout-proposal.md)

Built most of the platform buildout in one session. Sentinel is no longer a
single governed pipeline. It is a governed platform, and the demo now shows the
platform machinery, not just one analysis.

Shipped, all tested and on main, eight feature commits:

- LangGraph orchestrator. The hand-written state machine is gone. The pipeline is
  a static LangGraph graph: the human gate is a real interrupt, a checkpointer
  persists state across the pause, and the interrupt survives Streamlit reruns. A
  rendered DAG on the Pipeline tab shows the fixed path and makes the workflow,
  not autonomous agent, argument concrete.
- Platform assets. A patterns catalog (the five Building Effective Agents
  patterns, each mapped to where Sentinel uses it or why it is avoided), three AI
  playbooks, and five agent templates with a reuse metric. All in a Platform tab.
- Identity. Five personas with a role-aware approval gate. An Analyst cannot
  promote; only the MRM Approver and Admin can. A non-approver's Approve attempt
  is denied and audited. Every audit event now carries the acting identity and
  the policy version.
- Gateway as control point. Routing by stakes to a model tier, a process-level
  cache, cost-cap policy, and a Gateway Ledger that records every call. In
  scripted mode the routing decision is still logged.
- The control toggle. The headline demo device. An Admin can switch a control off
  and watch the run break: RBAC off leaks the sex-proxy column, PII off leaks an
  applicant email, the eval gate off promotes unchecked. Disabling a control is
  itself audited, and the run is marked UNGOVERNED. The controls prove they are
  load-bearing instead of asking the panel to take it on faith.
- Registry and adoption. A model inventory that versions every run with its
  metrics, fairness verdict, and promotion status, plus an agent registry. An
  adoption view with per-agent utilization and weekly run counts.

That is eight of the thirteen items plus both lead asks. Test count went from 36
to 82. Verified end to end through the app with Streamlit's AppTest harness at
each step, not just unit tests: run to gate to approve, the role-aware denial,
the ungoverned banner, the ledger, the registry.

One decision reversed cleanly. LangGraph was on the ruled-out list for the single
pipeline. For the platform it is the right call: the static graph keeps the
workflow inspectable, and the interrupt and checkpointer are exactly the human
gate and the memory persistence the later phases need.

Held the line on two things while working unattended. No paid AWS was
provisioned, so the vector DB (item 2) is not built; it is blocked on the RDS
cost decision. And nothing was pushed or deployed. The live app at
sentinel.sandip.dev is still the pre-platform version until a deliberate deploy.

Remaining: RAG plus the real AWS vector store (item 2), the MCP server (item 5),
memory plus retention (item 6), OpenTelemetry plus promptfoo plus Ragas (item 8),
and the agent runtime (item 4). These are the next session. RAG and MCP are the
highest value of the five and both want a bit of input: RAG on the AWS cost and
corpus, MCP on how far to take the runnable server.
