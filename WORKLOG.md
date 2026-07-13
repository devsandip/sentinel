# Sentinel Worklog

Append-only session handoff log. Newest entries at the bottom.

## 2026-07-12 — P1 ML core + P2 model card

**Did:**
- Scaffolded the Python-only project (uv, pyproject, ruff, pytest) and pulled the real UCI Statlog German Credit data.
- Built the real ML core: `sentinel/ml/data.py`, `pipeline.py` (live logistic regression), `fairness.py` (direct group metrics + four-fifths disparity ratio), and `cli.py`.
- Built the model card generator (P2): SR 11-7-style document to Markdown + PDF.
- 13+ tests passing, ruff clean.

**State now:**
- P1 done: AUC 0.80, age-band disparity 0.569 (FLAGs naturally), sex disparity 0.82 (passes). Metrics move with seed, reproducible within seed.
- P2 in progress: model card module + sample PDF.

**Next:**
- P3 — governance harness (audit, rbac, pii, guardrails, eval_gate, cost) with tests proving a blocked RBAC access and a redaction are logged.

**Decisions:**
- Stack: Streamlit fallback (Python-only) instead of Next.js + FastAPI, for faster ship. Same backend logic.
- Fairness implemented directly (no fairlearn) so every number is auditable in a few lines.
- Protected attribute is excluded from model features (configurable: age_band default, sex, foreign_worker).

## 2026-07-12 (later) — P3 harness through P7 polish; full app shipped

**Did:**
- P3 harness: audit (append-only, immutable), rbac, pii, guardrails, eval_gate, cost, plus config YAMLs. Tests prove a blocked RBAC access and a PII redaction are logged.
- P4 agents + orchestrator: Profiler, EDA, Modeler, Validator + plain-Python orchestrator with the human approval pause. Model gateway (templated default, lazy anthropic/openai live providers, cost cap + fallback).
- P6 UI: six-tab Streamlit app (Pipeline, Results, Audit Log, Fairness, Model Card, Cost & KPIs), Governance badge, narration toggle, inline Approve/Reject gate, model-card PDF download. Verified end to end in the browser.
- P7: PRODUCT_BRIEF.md (controls -> bank KRAs, metric tree, prototype->platform), README, .env.example, Procfile, render.yaml, requirements.txt, .claude/launch.json.

**State now:**
- 36 tests passing, ruff clean. Full governed pipeline runs in scripted mode at zero cost, pauses at the human gate, and completes with a real fairness FLAG and eval gate 6/6.
- App runs locally via `uv run streamlit run app.py`. Not deployed yet.

**Next:**
- Deploy to Render + attach a custom domain (P7 deploy step). Optionally P8 live-LLM exercise with a real key.
- Capture a demo GIF/Loom for the README.

**Decisions:**
- Orchestration is a plain Python state machine, not LangGraph — fully owned, and the audit log makes it inspectable anyway.
- BLAS threading segfault (sklearn from Streamlit's worker thread on macOS) fixed with `threadpoolctl.threadpool_limits(1)` around the sklearn calls, so it is host-independent (no launch-time env var needed).
- Synthetic PII columns (applicant_email/ssn) injected at load, RBAC-restricted globally, to make the redaction control fire on every run.

## 2026-07-13 — Stabilize the Streamlit crash; strip the OpenMP cruft

**Did:**
- Chased a recurring Streamlit SIGSEGV (no Python traceback) that killed the app seconds after a DataFrame-heavy tab rendered. Read the actual macOS crash report (`~/Library/Logs/DiagnosticReports/python3.12-*.ips`) and found the real cause: pyarrow's bundled mimalloc allocator faulting in `mi_thread_init` when Streamlit serializes a DataFrame to Arrow on its worker thread.
- Fixed it with a single env var, `ARROW_DEFAULT_MEMORY_POOL=system`, set at launch (before pyarrow imports) in `run.sh`, `.claude/launch.json`, and `render.yaml`. Added a `run.sh` stable launcher and disabled Streamlit's file watcher.
- Empirically disproved my earlier OpenMP/BLAS-threading theory: a standalone harness ran sklearn + pyarrow on worker threads 25x fully unpinned with no crash, and the real app ran the full flow with zero OpenMP pins. Removed all of it: the OMP env vars, the in-code `threadpool_limits(1)` wraps in `pipeline.py` / `fairness.py`, and the explicit `threadpoolctl` dependency.
- Fixed the `use_container_width` deprecation (past its removal date) -> `width="stretch"`.
- Verified the minimal config end to end in the browser: Run -> Approve -> Fairness/Audit/Cost/Model Card tabs -> sustained polling, stable. 36 tests pass, ruff clean.

**State now:**
- App is stable on the minimal config. The ONLY launch mitigation is `ARROW_DEFAULT_MEMORY_POOL=system`. Run locally with `./run.sh` (a bare `streamlit run app.py` on macOS will still crash because it won't set that env var).
- Nothing is committed to git yet (only `git init` ran). Branch is `master`.
- Streamlit is not currently running (last background instance was killed).

**Next:**
- Make clean per-phase git commits (P1 -> P7) so history reads well, then a remote.
- Deploy to Render via `render.yaml` and attach a custom domain (CNAME).
- Optional: P8 live-LLM exercise with a real key; capture a demo GIF for the README.

**Decisions:**
- Root cause of the crash was pyarrow/mimalloc, not sklearn/OpenMP. The OpenMP pinning was cruft chasing a wrong diagnosis and was removed entirely.
- Keep exactly one mitigation, `ARROW_DEFAULT_MEMORY_POOL=system`, because it has a crash report proving it is load-bearing. It must be set before pyarrow imports, so it lives in the launcher, not in code.

## 2026-07-13 (evening) — Git history, public repo, and live on AWS EB

**Did:**
- Turned the uncommitted P1-P7 build into a clean per-phase git history (9 commits: scaffold, P1 ML core, P2 model card, P3 harness, P4 agents/orchestrator, P6 UI, P7 deliverables, the pyarrow fix, process docs). Renamed `master` -> `main`. Nothing secret or generated tracked.
- Created the public GitHub repo `devsandip/sentinel` and pushed. `main` is at `cdb60cb`.
- Deployed to AWS Elastic Beanstalk: single-instance `t3.small`, HTTP only, no load balancer (~$15/mo). CloudFormation stack (`deploy/aws/sentinel-eb.yaml`) provisions the EB app + env + IAM roles; `deploy/aws/deploy.sh` bundles, uploads to S3, and ships. Redeploy is one command.
- First deploy came up Red: my `.platform/nginx/nginx.conf` full override failed `nginx -t`. The app booted fine on 8501; the override was broken and unnecessary. Dropped it (EB's default AL2023 nginx already forwards WebSocket upgrade headers), redeployed Green.
- Verified live: health `ok`, root 200, raw WebSocket handshake on `/_stcore/stream` returns `101`, and the full UI renders in a browser.

**State now:**
- Live at http://sentinel-prod.eba-ik6jervr.us-east-1.elasticbeanstalk.com (EB env `sentinel-prod`, region us-east-1, health Green, scripted narration = zero cost).
- Repo public, `main` = `cdb60cb`, includes all deploy artifacts.
- Deploy uses the `admin` SSO profile (account 175110780229). SSO tokens expire; `aws sso login --profile admin` to refresh.

**Next:**
- HTTPS + custom domain: add an ALB + ACM cert to the stack (flips single-instance -> load-balanced, ~$28/mo), point a CNAME at the env.
- Optional: P8 live-LLM exercise with a real key (behind the $5 cap); capture a demo GIF/Loom now that there is a live URL.

**Decisions:**
- Chose EB over Render/Fly (persistent Python + WebSocket needs a real host) and ruled out Amplify (Hosting only runs JS frontends, not a Python Streamlit server).
- Single-instance HTTP first for cost; HTTPS + domain deferred as an explicit later step.
- No custom nginx on EB. The default proxy handles WebSockets; verified with a `101` handshake rather than assumed.

## 2026-07-13 (evening, cont.) — HTTPS on a custom domain

**Did:**
- Chrome could not open the http-only EB URL (silent https upgrade -> port 443 closed -> ERR_CONNECTION_TIMED_OUT). Diagnosed: HTTP 200 on 80, 443 not open, SG opens only 80.
- Put HTTPS in front on `sentinel.sandip.dev` via CloudFront (TLS termination + valid ACM cert + WebSocket pass-through) -> EB HTTP origin. Kept EB single-instance; CloudFront is pennies at demo traffic, so still ~$15/mo. Chose this over flipping EB to load-balanced with an ALB.
- Automated it end to end (all Route 53 native): `deploy/aws/enable-https.sh` requests the ACM cert, writes the DNS validation record, waits for issue, deploys `deploy/aws/sentinel-https.yaml` (CloudFront + Route 53 alias).
- Verified: valid cert, health `ok`, http->https 301, WebSocket `101` (over HTTP/1.1; HTTP/2 returns 200, a curl artifact), and the full UI renders in a browser.

**State now:**
- Live at https://sentinel.sandip.dev. `origin/main` = `1818efd`. Tree clean.
- Stacks: `sentinel-eb` (EB) and `sentinel-https` (CloudFront + cert + Route 53). CloudFront `d2ou568ieunbrr.cloudfront.net`.

**Next:**
- Demo GIF/Loom now that there is a clean HTTPS link.
- Optional P8 live-LLM exercise behind the $5 cap. Add the live URL to the README.

**Decisions:**
- HTTPS via CloudFront + ACM + Route 53, not an ALB. Cheaper and kept EB untouched.
- Cannot cert the raw elasticbeanstalk.com URL (AWS owns it), so a custom domain was required, not optional.

## 2026-07-13 (evening, cont.) — Platform buildout: phases A, B, and part of D

**Did:**
- Wrote and reviewed `docs/features/platform-buildout.md`: where Sentinel is, and how each of the 13 items in `docs/ideas.md` gets addressed. Answered the margin questions (who Sentinel serves, LangGraph, prompt storage, what the vector DB unlocks, why each agent needs a sandbox, agent-specific guardrails + toggle).
- Shipped 8 of 13 items + both lead asks (10 feature commits, tests 36 -> 82, ruff clean, all verified via AppTest): LangGraph orchestrator + DAG (3); Platform assets — patterns/playbooks/templates + reuse (12, 10, 11); identity personas + role-aware gate + enriched audit (9); gateway routing/caching/ledger (1); control on/off toggle + envelope (7); model/agent registry (13); adoption view (lead ask A).
- Added the README live URL + AWS Deploy section fix (committed earlier this session).

**State now:**
- On `main`, tree clean, NOT pushed, NOT deployed. `main` is ~11 commits ahead of `origin/main`. Live app at sentinel.sandip.dev is still the pre-platform version.
- 82 tests pass, ruff clean. New dep: `langgraph` (in pyproject + requirements.txt).
- New UI: sidebar nav (Run analysis / Platform / Registry / Adoption), a Gateway tab, the control toggle (Admin), the LangGraph DAG on Pipeline.

**Next:**
- Decide: push `main` and/or deploy the platform build (deliberate; adds langgraph to the deployed app).
- Item 2 RAG + AWS vector store — blocked on the RDS cost decision (~$12-15/mo). Recommend pgvector on RDS.
- Item 5 MCP server, item 6 memory + retention, item 8 OTel + promptfoo + Ragas, item 4 agent runtime.

**Decisions:**
- Migrated orchestration to LangGraph (reversed the earlier ruled-out). Static graph keeps it inspectable; interrupt = human gate, checkpointer = memory.
- Held two lines while unattended: no paid AWS provisioned, nothing pushed/deployed.
- Introduced a sidebar top-level nav instead of growing the tab row, since the buildout adds several always-on surfaces.

## 2026-07-13 (evening, cont.) — Platform buildout complete (all 13 items)

**Did:**
- Finished the remaining 5 items after the phase A/B checkpoint: RAG + citations (item 2, local vector store + AWS pgvector adapter, not provisioned); runnable MCP server (item 5); memory + retention (item 6); agent runtime (item 4); OpenTelemetry tracing + promptfoo/Ragas eval suites (item 8).
- All 13 items + both lead asks now built. Tests 36 -> 100, ruff clean, every feature verified end to end via AppTest.
- Regenerated requirements.txt (adds langgraph + opentelemetry-sdk; mcp/ragas kept as optional extras, excluded from deploy).

**State now:**
- On `main`, tree clean, ~19 commits ahead of `origin/main`, NOT pushed, NOT deployed. Live app at sentinel.sandip.dev is still the pre-platform version.
- UI: 4 sidebar sections (Run analysis / Platform / Registry / Adoption) + 10 run tabs (Pipeline, Results, Audit, Fairness, Model Card, Cost, Gateway, Knowledge, Memory, Traces).
- New deps in deploy: langgraph, opentelemetry-sdk. Optional extras (not deployed): mcp, ragas.

**Next:**
- Decide: provision the real AWS RDS pgvector store for item 2 (~$12-15/mo; runs on local store today), and push/deploy the platform build.
- If deploying: redeploy via `AWS_PROFILE=admin ./deploy/aws/deploy.sh` and re-verify health + WebSocket 101 (langgraph/otel are new on EB).
- Optional: demo GIF/Loom of the platform; wire Ragas faithfulness with a key.

**Decisions:**
- RAG default is the local TF-IDF vector store; AWS pgvector is code-ready but unprovisioned, holding the no-spend line.
- MCP and Ragas are optional extras so the deployed app stays lean.
- OpenTelemetry is the always-on observability layer (tested); promptfoo/Ragas are runnable offline artifacts (need Node / a key), not in pytest.

## 2026-07-13 (evening, cont.) — AWS pgvector store provisioned

**Did:**
- Provisioned CloudFormation stack `sentinel-vectordb`: RDS PostgreSQL 16 db.t4g.micro + pgvector, RDS-managed master password in Secrets Manager, SG locked to the operator IP + EB instance SG.
- Implemented PgVectorStore (search/index) with Bedrock Titan Embed v2 (1024d); ingested the 15 corpus chunks; verified dense retrieval returns the four-fifths rule + Reg B, backend reports pgvector.
- Kept local store the default fallback; psycopg + boto3 as an optional [pgvector] extra, out of deploy.

**State now:**
- `sentinel-vectordb` stack live in us-east-1. Endpoint sentinel-vectordb.cypkmm0qo4yj.us-east-1.rds.amazonaws.com, DB `sentinel`, secret in Secrets Manager. ~$13-15/mo.
- 101 tests pass (default local store), ruff clean. On `main`, ~21 commits ahead of origin, NOT pushed, NOT deployed.

**Next:**
- Deploy decision still open. To use pgvector in prod: set SENTINEL_* env on EB, add the pgvector extra to the deploy, grant the instance role Bedrock InvokeModel + secretsmanager:GetSecretValue, and confirm the EB SG can reach RDS (SG rule already added).

**Decisions:**
- RDS-managed master password (Secrets Manager), read at connect time; no plaintext password in config or env.
- pgvector on RDS over OpenSearch Serverless (cost). Bedrock Titan v2 for dense embeddings.

## 2026-07-13 (late evening) — Analysis platform first slice + pgvector in prod

**Did:**
- Built the analysis-spec engine: an analysis is a declarative `AnalysisSpec` (data contract + typed/bounded params + governed steps). A linear engine checks the contract against a dataset, then runs each step through the same harness as the hero pipeline (guardrail allow-list, RBAC, audit, cost, OTel spans). Blocks cleanly on contract violation, not-onboarded, or an off-list tool.
- Shipped two analyses on the engine: data profiling + quality triage (dependency-free profiler + declarative expectation suite) and relational feature engineering on Berka (per-account RFM/aggregates with a pre-decision window guard + an independent leakage scan). Added a new Analyses UI section (catalog, contract-matched dataset picker, editable params, governed results).
- Wired pgvector into prod: least-privilege EB instance-role policy (Secrets Manager GetSecretValue + bedrock:InvokeModel on the Titan model only), SENTINEL_VECTOR_STORE=pgvector env, psycopg+boto3 added to requirements. Added a runtime fallback so retrieval drops to the local index if RDS/Bedrock is unreachable.
- Deployed to prod and verified: CFN UPDATE_COMPLETE, EB Green, health ok, TLS redirect, WebSocket 101, hero pipeline runs to the gate (AUC 0.8018), and the profiling analysis runs to completion on the live instance. Verified the real pgvector path against prod RDS (Reg B query embeds via Bedrock, vector search returns the right passages, backend=pgvector).

**State now:**
- On `main`, pushed to origin at 7f3ccb4 (commits 8de91f9 engine, 25eb09f UI, 7f3ccb4 pgvector-prod). Deployed SHA in prod = 7f3ccb4.
- 126 tests pass (was 111), ruff clean. Live at https://sentinel.sandip.dev.
- GitHub Project #8: "[Infra] Wire pgvector to PROD" marked Done.

**Next:**
- Morning: onboard Kaggle-gated datasets (ULB fraud, LendingClub, etc.); exercise live-LLM narration behind the $5 cap using the local .env key; run Ragas faithfulness.
- Platform: decide whether the credit-risk spec ever executes through the engine, and whether linear analysis runs should feed adoption metrics + the model registry.

**Decisions:**
- Additive engine, not a rewrite: linear read-only analyses run in the new engine; the credit-risk pipeline keeps its human gate in the LangGraph orchestrator. The catalog is unified via specs; execution is not.
- Lightweight in-house profiler + quality suite + hand-rolled relational FE, not ydata-profiling/Featuretools (deferred to the backlog) to keep the t3.small deploy lean. No new heavy deps.
- Anthropic API key handled only via a gitignored local .env, never committed. Prod default stays scripted (free); pgvector-in-prod is the only paid path and it is cost-tiny (query embeddings + an already-running RDS).
