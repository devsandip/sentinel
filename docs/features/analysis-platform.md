# Analysis platform — scope proposal

**Status:** proposal, deciding scope before building.
**Consolidates:** the discussion since "what are the use cases for agentic AI in
data science in fintech" — the use-case landscape, the analysis-as-pipeline idea,
the registry, and the verified dataset inventory ([datasets.md](datasets.md)).

---

## 0. The thesis

Sentinel today is one governed pipeline (credit-risk on German Credit). The next
step is a **governed analysis platform**: a library of governed analyses a user
applies to governed datasets, and (stretch) composes themselves. The point stays
the same — governance is the product — but it now scales across analyses and
datasets, which is what an AI *platform* PM is judged on.

This build is the intersection of two threads that turn out to be the same thing:

- The **use cases** we chose to build (the "lifecycle copilot" bucket): data
  discovery/access, EDA + data-quality triage, feature engineering, experiment +
  causal design. See [[agentic-ai-fintech-ds-usecases]] in memory.
- The **platform features** requested: a registry of agents + tools, 3-5 pre-built
  analyses, editable parameters, and (stretch) edit/save + build-your-own.

The use cases *are* the pre-built analyses. One build.

---

## 1. The unifying abstraction: analysis = declarative spec

An **Analysis** is a declarative spec, not hardcoded Python:

```
Analysis:
  id, name, description, playbook, pattern
  data_contract:            # what a dataset must provide to run this
    requires: [target | protected_attr | relational | treatment | timeseries | entity_id ...]
    min_rows, column_roles
  steps: [ordered]
    step:
      agent:  <registry role>          # LLM-driven actor (narrate/decide/interpret)
      tools:  [<registry tool ids>]    # deterministic capabilities (incl. ML/stat algos)
      params: {name: {type, default, bounds, editable}}
      inputs / outputs:  <typed contract>   # enables composition + validation
      gate:   human | eval | none
  controls: [rbac, pii, guardrails, eval_gate, human_gate]   # default all
```

The orchestrator becomes a **spec interpreter**: it validates the dataset against
`data_contract`, builds a LangGraph from `steps`, binds each step to the harness
(RBAC, audit, guardrails, controls, tracing), runs it, and produces the usual
surfaces (audit, traces, citations, registry entry). Every analysis inherits the
controls **by construction** — including user-composed ones.

Why this abstraction: the requested features are all points on one continuum, so
they share an engine instead of being five separate builds:

| Requested feature | Becomes |
| --- | --- |
| 3-5 pre-built analyses | ship 3-5 specs |
| edit agent params | the spec declares editable params → UI form (edits audited) |
| add/delete agents + save | edit spec steps, persist under a new name (contract-validated) |
| build your own pipeline | the same editor from empty |

---

## 2. Registry ontology (five types)

"Analysis algorithms are tools" is correct; the refinement is that the registry
holds five types, and algorithms live as tools (or tool parameters):

| Type | What | Examples | Status |
| --- | --- | --- | --- |
| **Agents** | LLM-driven roles | profiler, eda, modeler, validator, feature-engineer, experiment-designer, discovery | extend |
| **Tools** | deterministic capabilities (incl. ML/stat algos) | train_classifier(algo=logistic\|xgboost), compute_fairness, run_profile (ydata), run_expectations (pandera), dfs_features (featuretools), power_analysis, ab_test, causal_impact, retrieve_policy | extend |
| **Models** | trained, versioned artifacts | the model registry | have |
| **Analyses** | pipeline specs | the 5 below | new |
| **Datasets** | onboarded inventory + contracts + license + classification | the default set in datasets.md | new |

The platform surface becomes an **analyses × datasets matrix**: which analyses can
run on which datasets, gated by data contracts.

---

## 3. The governed data connector (the spine)

Shared by every analysis. `GovernedDataSource(role, dataset, table/query)` applies
table/column RBAC + PII redaction + license/classification checks + audit, and
returns only permitted, redacted data to the tool that consumes it (profiler,
Featuretools, a model). This is the "connect data-with-governance to an EDA tool"
piece — build once, reused by all analyses.

---

## 4. Pre-built analyses (the 5) and their datasets

| Analysis | Steps (agent + tools) | Dataset (contract) |
| --- | --- | --- |
| **Credit-risk model + fairness** (existing, converted) | profiler → eda → modeler(train_classifier) → [human gate] → validator(compute_fairness, run_eval_gate, retrieve_policy) | UCI Taiwan credit / German / Berka |
| **Data discovery + profiling/quality** | discovery(catalog + entitlements) → profiler(run_profile ydata) → quality(run_expectations pandera) | any dataset; showcase Berka (multi-table) + LendingClub (messy) |
| **Feature engineering** | feature-engineer(dfs_features featuretools, rfm_features) → leakage/stability checks → feature registry | Berka (relational) |
| **Experiment analysis** | experiment-designer(power_analysis) → ab_test → uplift → interpret | Hillstrom |
| **Causal impact** | causal(causal_impact / interrupted_time_series) → recover-known-effect check | semi-synthetic ITS + Prop 99 |

(Fraud/AML detection on ULB is a natural sixth, later.)

Each carries a **data contract**, so "applies to any dataset" is really "any
dataset that satisfies the contract" — validated before the run, and itself a
governance control (the per-analysis data-classification checklist).

---

## 5. Governance angles worth keeping

- **Controls by construction:** a user-composed analysis still runs through RBAC,
  audit, guardrails, the eval gate, and the fairness check. You cannot compose an
  ungoverned analysis. This is the paved-road thesis made literal.
- **Audited parameter edits:** lowering a fairness threshold or an AUC floor is a
  governance-relevant act; log it ("Analyst set fairness_threshold 0.80 → 0.65").
- **License enforcement:** datasets carry their license; the platform blocks
  commercial use where flagged (Criteo NC, unlicensed sources).
- **Contract validation:** prevents garbage runs and invalid user compositions.

---

## 6. Scope decision (this is the call to make)

Three ways to build, by ambition:

- **A. Full engine + builder.** Declarative specs + contracts + registry + the
  pipeline-builder UI. Most elegant, best interview story ("governed pipeline
  builder"), largest scope.
- **B. Curated analyses.** A few more hardcoded pipelines + a dataset picker +
  param editing. Fastest, covers the must-haves (pre-built + params), but no
  build-your-own and no uniform engine.
- **C. Engine now, builder later (recommended).** Build the declarative engine +
  contracts + registry + dataset onboarding, ship the pre-built analyses + param
  editing, and DEFER the builder UI. Gets the elegant, uniform foundation (so
  every analysis is governed-by-construction) without paying for the builder UI
  until the pre-built analyses land — at which point the builder is cheap.

**Recommended phases under C:**

- **2A — Engine + spine:** analysis-spec engine + data contracts; convert
  credit-risk to a spec (proves no regression); dataset registry + onboard the
  first datasets (UCI Taiwan, Berka, Hillstrom); five-type registry surfaced.
- **2B — New analyses:** data discovery + profiling/quality (governed connector +
  ydata-profiling + pandera), then feature engineering (Featuretools on Berka),
  then experiment + causal (statsmodels + tfcausalimpact). Fairness becomes its
  own analysis too.
- **2C — Configurability:** parameter editing with audited edits.
- **2D — Stretch:** edit/save, then the constrained build-your-own.

**Recommended first slice to build now:** 2A + the two most novel 2B analyses
(profiling/quality and feature engineering, which exercise the governed connector
and the multi-table dataset) + 2C params. That is a complete, demoable story:
pick an analysis, pick a contract-compatible dataset, tweak params, run it
governed. Fairness-as-analysis, experiment/causal, fraud, and the builder follow.

---

## 7. New dependencies (all pip-installable, mostly optional extras)

ydata-profiling (EDA), pandera (quality), featuretools (relational FE),
statsmodels (power/tests/ITS — already adjacent), tfcausalimpact (causal). Keep
heavy ones as optional extras where the deployed app does not need them.

## 8. Open decisions

1. Architecture: A / B / **C**?
2. First slice: as recommended (engine + profiling/quality + feature eng + params),
   or different?
3. Does the deployed public app grow to multiple datasets/analyses, or does that
   stay local while prod keeps the single credit-risk demo? (Affects deploy + the
   dataset download footprint on EB.)
