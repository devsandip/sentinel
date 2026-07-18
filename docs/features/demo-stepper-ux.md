# Demo stepper + show-and-tell UX: implementation plan

Feature branch doc. Foundational truth stays in [governed-codegen.md](governed-codegen.md)
and [PRODUCT_BRIEF.md](../../PRODUCT_BRIEF.md); this file is the plan for the UX rework
requested in `docs/more_ideas.md`.

## 0. The problem, in one line

Sentinel has every control it claims, but the demo hides them. The governed run
executes behind a single spinner and lands as a static horizontal ribbon of nine
already-completed stages. The interviewer never watches a control fire. The brief:
turn the nine stages into an explicit, steppable, show-and-tell walkthrough where
each stage is a screen the user steps into, every control that fires is clickable
and explained, and the whole thing looks like product, not an internal tool.

The machinery does not change. The **surfacing** of the machinery changes.

## 1. Decisions (the real forks)

| Decision | Options | Call |
|---|---|---|
| The nine stages | Keep the one-shot ribbon / Replace with a guided stepper | **Guided stepper is the primary surface.** Keep a "fast run" fallback behind a toggle for power use, but the default governed-codegen experience is the walkthrough. |
| The header chips (Governance / PII / RBAC / Audit / Human Gate / Eval Gate) | Keep static / Make interactive / Drop | **Replace the six vanity chips with two things.** Today they are hardcoded strings bound to nothing (`app.py:128-137`). (a) Live run-context chips (persona, dataset + classification, purpose, computed tier) that reflect the actual run and are clickable to the relevant stage or control. (b) A single "Controls" button opening the full control plane: every control grouped by stage, its fired/idle state on this run, and, for the Platform Admin persona only, an audited toggle. Toggling a control must visibly change the run (turn off `CTL-DISC-02` and the suppressed n=6 band survives on Screen) or the toggle is decoration. A chip that means nothing is worse than no chip. |
| Run model | Re-run per stage / Compute once, reveal progressively | **Compute once, reveal progressively.** The flow already computes all nine stages and returns a `GovernedRunResult` carrying every stage's artifact. The stepper walks that finished object one stage at a time. The only genuinely live moment is Interpret under the live-LLM toggle, which can stream at that step. |
| Mockup vs. build | — | This plan ships with a clickable HTML mockup (`docs/mockups/`) as the design target. The Streamlit build follows the mockup; where Streamlit cannot match it exactly, the plan says so. |

## 2. Architecture in Streamlit

Streamlit is staying (the choice is defended in governed-codegen.md 10.7). The stepper
is built on top of it, not around it.

**State.** One new session key, `stage_index` (0..8), plus the existing
`govflow_result`. The run still executes once on "Run governed analysis" and stashes
`GovernedRunResult.to_public_dict()`. The stepper reads `stage_index` to decide which
stage panel to render.

**Stepper header.** A custom-CSS component (injected HTML, not `st.tabs`) rendering the
nine stages as a numbered progress rail with per-stage status states
(done / active / blocked / flagged / skipped) and a progress fill. Stage labels are
clickable to jump; Next / Back buttons advance `stage_index` and `st.rerun()`. This
replaces the flat `st.columns` ribbon in `_govflow_console` (`app.py:851-860`).

**Stage panels.** Nine functions, `_stage_ask` … `_stage_attest`, each rendering that
stage's own artifact from the result object. Most artifacts already exist on the
result; three stages need the flow to stop discarding data (Section 4).

**Chrome.** Hide the Streamlit menu/footer, set a `page_icon`, inject the wordmark +
shield lockup and the type system (Section 6). This is the single biggest "looks like
product" lever.

## 3. Per-stage screen spec

Each stage screen shows: what came in, what the stage did, which controls fired (as
clickable chips), and what went out. The hero run is the certified Analyst on
`german_credit`, fair-lending review, tier L2.

### Stage 1 — Ask (split into three sub-steps)

The brief asks Ask to become three obvious steps:

1. **Import dataset.** A dataset card for `german_credit`: Restricted, 1000 rows,
   CC BY 4.0, capabilities tabular/target/protected. Include the classification table
   the user already likes (dataset / class / fair-lending / credit-risk columns).
2. **Select purpose.** A purpose picker backed by the purpose-by-dataset matrix row for
   `german_credit`: fair-lending ✓, credit-risk ✓, quality ✓, fraud ✗, marketing ✗,
   causal ✗. Selecting a ✗ purpose (marketing) previews the `CTL-PURP-01` refusal live.
   Default: fair-lending review.
3. **Pick question.** Pre-built questions only (no free-text box, per the brief). The
   benign hero question is default: "Does the model decline older applicants more often,
   holding income constant?" Offer one adversarial question to demonstrate a later gate
   refusal.

Ask output: identity bound and tier computed. Render the tier as
`min(classification ceiling, person ceiling)` = `min(Restricted -> L2, analyst+certified
-> L2)` = **L2**, with the rationale sentence. Controls armed here: `CTL-TIER-01`
(entitlement), `CTL-PURP-01` (checked at Access).

### Stage 2 — Plan

- **Agent card:** `fair-lending v1.4`, status certified (green), with author / owner /
  validator and faithfulness score.
- **Only certified agents are selectable.** Show the draft `cohort-retention v0.3`
  greyed out with the two reasons it cannot be chosen: `CTL-EVAL-01` (faithfulness 0.72
  below the 0.90 floor) and `CTL-SOD-01` (names its own author as validator).
- **Data contract panel:** `certified_sha` vs `current_sha`. On the static demo data
  they match, so `CTL-CONTRACT-01` shows "pinned" green. Note honestly that drift cannot
  fire on static CSVs.
- **Params form** pre-filled with defaults so the user clicks straight through.

### Stage 3 — Access

- **Scoped table preview.** Granted columns present: `age_band`, `y`, `pred`,
  `credit_amount`, `duration_months`, `digital_engagement_score`.
- **Denied columns shown, not hidden.** Render `applicant_email`, `applicant_ssn`
  (PII, denied to everyone), `personal_status_sex` (proxy for sex), and the remaining
  non-granted columns with the name struck through in red and the cell data masked, each
  with a one-line reason. This is the brief's "mark in red, strike out, mask the data,
  add commentary" instruction, and it dramatizes "enforcement by construction: the denied
  column is absent, not hidden."
- **Purpose decision:** permitted (fair-lending). Controls: `CTL-RBAC-01`,
  `CTL-RBAC-02` (identity row filter applied, injected after generation so the model
  cannot remove it), `CTL-PURP-01` (pass), `CTL-CONTRACT-01`.

### Stage 4 — Generate

Show the generated Python against the fenced `ctx` API, labeled live or scripted. State
plainly that generating is not dangerous, running is. Set up the Gate: the first
generation reliably includes a webhook POST (network egress), which Gate will catch.

### Stage 5 — Gate

- Code with line numbers; the offending line (the egress call) flagged red with
  `CTL-EGRESS-01`.
- The two-parser explainer: Python `ast` (imports, egress, dynamic exec, dunder escapes)
  and `sqlglot` (columns, `SELECT *`, join shape). Neither reads the other's language.
- Violations listed with control id + line + message.
- **"Fix it" button** (the brief's exact ask): regenerate with the failure fed back,
  land attempt 2, show the pass banner. Real regenerate loop, capped at 3 attempts, then
  handed to a human.

### Stage 6 — Execute

Explain the sandbox as a capability boundary: subprocess with no network namespace,
read-only filesystem, memory and wall-clock caps (15s), `CTL-TIME-01`. Say the honest
limit out loud: a subprocess stops a language model doing something dumb, not a
determined attacker. Show `wall_clock_s`, the OK status, and the raw pre-screen emitted
table (the "before" for Screen).

### Stage 7 — Screen

- **Before / after, side by side.** Before includes the 71-75 band (n=6). After has that
  row struck through in red and removed, with `min_cell_before=6`, `min_cell_after=12`.
  The brief is explicit: show the suppressed band struck out, do not silently delete it.
- **Checks, each explained:** `CTL-DISC-01` (k-anonymity floor breached, so it fired),
  `CTL-DISC-02` (small-cell suppression n<10, the 71-75 band), `CTL-DISC-03` (PII scan),
  `CTL-PROXY-01` (digital_engagement_score is a candidate proxy for age_band, correlation
  ratio eta = 0.92, above the 0.5 threshold; flagged, not refused, because business
  necessity is Legal's call).
- Result numbers: selection rate by surviving band (18-25: 0.32, 26-35: 0.21, 36-45:
  0.16, 46-55: 0.23, 56-65: 0.26, 66-70: 0.25). Gap 0.16, 2.0x, 95% CI 0.08 to 0.2435.

### Stage 8 — Interpret

Step into the model writing. Scripted case: a "Generating..." shimmer, then the
narration. Live case: real streamed tokens. The narration must be descriptive, not
a one-liner: three short paragraphs (the finding and the disparity in fair-lending
terms; the confidence interval and the proxy caveat; then the honest cautions,
association-not-cause and bands-suppressed-below-the-floor). Then the faithfulness
verdict: `CTL-EVAL-01`, narration built from screened numbers only so it
structurally cannot state a rate for the suppressed 71-75 band.

### Stage 9 — Attest

The brief says this stage is mostly good; add polish and the control drill-downs.
Evidence pack: finding (gap 0.16, 2.0x, 95% CI 0.08 to 0.2435), provenance chain
(run_id, dataset_sha, tier, purpose, author, code), controls attested as chips, the
"what this does not say" negative statement, signoff pending with `CTL-SOD-01` (approver
may not be author), the OpenLineage events, and the Quarto `.qmd` + marimo `.py`
downloads.

## 4. Flow changes required

Six of nine stages already expose everything the UI needs. Three discard data the new
screens must show. All changes are additive optional fields on `GovernedRunResult`,
low risk.

| Stage | What is discarded today | Change |
|---|---|---|
| Ask | `TierDecision` (classification_ceiling, person_ceiling, rationale) survives only as prose in `StageRecord.detail` | Add `tier_decision: TierDecision \| None` field + `TierDecision.to_dict()`; surface in `to_public_dict()`. |
| Plan | `RegistryEntry` and `ContractCheck` (certified_sha, current_sha, drifted) are local vars | Add `plan_entry: dict \| None` and `contract: dict \| None`. |
| Access | The scoped `DataFrame`, the denied-column set (never computed), and `PurposeDecision` are local | Add `scoped_preview: list[dict]`, `granted_columns`, `denied_columns` (dataset columns minus grant, tagged with reason), `purpose_decision: dict`. |
| Generate | `to_public_dict()` surfaces only `live` + attempt count, not per-attempt code | Widen the `generation.attempts` projection to `{attempt, code, passed, violations}` so the Gate "Fix it" loop can show attempt 1 vs 2. |

Already exposed, no change: Gate (`gate.violations[].line/.message`), Execute
(`execution.emitted`, `wall_clock_s`), Screen (`screen.suppressed`, `proxy_flags`,
before/after), Interpret (`narration` + faithfulness via `StageRecord`), Attest
(`evidence.to_public_dict()`, `lineage`).

### 4.1 Control-catalogue reconciliation (found during mockup fact-check)

Two catalogue inconsistencies surfaced while grounding the mockup against the code.
Both are documentation bugs, not code bugs, and are worth fixing when this ships:

- **`CTL-PURP-01` stage placement.** The code enforces purpose at Access
  (`flow.py:370-390`) and the mockup follows the code. But `governed-codegen.md`
  lists `CTL-PURP-01` under Ask in the catalogue (:766) and its Stage 1 section
  (:404). Reconcile the doc to Access, or state explicitly that purpose is *decided*
  at Ask and *enforced* at Access.
- **`CTL-PURP-02` is real but undocumented in the walkthrough.** The Access-stage
  "column outside purpose scope" control (`governed-codegen.md:767`) had no home in
  the UI; the mockup now uses it for the ungranted-columns row (previously
  mis-tagged `CTL-COL-01`, which is a Gate control). The built app should do the same.

**Break risk:** any test asserting exact `to_public_dict()` equality will see new keys.
Additive keys only; update those assertions. `run_l3_analysis` leaves `generation` and
`screen` None, so the L3 path needs the panels to fall back gracefully (L3 Screen has no
cells to suppress by design).

## 5. Cross-cutting components

- **Control drill-down.** Every `CTL-xx` chip, anywhere, is clickable and opens a side
  drawer: what the control is (plain English), why it fired on this run, what it did.
  Backed by the full control catalogue (already extracted). This is the brief's core
  "show and tell" ask and the single most reused component.
- **Suppressed-cell treatment.** A shared table renderer that, given a suppressed row,
  shows it struck through in red with the reason on hover, rather than dropping it. Used
  in Screen and any result table.
- **Denied-column treatment.** The Access variant: column header struck red, cell data
  masked, reason inline.
- **"Fix it" interaction.** Gate button that runs the regenerate loop and reveals the
  before/after code.
- **Interpret reveal.** Shimmer for scripted, streamed tokens for live.
- **Chip control panel.** The reimagined header chips: a panel listing every control
  grouped by stage, its fired/idle state on this run, and an admin-only toggle.
- **Per-stage engine bar (buy the maths, build the governance).** A slim strip at the
  top of every stage naming the off-the-shelf library doing the work at that stage
  (the maths we bought) beside the controls governing it (the governance we built).
  Ask and Plan are policy-only (no external library); Generate and Interpret are
  Claude; Gate is `ast` + `sqlglot`; Execute is DuckDB; Screen is fairlearn +
  `scipy.stats`; Attest is OpenLineage + Quarto + marimo. This makes the thesis
  legible at every step instead of asserted once.
- **The Stack surface.** A top-bar panel that lays out the whole stack as two columns:
  bought (the analytical libraries, what each does, at which stage) and built (the
  controls per stage). The showpiece is the Gate import allowlist rendered as the
  governed catalogue the model may reach for (numpy, pandas, scikit-learn,
  statsmodels, fairlearn, scipy, DoWhy, lifelines, SHAP permitted; os, subprocess,
  requests, socket, pickle, eval/exec denied). Honest footer for what is on the
  dependency map but not yet wired (Presidio, Evidently, OPA, pandera). Only claim
  libraries that actually run; the roadmap ones are labelled as such.

## 6. Polish layer

The interviewer's hangup is "internal-tools builder, no UI sense." These push hardest
against that:

- **Wordmark + shield.** "Sentinel" is a guard. Draw a shield/sentinel-post glyph
  (inline SVG) + a tracked-caps wordmark lockup. Set a real favicon. There is no logo
  today.
- **Type system.** A display face for the wordmark and headers, a clean sans for body,
  and a monospace for control ids, run ids, SHAs, audit rows, and code. Mono on the
  evidentiary layer alone materially raises "immutable ledger" credibility.
- **Card surfaces + elevation.** Replace the flat stacked layout with card surfaces,
  section rules, and a quiet elevation system on the existing neutrals.
- **Semantic amber.** Today there is only green (pass) and red (fail); "needs review"
  (the proxy flag, the pending gate) has to borrow. Add a warning tier
  (amber tint + border) to the palette.
- **Hide Streamlit chrome.** Remove the default menu, footer, and header so it stops
  reading as a Streamlit app on sight.
- **Dark mode.** A governance/security product reads well in dark; token-driven so both
  themes are first class. Optional, but it is a strong "finished product" signal.

Palette stays anchored on `#1e50a0`; the plan does not repaint the brand, it builds a
real system around it.

## 7. Phasing (call it v5)

1. **v5.0 Chrome + design system.** Wordmark, favicon, hidden Streamlit chrome, type
   system, card surfaces, semantic amber. No behavior change. Ships the "looks like
   product" win immediately.
2. **v5.1 Stepper shell.** `stage_index` state, the custom stepper header, Next/Back,
   nine empty stage panels reading the existing result object. The one-shot ribbon
   becomes the walkthrough.
3. **v5.2 Flow field exposure.** The four additive changes in Section 4 so Ask, Plan,
   Access, and the Gate "Fix it" loop have their data.
4. **v5.3 Show-and-tell components.** Control drawer, suppressed-cell and denied-column
   renderers, chip control panel, "Fix it", Interpret reveal.
5. **v5.4 Per-stage screens.** Flesh all nine using the components. Ask sub-steps last
   since they are the most layout-heavy.

## 8. What is mockup vs. real

The mockup is the fair-lending hero, fully clickable, with real hero-run numbers. It is
the design target and the interview demo prop. The Streamlit build wires the same screens
to the live `GovernedRunResult`. Numbers in the mockup are the real ones from the current
run, so the mockup and the built app should read identically on the hero path.
