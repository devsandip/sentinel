# Retiring the Pipeline screen

## Why

The app carried two run surfaces. Run is the nine-stage governed walkthrough and
the centre of the product. Pipeline was the older four-agent credit-risk build,
with ten tabs of evidence hanging off whichever run you had just executed.

Two surfaces meant two vocabularies for reading a run, and the FAQ had an entry
whose whole job was explaining why both existed. The tabs were also the wrong
shape: an evidence tab answers a question, and the question is always asked at a
particular point in a run. Filing them all in one flat strip put the routing
decision three clicks from the code it produced.

## The test applied to each tab

Does the surviving route produce the data, and does a stage own the question the
tab answers? A panel that renders an empty state on every run forever is not a
move, it is a discard with extra steps.

## Disposition

| Tab | Went | Why |
| --- | --- | --- |
| Gateway | Generate | Generate is where the tokens are spent. `ModelGateway.ledger_dicts()` already existed; the flow was throwing it away at the door. |
| Results | Execute | It is what the sandbox emitted. Now rendered raw, so the Screen panel next door reads as a control acting on it. |
| Fairness | Interpret (merged) | The result contract refuses any result that is not a selection rate per group, so the screened table already *is* the fairness analysis. What moved was the vocabulary: disparity ratio, threshold, verdict. |
| Model Card | Registry | A card documents a model, and the Registry is the model inventory. This is a deviation from the original plan, which said Attest; see below. |
| Cost & KPIs | Header chips | Tokens, dollars and wall clock are cross-cutting. The eval-gate half did not follow: it was the orchestrator's model-promotion gate, a different control from the Gate stage. |
| Architecture | Topbar | Describes the platform, not a run. It was the rail's tenth stop under a footer reading "Stage N / 9". |
| Audit Log | Link out | A third rendering of the event stream re-opens drift the shared tint map already paid to close. |
| Pipeline | Discarded | Every element has a better Run equivalent. One thing salvaged: the fixed-control-flow argument, now made about the nine stages on the Architecture panel. |
| Knowledge | Discarded | This route runs no retrieval and makes no cited claims. |
| Memory | Discarded | No cross-run precedent store. The retention *argument* survives as a `regulation` line on the relevant control. |
| Traces | Discarded | `spans_for()` is called from the orchestrator only; govflow emits no spans. Instrumenting nine stages with OpenTelemetry is worth doing and is not part of retiring a screen. |

## Model Card: why the Registry and not Attest

The plan said Attest, on the reasoning that run documentation belongs beside the
evidence pack. Implementing it showed the premise fails: no govflow run trains a
model, so an Attest conditional would never fire. That is dead code wearing the
costume of a feature.

The card's live data is the seeded credit-risk runs, whose home is the model
inventory. Putting it on the registry row also fixed the anchor: the card used to
hang off whichever run you had just executed, which is the wrong way to find the
documentation for a *model*.

This needed the card in the seed store, because it is generated from run objects
that do not outlive the process that made them.

## What the flow had to start carrying

`GovernedRunResult` gained `gateway_ledger`, `elapsed_s` and `persona_id`, and
`to_public_dict` gained those plus `tokens`, `cost_usd` and `fairness`. None of
this is new computation. `_generate_execute_loop` already summed tokens and
dollars, the gateway already wrote a ledger row per call, and `_narrate` already
divided two selection rates. All of it was discarded at the door, which is why
the retired screen was the only place in the app that could show a routing
decision.

`fairness` is computed on the *screened* frame and carries the suppressed band
labels with it, so the panel can say the ratio does not include them. A fairness
number that quietly reads cells the disclosure control removed would make
CTL-DISC-02 decorative.

## Live runs reached the Audit Log for the first time

`audit_runs()` has always taken a `live` list. Nothing ever passed one, so the
ledger held seeded rows only and the screen's own "may have been a live run"
error message described a path that did not exist. The header's Audit trail
button made that visible, because a link landing on "no run on file" is worse
than no link.

Two bugs came out of wiring it, both found by clicking rather than by a test:

- The button was an `on_click` callback, and the opener calls `st.rerun()`.
  Streamlit prints "Calling st.rerun() within a callback is a no-op" on screen.
  The codebase already had this lesson written down at the Overview tiles.
- The live record filed `persona` (the display name) where `visible_runs`
  compares persona **ids**. A first-line analyst was refused the run they had
  just executed. Both now have assertions.

## The control toggles

Six harness controls were toggleable so an Admin could switch one off and watch
the failure it prevents. The only route that honoured them was the Pipeline
screen's Run button. With that gone the switches would have rendered and changed
nothing, so they are read-only, and the UNGOVERNED badge went with them: no run
the app can now start is capable of being ungoverned, by construction rather than
by policy.

The runs that did exercise those controls are still in the Audit Log.

## Re-seeding

`scripts/seed_runs.py` re-executed all 24 runs. Three changes to what is stored:

- `model_card` on credit-risk records, so the Registry can render one.
- Real `cost` on govflow and L3 records, which were writing `None` while nothing
  rendered them. A seeded run would otherwise show a blank where a live run now
  shows chips.
- `cycle_time_s` is the real elapsed time of the seeding execution, not a figure
  derived from the demo-timeline date.

Run ids were preserved, as the seeder is designed to do, so shared `?run=<id>`
links survive.
