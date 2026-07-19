# 2026-W29: The rethink and the rebuild, govern the LLM not scikit-learn

Week of Mon 2026-07-13 through Sun 2026-07-19. Previous week: [2026-W28-summary.md](2026-W28-summary.md).

## The week in one paragraph

The week started by finishing what W28 built and ended by tearing out its
premise and rebuilding on a better one. Monday shipped the platform: a deploy to
AWS with HTTPS on a custom domain, then a thirteen-item platform buildout
(LangGraph, personas, gateway ledger, registry, RAG on real pgvector, MCP,
memory, runtime, traces) and an analysis-spec engine. Tuesday turned on live-LLM
narration in prod and onboarded two more datasets. Then Friday I stopped
building and rethought the whole thing, and the rethink held: the governance
harness was auditing scikit-learn, not the language model, because the model
only narrated at the end and never touched anything. The fix moves the model
upstream to write the analysis code and puts a static-analysis gate between
generation and execution, organised around an autonomy ladder where policy
computes the tier from role times data class rather than letting anyone choose
it. From Friday night to Sunday I built it: v0 through v6, each a PR, each
deployed. By Sunday the mockup was the app and prod served a unified, governed,
code-writing platform. The governance is the product now, and it finally governs
the model.

## What happened

Monday 2026-07-13 was the platform day. First the segfault that dogged W28 got
re-diagnosed: it was pyarrow's mimalloc allocator, not the OpenBLAS threading I
blamed on Sunday. The single fix is `ARROW_DEFAULT_MEMORY_POOL=system`, and all
the OpenMP pinning came out as cruft. Then the build went public and live: a
clean per-phase git history, the repo on GitHub, and AWS Elastic Beanstalk
behind CloudFront with HTTPS on sentinel.sandip.dev. On top of that came the
platform reframe, from single governed pipeline to the platform that makes every
agent governed. All thirteen proposed items landed the same day: the LangGraph
orchestrator with a rendered DAG, five identity personas, the gateway as a
control point with its ledger, a control on/off toggle, a model registry,
adoption metrics, RAG with cited compliance, a runnable MCP server, memory with
retention, a runtime boundary, and OpenTelemetry traces. The RAG store moved to
real AWS: RDS pgvector plus Bedrock embeddings, with a local fallback so the
public link never breaks. An analysis-spec engine arrived too, running read-only
analyses through the same harness as the hero pipeline.

Tuesday 2026-07-14 fixed a quiet lie and added breadth. Live-LLM narration had
never actually run: the anthropic SDK was never installed, so the gateway
silently served scripted text. Fixed behind an optional extra and enabled in
prod behind a cumulative $50 cap, with the key riding in through a NoEcho
parameter read from a gitignored .env. ULB credit-card fraud and LendingClub
were onboarded through no-account substitutes, and Ragas faithfulness stopped
being a stub, implemented directly on the SDK and scoring a stable 1.0.

Friday 2026-07-17 was the hinge. Nothing shipped but documents, and the
documents were the point. The finding: turn the LLM off and every control still
passes, because the model writes prose about numbers already computed and never
touches anything. The interview question is whether I can put a language model
between a data scientist and a bank's customer data, and the honest answer to
how LLMs help data scientists is that they write the code. So the artifact has
to govern generated code before it executes. The organising idea is an autonomy
ladder: L0 explains, L1 picks a certified analysis and fills typed params, L2
writes code against a fenced API, L3 improvises in a sandbox, and the tier is
computed from who you are times how sensitive the data is, never chosen.
Fact-checking the proposal against the code found a real defect, the embarrassing
kind: `approve()` did a role check, not a segregation-of-duties check, and
`RunState` never stored who started the run, so a persona could approve its own
run. Filed as v0. Two more calls: proxy discrimination became the sharpest
control, measured empirically post-execution rather than by screening prompts,
and fairlearn came back in, because governing an off-the-shelf tool is more
on-message than hand-rolling it.

Then the build, fast. v0 fixed segregation of duties (CTL-SOD-01). v1 was one
vertical slice, Generate to Gate to Execute to Screen at L2 on german_credit,
with the ast gate catching a webhook at CTL-EGRESS-01 and the Screen suppressing
an n=6 band and flagging a proxy. v2 was the platform claim: `ctx.sql` parsed by
sqlglot on DuckDB, the certification lifecycle with a genuinely refused agent,
the scaffolding CLI, and CTL-CONTRACT-01 pinned honestly to a dataset SHA. v3
was oversight: the Attest evidence pack with its "what this does not say"
negative statement assembled from what the run actually did, OpenLineage events,
and a Quarto export.

Saturday 2026-07-18 merged v0 through v3 to main and deployed. The first deploy
crashed on import: requirements.txt was a stale uv export missing fairlearn,
sqlglot, duckdb, and openlineage, and health 200 hid it because the endpoint
answers before app.py runs. Regenerated, redeployed, and smoke-tested by loading
pages and running a flow, not by probing health. Then v4 added breadth: the
purpose-by-dataset matrix (CTL-PURP-01 refusing credit data for marketing), the
full L0-to-L3 ladder with the tier computed and routed on, synthetic_its
onboarded with a known +12 effect as the Public-class L3 home, and the two
secondary outputs, a loadable marimo notebook and a Quarto PDF path. L3 widens
the allowlist to whole packages but keeps the egress, filesystem, and
dynamic-code deny lists exactly as at L2: more rope, same hard limits. The
benign L3 difference-in-differences recovers +11.9; three adversarial L3
requests are refused. v4 merged and deployed the same evening.

Sunday 2026-07-19 made it an app. v5 turned the flow into a nine-stage
show-and-tell stepper with control explainers, struck and masked denied columns,
a Screen before-and-after, and a Gate "fix it" repair, then dressed the stepper
and chrome in the unified-app design system from the mockup and docs/ui-spec.md.
v6 made the mockup the real app across three workstreams: all eight datasets
onboarded (the lying `onboarded` flag deleted, synthetic_its given CAP_TABULAR),
a real seeded run-history store fed by nineteen actually-executed runs replacing
the fictional registry rows, and a login persona gate, a grouped sidebar with
live counts, and a command-center landing with live tiles. A 25-agent
adversarial review confirmed nine findings, all fixed, the sharpest a misleading
adoption number on the landing tile. v6 merged and deployed to prod, verified by
a governed flow run on the instance.

## State at end of week

Prod at sentinel.sandip.dev serves v6: the unified app, all the governed-codegen
surfaces, the autonomy ladder L0 to L3, and the platform substrate underneath.
374 tests pass, ruff clean. The whole arc v0 to v6 is merged to main and
deployed. Live-LLM is on behind the cumulative $50 cap. The only feature
explicitly waiting on me is OPA externalisation; dark mode, RBAC-gated
navigation, and B-style contextual drawers are deferred by choice.

## Beliefs that changed

The segfault attribution flipped. W28 ended believing it was OpenBLAS threading
and said the attribution deserved more scrutiny. It was pyarrow's mimalloc
allocator. The thread pinning was tested, shown to do nothing, and removed.

The central belief of the project changed. W28 held that the ML stays small and
the governance harness is the star, and that stayed true, but the harness was
governing the wrong thing. It audited scikit-learn while the model narrated at
the end and escaped governance entirely. The reframe moves the model upstream to
write code and governs that. It is the difference between putting an audit log
around a pipeline and putting a language model between a data scientist and
customer data without losing the licence.

Two supporting reversals followed. fairlearn, ruled out on 2026-07-13 to
hand-roll metrics for auditability, came back in, because under the new thesis
governing an off-the-shelf tool is the point. And "health 200 means deployed"
died on Saturday: an import crash returns 200 because the health endpoint
answers before the app runs. A deploy is verified by loading a page and running
a flow.

One belief got reaffirmed on stronger grounds. Streamlit over Next.js plus
FastAPI was a speed call in W28. Now it is load-bearing: the gate parses
generated Python with ast, the sandbox runs Python, and every DS library is
Python-only. Reimplementing fairlearn in TypeScript is the exact thing the
thesis says not to do.

## Carry-overs into W30

- OPA externalisation, the one deferred item that needs my call (external policy
  server, still an open PRD question).
- Dark mode, RBAC-gated navigation, and B-style contextual drawers, deferred by
  choice.
- app.py is now large with a hand-rolled router; the noted fix is Streamlit
  native multipage, not a framework switch.
- Drift monitoring (Evidently) is on the dependency map with no lifecycle stage.
- Retrieval ranking: the SR 11-7 query ranks the internal modeling standard
  above the SR 11-7 document itself.
- The KRAs are organisational and no amount of building closes that gap. The
  artifact buys a more serious conversation; it does not win one.

## Daily entries from this week

- [2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md](../entries/2026-07-13-1610-pyarrow-segfault-openmp-cleanup.md)
- [2026-07-13-1650-git-history-and-aws-eb-deploy.md](../entries/2026-07-13-1650-git-history-and-aws-eb-deploy.md)
- [2026-07-13-1720-https-via-cloudfront-custom-domain.md](../entries/2026-07-13-1720-https-via-cloudfront-custom-domain.md)
- [2026-07-13-1821-platform-buildout-proposal.md](../entries/2026-07-13-1821-platform-buildout-proposal.md)
- [2026-07-13-1903-platform-phases-a-b-shipped.md](../entries/2026-07-13-1903-platform-phases-a-b-shipped.md)
- [2026-07-13-1949-all-thirteen-items-built.md](../entries/2026-07-13-1949-all-thirteen-items-built.md)
- [2026-07-13-2005-aws-vector-store-provisioned.md](../entries/2026-07-13-2005-aws-vector-store-provisioned.md)
- [2026-07-13-2237-analysis-platform-and-pgvector-prod.md](../entries/2026-07-13-2237-analysis-platform-and-pgvector-prod.md)
- [2026-07-14-0646-live-llm-narration-in-prod.md](../entries/2026-07-14-0646-live-llm-narration-in-prod.md)
- [2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md](../entries/2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md)
- [2026-07-17-1940-govern-the-llm-not-sklearn.md](../entries/2026-07-17-1940-govern-the-llm-not-sklearn.md)
- [2026-07-17-2102-build-greenlit-v0-then-v1.md](../entries/2026-07-17-2102-build-greenlit-v0-then-v1.md)
- [2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md](../entries/2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md)
- [2026-07-17-2230-v1-slice-complete-and-verified.md](../entries/2026-07-17-2230-v1-slice-complete-and-verified.md)
- [2026-07-17-2332-v2-and-v3-built-and-verified.md](../entries/2026-07-17-2332-v2-and-v3-built-and-verified.md)
- [2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md](../entries/2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md)
- [2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md](../entries/2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md)
- [2026-07-18-1756-v3-outputs-and-v4-access-policy.md](../entries/2026-07-18-1756-v3-outputs-and-v4-access-policy.md)
- [2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md](../entries/2026-07-18-1844-autonomy-ladder-complete-l0-to-l3.md)
- [2026-07-18-1859-v4-merged-and-deployed-to-prod.md](../entries/2026-07-18-1859-v4-merged-and-deployed-to-prod.md)
- [2026-07-19-0113-showtell-stepper-and-design-system.md](../entries/2026-07-19-0113-showtell-stepper-and-design-system.md)
- [2026-07-19-1011-unified-app-shell-datasets-history.md](../entries/2026-07-19-1011-unified-app-shell-datasets-history.md)
- [2026-07-19-1030-v6-deployed-to-prod.md](../entries/2026-07-19-1030-v6-deployed-to-prod.md)
