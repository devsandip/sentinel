# Ten tabs, nine stages, one vocabulary

**2026-07-21 00:44**
Previous: [2026-07-21-0015-a-template-you-can-be-refused-by.md](2026-07-21-0015-a-template-you-can-be-refused-by.md)

The Pipeline screen is retired. Its evidence lives in the stage that owns the
question it answers. Merged with the Agent Templates branch and deployed:
bundle `sentinel-20260721-002533.zip`, `main` at `7e51602`, EB Green, 665 tests
and 2 skipped.

Sandip asked me to implement the recommendation from the thinking exercise, and
to work out for myself whether the seeded runs needed redoing. They did, and the
reason turned out to be the interesting part.

## The test each tab was put to

Does the surviving route produce the data, and does a stage own the question the
tab answers? A panel that renders an empty state on every run forever is not a
move. It is a discard with extra steps.

Four tabs moved into a stage. The gateway ledger to Generate, because Generate
is where the tokens are spent. The raw result to Execute, rendered unscreened,
so the Screen panel next door reads as a control acting on it rather than as a
second table. Fairness merged into Interpret, which needed no new computation:
the result contract refuses any result that is not a selection rate per group,
so the screened table already is the fairness analysis. What moved was the
vocabulary. Disparity ratio, threshold, verdict.

Cost split. Tokens, dollars and wall clock are cross-cutting, so they are header
chips. The eval-gate half of that tab died with the orchestrator screen, because
it was the model-promotion gate and not the Gate stage.

Audit Log links out. A third rendering of the same event stream would re-open
the drift that a shared tint map has already been paid to close.

Four discarded. Knowledge, because this route runs no retrieval and makes no
cited claims. Memory, because there is no cross-run precedent store. Traces,
because `spans_for()` is called from the orchestrator only and govflow emits no
spans. Instrumenting nine stages with OpenTelemetry is worth doing and is not
part of retiring a screen. And Pipeline itself, with one thing salvaged: the
argument that this is a fixed control flow rather than an autonomous agent, now
made about the nine stages on the Architecture panel.

## The finding: it was all being computed and thrown away at the door

I expected to write new instrumentation. Almost none was needed.
`ModelGateway.ledger_dicts()` already existed. `_generate_execute_loop` already
summed tokens and dollars. `_narrate` already divided two selection rates.
`GovernedRunResult` held all of it, and then `to_public_dict` dropped it on the
floor.

So the retired screen was not the only place that could show a routing decision
because it was better designed. It was the only place still holding the object
before the discard. That is a different problem from the one I thought I was
solving, and it generalises: **when one surface can show something no other
surface can, check whether it has better data or merely earlier data.** The
first is a feature. The second is a serialization boundary throwing away work
that has already been paid for.

## Model Card went to the Registry, against the plan

The plan said Attest, on the reasoning that run documentation belongs beside the
evidence pack. Implementing it showed the premise fails. No govflow run trains a
model, so an Attest conditional would never fire. That is dead code wearing the
costume of a feature, which is the thing this build keeps arguing against.

The card's live data is the seeded credit-risk runs, and their home is the model
inventory. Putting it on the registry row also fixed the anchor. The card used
to hang off whichever run you had just executed, which is the wrong way to find
the documentation for a model.

That is what made the re-seed necessary. A card is generated from a run object
that does not outlive the process, so it had to be in the store. The seeder also
wrote `cost=None` on govflow and L3 records while nothing rendered them, which
was harmless until cost became a header chip and a seeded run would have shown a
blank where a live run shows numbers. All 24 runs re-executed, run ids preserved
by plan slot, so shared `?run=` links survive.

## Fairness reads the screened frame, and says so

The ratio is computed on the frame after CTL-DISC-02 has removed small cells,
and it carries the suppressed band labels with it so the panel can name them. A
fairness number that quietly read the cells the disclosure control removed would
make that control decorative, and this build has spent months arguing that
nothing here is decorative.

## Live runs reached the Audit Log for the first time

`audit_runs()` has always taken a `live` list. Nothing ever passed one. The
ledger held seeded rows only, and the screen's own "this may have been a live
run" error message described a path that did not exist. Adding the header's
Audit trail button made that unavoidable, because a link landing on "no run on
file" is worse than no link.

Two bugs came out of wiring it, and both were found by clicking rather than by a
test.

The button was an `on_click` callback and the opener calls `st.rerun()`, which
Streamlit prints on screen as a no-op. The codebase already had this lesson
written down, at the Overview tiles, in a comment I had read.

Then the live record filed `persona`, the display name, where `visible_runs`
compares persona ids. A first-line analyst was refused the run they had just
executed, by a control working exactly as designed on a field that was the wrong
type of correct. Both have assertions now, including one that fails if the
entitlement warning appears at all.

## The toggles lost their only consumer

Six harness controls were toggleable so an Admin could switch one off and watch
the failure it prevents. The only route that honoured them was the Pipeline
screen's Run button. With that gone they would have rendered and changed
nothing, so they are read-only, and the UNGOVERNED badge went with them. No run
the app can now start is capable of being ungoverned, by construction rather
than by policy. The runs that did exercise those controls are still in the Audit
Log.

## Two sessions collided in one list, and it was fine

This is the first time the parallel-worktree question produced an actual
conflict rather than an abandoned branch. Both branches edited the sidebar nav.
The Agent Templates session moved its definition out of `app.py` into
`sentinel/ui/nav.py` so the manual could compute its screen count instead of
typing "Nine screens"; this branch deleted the Pipeline entry from it. Git could
not merge that, and a human takes about a minute: keep the move, apply the
deletion at the new home.

It resolved easily because both changes were the same kind of change to the same
list. The open question about concurrent sessions has been sitting on the theory
that the fix is splitting `app.py`, and this supports it from the other
direction. The conflict was in the 100-line file that had just been extracted,
not in the 3,400-line file both sessions also touched, and that is precisely
because the extraction had happened.

## Deployed and checked by clicking

Ran a governed analysis on prod rather than probing health. Header reads
`0 tokens · $0.0000 · 1.8s`, which is the honest scripted number. Generate
carries "Model gateway ledger (1 call(s))". Execute renders the raw frame.
Interpret says "Disparity ratio 0.496 (min/max selection rate across band;
threshold 0.8), below threshold", which is a failing result and the correct one
for german_credit. The Audit trail button resolved to `Run 3882d92b24fe`,
`origin live`, with no refusal and no rerun warning, which is the only way to
prove those two bugs are dead in prod.
