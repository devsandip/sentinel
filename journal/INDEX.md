# Sentinel — Journal Index

Last refreshed: 2026-07-13 17:20

Latest entry: [2026-07-13-1720-https-via-cloudfront-custom-domain.md](entries/2026-07-13-1720-https-via-cloudfront-custom-domain.md)

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

## Recent entries

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

- Do we exercise live-LLM mode with a real key before the interview, or leave it scripted?
- Capture a demo GIF/Loom for the README, now that there is a live HTTPS URL to record.

## Things ruled out

- Next.js + FastAPI split (chose Streamlit for speed).
- fairlearn dependency (implemented metrics directly for auditability).
- LangGraph (plain state machine is fully owned; audit log makes it inspectable).
- OpenMP/BLAS thread pinning as the crash fix (tested, did nothing, removed). The real fix is the pyarrow memory pool.
- FRED data (macro time-series does not fit the classification/fairness story).
- Render and Fly for the host (chose AWS Elastic Beanstalk).
- AWS Amplify (Hosting only runs JS frontends; it cannot run a persistent Python Streamlit server).
- A custom nginx override on EB (the default AL2023 nginx already forwards WebSocket upgrade headers).
