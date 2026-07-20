# Unified app build: shell, datasets, seeded history

The implementation plan for the next build phase. Three workstreams, matching
Sandip's goals: (1) build the mocked-up unified app into the real Streamlit app,
(2) finish dataset onboarding, (3) seed real run history per dataset so the
Registry and Adoption surfaces stop being empty-ish.

Sources of truth, in order:
- `docs/mockups/sentinel-stepper-mockup.html`: the pixel target for everything
  (login, dashboard, sidebar, run walkthrough, four surfaces, themes).
- `docs/ui-spec.md`: the WRITTEN design-system spec extracted from that mockup —
  every color token, layout rule, and component pattern in prose, independent of
  the HTML file. S0 below is literally "implement this doc."
- `docs/features/demo-stepper-ux.md`: the run-stepper spec (Sections 2-7: per-stage
  screens, the four additive flow fields, phasing v5.0-v5.4) and the shell decision
  record (Section 9.1, C-on-A). This doc turns 9.1 into a build plan and adds the
  two data workstreams.
- This doc: the shell phases (S0-S4), the dataset work (D0-D2), the seeding design
  (H0-H3), and the build order.

All facts below were verified against the code on 2026-07-18 (file:line refs
inline). Re-verify anything load-bearing before building on it.

---

## 1. Workstream S: the app shell

Today's nav is a `st.sidebar.radio("Section", ...)` at `app.py:1728-1740` with 7
options dispatching to `render_*` functions, and `persona_picker()` (a selectbox)
below it. The shell replaces this with the mockup's structure. The four surface
renderers (`render_platform` ~1158, `render_registry` ~1238, `render_datasets`
~1375, `render_adoption` ~1406) move under the shell largely unchanged.

### S0. Design tokens + chrome (extends v5.0 in demo-stepper-ux.md)

- Implement `docs/ui-spec.md` Sections 1-2 verbatim: `.streamlit/config.toml`
  theme for the base (light + dark), plus one injected CSS block (a single
  `st.markdown` with `unsafe_allow_html`) carrying every custom property in
  ui-spec.md Section 1 (`--chrome-*`, `--code-*`, semantic ok/warn/danger, mono
  stack, radii) and the shell grid in Section 2.
- Hide Streamlit chrome (menu, footer, header) per v5.0.
- Acceptance: side-by-side with the mockup, the topbar/canvas/cards read as the
  same design system in both themes.

### S1. Login gate (persona select)

- First screen, before any chrome: the six personas as clickable cards under
  "Acting as". No auth. Implementation: a `st.session_state["persona_id"]` gate at
  the top of `main()`; when unset, render the login full-page (HTML cards via
  markdown + `st.button` per persona, or six styled `st.button`s in `st.columns`)
  and `st.stop()`.
- Picking a persona sets `persona_id` and reruns into the shell. This REPLACES the
  sidebar `persona_picker` selectbox as the primary identity entry; keep a small
  "switch identity" affordance (topbar or sidebar footer) that clears the key and
  returns to the login.
- All sidebar items are always shown regardless of persona (Sandip's call). RBAC
  gating of nav is explicitly out of scope for now; the personas still drive tier
  resolution inside the run.
- Acceptance: fresh session lands on the login; picking Junior Analyst shows the
  full sidebar; the run resolves L1 for them.

### S2. Sidebar shell + routing

- Replace the section radio with the mockup's grouped sidebar: Overview, then
  Workspace (Run), Governance (Datasets, Registry), Platform (Platform, Adoption).
- Implementation choice: prefer `st.navigation`/`st.Page` (native multipage, per
  the PRD 10.7 note that the fix for app.py's hand-rolled router is Streamlit
  native multipage). If the installed Streamlit version fights the custom look,
  fall back to styled buttons writing `st.session_state["section"]`; keep the
  existing `render_*` dispatch either way.
- The legacy sections not in the mockup ("Run analysis" hero, "Governed codegen",
  "Analyses") need homes: "Run" in the sidebar is the governed run walkthrough
  (the stepper). Keep "Analyses" reachable (it is the linear-engine runner the
  seeding work uses); simplest is a fifth Governance/Workspace item, decided at
  build time with Sandip if it should be hidden instead.
- Acceptance: sidebar persists on every screen including the run; active item
  highlighted; counts match live data (datasets 8, certs 3, templates 5).

### S3. Command-center home (the landing)

- The tile dashboard from the mockup: four tiles with live numbers, each "Open"
  routing to its surface, plus the "Start a governed run" CTA routing to Run.
- Data sources (all existing): datasets by class = registry x
  `DATA_CLASSIFICATION` (`purpose_matrix.py:31-40`); cert statuses =
  `certification.all_entries()`; templates = `reuse_metrics()`
  (`templates.py:145`); adoption = `adoption_metrics()` (`adoption.py:23`).
- Acceptance: numbers on tiles equal the numbers on the surfaces they open.

### S4. The run walkthrough inside the shell

- The nine-stage stepper + Architecture stop, per demo-stepper-ux.md v5.1-v5.4.
  Build it as the "Run" page of the shell; the Back/Next footer lives inside the
  content area (the mockup offsets it past the sidebar).
- The four additive flow fields (demo-stepper-ux.md Section 4) are the only
  `sentinel/` package changes this workstream needs.

---

## 2. Workstream D: datasets

Ground truth (verified): `available()` in `sentinel/datasets/loaders.py:40-44`
checks disk (`sentinel/data/<id>.csv`, or `<id>/*.csv` for relational). Local data
EXISTS for german_credit (1000), uci_taiwan_credit (10000 sampled),
berka (8 tables), hillstrom (20000 sampled), ulb_fraud (20000 sampled),
lendingclub (13820 sampled), synthetic_its (365). Only **uci_bank_marketing** has
no file AND no onboarder (`ONBOARDERS` at `scripts/onboard_datasets.py:229-236`
has 6 entries; bank_marketing is not one).

### D0. Flag hygiene (do first, it is lying to us)

- `DatasetSpec.onboarded` (`registry.py:40`) is hardcoded True only for
  german_credit and synthetic_its, while 7 datasets are actually onboarded. The
  UI ignores it (calls `available()`), but the field misled this very planning
  session. Either delete the field or make it a derived property that calls
  `available()`. Update anything that reads it.
- The mockup's Datasets table carried the same stale values (fixed 2026-07-18 to
  show 7 onboarded / bank_marketing registered).

### D1. Onboard uci_bank_marketing

- Write `onboard_uci_bank_marketing` in `scripts/onboard_datasets.py` and add it
  to `ONBOARDERS`. Source: UCI repo 222 zip (`registry.py:156` has the URL); the
  no-account pattern to copy is `onboard_ulb_fraud` (OpenML fetch,
  `onboard_datasets.py:49-77`) or a direct-URL fetch like hillstrom (`:42-46`).
  Sample to ~20k rows like the others if needed (full set is 41188).
- Governance config is already present for it (classification Internal at
  `purpose_matrix.py:31-40`, purpose row at `:77-87`), so this is onboarder +
  data only.
- Acceptance: `available("uci_bank_marketing")` is True; the Datasets surface
  shows 8/8 onboarded; a data_profiling run completes on it.

### D2. Optional corrections (small, honest, decide at build time)

- `synthetic_its` provides `{timeseries, treatment}` but no `tabular`
  (`registry.py`), so data_profiling's contract (`requires {tabular}`) never
  matches it even though it is a plain 365-row CSV. Adding `CAP_TABULAR` to its
  provides makes profiling runnable there. Check tests that assert its provides.
- Known engine limitation: data_profiling on berka passes the contract but ends
  BLOCKED because relational datasets load via `load_tables` and leave
  `ctx.frame=None` while the profile step dereferences `ctx.frame`
  (`analyses/engine.py:71-88, 92, 276-277`). Fix only if berka needs a second
  analysis type beyond feature_engineering variants; otherwise record it.

---

## 3. Workstream H: seeded run history

### The problem (verified, load-bearing)

- The model registry is a module-global list, in-memory per process
  (`platform/registry.py:50-71`); restart resets to the two seeded rows.
  `register_model` has exactly one caller: the credit_risk Orchestrator's
  `_register` (`orchestrator.py:362-393`). The linear `AnalysisEngine` and
  govflow write NOTHING to it.
- Adoption is derived from that registry plus a hardcoded `SEEDED_WEEKLY`
  3-week list (`adoption.py:16-20`).
- The only persisted artifact of any run is the audit JSONL under `runtime/`
  (gitignored); govflow deliberately passes `persist=False`.

So "pre-run analyses so the surfaces show history" requires a thin persistence
layer. Running things at app startup is not it (slow boot, resets each process).

### H0. The run-history store

- New module `sentinel/platform/run_history.py`: an append-only JSONL store of
  completed runs at `sentinel/data/seed_runs.jsonl` (committed; it is demo seed
  data, same spirit as the committed CSVs). One record per run: run kind
  (analysis | credit_risk | govflow | l3), spec/question id, dataset id, params,
  status, headline metrics (auc/disparity/fairness for models; step count and
  findings for analyses), controls fired, cost, timestamp, `seeded: true`.
- Loaders merge it in at import: `model_versions()` folds in seed records of kind
  credit_risk as `ModelVersion(seeded=True)` rows; `adoption_metrics()` derives
  weekly counts from record timestamps (replacing or extending `SEEDED_WEEKLY`)
  and gains a per-dataset cut; the Analyses/Registry surfaces can list recent
  seeded runs per dataset.
- Honesty rule (project value: never stage what claims to be real): every record
  in the store must be produced by actually executing the run, and everything
  rendered from it is labeled seeded, exactly as the two existing registry rows
  are labeled today.

### H1. The seed script

- New `scripts/seed_runs.py`: executes the plan in H2 headlessly and writes the
  store. All paths run scripted/free, no LLM needed:
  - Linear analyses: `AnalysisEngine().run(spec, dataset_id, params)`
    (`analyses/engine.py:194`), the same call the UI makes at `app.py:1684`.
  - credit_risk (the only path that yields model rows):
    `Orchestrator().start_run(question, narration_mode="scripted")` then
    `approve(run_id, ...)`; copy the pattern from `demo.py:23-39`.
  - govflow hero: `run_governed_analysis(question, ...)` (`govflow/flow.py:199`),
    templated gateway by default. Hardwired to german_credit (`access.py:26`).
  - L3: `run_l3_analysis(...)` (`govflow/l3.py:142`), hardwired to synthetic_its,
    needs an L3-resolving persona.
- Idempotent: re-running replaces the store rather than duplicating. Tests: store
  round-trip, merge into `model_versions()`/`adoption_metrics()`, and a marker
  that every seeded row renders with the seeded label.

### H2. The per-dataset seed plan

Contract facts this respects: data_profiling requires `{tabular}`;
feature_engineering `{tabular, relational}` (berka only); credit_risk executes
only via the orchestrator on german_credit (questions wired there only,
`questions.yaml`); govflow only german_credit; L3 only synthetic_its. Purpose and
tier legality per `purpose_matrix.py:77-87` and `tiers.py:36-41`. Param variants
are distinct runs (different params, genuinely re-executed).

| dataset | runs (kind: variants) | count |
|---|---|---|
| german_credit | profiling x1; credit_risk x3 (protected_attribute age_band / sex / foreign_worker); govflow fair-lending x1 | 5 |
| uci_taiwan_credit | profiling x2 (default; sample_rows variant) | 2 |
| berka | feature_engineering x2 (window_days 365 / 180 or include_rfm toggle) | 2 |
| hillstrom | profiling x2 (param variants) | 2 |
| ulb_fraud | profiling x2 | 2 |
| lendingclub | profiling x2 (fires the commercial-use flag, good history) | 2 |
| uci_bank_marketing | profiling x2 (after D1) | 2 |
| synthetic_its | L3 causal x1; profiling x1 (needs D2's CAP_TABULAR) or a second L3 question | 2 |

Total ~19 seeded runs, at least 2 per dataset, 5 on the hero. Adoption's weekly
chart and totals then derive from real records instead of the hardcoded list.

### H3. Surfacing (ties back into S3/the mockup)

- Registry Models table: seeds appear as today's two rows do (seeded label).
- Adoption: totals, promotion rate, per-dataset runs, weekly chart all derived
  from the store plus live-session runs on top.
- Dashboard tiles inherit the same numbers via `adoption_metrics()`.

---

## 4. Build order

1. **D0 + D1** (flag hygiene, bank_marketing onboarder): small, unblocks "8/8"
   everywhere, no UI dependency.
2. **H0 + H1 + H2** (store, script, seeds): pure backend, testable without any UI
   change; the existing surfaces immediately show richer data.
3. **S0 + S1 + S2** (tokens, login, sidebar shell): the app now opens like the
   mockup with the existing surfaces under it.
4. **S3** (command-center home): tiles read the now-seeded metrics.
5. **S4 / v5.1-v5.4** (the run walkthrough): the biggest slice, per
   demo-stepper-ux.md, built inside the shell.
6. **D2** if wanted along the way.

Each step lands with green tests + ruff before the next (316 passing today).
Nothing deploys without Sandip's explicit go-ahead.

## 4b. Landed (2026-07-19, the v6 branch)

D0-D2, H0-H3, and S1-S3 shipped in three commits. Deviations from the plan
above, with reasons:

- **D0 deleted the field instead of deriving it.** Nothing in production read
  `DatasetSpec.onboarded` (UI and engine already call `available()`), and a
  derived property would need registry -> loaders, a circular import.
  `onboarded_datasets()` went with it (no production callers).
- **D2 landed** (synthetic_its + CAP_TABULAR): it is what makes "2 runs per
  dataset" reachable for synthetic_its (L3 causal + profiling).
- **H2's credit_risk variants are by question, not protected attribute.**
  `Orchestrator.start_run` has no protected_attribute kwarg; all questions
  hardcode age_band. The three genuinely re-executed runs are build_model
  (approved), fairness_age (approved), profile_risks (rejected).
- **fairness_age really promotes.** The old hand-written seed row said
  blocked; the actual executed run passes the eval gate (auc 0.8018,
  disparity 0.569, fairness_pass False). The real result replaced the
  fiction, per the honesty rule.
- **Timestamps: `executed_at` + `demo_date`.** Every seed record keeps its
  real execution time; `demo_date` places it on the demo timeline (W26-W29)
  that the weekly chart and registry dates render, continuing the convention
  the hand-labeled rows already used. Disclosed in run_history.py and
  scripts/seed_runs.py docstrings.
- **S2 uses styled sidebar buttons, not st.navigation.** The flat script +
  the AppTest suite + the custom look made the sanctioned fallback the right
  call. The active item renders as the primary button variant.
- **Two extra Workspace items.** The legacy credit-pipeline hero lives on as
  "Pipeline" and Analyses stays reachable, both under Workspace. The mockup
  has neither; recorded here as a deliberate addition.
- **The landing after login is Overview** (the command-center), matching the
  mockup's pick behavior.

## 4c. Landed (2026-07-19, the control-chip branch)

The gap: a control chip sometimes explained itself on click and sometimes did
not, with no rule for which. `_control_popover` in `sentinel/ui/govflow.py` was
already the right mechanism (it reads the 27-entry `ControlInfo` catalogue and
adds an "In this run" line off the published stage output) and was already
proven at three call sites, but the engine bar, the Architecture stop, the
import allowlist, the topbar scope chips, and the certification cards all
rendered control ids as inert `<span>`s or plain dataframe strings.

The rule this branch settles: **if a chip names a governance decision, it opens
the catalogue entry for the control that made it. If it names a fact (a module
name, a row count, a license), it stays inert.** Every disclosure calls
`_control_popover`; nothing else writes what/why copy.

### Decisions

| # | Surface | Options | Call |
|---|---|---|---|
| 1 | Engine bar, "Governance implemented" (every stage) | Leave inert / wire to `_control_popover` | **Wired.** The highest-value, lowest-risk fix: the mechanism sat in the same file, ~30 lines above the code building the dead spans. The strip becomes a horizontal container (chips must be Streamlit elements to be clickable, so the row cannot stay one markdown blob) wearing the same `.enginebar` skin. |
| 2 | Architecture stop, "Governance implemented (built)" | Leave inert / wire | **Wired**, same mechanism, one row per stage. |
| 3 | Gate, "What the parsers checked" table | Add a chip row under it / leave the ids as table text | **Left as text.** The Gate engine bar directly above now carries all eight of those controls as popovers; a second chip row would be the same ids twice on one screen. `CTL-CODE-00` was missing from the Gate engine list and was added, so every id the table names has a clickable home. |
| 4 | Screen, the `CTL-DISC-03` PII warning | Bare `st.warning` string / add a popover | **Wired**, in the same `[1, 5]` column shape the Gate violations list already uses. `CTL-DISC-03` was also added to the Screen engine list. |
| 5 | The global Controls popover (`_controls_plane`) | Wire its chips / leave static | **Left static.** Streamlit's own guidance for `st.popover` is "to follow best design practices, don't nest popovers", and this is the see-everything-at-once catch-all: a menu inside a menu reads badly regardless. Per-instance popovers are its complement, not its replacement. This is the one place a control chip is deliberately not clickable, and the caption already says where the clickable ones are. |
| 6 | Import allowlist (module chips) | A popover per module / one per row / leave inert | **One per row.** A module name is not a control id, so `numpy` has nothing to look up. The deny list is now grouped by the control that denies it, mirroring `import_verdict()`'s precedence (egress → filesystem → dynamic code), and each row carries one chip for that control. The allow row carries `CTL-CODE-01`. The module chips themselves stay inert, and the lede says why. 4 popovers instead of 36. |
| 7 | Topbar Data / Purpose chips | Leave static / make them popovers | **Popovers.** Both ui-spec 2.1 and demo-stepper-ux specified "clickable to the relevant stage or control" and the build never wired it. Both chips open `CTL-PURP-01`: the purpose matrix is dataset-by-purpose and these two chips name its two axes, so one control honestly explains both. The Data chip adds one factual line (classification, the ceiling it imposes, the purposes the matrix permits) read off the real policy. |
| 8 | Datasets + Registry tables | Leave as `st.dataframe` / rebuild by hand / middle ground | **Rebuilt by hand.** `st.dataframe` renders every cell as plain text: it cannot carry the `.cls` and `.badge` chips ui-spec 4.2 specifies, let alone a popover. All three tables are now a header band plus one `st.columns` row per record. Cost was accepted deliberately (see the trade below). |
| 9 | Which cells become clickable | Every chip / only governance decisions | **Only governance decisions.** Datasets: the classification chip (per row, since it differs per row). Models: the status chip, which is the eval gate's verdict plus the human decision. Agents: the `tools` and `rbac scope` **column headers**, because the control is identical for all four rows and only the value differs; four copies of one explanation would be noise. Commercial-use stays an inert badge: the platform does enforce it, but from the dataset registry, not from a catalogue control, and inventing `CTL-` ids for the demo is the thing this project refuses to do. |

### Deviations and costs, recorded honestly

- **The topbar stopped being one markdown blob.** A popover trigger cannot live
  inside raw HTML, so the topbar is now a horizontal container carrying the
  same `.topbar` skin. The old 9:3 `st.columns` split went with it, in favour of
  the mockup's actual structure (2.1): one flex row, brand left, everything
  else right, each item sized to its content.
- **Two knock-on chrome changes, both improvements.** The identity popover was
  being truncated to "Acting as: Data Sci..." by the old column split; its
  trigger is now the persona name behind the accent dot, which is the mockup's
  persona chip, and it no longer clips. The scope chips wear the neutral chrome
  pill with the classification badge inside the pill (Streamlit colour markdown,
  since a label cannot carry the `.cls` span), which is both closer to the
  mockup and what keeps the bar on one row at the 1120px content cap.
- **`st.dataframe`'s sorting and column resizing are gone** from Datasets and
  the two Registry tables. That is the real cost of item 8. It buys the
  documented visual language (classification chips, status badges) and per-row
  disclosure; at 8 / 3 / 4 rows, sorting was not earning its keep.
- **The Datasets table had no classification column at all**, despite ui-spec
  3.4 listing one. Found while scoping item 8; added, along with the
  class-count breakdown row above the table that the spec also calls for.
- **19 popovers on the Architecture stop and 8 on the dataset registry.** Chips
  are small and the alternative was inert decoration, but this is the density
  ceiling; a future surface with 50 rows should use a different pattern.
- **Not done, deliberately:** the `CTL-` ids inside prose (the Attest lede, the
  certification section header) stay plain text. They are sentences, not chips,
  and turning every mention into a button would make the prose unreadable.

## 4d. Landed (2026-07-19, the Ask-step branch)

The gap: the Ask stage showed a dataset table and then, separately, a radio to
choose between two modes. The table was decoration; the radio was the control,
and it did not name a dataset, it named an analysis. Steps 2 and 3 offered
dropdowns whose options the user had to already understand: six purpose labels
in lowercase with no account of what each one covers, and six prebuilt requests
with no account of what any of them computes.

### Decisions

| # | Surface | Options | Call |
|---|---|---|---|
| 1 | Dataset selection | Keep the mode radio below the table / `st.dataframe` with `selection_mode="single-row"` / a radio in each hand-laid row | **A radio in each row.** `st.dataframe` row selection is the only *real* row click Streamlit offers, but it renders every cell as plain text, so the classification chip (a governance decision, clickable per 4.3) would have been lost to get it. The hand-laid table from 4c already puts a popover in a cell; adding a one-option radio per row keeps the chip and makes the row the control. The trade is that exclusivity is code, not a widget: `_pick_dataset` clears the other rows' keys. It has a test. |
| 2 | Where the radio sits in the row | Its own narrow column / merged into the dataset cell | **Merged.** A radio with a blank option label is unreadable to a screen reader and takes a column for nothing. The option label *is* the dataset id (markdown, so it keeps the mono `code` styling), with the widget label collapsed to `Select <id>`. |
| 3 | Selected-row state | A "selected" badge in the cell / the mockup's `.row-sel` tint | **The tint**, plus the `.rowgood` left accent bar. Both are in ui-spec 4.4 and neither had ever been built. The row container's key carries the state (`tblrow_sel_*`), because a container key is the only hook CSS has on a Streamlit block. |
| 4 | What Confirm does | Cosmetic acknowledgement / gate steps 2 and 3 | **A real gate.** Steps 2 and 3 do not render until the dataset is confirmed, and changing the pick drops the confirmation and clears the drafted question, so Plan sends the user back. A purpose and an analysis are declared *against* a dataset; letting them survive a dataset swap would be a lie about what was reviewed. Cost: the "just click Run" path is one click longer, and four AppTest tests gained a `gv_ds_confirm` click. |
| 5 | "What purposes are allowed for this dataset" | A popover per row / a panel under the table | **Both, and they are not duplicates.** The classification chip already carries the permitted list (`purpose_extra`, shared with the topbar). The panel under the table is the mockup's `.pmatrix`, built for the first time: all six purposes as permit/refuse chips, read off `PURPOSE_MATRIX`. The chip explains the *control*; the panel shows the *set*. |
| 6 | Where purpose descriptions live | UI copy in `govflow.py` / the policy module | **`PURPOSE_SCOPE` in `govflow/purpose_matrix.py`**, next to the matrix it describes. A purpose's edges are policy, not presentation, and copy that lives away from the rule it describes drifts away from it. |
| 7 | Where analysis descriptions live | The policy modules / the UI module | **`_ANALYSIS_NOTE` in `sentinel/ui/govflow.py`**, keyed by the prebuilt request name, which is a UI string. The honesty problem this creates is solved by a test rather than by placement: `tests/test_govflow_ask.py` re-runs the real gate over every scripted sample and fails if a note names a control the gate does not fire, or claims a clean pass the gate refuses. |
| 8 | Shared table helpers | Duplicate `_table_head` / `_table_row` / `_td` into `govflow.py` / extract them | **Extracted** to `sentinel/ui/tables.py`. `app.py` cannot be imported from `sentinel/ui`, and a table renderer copied into two files drifts. `cls_label` and `purpose_extra` moved to `sentinel/ui/govflow.py` for the same reason: the Ask picker and the dataset registry now render one classification chip, not two that look alike. |

### Deviations and costs, recorded honestly

- **Two strings are in title case against the rest of the app.** "Confirm
  Dataset" and "Select the Analysis" were specified verbatim. Every other
  header and button here is sentence case ("Import a dataset", "Declare the
  purpose"). Flagged, not silently normalised.
- **Exclusivity is enforced in a callback, not by a widget.** Streamlit has no
  radio group that spans containers. `_pick_dataset` writes `None` into the
  other rows' widget keys. It works, and `test_dataset_table_is_a_single_select`
  holds it, but a third dataset row would need nothing new and a fortieth would
  need a different pattern.
- **The `govflow_mode` radio is gone.** The L3 route is now chosen by picking
  the `synthetic_its` row, which is what the choice always actually was: the
  only Public dataset is the only L3 home. Any test or bookmark referencing
  `govflow_mode` is stale.
- **The purpose grid renders all six purposes, always.** For `synthetic_its`
  every one is permitted, so the grid is six green chips and teaches nothing on
  that row. Left as is: an asymmetric grid would be harder to read against
  german_credit, which is the row that matters.

## 5. Out of scope (recorded so nobody re-litigates)

- RBAC-gated navigation (all sidebar items always shown, for now).
- Generalizing govflow beyond german_credit or L3 beyond synthetic_its (each is
  hardwired; a real feature, not a seeding task).
- B-style contextual drawers from the options exploration (layer on later).
- Mobile UI (removed from the mockup by decision 2026-07-18).
