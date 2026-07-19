# Sentinel — Journal Index

Last refreshed: 2026-07-19 10:58

Latest entry: [2026-07-19-1030-v6-deployed-to-prod.md](entries/2026-07-19-1030-v6-deployed-to-prod.md)

## Where we are now

**v6, the unified app, is merged and LIVE in prod. The mockup is now what
`sentinel.sandip.dev` serves: a login persona gate, a grouped sidebar with
live counts, a command-center landing, all 8 datasets onboarded, and a real
seeded run-history store behind the numbers. Verified the right way, by a
governed flow run on the instance.**

PR #5 merged to main (`2e47fce`). Deployed bundle `sentinel-20260719-101916.zip`,
CloudFormation changeset applied, EB Ready and Green, live-LLM on. Prod moved
v5 to v6. Verified on the instance: the login gate renders (it did not exist in
v5), the command center shows live tiles (Datasets 8, Registry 3, Adoption 19)
and a grouped sidebar with live counts, and run `7d306d5dfb64` completed all
nine stages at tier L2 with 3 controls fired.

v6 was three workstreams from docs/features/unified-app-build.md. **D**: all
eight datasets onboarded (added uci_bank_marketing; deleted the lying
`onboarded` flag; gave synthetic_its CAP_TABULAR). **H**: a real seeded
run-history store (sentinel/data/seed_runs.jsonl) fed by 19 actually-executed
runs, replacing the hand-written fictional registry rows and weekly list; the
Registry, Adoption, and dashboard surfaces read it. **S**: the login persona
gate, the grouped sidebar, and the command-center landing with four live-number
tiles. A 25-agent adversarial review of the diff confirmed 9 findings, all
fixed, the sharpest being a misleading adoption number on the landing tile.
374 tests pass, ruff clean.

Deferred still: dark mode, RBAC-gated navigation, B-style contextual drawers,
OPA externalisation (waits on Sandip). The W29 weekly summary is due Monday
2026-07-20. A docs-only PR (this entry + INDEX + WORKLOG) is open for merge.

Everything below is the prior state: v4/v5 in prod.

---

**v4 is merged to main (`3b17921`) and LIVE in prod, verified by loading the page
and running a flow. The autonomy ladder works end to end, L0 to L3. Only OPA
externalisation is deferred (needs an external server).**

PR #3 merged into main; feature branches gone. Deployed bundle
`bundles/sentinel-20260718-185231.zip`, EB green, HTTPS 200, HTTP->HTTPS 301,
live-LLM on (key read from the main-checkout .env at deploy time). No missing-deps
crash: v4 added no new runtime deps and the requirements-drift guard passed.
Verified on the instance at https://sentinel.sandip.dev: the Governed codegen
surface renders the mode toggle, the computed tier chip, the Access-policy section,
and the full purpose matrix; a governed run (696ef64456bc) completed through all
nine stages with CTL-DISC-02 suppressing the n=6 band and CTL-PROXY-01 flagging the
proxy (Execute passing = the subprocess sandbox ran generated code on the box). 316
tests pass, ruff clean.

What v4 delivered: the flow computes the tier from the persona and dataset and
routes on it. A certified analyst on german_credit resolves to L2 (writes gated
code); an uncertified Junior Analyst resolves to L1 (picks the certified analysis,
fills typed params, no code); a second-line persona resolves to L0 (may not run).
L3 runs broad code in the sandbox on synthetic_its (the only Public dataset, now
onboarded with a known +12 effect): the allowlist widens to whole packages and
stdlib compute but the egress/filesystem/dynamic-code deny lists stay as at L2, so
the benign DiD recovers +11.9 while three adversarial requests are refused. Plus the
purpose-by-dataset matrix (CTL-PURP-01, the credit-data-for-marketing showpiece),
autonomy tier resolution, and the two v3 secondary outputs (marimo notebook + Quarto
render).

Deferred: OPA externalisation (external server, a Sandip call). Weekly summaries
W28 + W29 still owed.

The flow computes the tier from the persona and the dataset classification and
routes on it. A certified analyst on german_credit resolves to L2 (writes gated
code, the hero path); an uncertified Junior Analyst resolves to L1 (picks the
certified fair-lending analysis and fills typed params, no code); a second-line
persona resolves to L0 (may not run). L3 runs broad code in the sandbox on
synthetic_its, the only Public dataset (now onboarded, generated with a known +12
effect). The L3 gate widens the analytical allowlist to whole packages and stdlib
compute but keeps the egress/filesystem/dynamic-code deny lists exactly as at L2:
more rope, same hard limits. The benign L3 analysis is a difference-in-differences
estimate that recovers +11.9 (95% CI 11.6-12.2); three adversarial L3 requests are
refused (CTL-EGRESS-01, CTL-CODE-02, CTL-CODE-03). The govflow surface has a mode
toggle (fair lending on german_credit, causal impact on synthetic_its), so
switching dataset recomputes the tier live: the analyst on Public data still caps
at L2 without a sandbox waiver, which is the tier resolver firing in the UI.

Also shipped earlier on this branch: the two v3 secondary outputs (a real loadable
marimo notebook with the generated analysis as a reviewable `def analysis(ctx)`,
and a Quarto `.qmd`/PDF render path with an honest fallback where no `quarto`
binary), and the purpose-by-dataset matrix (credit data for marketing refused at
Access with `CTL-PURP-01`, the showpiece).

Five feature commits + docs on `feat/govcodegen-v4`, all pushed, PR #3 open. 316
tests pass (up from 251 at the start of the day), ruff clean. Deferred: OPA
externalisation (external server, a Sandip call). Not deployed: prod is public and
the change is large; it waits for review.

Everything below is the prior state: v0-v3 in prod.

---

**v0 through v3 are merged to main and live in prod, verified by loading the site.
The governed-codegen rethink is now the public artifact, not a branch.**

Both PRs are merged: PR #1 (v0, v1) landed on main first, then PR #2 (v2, v3) was
retargeted onto main and merged. main is at `8aeccba` (a `requirements.txt` fix on
`4692c7c`, the v0-v3 code); both feature branches are gone. 251 tests green, ruff
clean. Prod runs bundle `bundles/sentinel-20260718-073829.zip`: EB green, health 200
over HTTPS, live-LLM on. The first deploy on 2026-07-18 crashed on import
(`requirements.txt` was a stale `uv export` missing `fairlearn`/`sqlglot`/`duckdb`/
`openlineage-python`); regenerating it and redeploying fixed it. All three new
surfaces are verified rendering on the instance: the governed code-generation console
runs the full Ask-to-Attest flow (Execute passes, so sqlglot+DuckDB work in prod),
the evidence pack shows its finding, CI, provenance, negative statement, and
OpenLineage events, and the registry shows the certified and refused agents with a
live CTL-SOD-01 self-signoff refusal. The deploy is additive, so
https://sentinel.sandip.dev keeps the platform build and gains these three surfaces.

**v2, the platform claim.** The SQL half of the gate: `ctx.sql` parses with
sqlglot, refuses an ungranted column / `SELECT *` / out-of-scope table
(`CTL-COL-01`, `CTL-PURP-01`) or a Cartesian join (`CTL-COMPLEX-01`), injects the
identity row filter, and runs on DuckDB. The certification lifecycle: four gates
between an agent and `certified`, status computed from the gates, only certified
agents visible to Plan. The scaffolding CLI (`sentinel new-agent`), the only path
to an agent. And `CTL-CONTRACT-01` drift, built honestly: the contract is pinned to
the real dataset SHA, the mechanism is proven in a test, and no fake drift is
staged. The refused-certification demo holds: cohort-retention v0.3 is refused on
two grounds, and a self-signoff is refused live with `CTL-SOD-01`.

**v3, the oversight claim.** The Attest stage assembles an evidence pack: the
finding with a Wald CI, the provenance chain, the controls attested as chips, and
the negative statement, the "what this does not say" block assembled from what the
run actually did (the suppressed band, the flagged proxy). Signing it refuses a
self-signoff (`CTL-SOD-01`). Provenance is also emitted as OpenLineage events at
Access and Attest; the leadership doc exports as Quarto-ready markdown.

All verified in the browser, and now in prod. Deliberately still out: the
DS-facing marimo notebook and the Quarto PDF render (secondary outputs), and all of
v4 (breadth), which includes two forks held for Sandip: OPA externalisation (needs
an external server, an open question in the PRD) and the L3 path (needs
`synthetic_its` onboarded first).

Everything below is the prior state: v0/v1, the rethink, and the platform in prod.

---

**The build is stable and in prod. The rethink is accepted, and the build has started.**

On 2026-07-17 I stopped building and rethought the whole thing, then accepted the
result. The finding: the governance layer is not governing the language model, it
is governing scikit-learn. Every control fires on a logistic regression, and
turning the LLM off leaves all of them passing. The model narrates at the end of
the pipeline and never touches anything, so nothing ever governs it. Meanwhile the
question being asked is whether I can deploy LLMs to help data scientists, and the
honest answer to how LLMs help data scientists is that they write the code.

The plan moves the model upstream of execution so it writes the analysis code, and
puts a static-analysis gate between generation and execution. Governance stops
being a perimeter and becomes differentiated controls at each transition: RBAC and
purpose at Access, code safety at Gate, disclosure at Screen, SR 11-7 at Attest.
The organising idea is an autonomy ladder (L0 explains, L1 chooses, L2 writes
inside a fence, L3 improvises) where the tier is computed from role times data
classification rather than chosen. Maths is bought off the shelf. The governance
is the product.

The proposal is now the plan, and building has started. Work goes on a feature
branch, `feat/governed-codegen`, with a PR per slice, and the code-generation step
calls the live model from the start of development rather than mocked fixtures.
**v0** is first: the segregation-of-duties fix, independent of the reframe and
worth doing regardless (see Things ruled out). **v1** is one vertical slice,
Generate to Gate to Execute to Screen at L2 on `german_credit`, with fairlearn
doing the maths and `CTL-PROXY-01` the one control that earns its way in. As of
this entry no code has changed; the branch exists off `b447e80`. The PRD is at
`docs/features/governed-codegen.md`, with the 15-slide argument beside it as HTML
and PDF.

Everything below describes the build as it stands. It is accurate and deployed.
It is also what the proposal would reframe.

---

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

- [2026-07-19-1030-v6-deployed-to-prod.md](entries/2026-07-19-1030-v6-deployed-to-prod.md) : Sandip said merge and deploy. PR #5 merged to main (`2e47fce`); deployed bundle `sentinel-20260719-101916.zip`, CFN changeset applied, EB green, live-LLM on. Prod moved v5 to v6. Verified the right way: the login gate renders (absent in v5), the command center shows live tiles (Datasets 8, Registry 3, Adoption 19) and a grouped sidebar with live counts, and run `7d306d5dfb64` completed all nine stages at tier L2 with 3 controls fired. `describe-application-versions` returned null for the bundle key (CFN manages the version label); the deploy upload log is the provenance. prod is v6.
- [2026-07-19-1011-unified-app-shell-datasets-history.md](entries/2026-07-19-1011-unified-app-shell-datasets-history.md) : the mockup became the app. Merged + deployed v5 (prod verified by a flow run). Then built v6 in three workstreams: D (all 8 datasets onboarded, deleted the lying `onboarded` flag, synthetic_its gains CAP_TABULAR), H (a real seeded run-history JSONL store from 19 executed runs, replacing fictional registry rows and the hardcoded weekly list), S (login persona gate, grouped sidebar with live counts, command-center landing with four live tiles). A 25-agent adversarial review confirmed 9 findings, all fixed (the sharpest: the adoption tile implied 13/19 promotions where only 2 of 3 models promoted). 374 tests. PR #5 open; prod is v5, v6 deploys after merge.
- [2026-07-19-0113-showtell-stepper-and-design-system.md](entries/2026-07-19-0113-showtell-stepper-and-design-system.md) : overnight build of the show-and-tell brief (docs/more_ideas.md). The govflow surface became a nine-stage stepper with control explainers, struck/masked denied columns, Screen before/after, and the Gate Fix it repair; an adversarial review confirmed 18 findings, all fixed. Mid-build Sandip pointed at the unified-app mockup + docs/ui-spec.md; the stepper and chrome now wear that design system (topbar lockup, nav-rail sidebar, node rail, phead/In-Does-Out/engine bar, Architecture stop). 355 tests. On a branch, PR for morning review; prod untouched.
- [2026-07-18-1859-v4-merged-and-deployed-to-prod.md](entries/2026-07-18-1859-v4-merged-and-deployed-to-prod.md) : Sandip said merge and deploy. PR #3 merged to main (`3b17921`); deployed bundle `sentinel-20260718-185231.zip`, EB green, live-LLM on, no drift/missing-deps. Verified the right way this time: loaded the page and ran a flow on the instance. The Governed codegen surface renders all the new v4 pieces (mode toggle, computed tier chip, purpose matrix), and run 696ef64456bc completed through all nine stages (Execute passing = the sandbox ran generated code in prod). prod is v4.
- [2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md](entries/2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md) : finished the buildable v4 (Sandip AFK, said "finish everything"). The flow computes the tier from the persona and routes: L2 codegen (analyst), L1 certified-analysis+params (junior, no code), L0 blocked (second line). Onboarded synthetic_its (fully synthetic, known +12 effect) and built the L3 broad-sandbox route: wide allowlist, same egress/fs/dyncode deny lists (more rope, same hard limits); benign DiD recovers +11.9, three adversarial requests refused. govflow mode toggle so the tier recomputes per dataset. 316 tests. Deferred: OPA (external server). Not deployed; prod still v0-v3.
- [2026-07-18-1756-v3-outputs-and-v4-access-policy.md](entries/2026-07-18-1756-v3-outputs-and-v4-access-policy.md) : on `feat/govcodegen-v4`, three slices. The two v3 secondary outputs: a real loadable marimo notebook (generated analysis as a reviewable `def analysis(ctx)` + governance context) and a Quarto `.qmd`/PDF render path (honest fallback where no `quarto` binary). Then two v4 items: the purpose-by-dataset matrix (`CTL-PURP-01` refuses credit-data-for-marketing at Access, wired into the flow) and autonomy tier resolution (`tier = min(class ceiling, person ceiling)`, both binding, demonstrated live in the Access tab). 293 tests, ruff clean. Pushed, no PR yet, prod untouched. Deferred: OPA, L3+synthetic_its, the frozen-L2 flow rewrite + L1/L3 execution routes.
- [2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md](entries/2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md) : the first prod deploy crashed on import (`ModuleNotFoundError: sqlglot`); `requirements.txt` was a stale `uv export` missing `fairlearn`/`sqlglot`/`duckdb`/`openlineage-python`, and health 200 hid it because that endpoint answers before app.py runs. Regenerated `requirements.txt`, redeployed (`8aeccba`, bundle `sentinel-20260718-073829.zip`), and smoke-tested all three surfaces on the live instance: the full flow runs (Execute passes = sqlglot+DuckDB in prod), the evidence pack renders, and the registry's CTL-SOD-01 self-signoff refusal fires live. Lesson: a deploy is verified when a page renders, not when a probe returns 200.
- [2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md](entries/2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md) : both PRs merged to main (PR #1 v0/v1, then PR #2 v2/v3 retargeted onto main), main at `4692c7c`, feature branches deleted, local main synced. Then deployed: prod moved from `9dcd20b` to `4692c7c`, EB green, health 200 over HTTPS, confirmed by source bundle key `bundles/sentinel-20260718-071819.zip`, live-LLM still on. The governed-codegen rethink is now the public artifact. Still out: marimo, Quarto-PDF, all of v4.
- [2026-07-17-2332-v2-and-v3-built-and-verified.md](entries/2026-07-17-2332-v2-and-v3-built-and-verified.md) : v2 (platform) and v3 (oversight) built and verified in-browser on `feat/govcodegen-v2` (PR #2). ctx.sql + sqlglot gate on DuckDB, the certification lifecycle with the refused-agent demo, the scaffolding CLI, CTL-CONTRACT-01 pinned honestly; the Attest evidence pack with the negative statement, CTL-SOD-01 on signoff, and OpenLineage events. 251 tests. Deferred: marimo, Quarto-PDF, all of v4 (forks: OPA, L3/synthetic_its). Prod untouched.
- [2026-07-17-2230-v1-slice-complete-and-verified.md](entries/2026-07-17-2230-v1-slice-complete-and-verified.md) : v1 is done and verified in the browser. Live code generation + the gateway repoint, the govflow orchestration (Ask to Interpret), the Console and Gate screens, and the seeded adversarial set. Webhook blocks at CTL-EGRESS-01 line 10; n=6 band suppressed before narration; proxy flagged. Gate true-block 100%, false-block 0%. 183 tests, PR #1, prod untouched.
- [2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md](entries/2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md) : first code since the rethink. v0 (CTL-SOD-01) shipped; v1 deterministic core built (the ast gate, the Screen with CTL-DISC-02 + CTL-PROXY-01, the sandbox with CTL-TIME-01); fairlearn reinstated in ml/fairness.py. 164 tests, all on PR #1. Prod untouched.
- [2026-07-17-2102-build-greenlit-v0-then-v1.md](entries/2026-07-17-2102-build-greenlit-v0-then-v1.md) : the rethink is accepted; building starts. A clarification pass on the PRD changed nothing. Model card survives as the Attest evidence pack. Order locked: v0 (SoD fix) then v1 (the vertical slice). Live LLM from the start, feature branch per slice. Branch created, no code yet.
- [2026-07-17-1940-govern-the-llm-not-sklearn.md](entries/2026-07-17-1940-govern-the-llm-not-sklearn.md) : the rethink. The harness audits scikit-learn, not the LLM. Autonomy ladder, proxy discrimination, a confirmed SoD defect, fairlearn back in. Docs only, no code.
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

- [2026-W29-summary.md](weekly/2026-W29-summary.md) : the rethink-and-rebuild week. Monday shipped the platform (AWS deploy + HTTPS, the 13-item buildout, pgvector on real AWS); Tuesday turned on live-LLM in prod. Friday's rethink found the harness was governing scikit-learn, not the LLM, and reframed the project around governing generated code via an autonomy ladder (tier = role x data class). v0 through v6 built and deployed across the weekend; by Sunday the mockup was the app and prod served a unified governed code-writing platform. Two beliefs flipped: the segfault was pyarrow not OpenBLAS, and "health 200 means deployed" died.
- [2026-W28-summary.md](weekly/2026-W28-summary.md) : the founding week. Sentinel went from nothing to a working governed app in one day (Sun 2026-07-12): real ML, six-module harness, human gate, six-tab UI.

## Working hypotheses

- Health 200 is necessary but not sufficient to call a deploy verified: Streamlit's health endpoint answers before app.py runs, so an import crash returns 200 while every page is broken (this happened 2026-07-18). Verify a deploy by loading a page and running a flow, not by probing health. And requirements.txt is a second dependency list that drifts from pyproject/uv.lock unless something regenerates it; the fix is to generate it at deploy time or diff it in CI.
- A naturally-flagging fairness result is more convincing than a staged one. Keep it real. This now extends to the gate: if the demo shows generated code being blocked, the block must be genuine, never seeded.
- The evidence pack with its "what this does not say" block is now built (v3) and is the showpiece the model card PDF pointed toward. The negative statement is assembled from what the run did (the suppressed band, the flagged proxy), not from boilerplate, which is what makes it more than a dashboard. The model card PDF survives as prior art.
- A control is only credible if it can be seen firing. Force RBAC and PII to fire every run.
- A control that can never fire is decoration. `CTL-CONTRACT-01` (dataset drift) cannot fire against static CSVs; say so rather than demo it. Built in v2 exactly this way: the contract is pinned to the real dataset SHA, the mismatch path is proven only in a test, and the pin test fails CI if the CSV ever changes. No fake drift is staged.
- Governance that blocks legitimate work gets routed around. The false-block rate matters as much as the true-block rate, and a demo that ignores it is not credible to anyone who has shipped internal tools.
- The artifact is evidence of judgment, not the case itself. The KRAs are organisational and no amount of building closes that gap.

## Open questions

- Which comes first, `ctx.sql` or `ctx.table`? Resolved for v1: `ctx.table`, because v1's done-when (a webhook caught at the gate, an n=3 cell suppressed) needs no SQL. `ctx.sql` plus the sqlglot row-filter rewrite is the more recognisable governance demo and lands in v2, where `CTL-COMPLEX-01` and `CTL-CONTRACT-01` also live.
- Is `n < 10` the right small-cell floor? It is the common default, but a real bank sets it per data domain. Now a `floor` parameter on the Screen (default 10) rather than a hardcoded constant, which is the right shape; making it a per-domain policy value is the OPA argument, still open.
- Where does drift monitoring live? Evidently is on the dependency map with no stage in the lifecycle.
- ~~Should linear analysis runs feed the adoption metrics and model registry?~~ Resolved 2026-07-19 (H phase). Linear analysis, govflow, and L3 runs now feed the adoption totals and the weekly/per-dataset cuts via the seeded run-history store. The model registry stays scoped to credit_risk runs only, since it is a model inventory and only that path promotes a model. Per-agent invocation counts are likewise scoped to the credit pipeline.
- Retrieval ranking: the SR 11-7 query ranks the internal modeling standard above the SR 11-7 document itself (SR 11-7 chunks still return at ranks 2-3). Worth a later look at chunking or reranking.
- ~~`synthetic_its` is registered but has no onboarder~~ Resolved: onboarded in v4 (generated with a known +12 effect), and in v6 (2026-07-19) it gained CAP_TABULAR so profiling is legal on it too. It is the Public-class L3 home.
- Demo GIF/Loom for the README: dropped for now per Sandip (2026-07-14).

## Things ruled out

- Next.js + FastAPI split (chose Streamlit for speed). Revisited 2026-07-17 and reaffirmed, now on stronger grounds than speed. The runtime is Python end to end and load-bearingly so: the gate parses generated Python with `ast`, the sandbox runs Python, the allowlist is a list of Python imports, and every DS library (fairlearn, statsmodels, DoWhy, lifelines, SHAP, ydata-profiling, sqlglot, Presidio) is Python-only. "Node entirely" would mean reimplementing fairlearn in TypeScript, which is the exact thing the thesis says not to do. "Node + FastAPI" is the prioritization trap: nobody hires an SVP AI PM for a React frontend, and spending three weeks there instead of the gate demonstrates the bad prioritization the role screens against. The demo has three surfaces, not two, and the split is already made: Streamlit (Console + Gate), marimo (DS output), Quarto (leadership doc). Streamlit is also a real deploy target (Databricks Apps, Snowflake), so "how would this productionize" is a one-sentence answer. The real friction is `app.py` at ~1,100 lines with a hand-rolled router and no `pages/`; the fix is Streamlit's native multipage, not a framework switch. Full reasoning in PRD 10.7. The one thing that could reopen it (editing code at the gate) is a v2 design question, not a framework one.
- Mocked codegen during development (chose live from the start, 2026-07-17). The code-generation step calls the real model throughout dev, with the cumulative spend cap as the backstop. Fixtures would harden the gate against code I wrote, not against code the model writes, which is the wrong target.
- Direct-to-main for the build (chose a feature branch, 2026-07-17). Work goes on `feat/governed-codegen` with a PR per slice. A clean reviewable history is worth more on a credibility artifact than a fast one.
- ~~fairlearn dependency~~ (reversed 2026-07-17, now wired). Adopting fairlearn. The original call was to hand-roll the metrics for auditability. Under the new thesis ("I govern off-the-shelf tools") that inverts: hand-rolling the one metric a regulator cares most about undercuts the pitch. Governing fairlearn is more on-message than reimplementing it. Done: `ml/fairness.py` now governs a `MetricFrame`, `fairlearn` is a base dependency, all fairness tests still green.
- **Segregation of duties is not enforced today (confirmed defect, 2026-07-17; fixed in v0 the same day).** Not a decision, a bug, recorded here so it is not rediscovered. `approve()` checked `actor.can_approve`, which is a role check, not an identity check. `RunState` never stored who started the run, so author and approver could not be compared. `mrm_approver` held both `can_run` and `can_approve`, so the same persona could approve its own run; so could `admin`. The docstring called it "the segregation-of-duties control." It was not one. v0 fixed it: `started_by` on `RunState`, `CTL-SOD-01` in `approve()`, and the second line lost `can_run` while admin lost `can_approve`. Shipped on PR #1.
- Prompt screening as the defence against proxy discrimination (ruled out 2026-07-17). Intent is easy to disguise, the analyst's intent is usually innocent, and the output discriminates regardless of what was asked. It also gives false comfort, which is worse than no control. The control is empirical and post-execution instead: measure association between granted features and the protected attribute at Screen, and flag rather than refuse, because business necessity is Legal's call.
- Thumbs up/down on generated code as adoption telemetry (ruled out 2026-07-17). In a governance product a thumbs-down usually means "the gate blocked me," which may be the system working. The instrument cannot separate "this is bad" from "this correctly stopped me," and optimising a control layer for satisfaction points one way: loosen the controls. Measure abandonment-after-block by control ID instead.
- ~~LangGraph~~ — reversed 2026-07-13. Adopting LangGraph for the platform buildout. Its graph is static (fixed nodes/edges), so it stays an inspectable workflow, and its interrupt/checkpointer primitives map onto the human gate and memory. The plain state machine was right for the single-pipeline demo, wrong for the platform.
- OpenMP/BLAS thread pinning as the crash fix (tested, did nothing, removed). The real fix is the pyarrow memory pool.
- FRED data (macro time-series does not fit the classification/fairness story).
- Render and Fly for the host (chose AWS Elastic Beanstalk).
- AWS Amplify (Hosting only runs JS frontends; it cannot run a persistent Python Streamlit server).
- A custom nginx override on EB (the default AL2023 nginx already forwards WebSocket upgrade headers).
- Executing the credit-risk spec through the linear analysis engine (decided 2026-07-14: it stays in the LangGraph orchestrator). The pipeline promotes a model and holds a human approval gate; the linear engine is for read-only analyses. Unifying execution would mean rebuilding LangGraph's interrupt/checkpointer primitives in the engine and risking the hero pipeline's gate. The catalog already unifies the two as specs; only execution differs, by design.
