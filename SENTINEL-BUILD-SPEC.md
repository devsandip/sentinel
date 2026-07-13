# Sentinel — Build Spec (hand-off to Claude Code)

> **What this is:** a complete, self-contained build brief for **Sentinel**, a hosted demo web app. Hand this whole file to Claude Code and build it phase by phase. Owner: Sandip. Purpose: an interview credibility artifact for an **SVP, AI Product Management** role on a bank's **data science** team (agentic AI platform for a regulated environment).
>
> *(Project name spelled "Sentinel". If the owner wants "Centinel", find/replace.)*

---

## 0. The one-paragraph goal

Build a **public, clickable web app** at a custom domain where a visitor picks a preset banking question + dataset, clicks **Run**, and watches a small team of AI agents perform a **real data-science analysis** — wrapped in the **governance controls a regulated bank demands**: immutable audit log, RBAC + PII redaction, a human-in-the-loop approval gate, an eval gate, a fairness/bias check, an auto-generated **model-risk (model card) document**, and a cost/KPI readout. It must load fast, cost ~nothing to run publicly, and never fake the analysis.

**What it proves to interviewers:** the candidate doesn't just know agents can do data science — they know how to make agentic AI *governed, auditable, and shippable in a regulated bank.* That is the job.

---

## 1. Core principles (do not violate)

1. **The analysis is always real.** Layer-1 ML (pandas/scikit-learn) executes live on every run and produces genuine, reproducible numbers. Never hard-code or fake metrics, the model, fairness numbers, or the model card.
2. **Honesty about the LLM layer.** The agents' natural-language narration may be *templated* (deterministic) by default to keep the public app free and reliable; a **"Run live LLM"** toggle calls a real model. The UI must not claim live reasoning when narration is templated — label it accurately ("scripted narration over a live analysis").
3. **Governance is the star, not the ML.** Keep the ML deliberately simple (a logistic-regression baseline is fine). Spend effort on the harness and the UI that surfaces it.
4. **Cheap + bulletproof for a public link.** No login. No free-text prompt box (preset questions only). Live-LLM mode is rate-limited and cost-capped.
5. **Everything auditable.** Every agent step emits a structured audit event.

---

## 2. Scope

**In scope (MVP):**
- One dataset end-to-end (UCI **German Credit**), 3–4 preset questions.
- 4-agent pipeline: Data-Profiler → EDA/Feature → Modeler → Validator, plus an Orchestrator.
- Full governance harness (see §5).
- 6-tab web UI (see §6).
- Hosted on a custom domain.

**Non-goals (explicitly out):** production-grade ML; real bank data; user accounts/auth; a real database (use in-memory + JSON files); multi-dataset support at launch (design for it, ship one); actually training deep models.

---

## 3. Tech stack (default — swappable)

- **Backend:** Python 3.11, **FastAPI**. Holds the real ML (pandas, scikit-learn, optionally `fairlearn`), the agents, and the governance harness. Deploy to **Render** (free/starter) or Railway/Fly.
- **Frontend:** **Next.js (App Router) + TypeScript + Tailwind**. Deploy to **Vercel**; attach custom domain via CNAME.
- **LLM (optional live mode):** provider-agnostic gateway (OpenAI or Anthropic) behind an interface; default provider is `templated` (no external call).
- **Data:** bundle the German Credit CSV (public, UCI) in the repo.

**Simpler fallback (if the owner prefers one language / faster ship):** a single **Streamlit** app (Python only) on Render with a custom domain. Same backend logic; Streamlit renders the 6 tabs. Less polished, ~half the build effort. Only do this if asked.

---

## 4. Repository structure

```
sentinel/
├── README.md                  # setup + deploy + "what this is"
├── PRODUCT_BRIEF.md           # the PM artifact (see §10) — write this too
├── backend/
│   ├── main.py                # FastAPI app + endpoints
│   ├── orchestrator.py        # runs the agent graph, emits audit events
│   ├── agents/                # profiler.py, eda.py, modeler.py, validator.py
│   ├── ml/                    # pipeline.py (real sklearn), fairness.py
│   ├── harness/               # audit.py, rbac.py, pii.py, guardrails.py,
│   │                          #   eval_gate.py, model_card.py, cost.py
│   ├── gateway/               # model_gateway.py (templated | openai | anthropic)
│   ├── config/                # agents.yaml, rbac.yaml, questions.yaml, evals.yaml
│   ├── data/                  # german_credit.csv
│   └── tests/
└── frontend/
    ├── app/                   # Next.js pages
    ├── components/            # PipelineView, AuditLog, ModelCard, Fairness, KpiPanel, ApprovalGate
    └── lib/api.ts             # calls backend
```

---

## 5. The governance harness (the differentiator — build these as clean modules)

Each is a small, well-named module with a clear interface. Every agent action flows through them.

- **`audit.py` — Audit log.** Append-only JSONL. Each event: `{run_id, ts, agent, action, inputs_summary, data_touched, output_summary, tokens, cost}`. Immutable (never mutate past entries). Exposed to the UI.
- **`rbac.py` — Role-based access control.** `rbac.yaml` declares which columns/tables each agent may read. Attempted access outside the allow-list is blocked and logged. Demonstrate by denying an agent access to a restricted column.
- **`pii.py` — PII handling.** Regex-based detection/redaction (emails, phone, IDs) applied before any text would go to an LLM. Log redaction events. (German Credit has little PII — inject a synthetic PII field to demonstrate redaction working.)
- **`guardrails.py` — Tool allow-list + sandbox.** Agents may only call whitelisted tools; code execution (if any) is sandboxed/limited. Anything else is blocked + logged.
- **`eval_gate.py` — Eval-as-CI-gate.** A small golden set (`evals.yaml`) of question→expected-property checks (e.g., "AUC computed", "fairness section present", "model card has all required fields"). If checks fail, the run is flagged "blocked from promotion." Show pass/fail in UI.
- **`model_card.py` — Model-risk documentation generator.** From the real run, generate an SR 11-7-style model card: purpose, data lineage (dataset + version + transforms applied), methodology, performance (AUC/accuracy/confusion), **fairness results**, assumptions, limitations, intended use. Render in UI + downloadable **PDF**. ⭐ Showpiece.
- **`cost.py` — Cost + KPI tracker.** Tokens & $ per run (0 in templated mode), wall-clock cycle time, eval pass-rate, human-override count. Feeds the KPI tab.

**Human-in-the-loop gate:** the pipeline pauses after the Modeler proposes a model. Backend returns state `awaiting_approval`; frontend shows **Approve / Reject**; approval resumes the run. Log the decision.

**Model gateway (`gateway/model_gateway.py`):** interface `generate(prompt) -> text`. Providers: `templated` (returns pre-written narration keyed by step — default), `openai`, `anthropic`. Selected via env/config. This mirrors the real-world "model-agnostic gateway" talking point.

---

## 6. The ML core (real — `ml/pipeline.py`, `ml/fairness.py`)

On each run, for German Credit:
1. Load CSV → basic profiling (rows, columns, dtypes, missing, class balance).
2. Train/test split (stratified). Preprocess (encode categoricals, scale).
3. Train a **logistic regression** (baseline) predicting credit default (good/bad).
4. Metrics: AUC, accuracy, precision/recall, confusion matrix, top feature importances (coefficients).
5. **Fairness (`fairness.py`):** pick a protected attribute (e.g., age band, or `foreign_worker`/`sex` present in the dataset). Compute group metrics: selection rate, TPR/FPR, and a disparity ratio. **Exclude the protected attribute from the model features** and state this explicitly (responsible-AI signal). `fairlearn` is fine, or implement the few metrics directly.
6. Everything returned as structured JSON for the API + fed to the model card.

All numbers are computed live. Keep it fast (<2s).

---

## 7. Agents & orchestration (`orchestrator.py`, `agents/`)

Keep agents simple — each is a class with `run(state) -> state` that (a) does its job by calling the ML/harness tools, (b) emits an audit event, (c) produces a short narration via the model gateway.

- **Profiler** — profiles the dataset, flags class imbalance / data-quality notes.
- **EDA/Feature** — key distributions, correlations, proposes feature handling.
- **Modeler** — trains the baseline, reports metrics → triggers the **approval gate**.
- **Validator** — runs eval_gate checks + fairness review; flags issues (e.g., "disparity ratio exceeds 0.8 threshold — review").
- **Orchestrator** — sequences them, manages shared state + the approval pause, assembles the final payload.

Use **LangGraph** if convenient, or a plain Python state machine (simpler, fully owned — acceptable and arguably cleaner for a demo). The audit log makes the flow inspectable either way.

---

## 8. Datasets & preset questions (`config/questions.yaml`)

Ship German Credit + 3–4 presets, e.g.:
1. "Build a credit-default risk model for this loan portfolio and report performance."
2. "Is the model fair across age groups? Show disparity and how you controlled for it."
3. "Profile this dataset and flag data-quality risks before modeling."
4. "Generate the model-risk documentation for this model."

(Design config so a second dataset — e.g., PaySim fraud — can be dropped in later, but ship one.)

---

## 9. The UI — 6 tabs (`frontend/`)

Home: title, one-line pitch, dataset + question dropdowns, **Run** button, and a persistent header badge **"Governance: ON"** listing active controls (PII · RBAC · Audit · Human Gate · Eval Gate). A toggle: **Narration: Scripted / Live LLM**.

Tabs:
1. **Pipeline** — animated agent steps with status + each step's narration; the **Approve/Reject** gate appears inline at the Modeler step.
2. **Results** — charts (class balance, top features, ROC/confusion), model metrics.
3. **Audit Log** — live, timestamped, scrollable feed of every event (incl. an RBAC "access denied" and a PII "redacted" example).
4. **Fairness** — group metrics + disparity ratio, with the "protected attribute excluded from model" note.
5. **Model Card** — the rendered SR 11-7-style doc + **Download PDF**.
6. **Cost & KPIs** — tokens/$ (0 in scripted mode), cycle time, eval pass-rate, human-override count.

Keep the visual clean/enterprise (neutral palette, one accent). Mobile-friendly enough to open from a phone.

---

## 10. Deliverables beyond the app

- **`PRODUCT_BRIEF.md`** (1–2 pages) — the PM artifact. Sections: problem, the platform thesis, how each governance control maps to a bank KRA, the metric tree, and how this prototype scales prototype → enterprise platform. (This is what distinguishes an SVP-PM candidate from an engineer — write it.)
- **Sample model-card PDF** committed to the repo.
- **README** with a 60-second "what this is" + live demo URL + a short GIF/Loom placeholder.

---

## 11. Deployment (custom domain)

1. **Backend → Render:** deploy `backend/` as a FastAPI web service. Set env vars (`MODEL_PROVIDER=templated` default; optional `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`; `LIVE_MODE_MONTHLY_CAP`). Enable CORS for the frontend origin.
2. **Frontend → Vercel:** deploy `frontend/`. Set `NEXT_PUBLIC_API_URL` to the Render URL. Add the custom domain in Vercel → set the CNAME at the owner's DNS.
3. **Cost controls for live mode:** per-IP + global rate limit, a hard monthly token/$ cap, a cheap small model, short timeouts. Keys only in backend env (never client-side).
4. **Default = scripted narration**, so the public link costs ~$0 and can't be abused.

---

## 12. Build phases (do in order; each should run/tested before the next)

- **P0 — Scaffold:** repo structure, backend + frontend hello-world, CI lint/test.
- **P1 — Real ML:** `ml/pipeline.py` + `fairness.py` producing real metrics from German Credit via a CLI. Unit tests on metric shapes.
- **P2 — Model card:** `model_card.py` generating the doc + PDF from P1 output.
- **P3 — Harness:** audit, rbac, pii, guardrails, eval_gate, cost — with tests proving a blocked RBAC access and a redaction are logged.
- **P4 — Agents + orchestrator:** wire agents through the harness; emit audit events; implement the approval pause. Model gateway with `templated` provider.
- **P5 — API:** FastAPI endpoints: `POST /run` (returns run state incl. `awaiting_approval`), `POST /approve`, `GET /run/{id}`. Structured JSON payloads for all 6 tabs.
- **P6 — UI:** Next.js 6-tab app consuming the API; the Governance badge; the narration toggle.
- **P7 — Deploy + polish:** Render + Vercel + custom domain; capture the demo GIF; write `PRODUCT_BRIEF.md` and README; commit sample model-card PDF.
- **P8 (optional) — Live LLM:** implement `openai`/`anthropic` gateway providers behind the cap + toggle.

---

## 13. Definition of done (acceptance criteria)

- Public URL on the owner's domain loads in <3s, no login.
- Clicking Run executes a **real** analysis (metrics change if the dataset/seed changes) and pauses at a human approval gate.
- Audit Log shows every step incl. one RBAC "denied" and one PII "redacted" event.
- Fairness tab shows real group metrics; model card downloads as a PDF with all required sections.
- KPI tab shows cost (0 scripted) + cycle time + eval pass-rate.
- Scripted mode makes zero external LLM calls; live toggle works and is cost-capped.
- `PRODUCT_BRIEF.md` maps controls → bank KRAs.
- Nothing about the analysis is faked; narration mode is labeled honestly.

---

## 14. North-star reminder for the builder

Every decision serves one message: **"I can make agentic AI safe and shippable in a regulated bank."** When in doubt, invest in the *governance harness and its visibility*, not in fancier ML. The model card, audit log, human gate, and fairness check are the point.
