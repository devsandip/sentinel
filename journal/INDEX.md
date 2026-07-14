# Sentinel — Journal Index

Last refreshed: 2026-07-14 08:54

Latest entry: [2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md](entries/2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md)

## Where we are now

Sentinel is a governed agentic data-science demo, built as an interview
credibility artifact for an SVP AI Product Management role at a bank. The thesis:
agentic AI can be made governed, auditable, and shippable in a regulated bank.
The ML is kept small on purpose; the governance harness is the star.

The full app is built and now stable. A four-agent pipeline (Profiler, EDA,
Modeler, Validator) plus a plain-Python orchestrator runs a real
logistic-regression analysis on UCI German Credit, pauses at a human approval
gate, and completes with a fairness review, an eval gate, and a generated
SR 11-7-style model card (PDF). Every agent action flows through the governance
harness (audit, RBAC, PII, guardrails, eval gate, cost). Two controls fire on
every run (an RBAC denial and a PII redaction), and the age-band fairness check
flags a real disparity (0.57). The six-tab Streamlit UI is verified end to end.

A recurring Streamlit segfault was root-caused (via the macOS crash report) to
pyarrow's mimalloc allocator, not sklearn/OpenMP as first assumed. The single
fix is `ARROW_DEFAULT_MEMORY_POOL=system`, set in the launcher. All the earlier
OpenMP thread-pinning was tested, shown to do nothing, and removed.

Stack: Streamlit (Python only). 36 tests passing, ruff clean. Run locally with
`./run.sh`.

The build now has a clean per-phase git history and is public at
https://github.com/devsandip/sentinel. It is live on AWS with HTTPS on a custom
domain: https://sentinel.sandip.dev.

The stack is CloudFront in front of a single-instance Elastic Beanstalk env.
CloudFront terminates TLS with an ACM cert and forwards to the EB instance over
HTTP, passing the WebSocket through (caching disabled, all viewer headers
forwarded). EB is a single t3.small, no load balancer, about 15 dollars a month;
CloudFront adds pennies at demo traffic. Verified end to end: valid cert, health
ok, http-to-https redirect, WebSocket 101, and the full UI renders in a browser.
Redeploy the app with `AWS_PROFILE=admin ./deploy/aws/deploy.sh`; the HTTPS front
is `./deploy/aws/enable-https.sh` (idempotent).

The platform buildout is complete. All thirteen items in the proposal
(`docs/features/platform-buildout.md`) plus both lead asks are built, tested, and
on main. Sentinel is a governed platform demo end to end: not one governed agent,
but the platform that makes every agent governed, auditable, and reusable.

Built (test count 36 to 100, ruff clean, all verified via AppTest): LangGraph
orchestrator with a rendered DAG; a Platform surface (pattern catalog, playbooks,
agent templates, reuse metric); five identity personas with a role-aware gate and
enriched audit; the gateway as a control point (routing, caching, Gateway Ledger);
the control on/off toggle; a model/agent registry; adoption metrics; RAG with
cited compliance on a local vector store; a runnable MCP server; short/long-term
memory with retention; an agent runtime lifecycle boundary; and OpenTelemetry
tracing plus promptfoo/Ragas eval suites.

Sentinel is now a governed analysis platform, not a single pipeline, and the
whole thing is in prod. An analysis is a declarative spec: a data contract, typed
editable parameters, and governed steps. A linear engine checks the contract
against a dataset, then runs each step through the same harness as the hero
pipeline (guardrails, RBAC, audit, cost, tracing). Two analyses run on it, data
profiling plus quality triage and relational feature engineering on Berka with a
pre-decision leakage guard, both exposed in a new Analyses UI with contract-
matched dataset picking and parameter editing. The credit-risk pipeline is in the
catalog as a spec but still runs in the LangGraph orchestrator, because it
promotes a model and keeps the human gate.

The RAG vector store now runs on real AWS in prod: the EB instance role has a
least-privilege policy (RDS-managed secret + the Titan model only), the store is
set to pgvector, and retrieval falls back to the local index if RDS or Bedrock is
unreachable so the public link never breaks. The real pgvector path is verified
against the same prod RDS. Deployed and verified live: health ok, TLS redirect,
WebSocket 101, hero pipeline runs to the gate (AUC 0.8018), and the new profiling
analysis runs to completion on the instance. 126 tests pass, ruff clean.
Deployed SHA 7f3ccb4.

Live-LLM narration works and is on the public link. It never actually ran before
(the anthropic SDK was never installed, so the gateway's fallback silently served
scripted text). Fixed via an optional `live` extra. Sandip approved enabling it
in prod: the key rides in via a NoEcho CloudFormation parameter read from the
gitignored .env at deploy time (never committed), the default stays scripted and
free, and "Live LLM" is selectable per run. The $50 cap is now a cumulative
process-global ceiling (not a per-run budget), so it bounds total public spend.
Verified live: a run narrated LIVE end to end, ledger showed $0.0018 of real
spend on the instance.

Both morning-deferred items are now done and in prod. ULB credit-card fraud
(OpenML 1597) and LendingClub (DePaul mirror) are onboarded through their
no-account substitutes, both run clean through the governed analysis engine, and
LendingClub fires the commercial-use flag on profiling. The Ragas faithfulness run
is no longer a stub: faithfulness is implemented directly on the Anthropic SDK
(the ragas pip package is broken in this env), scoped to the policy claims RAG
grounds, calibrated, and averaged over three passes. It scores a stable 1.0 on
both cases. 127 tests pass, ruff clean.

Deployed to prod (SHA 9dcd20b): CFN UPDATE_COMPLETE, EB green, the new bundle
ships both CSVs, and the live Dataset registry at https://sentinel.sandip.dev
lists ulb_fraud and lendingclub. Live-LLM stayed enabled (key sourced from the
main-repo .env at deploy time, since the worktree has none). The credit-risk-spec
routing question is decided: it stays in the LangGraph orchestrator (see ruled
out).

## Recent entries

- [2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md](entries/2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md) — ULB fraud + LendingClub onboarded via no-account sources; Ragas faithfulness wired on the Anthropic SDK and run, stable 1.0. 127 tests.
- [2026-07-14-0646-live-llm-narration-in-prod.md](entries/2026-07-14-0646-live-llm-narration-in-prod.md) — live-LLM narration was silently broken (SDK never installed); fixed + enabled in prod behind a cumulative $50 cap. Verified live.
- [2026-07-13-2237-analysis-platform-and-pgvector-prod.md](entries/2026-07-13-2237-analysis-platform-and-pgvector-prod.md) — analysis-spec engine + profiling & feature-eng analyses; pgvector live in prod. 126 tests.
- [2026-07-13-2005-aws-vector-store-provisioned.md](entries/2026-07-13-2005-aws-vector-store-provisioned.md) — RAG on real AWS: RDS pgvector + Bedrock embeddings, corpus ingested, dense retrieval verified.
- [2026-07-13-1949-all-thirteen-items-built.md](entries/2026-07-13-1949-all-thirteen-items-built.md) — all 13 platform items done: RAG citations, MCP server, memory, runtime, OTel traces. 100 tests.
- [2026-07-13-1903-platform-phases-a-b-shipped.md](entries/2026-07-13-1903-platform-phases-a-b-shipped.md) — eight of thirteen platform items shipped: LangGraph, personas, gateway ledger, control toggle, registry, adoption.
- [2026-07-13-1821-platform-buildout-proposal.md](entries/2026-07-13-1821-platform-buildout-proposal.md) — reframe from governed pipeline to governed platform; 13-item proposal reviewed and decisions locked.
- [2026-07-13-1720-https-via-cloudfront-custom-domain.md](entries/2026-07-13-1720-https-via-cloudfront-custom-domain.md) — HTTPS lands on sentinel.sandip.dev via CloudFront (Chrome forced the issue).
- [2026-07-13-1650-git-history-and-aws-eb-deploy.md](entries/2026-07-13-1650-git-history-and-aws-eb-deploy.md) — clean git history, public repo, and live on AWS Elastic Beanstalk.
- [2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md](entries/2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md) — the crash was pyarrow all along; OpenMP pinning removed as cruft.
- [2026-07-12-1145-full-governed-app-lands.md](entries/2026-07-12-1145-full-governed-app-lands.md) — harness, agents, orchestrator, and six-tab UI land end to end.
- [2026-07-12-1015-p1-ml-core-lands.md](entries/2026-07-12-1015-p1-ml-core-lands.md) — P1 ML core lands; fairness flags on its own.

## Recent weekly summaries

None yet. Week 2026-W28 (through Sun 2026-07-12) has entries but no summary.

## Working hypotheses

- A naturally-flagging fairness result is more convincing than a staged one. Keep it real.
- The model card PDF is the single highest-leverage showpiece.
- A control is only credible if it can be seen firing. Force RBAC and PII to fire every run.

## Open questions

- Should linear analysis runs feed the adoption metrics and model registry? (The execution-routing half of this is now decided; see ruled out.)
- Retrieval ranking: the SR 11-7 query ranks the internal modeling standard above the SR 11-7 document itself (SR 11-7 chunks still return at ranks 2-3). Worth a later look at chunking or reranking.
- Demo GIF/Loom for the README: dropped for now per Sandip (2026-07-14).

## Things ruled out

- Next.js + FastAPI split (chose Streamlit for speed).
- fairlearn dependency (implemented metrics directly for auditability).
- ~~LangGraph~~ — reversed 2026-07-13. Adopting LangGraph for the platform buildout. Its graph is static (fixed nodes/edges), so it stays an inspectable workflow, and its interrupt/checkpointer primitives map onto the human gate and memory. The plain state machine was right for the single-pipeline demo, wrong for the platform.
- OpenMP/BLAS thread pinning as the crash fix (tested, did nothing, removed). The real fix is the pyarrow memory pool.
- FRED data (macro time-series does not fit the classification/fairness story).
- Render and Fly for the host (chose AWS Elastic Beanstalk).
- AWS Amplify (Hosting only runs JS frontends; it cannot run a persistent Python Streamlit server).
- A custom nginx override on EB (the default AL2023 nginx already forwards WebSocket upgrade headers).
- Executing the credit-risk spec through the linear analysis engine (decided 2026-07-14: it stays in the LangGraph orchestrator). The pipeline promotes a model and holds a human approval gate; the linear engine is for read-only analyses. Unifying execution would mean rebuilding LangGraph's interrupt/checkpointer primitives in the engine and risking the hero pipeline's gate. The catalog already unifies the two as specs; only execution differs, by design.
