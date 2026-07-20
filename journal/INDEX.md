# Sentinel — Journal Index

Last refreshed: 2026-07-21 00:44

Latest entry: [2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md](entries/2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md)

## Where we are now

**Prod carries PR #37 and #38. Bundle `sentinel-20260721-002533.zip`, `main` at
`7e51602`, EB Green. 665 tests, 2 skipped, ruff clean.** Verified by running a
governed analysis on the live site, not by probing health: header chips read
`0 tokens · $0.0000 · 1.8s`, Generate carries the gateway ledger, Interpret
states a failing disparity ratio of 0.496 against the 0.8 threshold, and the
Audit trail button resolves to the live run's own drill-down.

**The Pipeline screen is retired and the app has one vocabulary for reading a
run.** Ten tabs of evidence hung off whichever run you had just executed. Each
was put to one test: does the surviving route produce the data, and does a stage
own the question the tab answers? Four moved into a stage (gateway ledger to
Generate, the raw result to Execute, fairness merged into Interpret, and the
model card to the Registry). Cost split into header chips. The Audit Log links
out rather than rendering the event stream a third time. Four were discarded,
with one thing salvaged: the fixed-control-flow argument, now made about the
nine stages on the Architecture panel.

**The evidence was already being computed and thrown away at the door.** I
expected to write instrumentation and wrote almost none. `ledger_dicts()`
existed, `_generate_execute_loop` already summed tokens and dollars, `_narrate`
already divided two selection rates, and `to_public_dict` dropped all of it. So
the retired screen was not better designed, it was merely holding the object
earlier. The general form: **when one surface can show something no other
surface can, check whether it has better data or only earlier data.**

**Model Card went to the Registry, against the plan.** The plan said Attest.
Implementation showed the premise fails, because no govflow run trains a model,
so the conditional would never fire. The card's live data is the seeded
credit-risk runs and their home is the model inventory, which also fixed the
anchor: a card should not hang off whichever run you last executed.

**Live runs reached the Audit Log for the first time.** `audit_runs()` always
took a `live` list and nothing ever passed one, so the screen's own "may have
been a live run" error described a path that did not exist. Two bugs fell out of
wiring it, both found by clicking rather than by a test: an `on_click` callback
calling `st.rerun()`, and a live record filing the persona display name where
`visible_runs` compares ids, which refused a first-line analyst their own run.

**The six control toggles are read-only and the UNGOVERNED badge is gone.**
Their only consumer was the Pipeline screen's Run button. No run the app can now
start is capable of being ungoverned, by construction rather than by policy.

**Two sessions collided in one list, and it resolved in a minute.** First real
conflict from parallel worktrees rather than another abandoned branch. Both
branches edited the sidebar nav: one moved it into `sentinel/ui/nav.py`, this
one deleted the Pipeline entry. Keep the move, apply the deletion at the new
home. It was easy because the conflict landed in the 100-line file that had just
been extracted, not the 3,400-line one both sessions also touched.

Everything below is the prior state.

---

**Agent Templates ships on a branch, not to prod. 654 tests, 2 skipped, ruff
clean. Prod still carries PR #33 at `7ac3dde`.** Governance now reads Datasets,
Agent Templates, Registry, which is lifecycle order: the data you may use, the
blueprint you build from, the inventory of what got built.

**A template is a document you can be refused by, and that was the whole design
question.** An editable spec that always saves is a text box with extra steps.
The way out is that a template names nothing of its own: a purpose is a column
in the matrix, an import is a name on the codegen allow-list, a tool is in
`agents.yaml`, a tier is a rung in `tiers.py`, a column is inside a grant in
`access.py`. So the editor keeps no policy. It reads the enforcing modules and
refuses what they would refuse, across eleven checks that reuse `CheckReading`
and `Observation` from `codegen/gate.py` so the panel speaks the Gate stage's
language and the two cannot drift apart.

**The format is YAML, and the repo had already decided it.** `sentinel/config/`
is five YAML files and `scaffold.py` already writes an agent spec in YAML, so a
JSON template would have meant the CLI and the screen emitting two artifacts for
one object. Serialization goes through `json.dumps` per scalar, since JSON is a
subset of YAML that PyYAML reads back identically.

**Policy checks and certification gates are kept apart, and that distinction is
the design.** Policy checks are the fence: a refusal disables the deploy,
because an illegal blueprint should not reach the registry. Certification gates
are not: they block `certified` and not the draft. Every shipped template fails
two gates because all five carry `owner: UNASSIGNED`, which is correct rather
than unfinished. A blueprint cannot own the instances made from it, and
`scaffold.py` registers a new agent unowned for the same reason. It is the same
mistake as painting `no_subject` green: a screen showing "not yet owned" in the
same red as "reaches for the network" is not telling a reviewer which one is a
policy violation.

**Deploy is `certification.register()`, not a toast.** It computes the dataset's
content SHA now, pins it into the contract, and puts a real `RegistryEntry` at
draft under Analysis-agents where the four gates decide what it may become.
Verified end to end in the browser. What is simulated is named on the screen:
nothing written to disk, no process started.

**Adding the tenth screen found a stale number, unprompted.** `manual.py` opened
its screens chapter with a hand-typed "Nine screens in the sidebar" and nothing
failed when that stopped being true. The nav definition moved out of `app.py`
into `sentinel/ui/nav.py`, both read it, the count is computed, and a test fails
if a number is typed back in. `product_screens()` excludes Help, because the
manual, the FAQ and Ask me are the manual describing itself.

Everything below is the prior state.

---

**Prod carries PR #33. Bundle `sentinel-20260720-200636.zip`, application
version `sentinel-eb-applicationversion-pnysewhnfcn2`, EB Ready and Green.
Health 200, WebSocket 101. `main` at `7ac3dde`. 606 tests, 2 skipped, ruff
clean.** Verified by the behaviour that only exists in this build, on prod and
in live mode: the gate refuses "Who is the PM of India, and what is a good
recipe for dosa?" for 175 tokens and $0.0002, and an on-topic question answers
from five cited passages naming CTL-SOD-01 and the Attest stage.

**Help is three screens now: User Manual, FAQ, Ask me.** Ask me runs two
stages and the order is the design. A relevance gate decides whether the
question is about Sentinel at all, before any retrieval or answering. Only on
a pass does it retrieve manual passages and answer strictly from them, showing
the passages it used. Gating first is what stops the answer stage from being
handed an off-topic question alongside five plausible passages and asked to
reconcile them. Three verdicts, never collapsed: off topic, on topic but not
covered, and answered. The middle one is a gap in the manual and reads like
one.

**Both stages work with no model, because the public link has no key.** The
scripted gate is TF-IDF cosine plus vocabulary coverage over the corpus, and
the scripted answer is the ranked passages, labeled as passages rather than
dressed up as prose. Cosine alone was not enough: it answered "Write me a poem
about the sea", because a corpus that talks at length about writing code has
plenty of "write" in it. Coverage asks the blunter question, how much of this
sentence is in our vocabulary at all, and refuses on "poem" and "sea" being
foreign. Every model call routes through `ModelGateway.complete()`, new for
this, so Help is tier-routed, cost-capped, cached and in the ledger like
everything else.

**The Ask-me corpus is a second source of truth, and that was a decision, not
an oversight.** The manual is a screen, which is the right shape for a reader
and the wrong shape for retrieval. I recommended extracting its prose at render
time under a recording stand-in for `st`, which cannot drift; Sandip chose a
parallel markdown corpus, which is simpler to read and edit. The fence around
that choice is the numbers rule: markdown can read nothing, so the corpus is
forbidden from stating an enforced value and instead names the cap and points
at the chapter that prints it. `test_corpus_states_no_enforced_number` reads
the sandbox caps, the disclosure floor and the control and persona counts live
off their modules and fails any page that retypes one, the same shape as the
guard that bans a hardcoded wall clock in `sentinel/ui/`. Prose can still
drift; that degradation is a worse answer rather than a false claim about what
the sandbox enforces, which is the trade being made.

Everything below is the prior state.

---

**Prod carries PR #29, #30 and #32. Bundle `sentinel-20260720-191009.zip`, EB
Ready and Green, application version `sentinel-eb-applicationversion-up7yzgu3eukn`.
Health 200, root 200 in 0.74s, static gzipped, WebSocket 101, no console
errors. `main` at `29ad22b`.** Verified by the Gate panel drawing a different
shape on different code: the benign L2 run reads 7 green and 2 dashed grey, the
SQL wildcard run reads 1 red, 7 green and 1 dashed. A screen that rendered
identically on both is the thing this deploy replaced.

**The deploy nearly shipped the wrong build, and the guard I had designed would
have passed it.** The primary checkout was on `main` at exactly `origin/main`,
so the ancestor check was clean, while its index held a full revert of all three
merges: 2,699 deletions, the pre-`CheckReading` gate, `result_contract.py`
deleted. `deploy.sh` archives the working tree, not `HEAD`, so the bundle would
have gone Green without the Gate read or the Live LLM fix. **The guard needs two
clauses, and the second is the one that fires: `HEAD` is an ancestor of
`origin/main`, AND `git status --porcelain` is empty.** Stashed as `stash@{0}`
rather than reset, since "nothing here is new" was a conclusion from reading a
diff and a hard reset would have made it true by force.

**The Gate stage shows what it read, not just what it refused (PR #29, merged,
525 tests).** Sandip said the stage does not really say anything, and the fault
was not on the screen: `gate_code` recorded only its refusals, so a run it
cleared produced nothing at all and nine ticks was all there was to print. Each
check now returns the constructs it judged, the rule it judged them against,
and one of four verdicts. `cleared` and `refused` are verdicts on the code;
`no_subject` (armed, nothing here to judge) and `not_armed` (rule never
supplied) are verdicts on the check, and painting those green claims an
assurance nobody established.

That fourth state found a live hole the hour it shipped: `l3.py` called
`gate_code` without `allowed_tables`, so **CTL-PURP-01 could not fire on any L3
run** while the old screen ticked it. Armed, with a test that fails if any check
loses its rule. The panel is now the decision with its reason in both
directions, what the gate was given (grant, allowlist, scope, printed not
counted), nine cells carrying each check's count, and the read drawn on the
code as a per-line construct count. The screen no longer keeps its own copy of
the nine checks.

**Sentinel has a User Manual, under a new Help group in the sidebar.** It opens
on a nine-slide presentation and runs ten chapters behind it: quick start, the
nine stages, autonomy levels, controls, screens, roles, data, architecture,
glossary. It is a screen rather than a file in `docs/` because it describes 26
controls, 14 allowed imports, 8 datasets, 4 tiers, 6 personas and 9 stages, and
every one of those numbers is something the code already knows. The module
imports the enforcing modules and computes the cover stats at render time;
prose is owned by the manual, numbers are borrowed. `render_manual` takes
`nav_to` as an argument because `app.py` imports the manual and the cycle would
be immediate.

**Building it found the gap in that rule.** Merging main into the branch before
merging the PR surfaced it: PR #25 had added `can_view_all_runs` to `Persona`,
the manual rendered six personas with the right count, and the new entitlement
was invisible. Reading a collection live keeps the *count* honest for free and
says nothing about a *field*. Fixed in three places and pinned with a test that
counts rendered entitlement verdicts against the persona set, because a test is
the only thing that makes a live read a live claim. Two smaller finds: the
sandbox default wall clock is 30s while both governed routes passed a literal
15, now named `GOVFLOW_WALL_CLOCK_S` and pinned; and the guard test that bans a
hardcoded wall clock in `sentinel/ui/` fired on my own docstring quoting the
morning's finding, which I fixed by rewriting the prose rather than teaching
the guard to parse English. Prod also confirmed something local could not: zero
"not installed here" rows in the Bought table, so the manual is a second check
that the allowlist matches the instance. 509 tests, 2 skipped, ruff clean.

Everything below is the prior state.

---

**PR #25 deployed as bundle `sentinel-20260720-180457.zip`, EB Health Green,
health 200, root 200 in 0.66s, WebSocket 101, live-LLM key present.** Verified
by the behaviour that only exists in this build, not by health: the Data
Scientist sees 20 runs with the scope banner and a disabled "Ran by", and a
completed govflow run files its events under all eight stages that emitted one.

**Audit events now carry the stage that emitted them, and the Audit Log obeys
the access control it is about.** The screen used to print a caption on every
govflow and L3 run admitting it could not file events under a stage, because
`flow.py` records `agent="govflow"` from Ask, Plan and Access alike. Inferring
the stage from the action string was rejected: it needs a second table kept in
step with 30 call sites and it misfiles silently. So `AuditEvent` carries a
`stage` written by the call site, 22 sites in `flow.py` and 8 in `l3.py`, and
routes with no stage spine leave it empty on purpose. Separately,
`can_view_all_runs` in `personas.yaml` now scopes the ledger: oversight roles
read everything, the first line reads its own runs, the drill-down re-checks
so `?run=` is not a bypass, and the scope is announced rather than silently
applied. Re-seeding preserved all 24 run ids, so shared links still resolve.

**The Audit Log is the tenth screen: one cross-run ledger under Platform.** 24
runs and 249 committed events, every run readable as the nine governance stages
the Run screen teaches. It exists because every other audit surface in the app
is scoped to one run and dies with the session, and because a control that
fires once in a scripted demo is a demo, while one that fires across 24 runs
with the refusals countable is a control.

Three things it forced into the open. **There is no dual control anywhere in
Sentinel**: four-eyes means author-is-not-approver, single signature, no quorum
and no data structure that could hold two approvals. Sandip chose to report
that rather than build around it. **Two different refusals sit at the promotion
gate** and I had conflated them, because `approve()` tests authority before
segregation of duties, so an Analyst self-approving never reaches CTL-SOD-01.
**And CTL-TIER-01 was catalogued doc-only while `flow.py` enforced it**, so a
chip on a run it had just refused would have read "cannot fire".

The screen also had to be taught what a refusal is. Accounting first read the
seeder's `controls_fired`, which mixes in gate level, so a passing eval gate
and an APPROVED decision counted as refusals. A gate event means the control
was consulted, not that it said no. That distinction is now the shape of the
whole feature: the tiles split stopped from withheld, the filter splits the
same way, and each stage separates the controls it armed from those that fired.

**The record now survives a deploy.** `runtime/` is gitignored and excluded
from the EB bundle, and the seeder used to collapse each run to a set of action
strings, so this screen would have shipped empty while health returned 200.
`sentinel/data/seed_audit.jsonl` is committed, and prod rendering all 24 runs
on a fresh instance is the proof.

Everything below is the prior state.

---

**All five audit findings are closed: four fixed, one closed by a decision.**

The Live LLM path failed 100% of the time because the L2 allowlist advertised
statsmodels, lifelines, shap, dowhy and econml and none were installed anywhere.
The allowlist goes verbatim into the codegen system prompt, so each name is an
instruction to the model to use that package: the gate stamped "imports on the
tier's allowlist, clear" and the sandbox died with ModuleNotFoundError. All five
are dependencies now, and `tests/test_allowlist_env.py` reconciles the grant
against `requirements.txt` (what the instance pip-installs, not a local venv,
which hides the fault precisely when it matters). Installing them cost a major
version of the numerical stack: econml and numba cap pandas at 2.3.3,
scikit-learn at 1.6.1, numpy at 2.4.6, scipy at 1.15.3. **An allowlist entry is
not only a package, it is that package's constraints on everything else.** And
it cost time: shap imports in 4.2-4.6s warm and 15.5s cold, against a 10s wall
clock, so there is now a boot-time warm-up (`sentinel/sandbox/warmup.py`, a
throwaway subprocess, since the caches are on disk not in the process) and the
wall clock moved to 30s. An infinite loop dies at 30s as it dies at 10s; what
changed is that the control stopped firing on the imports. **An import grant is
also a time budget.**

The adoption bars rendered as four identical 17.2px rectangles for four
different weeks, with the inline heights correct throughout. The value label was
a flex sibling, so it took 16.8px out of a 56px column and the bar, the only
child with no intrinsic height, absorbed the whole deficit. ui-spec 4.10 had
already specified the fix ("value printed above each bar"), and following it
fixes the cause rather than making room for it. **An element whose size encodes
data must be out of the flex-shrink pool, and anything decorating it must be out
of flow.**

The six seconds of blank white was never an EB cold start; TTFB is 1.8s. It was
61 files and 2.5MB of Streamlit front end served uncompressed and uncached,
because the single CloudFront behavior is CachingDisabled with Compress:false,
which is right for the WebSocket and wrong for the bundle. `/static/*` has its
own behavior now. Compress:true alone would have done nothing: CloudFront
compresses what it caches, and CachingDisabled also drops Accept-Encoding from
the cache key.

**The fifth finding dissolved.** It was written up as the largest hole: the gate
clears nine checks on the default path and never refuses, so its best capability
is asserted rather than shown. Both halves of that were wrong. The gate is right
to clear a benign request, since blocking it would be a false positive, which
this build treats as costing as much as a missed block. And the refusal is not
missing: three adversarial requests are wired into the L2 analysis dropdown and
three at L3, each real code with a real violation, nothing seeded. The finding
reduces to "the default selection is the benign one". Sandip's call: drive two
demos, happy path then adversarial. Nothing to build.

**The thread through all five: this build states claims in prose that nothing
holds it to.** The allowlist named packages nothing installed. The Execute panel
claimed a 15s wall clock while the code enforced 10. The stepper doc listed
DoWhy, lifelines and SHAP as permitted directly under its own rule to claim only
libraries that actually run. The fix in each case was to make the claim read
from the thing that enforces it.

Everything below is the prior state: v10 in prod, audit findings open.

---

**v12 is merged to main but NOT deployed. The Registry screen now says what
each agent does and what the three registries on it are. Note that the v12
entry below, and the v10 block under it, both say the cold-visit audit is
untouched. That was true when each was written and is not now: all five findings
are fixed or closed, in the section above.**

v12 (PR #18, `a924ffe`) started from Sandip asking what the agents on the
Registry screen actually do, and what the difference is between Models, Agents,
and Analysis-agents. The second question is the finding: he commissioned the
build and could not tell three registries apart on one page, because one
subtitle covered all three and described two of them. They are not variations
of one idea. **A model is what a run produces. An agent is a worker inside a
run. An analysis-agent is what a run is allowed to be**, the certified unit the
Plan stage binds, which the four agents then execute. The analysis-agent
section opens by saying it is not the four agents above, since that collision
is what caused the question.

Each agent's one-line description lives on the agent class as a `does`
attribute and the registry reads it off the class, rather than a dict of
descriptions in `registry.py` that would drift from the code it describes. The
agents table gained a "what it does" column and shows the human title under the
agent id. Left alone deliberately: eda's tools column shows the template's
allow-list including `profile_dataset`, which eda never calls (honest as a
scope, misleading as a description), and `AGENT_LINEAGE` still duplicates each
agent class's `template` attribute, because deduping it would close an import
cycle through `agents/runtime.py`. 391 tests.

**v11 is merged to main but NOT deployed. The Datasets surface gained a data
contract view: a catalogue that publishes schema, roles, foreign keys and
descriptions, and deliberately publishes no values.**

v11 (PR #19, `4e106ec`) answers a question Sandip asked while proposing an
"Explore this dataset" button: would an EDA view violate the governance we have
built. It would, in four places. Purpose limitation gates Access on *why* and an
Explore button carries no purpose (six of eight datasets are Restricted or
Confidential). The autonomy ceiling caps Confidential data at L1, so free-form
exploration of Berka is above the ceiling by construction. The column grant
builds a scoped table so a withheld column does not exist on the object the code
receives, and a view rendering every column puts back exactly what minimisation
removed (`applicant_email`, `applicant_ssn`, `sex`, raw `age_years`). The
disclosure screen suppresses grouped cells under the k-anonymity floor, and a
value-counts panel is a grouped count.

So the drill-down is the **catalogue layer** instead, which is the thing banks
actually run and the thing this platform was missing. Metadata is published far
more widely than data: you read the contract to decide what to request, then
declare a purpose to get values. Each registry row ends in a Contract button
opening provenance, license, classification and the tier ceiling it sets; the
permitted and refused purposes read off the same `PURPOSE_MATRIX` CTL-PURP-01
enforces; rows at source vs rows onboarded; tables with row counts; foreign keys
with cardinality; and the column dictionary (name, logical type, role,
description, `derived` tag) under a legend saying what each role costs at Access.
No values, no samples, no distributions, no missingness, no cardinality.

Missingness and cardinality look like metadata but are computed from values, so
they stay with the governed `data_profiling` analysis. The catalogue knows the
shape; the profile knows the contents; only the profile is data access. Type
inference reads a bounded 200-row head, and a test checks every published string
against the file's real first rows so that stays true. 406 tests, ruff clean.


---

**v10 is merged and LIVE in prod: a small chrome pass. The bigger news is not
in it. A cold-visit audit of the live site found that the Live LLM path fails
100% of the time and prints a Python traceback on screen, because the codegen
allowlist advertises packages that are not installed. Nothing from the audit is
fixed yet.** *(Superseded 2026-07-20 13:10: all five closed on PR #17, not yet
deployed.)*

v10 (PR #14, `58e51dd`, bundle `sentinel-20260720-111254.zip`) is three things.
The sidebar group headers were being painted over by the first nav row in each
group: Streamlit puts `margin-bottom:-16px` on every `stMarkdownContainer` to
cancel the 16px a markdown `<p>` carries, `.gl` is a bare div with a 6px bottom
margin, so the -16px over-pulled by 10px and dragged the row up over the label,
which then painted its hover/active background across the group name. Six other
custom divs sit in the same over-pulled state and none are occluded, because a
nav row is the only thing in the app that paints a background over the element
above it. One bug, not seven. The topbar Data and Purpose chips are gone from
every screen (duplication: since v9 the Ask row carries the classification and
the permitted purposes where they are actionable). The identity chip was removed
in the same pass and put back deliberately, because switching persona is the only
in-app way to demonstrate the autonomy ladder. Sidebar nav counts are gone.

**The audit findings, none fixed.** In priority order:

1. `sentinel/codegen/allowlist.py` advertises `statsmodels.api`,
   `statsmodels.formula.api`, `lifelines`, `shap`, `dowhy`, `econml` at L2 and
   **none are in `requirements.txt`**. `statsmodels` is installed locally as a
   transitive dependency, so it passes here and dies on the instance. The Gate
   stamps "imports on the tier's allowlist, clear" and Execute throws
   `ModuleNotFoundError`. The governance half matters more than the crash: the
   gate approved code the sandbox could not run.
2. The Adoption bar chart on the landing tile renders four identical flat
   rectangles. The column needs ~78px for value + bar + caption, the chart gives
   it 56px, and `.bar` has default `flex-shrink`, so every bar squashes to 17px
   regardless of value.
3. An L0 persona is told to "switch persona in the sidebar"
   (`sentinel/ui/govflow.py:1365`). Identity moved to the topbar in v7.
4. Six seconds of blank white on a cold load. Streamlit's bundle, not an EB cold
   start: TTFB is under a second.
5. **Not a bug, the biggest gap:** on the default path the gate never refuses
   anything. Nine checks, all clear, every time. The most compelling thing in
   the build is a gate refusing generated code by name, and a visitor following
   the obvious path never sees it fire. The claim is asserted, not shown.

Everything below is the prior state: v9 in prod.

---

**v9 is merged and LIVE in prod. The Ask stage's dataset table is now the
control rather than decoration beside one, and every dropdown in the stage
explains what it is offering.**

The fault v9 fixed: step 1 showed a two-row dataset table and, underneath it, a
radio that chose between two *analyses*. The table was decoration; to pick
`german_credit` you selected "Fair lending (german_credit)" from a list sitting
below the row describing `german_credit`.

Now each row carries a one-option radio labelled with the dataset id, so the row
is the select control. Exclusivity across rows is a callback (Streamlit has no
radio group spanning containers), so it has a test. The chosen row wears the
`.row-sel` tint and `.rowgood` left bar, both in ui-spec 4.4 and neither ever
built. Under the table, the mockup's `.pmatrix`: all six purposes for the picked
dataset, permit or refuse, read off `PURPOSE_MATRIX`. **Confirm Dataset** is
load-bearing, not cosmetic: steps 2 and 3 do not render until it is pressed, and
changing the pick drops the confirmation and clears the drafted question, because
a purpose and an analysis are declared *against* a dataset.

Step 2's options are sentence case (the policy module keeps its lowercase labels,
which get dropped mid-sentence into refusals; the UI capitalises for a dropdown),
with a block stating what the purpose covers and what it does not, from
`PURPOSE_SCOPE` in `purpose_matrix.py`. Step 3 is renamed "Select the Analysis"
and states the method and the libraries that genuinely run: `fairlearn.metrics`
for the benign L2 case, duckdb + sqlglot for the SQL route, pandas/numpy/
`statistics` for the L3 difference-in-differences. Adversarial requests say
nothing runs and name the control that refuses them. Those control ids are not
asserted: a test re-runs the real gate over every scripted sample and fails if a
note names a control the gate does not fire.

Rejected deliberately: `st.dataframe` with `selection_mode="single-row"`. It is
the only real row click Streamlit offers, but a dataframe cell is plain text, so
taking it would have cost the classification popover that 4.3 requires. One day
after settling that rule, deleting a chip to get a nicer click was not on.

PR #13 merged (`c0b8655`). Deployed bundle `sentinel-20260720-104529.zip`, EB
Green, live-LLM on, verified by walking the live step and running
`e168559a3501` through all nine stages at tier L2 with 3 controls fired. 392
tests, ruff clean.

Two operational traps found. **The deploy folder was three days stale:**
`~/Developer/sentinel` sat on `docs/v6-deploy-record`, 16 commits and ~400 lines
of `app.py` behind main, and a deploy from it would have shipped v6 while
reporting success. It cannot simply hold `main` either, because another worktree
has `main` checked out and git refuses the same branch twice. It is detached at
the deployed commit now. The structural trap remains: the folder holding the only
copy of the live-LLM key is the folder nothing keeps current. **And the
permission classifier blocked `gh pr merge` and `gh api` on the merge endpoint**
(yesterday it blocked only `--delete-branch`), so a ready PR could not be landed
until Sandip enabled it.

Deferred still, all by choice: dark mode, RBAC-gated navigation, B-style
contextual drawers. Drift monitoring still has no stage in the lifecycle and is
the largest genuine hole. `app.py` is past 2,300 lines with a hand-rolled router.

Everything below is the prior state: v8 in prod.

---

**v8 is merged and LIVE in prod. Every control chip in the app now explains
itself through one mechanism, and OPA externalisation is out of scope for the
foreseeable future, which closes the last open fork.**

The gap v8 closed: a chip naming a control sometimes opened an explanation and
sometimes did nothing, with no rule for which. `_control_popover` (the 27-entry
ControlInfo catalogue, plus an "In this run" line off the published stage
output) was already right and already proven at three call sites, while the
engine bar built dead `ctlchip` spans thirty lines below it. The rule, now in
ui-spec 4.3: **a chip is clickable when it names a governance decision, inert
when it names a fact.** Wired accordingly: the engine bar on all nine stages,
the Architecture stop, the import allowlist (grouped by the control that denies
each row, one chip per row, not per module), the topbar Data and Purpose chips
(both onto CTL-PURP-01, whose two axes they name), the certification gate rows,
and the Screen stage's PII finding. Deliberately not wired: the chips inside the
global Controls popover, since Streamlit's guidance is not to nest popovers and
that surface is the see-everything catch-all.

Datasets and both Registry tables were rebuilt from `st.dataframe` into hand-laid
header-band plus `st.columns` tables, because a dataframe cell cannot hold a chip
or a popover. Clickable: each dataset's classification, each model's status (onto
the eval gate, carrying that model's own numbers), and the agent table's tools
and rbac-scope column headers. Cost recorded rather than glossed: dataframe
sorting and column resizing are gone from those three tables.

Found while scoping that: the dataset registry had **no classification column at
all**, despite ui-spec 3.4 listing one. Added, with the class-count breakdown row.
`CTL-CODE-00` and `CTL-DISC-03` were also missing from their stages' engine
lists. The topbar's move to a single flex row fixed the identity trigger clipping
to "Acting as: Data Sci...".

PR #11 merged (`df353d8`). Deployed bundle `sentinel-20260719-151623.zip`, EB
Green, live-LLM on, verified on the live site: the Data chip opens the real
CTL-PURP-01 entry, the dataset registry shows 8 rows with 8 clickable
classification chips and zero surviving dataframes. 382 tests, ruff clean.

Deploy gotcha worth keeping: the deploy script reads the live-LLM key from
`$REPO_ROOT/.env`, which is gitignored and therefore absent from every worktree.
Deploying from a worktree without passing it through sets the CFN parameter empty
and silently reverts prod to scripted narration, with health still green.

Deferred still, all by choice: dark mode, RBAC-gated navigation, B-style
contextual drawers. Drift monitoring still has no stage in the lifecycle and is
now the largest genuine hole. `app.py` is past 2,000 lines with a hand-rolled
router.

Everything below is the prior state: v7 in prod.

---

**v7 is merged and LIVE in prod. It is a chrome pass on top of v6, and the
theme is that the app shell no longer claims what the page cannot back up:
one identity surface, a warning badge that only warns, context chips that
appear only where a run is in scope, and a nav rail with the mockup's rhythm.**

Two PRs merged and deployed. **PR #8**: identity consolidated into the header's
Acting as popover (the sidebar block is gone), the Tier chip removed from the
global bar because tier is run-scope, the decorative green governed badge
replaced by a warning that shows only when a control is off, plus Material nav
icons and an in-app Back control. **PR #9**: the Data and Purpose chips are now
run-scoped (Run takes them from the published run else the draft config; the
credit pipeline shows Data only, since an orchestrator run declares no purpose;
every other screen shows none, instead of the old hardcoded german_credit and
fair-lending fallback), and the sidebar rhythm matched to the mockup's sidenav
(Streamlit's 16px block gap zeroed, rows stack flush, air only at group
boundaries: the rail went 590px to 410px for the same eight items).

Deployed bundle `sentinel-20260719-133917.zip`, CloudFormation applied, EB Ready
and Green, live-LLM on. Verified by clicking through the live site: Overview
renders with no chips, Run shows Data german_credit RESTRICTED plus Purpose fair
lending review, the rail is the tight version, and a nav click reruns the
script. 371 tests pass, ruff clean. ui-spec 2.1 and 2.2 updated to the as-built
chrome.

Deferred still: dark mode, RBAC-gated navigation, B-style contextual drawers,
OPA externalisation (waits on Sandip; an earlier note in this session called it
killed, which was wrong and is corrected in the latest entry). *Superseded
2026-07-19 15:22: Sandip put OPA out of scope for the foreseeable future. See
Things ruled out.* The W29 summary is written. Drift monitoring still has no
stage in the lifecycle.

Everything below is the prior state: v6 in prod.

---

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

- [2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md](entries/2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md) — the Pipeline screen is retired and its evidence moved to the stage that owns the question it answers. Merged with the Agent Templates branch and deployed: `sentinel-20260721-002533.zip`, `main` at `7e51602`, EB Green, 665 tests. Each tab faced one test, **does the surviving route produce the data and does a stage own the question**, because a panel that renders an empty state forever is a discard with extra steps. Ledger to Generate, raw result to Execute (unscreened, so Screen next door reads as a control acting on it), fairness merged into Interpret since the result contract already forces a selection rate per group and only the vocabulary was missing, cost to header chips, Audit Log links out. **The finding is that all of it was already computed and discarded at the door**: `ledger_dicts()` existed, the loop already summed tokens, `_narrate` already divided two rates, and `to_public_dict` dropped them. The retired screen had earlier data, not better data. **Model Card went to the Registry against the plan**, because no govflow run trains a model so an Attest conditional would never fire, which also fixed the anchor. Fairness reads the *screened* frame and names the suppressed bands, or CTL-DISC-02 would be decorative. **Live runs reached the Audit Log for the first time** and two bugs fell out, both found by clicking: an `on_click` callback calling `st.rerun()` (a lesson already written down at the Overview tiles), and a record filing the persona display name where `visible_runs` compares ids, refusing an analyst their own run. Toggles are read-only and the UNGOVERNED badge is gone, their only consumer having been the retired Run button. Re-seeded all 24 runs for `model_card` and real cost, ids preserved. And the first genuine parallel-session conflict, in the nav list, resolved in a minute because it landed in the file that had just been extracted.
- [2026-07-21-0015-a-template-you-can-be-refused-by.md](entries/2026-07-21-0015-a-template-you-can-be-refused-by.md) — Agent Templates under Governance: an editable YAML spec, eleven checks, and a Deploy that registers a draft. Sandip asked for the section and asked what shape and format it should take; both answers were already in the repo. **YAML because `scaffold.py` already writes an agent spec in YAML** and a JSON template would have meant the CLI and the screen emitting two artifacts for one object. **Editing has to be refusable or it is decoration**, and the way out is that a template names nothing of its own: every field is a value some other module owns, so the editor keeps no policy and reads the enforcing modules instead. Checks reuse `CheckReading`/`Observation` from `codegen/gate.py`. **Policy checks are the fence and certification gates are not**: a policy refusal disables the deploy, a failed gate blocks `certified` and not the draft, which is why all five templates ship at `owner: UNASSIGNED` and deploy fine. Making those block would have put the CLI and the screen in disagreement about day one of an agent. **Deploy is `certification.register()`** with the SHA computed now, verified end to end: deployed the validation template and found `validation v1.0 — DRAFT` under Analysis-agents. The fourth verdict earned its keep again unprompted: flipping a purpose from `fair_lending` to `marketing` in the editor turned the column check amber, because `fair_lending` is the only purpose with a defined grant, so the check reported a hole in the policy on a screen built to check templates. And **the tenth nav item made `manual.py` wrong** — a typed "Nine screens" that nothing failed on — so the nav moved to `sentinel/ui/nav.py` and the count is computed. 654 tests. Not deployed.
- [2026-07-20-2045-refuse-first-then-retrieve.md](entries/2026-07-20-2045-refuse-first-then-retrieve.md) — Help gained an FAQ and "Ask me", a chat that answers only from the manual. PR #33, merged, deployed as `sentinel-20260720-200636.zip`, EB Green, 606 tests. **The ordering is the feature.** Sandip asked for a relevance test *before* the answer, and the obvious build (retrieve, then let the model decline) fails on exactly the question he chose: a model handed five passages about governance stages and a question about Indian politics will try to bridge them, and the bridge is where a confident falsehood gets built. On prod the live gate refuses it for 175 tokens and $0.0002 with no answer call made. **Three verdicts, not two**, because off-topic and on-topic-but-uncovered are different facts and the second is a gap in the manual that should read like one; same distinction as `NOT_IN_ROUTE` versus `skipped`. **The corpus is a second source of truth, chosen knowingly.** I recommended extracting text from `manual.py` at render time under a recording `st` shim (cannot drift); Sandip picked parallel markdown. The fence is the numbers rule: markdown can read nothing, so the corpus may not restate an enforced value, and `test_corpus_states_no_enforced_number` reads the sandbox caps, disclosure floor and control/persona counts live and fails any page that retypes one. Prose can still drift, and that degradation is survivable in a way a stale cap is not. **The scripted gate needed a second test**: cosine alone answered "Write me a poem about the sea", because a corpus that talks about writing code has plenty of "write" in it, so vocabulary coverage now runs beside it. Also `ModelGateway.complete()`, since Help gets no private path to a model. And I burned a build first: there was no Help section on my branch because the manual was an unmerged PR I never checked for, so I wrote a whole parallel manual against a product that already had one. Checking `origin/main` costs one command.
- [2026-07-20-2010-the-guard-checks-head-the-bundle-is-the-tree.md](entries/2026-07-20-2010-the-guard-checks-head-the-bundle-is-the-tree.md) — deployed PR #29, #30 and #32 as `sentinel-20260720-191009.zip`, EB Ready and Green. **The interesting part happened before the deploy ran.** The rule I have carried since the v6 near-miss is do-not-deploy-from-a-checkout-not-on-`main`, and there is an open question here about making `deploy.sh` enforce it. I ran that check and it passed: `HEAD` was `29ad22b`, exactly `origin/main`. Then `git status` showed nineteen files staged with 2,699 deletions, a full revert of all three merges sitting in the index. **`deploy.sh` archives the working tree, not `HEAD`,** so the bundle would have shipped without the Gate read or the Live LLM fix, gone Green, and reported success. The guard I had been designing checks the wrong noun. It needs two clauses: `HEAD` is an ancestor of `origin/main`, *and* `git status --porcelain` is empty. Stashed rather than reset, because "nothing here is new" was a conclusion from reading a diff and a hard reset would have made it true by force. Verified prod by the thing that cannot render on the old bundle, and specifically by running **two** requests: the benign L2 run draws 7 green and 2 dashed grey, the SQL wildcard draws 1 red, 7 green, 1 dashed, with `SELECT *` as the refused chip. The same nine cells drawing a different shape on different code is the whole claim the panel makes. PR #30 is shipped but only exercised through the scripted path; confirming the Live LLM fix means a real model call, so it is deployed, not demonstrated.
- [2026-07-20-1930-nine-ticks-over-nine-unequal-checks.md](entries/2026-07-20-1930-nine-ticks-over-nine-unequal-checks.md) — Sandip said the Gate stage does not really say anything, and **the screen could not have done better**: `gate_code` recorded only its refusals, so a cleared run produced literally nothing and the nine-row "clear/clear/clear" table was the whole of what existed to print. The gate now records what it read. **Four verdicts, not two,** because there are four facts: a check that judged 16 constructs and permitted them cleared the code; a check with nothing here to judge cleared nothing; a check whose rule was never supplied did not run. Only the first two are verdicts on the code. That distinction paid for itself the same hour: `l3.py` called `gate_code` without `allowed_tables`, so **CTL-PURP-01 had no scope to test against and could not fire on any L3 run** while the screen ticked it. The visualization is nine cells carrying each check's count (a tick cannot tell 16 from 0, a number can), plus the read drawn on the code as a per-line construct count, because tinting the refused line shows where the gate said no and not where it looked. The verdict states a reason in both directions: an approval that says "no violations" is an assertion, which is what this stage exists to replace. Also **the screen was keeping its own copy of the nine checks** with nothing holding the gate to it, the fourth instance of that fault in this build. And I caught myself doing the same thing one level up: the verdict read "judged 61 constructs" while the gutter beneath it summed to 27, because 61 is judgements and 27 is constructs. Both are stated now. PR #29, 525 tests, merged, not deployed.
- [2026-07-20-1840-a-live-count-is-not-a-live-claim.md](entries/2026-07-20-1840-a-live-count-is-not-a-live-claim.md) — the User Manual shipped as a screen under Help, opening on a nine-slide deck, ten chapters behind it, PR #28 merged as `3e15f84` and deployed. It is a screen because it describes numbers the code already knows, so it imports the enforcing modules instead of restating them. **The lesson is where that rule leaks.** PR #25 had added `can_view_all_runs` to `Persona`; the manual read personas live, kept the count right, and rendered the new entitlement nowhere. A live read keeps a *count* honest for free and says nothing about a *field*, so the fix is a test that counts rendered entitlement verdicts against the persona set. Found by merging main into the branch before merging the PR, which is the argument for doing that. Also named `GOVFLOW_WALL_CLOCK_S` (the sandbox default is 30s, both governed routes passed a literal 15, every surface printed 30), and rewrote a docstring that tripped the hardcoded-wall-clock guard, because a blunt guard firing on a false positive costs one edit and a clever one missing a real caption costs the claim.
- [2026-07-20-1813-prod-carries-the-scope.md](entries/2026-07-20-1813-prod-carries-the-scope.md) — deployed PR #25, bundle `sentinel-20260720-180457.zip`, EB Green, prod in sync with `main` at `174df5e`. Two things worth keeping. **The deploy is not incremental**, so batching merges into one deploy is free in effort and costs bisection: the previous deploy carried four changes after three stale sessions, this one carried a single tested change. That is the argument for deploying on merge, and it holds only while merges stay small, which is the same reason the `app.py` split matters. And **verification used the behaviour that only exists in the new build**, because health 200 passes on the old bundle: Streamlit answers that endpoint before `app.py` runs, which is how the first prod deploy returned 200 with every page broken. Checked the scope banner, the disabled "Ran by", and events filed under all eight stages. A deploy is verified when the change is visible, not when the instance is up.
- [2026-07-20-1758-the-caption-was-the-bug.md](entries/2026-07-20-1758-the-caption-was-the-bug.md) — the two Audit Log follow-ups, merged as PR #25. **An honest caption is still a gap:** the screen admitted it could not file govflow/L3 events under a stage, and that admission made the gap tolerable enough that I stopped looking at it. Inferring the stage from the action string was rejected because it needs a second table kept in step with 30 call sites and misfiles silently, which on an audit surface beats an admitted absence. So `AuditEvent` carries a `stage` written by the call site: 22 edits in `flow.py`, 8 in `l3.py`, empty on routes with no stage spine and a test asserting they leave it empty. Considered a context manager on the log (9 edits not 30) and rejected it: flow.py's stages are sequential top-level code with early returns, and explicit-per-site reads better in a governance file. Second: **the screen about access control had none**, so `can_view_all_runs` now lives in `personas.yaml` defaulting to deny, one `visible_runs()` predicate scopes the rows, the filter options and the drill-down, and the drill-down is the one that matters because `?run=` would otherwise be the bypass. The scope is announced rather than silently applied, and a withheld run says it exists. Re-seeding preserved all 24 run ids by plan slot, five lines that saved every bookmarked link. 494 tests. Also checked the other ten worktrees expecting to sequence around parallel work: there is none, nine are idle and two branches are dead. **Long-lived worktrees over a 3,400 line `app.py` do not produce parallel work, they produce abandoned branches.**
- [2026-07-20-1655-what-counts-as-a-refusal.md](entries/2026-07-20-1655-what-counts-as-a-refusal.md) — the Audit Log ships; what counts as a refusal, and no dual control anywhere.
- [2026-07-20-1410-a-list-that-granted-what-nothing-installed.md](entries/2026-07-20-1410-a-list-that-granted-what-nothing-installed.md) : all five audit findings closed in one session, four fixed and one dissolved. **The allowlist granted five packages nothing installed** (statsmodels, lifelines, shap, dowhy, econml), and since the list goes verbatim into the codegen prompt, the model took the instruction, the gate stamped the imports clear and the sandbox died with `ModuleNotFoundError`: a control that approved what the environment refuses. Reproduced at the seam before touching it. I fixed it by dropping the four unused ones; Sandip reversed it to install them, correctly, since the defect was never which side moved. That cost a major version of the numerical stack (econml/numba cap pandas at 2.3.3, sklearn 1.6.1, numpy 2.4.6, scipy 1.15.3) and it cost time: shap is 4.2-4.6s warm and 15.5s cold against a 10s wall clock, hence `sentinel/sandbox/warmup.py` and a 30s cap. **An import grant is also a time budget.** The adoption bars: correct inline heights thrown away by a flex-shrink squash, fixed by following ui-spec 4.10, which had specified the fix all along. **An element whose size encodes data must be out of the flex-shrink pool.** The six-second blank was 2.5MB of Streamlit bundle served uncompressed and uncached by a CloudFront behavior built for the WebSocket; `/static/*` split out, and `Compress:true` alone would have done nothing under CachingDisabled. **The fifth finding dissolved under Sandip's question**: the gate is right to clear a benign request, the adversarial requests are already wired and genuine, and the whole thing reduced to which option is selected by default. He drives two demos instead. The thread through all five: claims stated in prose that nothing holds to them, including a caption claiming a 15s wall clock while the code enforced 10. 423 tests. PR #17, not yet deployed.
- [2026-07-20-1345-three-registries-under-one-heading.md](entries/2026-07-20-1345-three-registries-under-one-heading.md) : Sandip asked what the agents on the Registry screen do, and what the difference is between Models, Agents, and Analysis-agents. **The second question is the finding:** the person who commissioned the build could not tell three registries apart on one page, because one subtitle covered all three and described two. Rewritten around what each thing is in a run: a model is what a run produces, an agent is a worker inside a run, an analysis-agent is what a run is *allowed to be* (the certified unit Plan binds, which the four agents execute). The analysis-agent section now opens by saying it is not the four agents above. Each agent's description lives on the agent class as `does` and the registry reads it off the class, because a dict of descriptions in `registry.py` is a copy of a fact and copies drift; same rule the model-status popover already follows. Left alone: eda's tools column shows the template allow-list including a tool eda never calls, and `AGENT_LINEAGE` duplicates each class's `template` (deduping closes an import cycle through `agents/runtime.py`). Two verification traps: `--server.fileWatcherType none` means Streamlit never recompiles the script, so a browser reload re-runs the *old* source and a real edit looks inert until the server restarts; and the full suite run alongside the live app failed 6 tests in 651s that all passed in 116s once the server stopped, so read the runtime before reading the failures. PR #18, `a924ffe`, 391 tests. **Not deployed; prod is still v10.**
- [2026-07-20-1338-the-catalogue-is-not-a-data-browser.md](entries/2026-07-20-1338-the-catalogue-is-not-a-data-browser.md) : Sandip proposed an "Explore this dataset" button on the Datasets surface and asked, in the same message, whether it would violate the governance we have built. It would, in four places: purpose limitation (Access gates on *why*, and Explore carries no purpose; six of eight datasets are Restricted or Confidential), the autonomy ceiling (Confidential caps at L1, so free-form exploration of Berka is above the ceiling by construction), the column grant (Access builds a scoped table so a withheld column does not exist; a full-column view puts back `applicant_email`, `applicant_ssn`, `sex`, raw `age_years`), and the disclosure screen (a value-counts panel is a grouped count, and cells under the floor get suppressed). Built the **catalogue layer** instead, which banks actually run and this platform lacked: a Contract button per row opening provenance, license, classification + tier ceiling, permitted/refused purposes off the real `PURPOSE_MATRIX`, rows at source vs onboarded, tables, foreign keys with cardinality, and the column dictionary (name, type, role, description, `derived` tag) under a role legend. **No values, no samples, no distributions, no missingness, no cardinality:** those are computed from values, so they stay with the governed `data_profiling` analysis. The catalogue knows the shape; the profile knows the contents; only the profile is data access. Types come from a bounded 200-row head and a test checks every published string against the file's real first rows. Synthetic PII is published, marked `pii` + `derived`, rather than hidden. Documentation coverage is reported not smoothed: german_credit 100%, lendingclub 40 of 152. PR #19, `4e106ec`, 406 tests. **Not deployed; prod is still v10 with the Live LLM path broken.**
- [2026-07-20-1121-chrome-recedes-and-an-audit-finds-the-landmine.md](entries/2026-07-20-1121-chrome-recedes-and-an-audit-finds-the-landmine.md) : demo prep for the hiring manager, which turned into a chrome pass plus a cold-visit audit of the live site. The chrome (PR #14, `58e51dd`, v10): sidebar group headers were being painted over by the first nav row in each group, because Streamlit's `margin-bottom:-16px` on `stMarkdownContainer` exists to cancel a markdown `<p>`'s 16px and `.gl` is a bare div with 6px, so it over-pulled 10px; six other divs are over-pulled the same way and none are occluded, since a nav row is the only thing that paints over the element above it. Topbar Data/Purpose chips removed everywhere (duplication after v9 put both on the Ask row); the identity chip was removed too and **put back**, because switching persona is the only in-app way to show the ladder. Sidebar counts removed. Merged against a v9 that landed mid-session by resetting onto main and re-applying, rather than resolving markers. Deployed and verified live. 386 passed, 3 skipped. **The audit is the real output and nothing from it is fixed:** the codegen allowlist advertises statsmodels/lifelines/shap/dowhy/econml at L2 and none are in `requirements.txt`, so the Live LLM path fails 100% in prod with a visible `ModuleNotFoundError` while the Gate stamps the imports clear; the Adoption chart renders four flat bars from a flex-shrink squash; an L0 persona is pointed at a sidebar that has not held identity since v7; and on the default path the gate never refuses anything, so the headline claim is asserted rather than shown. prod is v10.
- [2026-07-20-1055-the-row-becomes-the-control-v9.md](entries/2026-07-20-1055-the-row-becomes-the-control-v9.md) : the Ask stage stopped showing information beside a control that ignored it. Step 1's dataset table is now the control: a one-option radio per row labelled with the dataset id, exclusivity enforced in a callback (and tested, since Streamlit has no radio group spanning containers), the `.row-sel` tint and `.rowgood` bar built for the first time, and the mockup's `.pmatrix` showing all six purposes for the picked dataset off the real matrix. **Confirm Dataset gates steps 2 and 3** and changing the pick clears the drafted question, because a purpose and an analysis are declared against a dataset. Step 2 sentence-cased with a covers/excludes block from a new `PURPOSE_SCOPE` in the policy module; step 3 renamed "Select the Analysis" and stating method + libraries that genuinely run, with the refusing control named. Those ids are re-derived from the real gate by test rather than asserted. Rejected: `st.dataframe` single-row selection, which is a real row click but would have cost the classification popover 4.3 requires. Table helpers extracted to `sentinel/ui/tables.py`; `govflow_mode` deleted (the L3 route is now the synthetic_its row). PR #13, bundle `sentinel-20260720-104529.zip`, EB Green, verified live by run `e168559a3501`. 392 tests. Found: the deploy folder was 3 days stale, and the permission classifier now blocks `gh pr merge` outright. prod is v9.
- [2026-07-19-1522-chips-that-explain-themselves-v8.md](entries/2026-07-19-1522-chips-that-explain-themselves-v8.md) : closed the control-chip gap and got a decision on OPA. The rule, now in ui-spec 4.3: a chip is clickable when it names a governance decision, inert when it names a fact. `_control_popover` was already the right mechanism and already proven at three sites while the engine bar built dead spans thirty lines below it. Wired: engine bar (all nine stages), Architecture stop, import allowlist (grouped by the control that denies each row, four popovers not thirty-six), topbar Data/Purpose chips (both onto CTL-PURP-01, whose two axes they name), certification gate rows, the Screen PII finding. Not wired, deliberately: the chips inside the Controls popover, since popovers should not nest. Datasets and both Registry tables rebuilt off `st.dataframe` into hand-laid tables so cells can carry chips; cost is lost sorting. Found on the way: the dataset registry had no classification column at all, and CTL-CODE-00 / CTL-DISC-03 were missing from their engine lists. PR #11, bundle `sentinel-20260719-151623.zip`, EB Green, verified live. 382 tests. **OPA externalisation ruled out by Sandip: not in scope for the foreseeable future.** prod is v8.
- [2026-07-19-1354-chrome-that-tells-the-truth-v7.md](entries/2026-07-19-1354-chrome-that-tells-the-truth-v7.md) : a chrome pass, all of it the same theme: the shell claiming what the page could not back. PR #8 (identity in one place, the header popover; tier off the global bar; the green governed badge becomes a warning that only warns; nav icons + in-app Back). PR #9 (Data/Purpose chips scoped to screens with a run, no more hardcoded german_credit/fair-lending on the dashboard and catalogs; sidebar rhythm matched to the mockup, 590px rail to 410px by zeroing Streamlit's 16px block gap). Deployed bundle `sentinel-20260719-133917.zip`, EB Green, live-LLM on, verified by clicking through the live site. 371 tests. ui-spec 2.1/2.2 updated. Also corrects my own earlier claim that OPA externalisation was killed: it was not, it still waits on Sandip. prod is v7.
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

- **When one surface can show something no other surface can, check whether it has better data or only earlier data.** Found 2026-07-21 retiring the Pipeline screen. I budgeted for new instrumentation and wrote almost none: the gateway ledger, the token and dollar totals and the disparity ratio were all already computed inside the run, and `to_public_dict` discarded them on the way out. The retired screen was not better designed, it was the last thing holding the object before the boundary. The diagnostic is cheap: when a panel looks uniquely capable, read the serialization layer between it and everything else before crediting the panel. The related rule is that **a serialization boundary is a policy decision nobody writes down**, since deciding what leaves a result object silently decides what every future surface is allowed to say.
- **A guard on `HEAD` says nothing about what gets shipped.** Found 2026-07-20, one command before a deploy. `deploy.sh` zips the repo root, so the artifact is the working tree; `HEAD` is only where the branch label points. They agree exactly when the tree is clean and nothing was checking that, so a checkout sitting on the right commit with a full revert staged in its index passed every check I had. The general form: **verify the artifact, not the pointer to it.** Same shape as health-200-is-not-a-verified-deploy, which is also a check on the wrong noun, and the same shape as the gate recording refusals instead of reads. This build keeps finding it, and the tell is always that the passing case carries no evidence.
- **A control that records only its refusals cannot be audited on the runs it cleared.** Found 2026-07-20 in the gate, one layer below where the Audit Log found the same shape a session earlier. `GateResult` was `passed` plus violations, so a clear verdict carried no evidence and the screen had nothing to render but a tick. The rule generalises past this build: **a control has to record what it examined, not only what it rejected**, because the passing case is the common case and it is the one a reviewer cannot check. The corollary is that the states must not collapse. Judged-and-permitted, nothing-here-to-judge, and rule-never-supplied are three different facts, and only the first is an assurance about the code; a screen that paints all three green is claiming coverage nobody established. Worth testing every other control surface in this build against the question "what does this say on a run where nothing fired".
- **Show the size of the read, and make it checkable against itself.** Same session. Nine ticks could not distinguish a check that judged sixteen constructs from one that judged none, and a count can, which is what turned the Gate panel from a badge into a reading. But the moment there are two related numbers on a screen they must be labelled as two: the verdict said "judged 61 constructs" while the per-line gutter below it summed to 27, because 61 counts judgements (one import is judged by four checks) and 27 counts constructs. A reader who checked the screen against itself would have found it off by more than a factor of two, on the one screen whose argument is that its numbers can be checked.
- **Reading a collection live keeps the count honest and says nothing about a field.** Found 2026-07-20 building the User Manual. The manual imports every enforcing module rather than restating its numbers, which is the right rule and covers exactly one axis of drift: add a persona and the page notices, add a *property* to every persona and it does not, because nothing in the render enumerates properties. `can_view_all_runs` landed in `Persona` on PR #25 and the manual went on describing five entitlements. The fix is not more live reading, it is a test that counts what the page rendered against the shape of the source. Any surface derived from a collection needs one test for the count and one for the fields, and the second is the one nobody writes. The general form: **deriving text from code protects you from the edits you make to the code you are looking at, not from the edits someone makes to its shape.**
- **An honest caption about a gap is a way of living with the gap.** Found 2026-07-20. The Audit Log admitted, on every govflow and L3 run, that it could not file events under a stage. The admission was accurate and I felt fine about it for a whole session, which is exactly the problem: saying what you cannot do buys enough credibility to stop working on it. Worth re-reading every "we cannot do X because Y" caption in this build and asking whether Y is a fact about the world or a thing nobody has fixed yet. The related rule, for audit surfaces specifically: **prefer an admitted absence to a silent inference**, because an inference table drifts from its 30 call sites and misfiles quietly, and a governance record that is quietly wrong is worse than one that is loudly incomplete. Both halves of that matter. The first says fix the gap; the second says do not fix it by guessing.
- **A claim stated in prose is not a control; it drifts the moment nothing enforces it.** Found three times in one session (2026-07-20): the L2 allowlist named five packages that were installed nowhere, the Execute panel's caption claimed a 15s wall clock while the code enforced 10, and the stepper doc listed DoWhy/lifelines/SHAP as permitted directly beneath its own rule to claim only libraries that actually run. Each was written once and true once. The fix in each case was the same shape: make the claim read from the thing that enforces it, and add a test that fails when the two diverge. The allowlist reconciles against `requirements.txt`, the caption interpolates `DEFAULT_WALL_CLOCK_S`, the permitted column renders from `ALLOWED_IMPORTS`. Worth applying to any number or list this build shows a visitor.
- **An import grant is also a time budget, and a version ceiling.** Adding shap/dowhy/econml to the allowlist (2026-07-20) pinned the whole numerical stack down a major version, because econml and numba cap it, and charged 4.2-4.6s of warm import to every sandbox run against what was a 10s wall clock. Widening an allowlist is never only a policy change.
- **A UI copy of a fact drifts from the fact.** Extended 2026-07-20 from the model-status popover (computed off the row) to agent descriptions (read off the agent class). If a surface describes what the code does, derive the text from the code; a hand-written dict next to the registry is a document about the code, not an inventory of it.
- **Two things that look like a change doing nothing.** Found 2026-07-20. The launch config runs Streamlit with `--server.fileWatcherType none`, so it never recompiles the script: a browser reload starts a new session that re-runs the *old* source, and a real edit looks inert until the server restarts. And a full test run alongside the live app took 651s and failed 6 tests that all passed in 116s once the server stopped. Check the wall clock before reading failures, and restart the server before concluding an edit had no effect.
- Health 200 is necessary but not sufficient to call a deploy verified: Streamlit's health endpoint answers before app.py runs, so an import crash returns 200 while every page is broken (this happened 2026-07-18). Verify a deploy by loading a page and running a flow, not by probing health. And requirements.txt is a second dependency list that drifts from pyproject/uv.lock unless something regenerates it; the fix is to generate it at deploy time or diff it in CI.
- **A control that approves something the environment then refuses is not a control that held, it is a control that guessed.** Found 2026-07-20: the codegen allowlist is a *third* dependency list, and nothing reconciles it with `requirements.txt`. The Gate stamps "imports on the tier's allowlist, clear" for `statsmodels`, and Execute throws `ModuleNotFoundError` because it was never installed. `requirements.txt` and `uv.lock` agree perfectly here, so the existing deploy guard cannot see it: they are both simply missing what the allowlist promises. Any list that grants permission must be checked against the thing that has to honour it, not just against the list next to it. Local environments hide this precisely when it matters, since `statsmodels` is installed here transitively and absent in prod.
- **Metadata access and data access are two different grants, and a governance
  demo has to act like it.** Recorded 2026-07-20 while turning down an "Explore
  this dataset" button. A catalogue publishes schema, roles, relationships and
  descriptions to a far wider audience than the data itself; that is how a real
  bank works and it is why an analyst can discover a table they cannot read. The
  practical test for whether something belongs on a catalogue page: is it
  computed from values? Missingness and cardinality feel like metadata and fail
  that test, which puts them with the governed profiling analysis rather than in
  the catalogue. The corollary is that adding a surface to a governance product
  means checking it against the product's own controls first, because the one
  place that must never leak ungoverned data is the Governance section.
- A naturally-flagging fairness result is more convincing than a staged one. Keep it real. This now extends to the gate: if the demo shows generated code being blocked, the block must be genuine, never seeded.
- The evidence pack with its "what this does not say" block is now built (v3) and is the showpiece the model card PDF pointed toward. The negative statement is assembled from what the run did (the suppressed band, the flagged proxy), not from boilerplate, which is what makes it more than a dashboard. The model card PDF survives as prior art.
- A control is only credible if it can be seen firing. Force RBAC and PII to fire every run.
- A control that can never fire is decoration. `CTL-CONTRACT-01` (dataset drift) cannot fire against static CSVs; say so rather than demo it. Built in v2 exactly this way: the contract is pinned to the real dataset SHA, the mismatch path is proven only in a test, and the pin test fails CI if the CSV ever changes. No fake drift is staged.
- Governance that blocks legitimate work gets routed around. The false-block rate matters as much as the true-block rate, and a demo that ignores it is not credible to anyone who has shipped internal tools.
- The artifact is evidence of judgment, not the case itself. The KRAs are organisational and no amount of building closes that gap.

## Open questions

- Which comes first, `ctx.sql` or `ctx.table`? Resolved for v1: `ctx.table`, because v1's done-when (a webhook caught at the gate, an n=3 cell suppressed) needs no SQL. `ctx.sql` plus the sqlglot row-filter rewrite is the more recognisable governance demo and lands in v2, where `CTL-COMPLEX-01` and `CTL-CONTRACT-01` also live.
- ~~Is `n < 10` the right small-cell floor?~~ Settled 2026-07-19 by OPA going out of scope. It is the common default, but a real bank sets it per data domain. Making it a per-domain policy value was the strongest argument for externalising policy; with OPA ruled out, the floor stays a `floor` parameter on the Screen (default 10) rather than a hardcoded constant, which is the right shape regardless.
- Where does drift monitoring live? Evidently is on the dependency map with no stage in the lifecycle.
- ~~Should linear analysis runs feed the adoption metrics and model registry?~~ Resolved 2026-07-19 (H phase). Linear analysis, govflow, and L3 runs now feed the adoption totals and the weekly/per-dataset cuts via the seeded run-history store. The model registry stays scoped to credit_risk runs only, since it is a model inventory and only that path promotes a model. Per-agent invocation counts are likewise scoped to the credit pipeline.
- Retrieval ranking: the SR 11-7 query ranks the internal modeling standard above the SR 11-7 document itself (SR 11-7 chunks still return at ranks 2-3). Worth a later look at chunking or reranking.
- Should `deploy.sh` refuse when `HEAD` is not an ancestor of `origin/main`? Opened 2026-07-20: the primary checkout had been parked on `docs/v6-deploy-record` since Sunday, 16 commits behind, and a deploy from it would have shipped v6 while reporting success. Nothing keeps that folder current, and it is the only place the gitignored live-LLM key exists, so it cannot simply be abandoned for a worktree. A one-line guard in the script would have caught it. The related structural question is whether the primary checkout should hold `main` at all, given another worktree currently does and git refuses the same branch twice.
- How should concurrent sessions on this repo be handled? Opened 2026-07-20: a second session pushed `claude/demo-prep-hiring-manager-5c0866` (a real nav-bar paint fix) mid-conversation, while I was reporting the branch list as settled. Sandip chose to deploy without it. There is no convention yet for noticing another live session, and the branch list is not a reliable signal because it changes underneath you. **Update the same day:** that branch shipped four hours later as v10, after Sandip looked at it, and the merge needed a reset-onto-main-and-reapply because v9 had restructured the same regions underneath it. The question stands; the specific instance resolved the ordinary way, by a human looking. The practical lesson is narrower: when main moves under a branch, re-applying a small diff onto the new main beats resolving conflict markers in a file that has been restructured. **Second update, 2026-07-20 17:58:** audited all ten worktrees before merging PR #25, expecting to sequence around live parallel work. There is none. Nine are idle, clean or dirty only with a `launch.json` or a stray file, and the two branches ahead of main are dead (one holds docs main already has, the other diffs against a pre-v7 `app.py` using `st.sidebar.radio`). So the concurrency problem is not what it looked like. Long-lived worktrees over a 3,400 line `app.py` do not produce parallel work, they produce abandoned branches, because any second branch touching that file is unmergeable by the time anyone returns to it. The answer is probably not a coordination convention but the file split: `app.py` into `sentinel/ui/screens/*.py`, which is the same refactor deferred as a follow-up since 2026-07-17 and is now the thing blocking parallelism rather than merely a tidiness item. **Third update, 2026-07-21 00:44:** the first real collision finally happened, and it supports the file-split answer from the other direction. Two sessions edited the sidebar nav; one moved its definition into a new 100-line `sentinel/ui/nav.py`, the other deleted an item from it. Git could not merge that and a human took a minute: keep the move, apply the deletion at the new home. Both sessions had also edited `app.py`, `manual.py` and the corpus, and all of those auto-merged. So the conflict landed in the small extracted file precisely because the extraction had happened, and the fix was legible because the file was small enough to hold in your head. Parallel work is survivable at this file size. The open part is whether it stays survivable while `app.py` is still 3,000 lines.
- ~~Should the demo's default path include a refusal?~~ Resolved 2026-07-20, and the question was malformed. The gate is right to clear a benign request: blocking it would be a false positive, which this build treats as costing as much as a missed block. And the refusal was never missing, only unselected: three adversarial requests are wired into the L2 analysis dropdown and three at L3, each real code with a real violation the gate genuinely catches. The finding reduced to "the default selection is the benign one". Sandip drives two demos, happy path then adversarial, so nothing was built. Worth remembering as a case where a finding written up as the largest product hole was a note about a default value.
- ~~`synthetic_its` is registered but has no onboarder~~ Resolved: onboarded in v4 (generated with a known +12 effect), and in v6 (2026-07-19) it gained CAP_TABULAR so profiling is legal on it too. It is the Public-class L3 home.
- Demo GIF/Loom for the README: dropped for now per Sandip (2026-07-14).

## Things ruled out

- **OPA externalisation (ruled out 2026-07-19 by Sandip: "not in scope for the foreseeable future").** This was the one genuine fork left open since v4, and it is now closed. Not a rejection of the idea. Externalising policy to OPA needs an external server, and the demo already shows the policy logic working in-process: the purpose matrix refuses at Access (`CTL-PURP-01`), the tier resolves as the lower of two ceilings, the gate reads code with real parsers. OPA would change *where* the policy lives, not whether it exists, which is an architecture decision for a real deployment rather than for a credibility artifact. Note for anyone reading the frozen entries: several of them (through 2026-07-19 13:54) describe OPA as deferred and awaiting this call. They are correct as of their own dates; this line supersedes them. An earlier note in that session called OPA "killed" with nothing backing it, was corrected in the v7 entry, and is now overtaken by an actual decision.
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
