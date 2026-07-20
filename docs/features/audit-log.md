# Audit Log

**Status:** built — data layer, screen, and the run drill-down
**Nav:** Platform group, immediately after Adoption
**Owner surface:** `render_audit_log()` + `render_audit_run()` in `app.py`, data layer in `sentinel/platform/audit_store.py`
**Approval model:** Option A of section 7 — report what is true, add nothing

---

## 1. What this is

One screen that answers, across every run the platform has ever executed:

1. What ran, when, and against what data.
2. Every step inside that run, in the run's own vocabulary.
3. What a control allowed.
4. What a control caught and refused.
5. Who ran it.
6. Who else had to sign, and whether one signature was enough.

Sentinel already has eight surfaces that show a single run's trail: the Pipeline
screen's audit tab, the govflow stepper's per-stage control chips, the Analyses
run panel, the evidence pack, the model card, the cost ledger, the trace viewer,
the Registry. Every one of them is scoped to one run, and all but the seeded
Registry rows vanish when the session ends.

The gap is the cross-run view. A control that fires once in a scripted demo is a
demo. A control that fires on 23 runs across four weeks, with the refusals
countable and the signatures attributable, is a control. That is the only thing
this screen adds, and it is why it earns a nav slot instead of a tab.

**It reads the record. It cannot write to it.** No action on this screen mutates
anything.

---

## 2. What exists today

The raw material is better than expected. `AuditEvent` is already a frozen
dataclass with fourteen fields, and every run kind emits through it.

| Field | Populated | Note |
|---|---|---|
| `run_id` | always | 12-hex uuid4 slice, all four run kinds |
| `seq` | always | monotonic, **per run**, restarts at 0 |
| `ts` | always | ISO-8601 UTC |
| `agent` | always | 11 distinct values in the local corpus |
| `action` | always | 22 distinct values in the local corpus |
| `level` | always | `info` / `blocked` / `redaction` / `gate` |
| `actor` | defaults to `agent` | the trap, see 3.3 |
| `policy_version` | always | `2026.07-rbac-v1`, stamped at `AuditLog` construction |
| `data_touched` | on data events | column lists, the RBAC denial's payload |
| `inputs_summary` / `output_summary` | free text | prose, no vocabulary |
| `tokens` / `cost` | always 0 | no call site passes them; `CostTracker` is the real accountant |
| `extra` | 12 of 61 sites | where `control` lives when it lives anywhere |

Four run kinds, four step vocabularies, no shared base class:

- **analysis** — declarative `spec.steps`; `data_profiling` is load → profile →
  quality, `feature_engineering` is load → features → leakage. Statuses
  `completed` / `blocked`.
- **credit_risk** — a compiled LangGraph: profiler → eda → modeler → **human
  gate** → validator. Statuses `running` / `awaiting_approval` / `completed` /
  `rejected` / `blocked`.
- **govflow** — nine stages: Ask, Plan, Access, Generate, Gate, Execute, Screen,
  Interpret, Attest. Statuses `completed` / `blocked_at_gate` / `error`.
- **l3** — the same nine stages at tier L3.

Refusals are real and enforced in code, not asserted in prose: `tier_block` at
Ask, `CTL-PURP-01` at the purpose matrix, the static AST gate at Gate,
`CTL-EGRESS-01`, `CTL-SOD-01` at the promotion gate, RBAC column denial,
PII redaction, the eval gate.

---

## 3. What does not exist, stated plainly

This section matters more than the design. Four of these are load-bearing for
the feature and one of them is the question you actually asked.

### 3.1 There is no dual control anywhere in Sentinel

You asked whether a run "required more than one user for additional approvals."
Today the honest answer is **no run ever requires more than one**.

What exists is **author is not approver**, enforced by identity comparison:
`RunState.started_by` is set from `actor.id` at `start_run`, and
`Orchestrator.approve()` refuses when `actor.id == state.started_by`, recording
`approval_denied` at `LEVEL_BLOCKED` naming `CTL-SOD-01`. A test drives the full
path. That is real, and it is what the login card means by "four-eyes."

**Correction found while building (2026-07-20).** There are *two* refusals at
that gate, not one, and they are easy to conflate. `Orchestrator.approve()`
tests promotion authority **before** it tests segregation of duties
([orchestrator.py:489](sentinel/orchestrator.py:489) then
[:503](sentinel/orchestrator.py:503)). So an Analyst self-approving is refused
for *lacking authority* and never reaches `CTL-SOD-01` at all; only an author
who already holds promotion authority exercises the four-eyes control itself.
Both are now in the seeded corpus, and a test asserts they stay distinct, so
the screen cannot credit `CTL-SOD-01` with a refusal it did not make. The
authority refusal writes no `extra['control']`, which is how they are told
apart.

But there is no approver list, no quorum, no vote count, no pending-second-
signature state, and no data structure anywhere that could hold two approvals.
One MRM Approver click promotes the model.

Three further holes in the same area:

- **Rejection is unguarded.** Both the role check and the SoD check are
  conditioned on `approved` being `True`. Any persona, including the run's own
  author and the read-only Auditor, can reject a run and terminate it.
- **No rationale is captured on any decision.** The gate is two bare buttons.
  `output_summary` is a fixed literal, `APPROVED at model gate`.
- **The govflow nine-stage route has no human gate at all.** The interrupt
  belongs solely to the legacy credit_risk pipeline. The flow with all the
  interesting refusals has the thinnest accountability, and
  `sign_evidence_pack()` — which has a real `CTL-SOD-01` refusal — is called
  only from tests. Every pack the product ships is `status='pending'`.

So the "Second pair of eyes" column reads `not required` on 16 of 19 seeded
runs. **See section 7 for the decision this forces.**

### 3.2 The audit record does not survive a deploy

`runtime/` is gitignored and excluded from the Elastic Beanstalk bundle, and EB
replaces `/var/app/current` wholesale. There are 324 audit JSONL files on this
machine and zero on the instance.

Worse, `govflow` and `l3` construct their `AuditLog` with `persist=False`, so
their events never touch disk even locally. That is why the local corpus has
1,050 `agent_started` events and not one govflow stage event.

Worse still, `scripts/seed_runs.py` collapses each run's event stream into a
sorted set of distinct action strings and discards seq, ts, actor, agent, level,
and `data_touched`. **The 19 seeded runs carry no per-step detail at all.**

Net: without prerequisite work, this screen ships empty in prod and the detail
view is blank on 19 of 19 rows. Design quality is irrelevant to that outcome.

### 3.3 The actor is self-asserted, and often is not a person

Persona selection is a faux sign-in driven by a URL query param with no
credential. Every `actor` value in the log is self-asserted.

And `AuditEvent.actor` defaults to `agent` when a call site omits it, which most
do. So the actor column is populated with `orchestrator`, `sandbox`,
`analysis_engine`, `data_connector` — module names presented in the column
labelled "who." An audit screen that renders a module as a person is worse than
one that admits it has no identity model.

### 3.4 The record is immutable by convention, not by cryptography

Immutability is enforced by a frozen dataclass and a copy-on-read. The JSONL is
a plain file. No hash chain, no signature, no seal. `seq` is per-run and resets,
so there is no global ordering either.

The only tamper evidence available today is **sequence continuity within a
run**: seq 0..N with no gaps. That is worth printing. A "Record integrity" tile
that checks only monotonicity and calls itself integrity is not.

### 3.5 Control ids are not first-class

Only 12 of 61 emission sites populate `extra['control']`. Everywhere else the
control id lives in prose inside `output_summary`. Until `control_id` is
promoted to a real `AuditEvent` field, any filter keyed on control is
structurally near-empty.

---

## 4. The screen

Master-detail. Runs are the rows, not events. An examiner reasons in runs
("show me the run that was refused"); a 5,000-row event table reads as log spew.

Top to bottom, at the app's 1120px container:

**1. Header.** `st.subheader("Audit log")` plus one muted lede, matching the
Datasets / Registry / Platform / Adoption pattern. Then a coverage caption
stating provenance in the house style: how many runs are seeded, how many are
live this session, and that live runs are lost on restart.

**2. KPI row.** Four `st.metric` tiles, one caption under the row giving the
derivations.

| Tile | Definition |
|---|---|
| Runs logged | Records in the store. Delta: `N this session`. |
| Refusals | Runs with at least one `level='blocked'` event, as "X of Y runs". Caption splits it: **A stopped the run outright. B completed with something withheld** (a column denied, a cell suppressed, a value redacted). This is the sentence the screen exists to print. |
| Four-eyes coverage | N of M, where M = runs that reached a human gate (`approval_requested` present) and N = runs whose `approval_decision` actor differs from `started_by`. Caption: self-approval attempts count as refusals, not as coverage. |
| Controls fired | Distinct control ids that actually fired, over the catalogue's resolvable id space. Caption states honestly how many catalogue entries are documented-but-not-implemented, so the ratio is not misread as a coverage failure. |

**3. Filter bar.** One `st.container(border=True)`, two rows. Row 1 is the
posture control, a full-width `st.segmented_control`: **All runs / Refusals only
/ Approval decisions**. Row 2 is four narrow selectors: Kind, Ran by, Dataset,
Control. A right-aligned caption reads "showing N of M runs"; a Clear button
appears only when a filter is active.

No surface in Sentinel has a filter bar today, so this deliberately uses only
existing primitives and adds no new CSS class. In the "Ran by" selector, module
identities are grouped under a separate heading, **system components, not
people**, per 3.3.

Deliberately omitted: date range (the seeded timeline is four weeks wide, a date
picker filters nothing) and free-text search (43 free-form action literals with
no vocabulary; it would look powerful and return arbitrary results).

**4. Run table.** Hand-laid `table_head` / `table_row` / `td` from
`sentinel/ui/tables.py`, not `st.dataframe`, because the cells must carry `.cls`
classification chips, `.badge` status pills and live control popovers
(ui-spec 4.3, 4.4). Newest first, fixed sort. Ten columns:

| Column | Source |
|---|---|
| When | `demo_date` (seeded) / `executed_at` (live), with origin as a muted suffix |
| Run | 12-hex `run_id`, and the row's select control |
| Kind | `.badge neutral`: analysis / credit risk / govflow / L3 |
| Analysis | `ref_id` |
| Dataset | `dataset_id` + `.cls` chip, the chip being a `CTL-PURP-01` popover |
| Ran by | persona display name. **New field**, see 5 |
| Second pair of eyes | signed / self-approval refused / awaiting / not required. **New field**, see 5 |
| Outcome | normalized status badge; when refused, the badge itself is the popover for the control that stopped it |
| Stopped at | the step or stage where it ended: Access, Gate, modeler. Blank when it ran clean |
| Caught | the widest column and the point of the screen. Fired controls as clickable chips, refuse-first, three then `+N` |
| (action) | an **Open** button. Two ways into a run, deliberately: the id is styled as a link (accent, mono, underline on hover) because a Streamlit tertiary button renders as plain body text, so the id alone read as an inert cell value and the drill-down was undiscoverable. On a screen whose whole job is "open the evidence", one entry point is thin. |

Row states: any run with a `blocked`-level event takes the `.rowbad`
`--danger-soft` tint, so the eye lands on refusals before reading a word. The
selected row takes the existing `.row-sel` accent tint. A run with zero
persisted events renders its event count **struck through, not blank** — the
"suppressed, not deleted" principle applied to missing evidence.

**5. Detail block.** Inline beneath the table, inside a bordered container. Six
blocks:

- **A. Identity line.** run_id, kind, ref_id, dataset + classification, tier
  (only for govflow and L3; for the other two the cell says so rather than
  faking it), outcome, origin, policy version.
- **B. Decision summary.** Three labelled lines answering the requirement in its
  own words. **ALLOWED**: what the run was permitted to touch. **CAUGHT**: "N
  refusals. M stopped the run. K were recorded and the run continued."
  **APPROVALS**: the chain of custody, ran by → approved by → evidence artifact,
  with the acting persona's role and attestations, the `CTL-SOD-01` popover
  where it fired, and one faint honest line that persona selection is a demo
  sign-in with no credential. The distinction between "nothing was refused on
  this run" and "no event trail was persisted for this run" is explicit and in
  danger ink. They are not the same statement and conflating them is the exact
  failure this product exists to avoid.
- **C. Stages.** One entry per governance stage. **Superseded 2026-07-20**, see
  below. Originally: one entry per step in the run's own vocabulary, no
  invented normalization: analysis renders its spec steps, credit_risk renders
  profiler → eda → modeler → human gate → validator, govflow and L3 render the
  nine stages. Each row carries a status glyph, the acting agent, the event
  count at that step, and the control chip if one fired there. The blocked row
  is tinted; skipped rows are struck, not hidden.
- **D. Event stream.** The persisted events: seq, ts, agent, actor, action,
  level, summary, data_touched, control. Tinted by level using the real semantic
  tokens. `tokens` and `cost` are deliberately not columns; they are always zero
  and printing them would be theatre. Above the table, one caption asserting
  sequence continuity: "seq 0-20, no gaps." An expander per event shows the raw
  persisted JSON verbatim, so the screen can be diffed against the export.
- **E. Export.** Two download buttons: events as JSONL byte-identical to what
  `AuditLog` persists, and the run record as JSON. The first thing the Internal
  Auditor persona can actually do.
- **F. Footer caption.** Names what is not captured: rationale on approve or
  reject, an authenticated principal, tamper evidence. Putting the gap on the
  screen is stronger than designing an affordance around it.

**6. Empty state.** The app's existing `st.info` convention.

**Two corrections after first use (2026-07-20).**

*The posture filter conflated two findings.* It offered "Refusals only",
meaning "a control caught something on this run" — which includes runs that
then completed, because a denied column or a redacted value is a refusal the
run survived. Reading that label beside an `approved` outcome is a fair
contradiction to raise. The filter now splits on the same axis the Caught line
already used, with counts in the labels: **All runs / Stopped by a control /
Withheld, ran on / Reached a human gate**. Nothing appears under both of the
middle two, and a test asserts it.

*Opening a run is a navigation, not an accordion.* The detail was an inline
block under the table, so every run rendered into the same spot at the bottom
of a 24-row list. A run now opens as its own screen, pushed onto the app's nav
stack, so sidebar Back works like everywhere else, plus an in-page Back. The
run id also goes into the query string: `?run=<id>` is a real address, so a
single run's evidence can be linked, bookmarked, or opened in a new browser
tab. That matters more here than anywhere else in the app, because "send me
the evidence for that run" is the actual examiner workflow. An unknown id says
which id failed rather than rendering blank.

Drilling in unmounts the filter widgets, and Streamlit discards the state of a
widget it did not render, so Back originally returned you to an unfiltered
ledger. Durable `_`-prefixed copies re-seed them.

*A step showed a status word and nothing else.* "ok" is a claim with the
evidence removed. Each run kind records the substance of a step somewhere
different and the first store kept none of it: `StepRun.summary` for an
analysis, `StepRecord.narration` for a credit-risk agent, `StageRecord.detail`
for a govflow stage. All three now land in `detail`, and each step also shows
its tool and produced artifacts (analysis), the controls that fired at that
step (govflow/L3), and its own events.

Per-step event attribution is **declared, not guessed**. analysis and
credit_risk name one agent per step, so an event's `agent` identifies its step
exactly and those events group under it. govflow and L3 do not: `flow.py`
records `agent="govflow"` from Ask, Plan and Access alike, so grouping by agent
would file events under the wrong stage. Those stages carry a false
`attributable` flag, show their own exact detail and controls, and their events
stay in the run-level stream under a caption saying why. Making that honest
would mean stamping the stage onto the event, which is a follow-up: ~30 call
sites in `flow.py` and `l3.py`.

### The nine-stage shape (2026-07-20, supersedes "the run's own vocabulary")

The original design rendered each run in its own step vocabulary and argued
against normalizing, on the grounds that mapping credit_risk's
profiler/eda/modeler onto Ask..Attest is an interpretation. That was the wrong
call. The nine stages **are** the product's governance spine, the Run screen
teaches them, and an auditor should learn one vocabulary rather than four.

Every run now renders as Ask, Plan, Access, Generate, Gate, Execute, Screen,
Interpret, Attest. The mapping lives in `sentinel/platform/audit_stages.py` and
three rules keep it from lying:

1. **A stage a route does not have is `not in this route`** — never `ok`, never
   `skipped`. Three different facts: `ok` ran, `skipped` was reached and
   declined, `not in this route` means no such stage exists on that path. A
   linear analysis generates no code, so its Generate stage is absent, not
   skipped. Stages a route performs without recording a discrete step (RBAC at
   Access on the credit pipeline) are marked as such in italics.
2. **Native step names stay visible** inside each stage. Execute on a credit
   run lists Data Profiler, EDA / Feature and Modeler by name with their own
   narrations and events. The mapping is additive.
3. **A stage folding several steps takes the worst outcome.** Two of three
   steps passing does not make a stage green.

**Frameworks and governance per stage.** The nine-stage routes read
`sentinel/ui/govflow.py:_ENGINE` directly — the same table the Run screen's
engine bar renders — so the two surfaces cannot drift, and a test asserts it.
The other two routes declare their own, grounded in what those modules actually
import: printing govflow's duckdb sandbox against a credit-risk run that trains
a scikit-learn model would be a plain falsehood.

Each stage shows the controls it **armed** and how many **fired** on this run,
with the fired ones dot-marked. The Gate arming eight code checks and tripping
none is the normal case; reading those eight as eight refusals would be the
same over-count the KPI tiles already avoid, and a test asserts fired is always
a subset of armed.

Not gated to the Auditor persona. It is the auditor's natural home, but gating
it would hide the platform's best argument from a panelist logged in as the
Analyst, and every other surface is persona-independent.

---

## 5. Engineering, in dependency order

Items (a) to (d) are **built**. The corpus is now 24 runs and 249 committed
events: 9 runs carry a refusal (6 stopped the run, 3 completed with something
withheld), four-eyes coverage reads 3 of 5, and 13 distinct controls have
actually fired. `uv run --extra dev pytest` is green at 413 passed, 2 skipped,
with 22 new tests in `tests/test_audit_store.py`.

Nothing above renders without (a) and (b).

**(a) Commit the seeded event stream. DONE.** `scripts/seed_runs.py` now writes
the full per-event stream to a committed `sentinel/data/seed_audit.jsonl`, and
`SeedRun` gained `actor`, `approver` and `steps`. `approver` is read off the
decision event rather than the persona passed in, so a refused approval records
no approver. All four run kinds already exposed their events in memory, so no
new write path was needed. Cost was 249 lines, not the ~5k first estimated.

**(b) Extend the seeder with refusal runs. DONE.** Five additions, all existing
code paths executed for real, nothing hand-written:

1. an L3 run with `intent='exfiltrate'` → `CTL-EGRESS-01` blocks at Gate;
2. a govflow run with `intent='exfiltrate'` → the L2 static gate blocks;
3. a govflow run by the `auditor` persona → resolves L0, `tier_block` at Ask;
4. a credit_risk run where the **Analyst** self-approves → refused for lacking
   promotion authority;
5. a credit_risk run where the **MRM Approver** authors and self-approves →
   `CTL-SOD-01`, the four-eyes control proper.

Two corrections to the original list. The proposed "junior_analyst on a
Confidential dataset" is not reachable: govflow is bound to `german_credit` by
a module constant, and `junior_analyst` resolves to L1 there, which is a
different path, not a refusal. The `auditor` persona resolving to L0 is the
real tier-block path. And the "permitted-but-unwired purpose" stop was dropped;
items 4 and 5 cover more ground.

Run 5 puts a record in the corpus of an approver authoring a run, which is
itself the wrong thing for an approver to do. That is deliberate: nothing
enforces `can_run` at the entrypoint, so the platform has to catch the
consequence at the gate, and the ledger showing it caught it is the point.

Say out loud in the caption that refusal density is a seeding choice. The
alternative is a ledger that implies the platform refuses things at that rate
naturally.

**(c) `sentinel/platform/audit_store.py`. DONE.** The first reader across runs.
`AuditRun` wraps a record plus its events and computes the refusal accounting
the screen needs. Two properties earned their keep:

- `refusal_controls` reads the event stream **before** `controls_fired`,
  because govflow only accumulates CTL- ids raised at Gate and Screen. The
  auditor tier-block run has an empty `controls_fired` while its events plainly
  record a `tier_block` at blocked level, so without this the Caught column
  would be blank on a run that was visibly refused. A test asserts no refused
  run ever renders blank.
- `has_refusal` falls back to `controls_fired` when no events exist, so "no
  trail was persisted" can never be reported as "nothing was refused."

`stopped_at` reads the run's own step records rather than the status constant,
so a govflow run refused at Ask reports Ask, not `blocked_at_gate`.

**(d) Backfill the missing actors. DONE.** 12 emission sites defaulted `actor`
to the agent name: 9 in `flow.py` and **3** in `l3.py`, not the 8 first
reported. All now pass `actor=persona.id`, and a test asserts every seeded
run's actor resolves to a real persona rather than a module id.

Flipping `persist=False` at `flow.py:265` and `l3.py:169` turned out to be
**unnecessary**. `GovernedRunResult.audit` already carries the full event list
in memory, so the seeder captures it directly. Leaving the flags alone keeps
`runtime/` free of govflow noise and avoids a write on every UI run.

**(e) Promote `control_id`.** Add it as a real `AuditEvent` field and populate
it at the 49 sites that today bury it in prose. Without this the Control filter
is decorative.

**(f) Shared level-tint helper.** Three untokenized hexes at `app.py:1085` are
near-misses on the palette. Fix them in one helper and reuse it in the existing
Pipeline audit tab so the two surfaces converge rather than diverge. An audit
screen is a bad place to have two reds.

Deferred, and said on the screen rather than designed around: hash chaining, an
authenticated principal, approval rationale capture, a durable sink.

---

## 6. Tests

- `audit_store` normalization: every status constant across the four kinds maps
  to exactly one of ok / refused / awaiting, asserted by set equality so a new
  constant breaks the test.
- Sequence continuity: for every run in the corpus, seq is 0..N-1 with no gaps.
- Four-eyes coverage arithmetic: on the seeded corpus with the new refusal run,
  the tile reads 3 of 4 and the fourth is the self-approval refusal, counted as
  a refusal and not as coverage.
- Every control chip the screen renders resolves through `control_info()`. This
  test already exists in spirit for the govflow notes; extend the same pattern.
- Refusal split: stopped + withheld equals the refusal count, on the real corpus.
- The screen renders with an empty store and with a run that has zero persisted
  events, and says different things in the two cases.

---

## 7. The one decision for you

**Does Sentinel get real dual control, or does the Audit Log faithfully report
that it has none?**

Option A, **report honestly**. Build sections 4 and 5 as written. The column
reads `not required` on most rows and `signed` on the credit_risk runs. Cheap,
truthful, and a careful panelist will notice that the governance-heaviest path
(govflow, L3) has the thinnest accountability.

Option B, **wire the second signature that already half-exists**. Call
`sign_evidence_pack()` from the Attest stage, which is currently dead code with
a working `CTL-SOD-01` refusal in it. That gives govflow and L3 runs one real
independent signature and makes the column meaningful on every row. Small: one
call site, one UI affordance, one test.

Option C, **build genuine dual control for high-risk runs**. Require two
distinct approvers when a run trips a risk trigger (restricted data, or fairness
below the four-fifths threshold, or tier L3). This is the only option that makes
"more than one user for additional approvals" literally true, and it is the
strongest bank-legible story: a quorum policy, a pending-second-signature state,
and an audit trail showing both signatures. It is also the largest: new state on
the run record, a new UI surface for the second approver, and a real policy
config.

**Recommendation was B now, C next. Decided 2026-07-20: Option A.**

The Audit Log reports what is true and adds no approval machinery.
`sign_evidence_pack()` stays dead, evidence packs stay `pending`, and the
second-signature column reads `not required` where that is the fact and `not
reached` where the run was refused before any approval point existed.

Two things make A land better than it first looked. The corpus now contains
both gate refusals, so the column carries a real story on the credit_risk rows
rather than a single happy path. And the distinction the build surfaced -
authority versus segregation of duties - is itself the more interesting finding
for a bank audience, because it shows the order the guards run in.

What A leaves on the table, stated so it is a choice and not an oversight: the
govflow and L3 routes still have no human gate, so the platform's
governance-heaviest path has its thinnest accountability. That is a product
gap, not a reporting one, and the screen names it rather than papering over it.

The Audit Log renders what is true. It does not print a column that implies a
control the platform does not have.
