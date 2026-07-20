# Sentinel

**Live:** https://sentinel.sandip.dev

A public, clickable demo where a visitor picks a preset banking question, hits
Run, and watches a small team of AI agents perform a **real** data-science
analysis wrapped in the governance controls a regulated bank demands: an
immutable audit log, RBAC, PII redaction, a human-in-the-loop approval gate, an
eval gate, a fairness check, an auto-generated model-risk (model card) document,
and a cost/KPI readout.

The message it proves: agentic AI can be made governed, auditable, and shippable
in a regulated bank. Governance is the star; the ML is deliberately simple. See
[PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) for the PM framing (controls mapped to bank
KRAs, the metric tree, and the prototype-to-platform path).

## What it does

- One dataset end to end: UCI Statlog German Credit (1,000 loan applicants).
- Four agents plus an orchestrator: Profiler, EDA/Feature, Modeler, Validator.
- A live logistic-regression baseline: real AUC, accuracy, confusion, fairness.
- A full governance harness, with two controls that fire on every run (an RBAC
  denial and a PII redaction) and a fairness check that flags a real disparity.
- A Streamlit UI built around a nine-stage governed walkthrough (Ask, Plan,
  Access, Generate, Gate, Execute, Screen, Interpret, Attest), with the model
  inventory, the cross-run audit ledger and the manual beside it.

The analysis is always real (metrics change with the dataset and seed). Agent
narration is deterministic ("scripted") by default so the public link costs
about zero and cannot be abused; a Live LLM toggle routes narration through a
real model behind a cost cap, and the UI labels the mode honestly.

## Quick start

```bash
uv sync --extra dev
uv run python scripts/prepare_data.py        # build the named CSV from the raw source
uv run pytest -q                             # 36 tests
uv run python cli.py                         # ML core only (metrics + fairness)
uv run python demo.py                        # full governed pipeline in the terminal
./run.sh                                      # the full UI (stable launcher)
```

Open the UI at http://localhost:8501, pick a persona, open Run, confirm a
dataset and step through the nine stages.

Use `./run.sh` rather than a bare `streamlit run` on macOS: it pins BLAS/OpenMP
to one thread and disables the file watcher, which avoids a duplicate-OpenMP
crash seen with an Anaconda base Python. (The in-code `threadpoolctl` guard
already covers deploy hosts like Render, so no env var is needed there.)

## Architecture

```
sentinel/
  ml/          data.py, pipeline.py (real sklearn), fairness.py
  harness/     audit.py, rbac.py, pii.py, guardrails.py, eval_gate.py,
               cost.py, model_card.py
  gateway/     model_gateway.py (templated | anthropic | openai)
  agents/      base.py, profiler.py, eda.py, modeler.py, validator.py
  config/      rbac.yaml, questions.yaml, evals.yaml, agents.yaml
  orchestrator.py   LangGraph StateGraph + interrupt-based approval + run store
  data/        german_credit.csv
  ui/          screens/ (one module per sidebar screen), shell.py (nav + chrome),
               theme.py (the stylesheet), govflow.py (the Run walkthrough)
app.py         Streamlit entry point: boots the session and routes one screen
```

The pipeline (agents) and the control plane (harness) are separate modules.
Every agent action funnels through the harness: RBAC on column reads, guardrails
on tool calls, PII redaction before narration, an audit event, and cost
accounting. The orchestrator is a LangGraph StateGraph with a fixed topology and
an interrupt-based human gate, so the flow is inspectable via the audit log and
an examiner can read the whole path before any request takes it.

### A note on the launcher

On macOS, pyarrow's bundled mimalloc allocator segfaults (SIGSEGV, no Python
traceback) when Streamlit serializes a DataFrame to Arrow from its worker
thread. Setting `ARROW_DEFAULT_MEMORY_POOL=system` routes pyarrow to the system
allocator and fixes it; it must be set before pyarrow imports, so `run.sh` (and
`.claude/launch.json`, `render.yaml`) set it. That single env var is the only
mitigation needed. An earlier round of OpenMP/BLAS thread pinning was tried and
removed after testing showed it made no difference.

## Live LLM mode (optional)

Default is `templated` (zero external calls). To use a real model, install the
SDK and set a key, then flip the Narration toggle to Live LLM:

```bash
uv pip install anthropic   # or openai
export ANTHROPIC_API_KEY=...    # or OPENAI_API_KEY
export LIVE_MODE_MONTHLY_CAP=5  # hard dollar ceiling
```

If a live call fails or the cap is reached, the gateway falls back to scripted
narration and records why.

## Deploy

Single Streamlit web service. It is live on AWS; `render.yaml` and `Procfile`
are also included for a one-click Render deploy.

**AWS (current prod at https://sentinel.sandip.dev):** CloudFront terminates TLS
(valid ACM cert, WebSocket pass-through) in front of a single-instance Elastic
Beanstalk `t3.small` running over HTTP. Two idempotent scripts under
`deploy/aws/` own it:

- `AWS_PROFILE=admin ./deploy/aws/deploy.sh` — app code (CFN
  `deploy/aws/sentinel-eb.yaml` + S3 bundle bucket).
- `AWS_PROFILE=admin ./deploy/aws/enable-https.sh` — the HTTPS front (CFN
  `deploy/aws/sentinel-https.yaml`: ACM cert, CloudFront, Route 53 alias).

The distribution has two cache behaviors, and the split matters. The default one
carries the app: caching disabled, all viewer headers forwarded, because the
WebSocket at `/_stcore/stream` needs the upgrade headers passed straight
through. `/static/*` is separate: compressed and cached at the edge. Streamlit's
front end is 61 files and 2.5MB, content-hashed and immutable, and under the
default behavior every visitor pulled all of it uncompressed from the t3.small.
That was the six seconds of blank white on a cold load, not an EB cold start
(TTFB was under a second). The main chunk is 908KB and gzips 3.4x. Compression
needs both halves of that behavior: `Compress: true` alone does nothing under
the CachingDisabled policy, since CloudFront compresses what it caches and that
policy drops `Accept-Encoding` from the cache key.

**Render (alternative):** point a new Web Service at the repo; it reads
`render.yaml` (build `pip install -r requirements.txt && pip install -e .`,
start `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`), then
add a custom domain in the dashboard and set the CNAME at your DNS.

Default `MODEL_PROVIDER=templated` keeps the public link free.

## Deliverables

- [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) — the PM artifact.
- [docs/sample_model_card.pdf](docs/sample_model_card.pdf) — a generated model card.
- `SENTINEL-BUILD-SPEC.md` — the original build brief.
```
uv run python scripts/generate_model_card.py   # regenerate the sample card
```
