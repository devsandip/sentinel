# What counts as a refusal

**2026-07-20 16:55**
Previous: [2026-07-20-1410-a-list-that-granted-what-nothing-installed.md](2026-07-20-1410-a-list-that-granted-what-nothing-installed.md)

The Audit Log is built, merged as PR #23, and live. Prod is current for the
first time in three sessions: it carries the five audit fixes, the data
contract catalogue, the registry rewrite, and this.

The screen is one nav item under Platform. Every run the platform has executed,
every step inside it, what a control allowed, what it caught, who ran it, who
else signed. 24 runs and 249 events on file.

## The feature kept catching the platform

I expected to build a reader over an existing record. Most of the session went
on discovering that the record did not say what I assumed, and each discovery
was a governance fact rather than a bug in my code.

**There is no dual control anywhere in Sentinel.** Sandip asked whether a run
required more than one user for additional approvals. The honest answer is that
no run ever requires more than one. What exists is author-is-not-approver,
enforced by identity comparison, single signature. No approver list, no quorum,
no second-signature state, nothing that could hold two approvals. He picked
Option A: report what is true and add nothing. I think that was right. The
screen now says it in plain words instead of implying a control the platform
does not have.

**Two different refusals sit at that gate and I had conflated them.**
`Orchestrator.approve()` tests promotion authority *before* it tests
segregation of duties. So an Analyst self-approving is refused for lacking
authority and never reaches CTL-SOD-01 at all. Only an author who already holds
promotion authority exercises four-eyes. My plan doc and my mockup both
credited CTL-SOD-01 with a refusal it did not make. Both are seeded now and a
test asserts they stay apart. The authority refusal stamps no control id, which
is how you tell them apart in the record.

**CTL-TIER-01 was catalogued as doc-only while `flow.py` was enforcing it.**
The chip on a run the tier gate had just refused would have read "cannot fire:
not implemented". The catalogue was stale, not the code. The test that pinned
it as unimplemented now asserts the opposite, with the seeded tier-block run as
its evidence.

**And the record does not survive a deploy.** `runtime/` is gitignored and
excluded from the EB bundle. 324 audit files on my machine, zero on the
instance. Worse, the seeder collapsed every run to a sorted set of action
strings and threw away seq, ts, actor, level and data_touched. Without work,
this screen deploys empty while health returns 200. That was the highest-risk
item in the plan and the reason `sentinel/data/seed_audit.jsonl` is now
committed. Prod showing all 24 runs on a fresh instance is the proof.

## The counting bug

The worst defect I shipped and caught was arithmetic. Refusal accounting read
the seeder's `controls_fired`, which is built from blocked, redaction **and**
gate levels. So an eval gate that fired and *passed*, and an approval decision
that *approved*, both counted as refusals. Every number on the screen was
inflated and controls were credited with stopping things they had waved
through.

A gate event means the control was consulted, not that it said no. Where a gate
does refuse it writes `blocked` instead. `caught_events` reads blocked and
redaction only, and two tests pin it.

That distinction then repeated three more times. It is the whole content of the
feature. Sandip's first question on seeing the screen was why "Refusals only"
listed runs whose outcome was approved, which is the same confusion wearing a
label instead of a number: a denied column is a refusal the run survived. The
filter now splits into Stopped by a control, Withheld ran on, and Reached a
human gate, with counts. And each stage separates the controls it *armed* from
the ones that *fired*, because a Gate arming eight code checks and tripping
none is the normal case.

## I was wrong about the vocabulary

I designed the run detail to render each run in its own step vocabulary and
argued in the doc against normalizing, on the grounds that mapping
profiler/eda/modeler onto Ask..Attest is an interpretation. Sandip asked why it
could not take the same shape as the Run screen. He was right and the argument
was precious.

The nine stages are the governance spine. The Run screen teaches them. An
auditor should learn one vocabulary, not four. Every run now reads as Ask,
Plan, Access, Generate, Gate, Execute, Screen, Interpret, Attest.

Three rules keep the mapping from lying. A stage a route does not have is "not
in this route", never ok and never skipped: three different facts, and a linear
analysis generates no code, so its Generate stage is absent rather than
skipped. Native step names stay visible inside each stage, so Execute on a
credit run still lists Data Profiler, EDA / Feature and Modeler by name with
their own narrations. And a stage folding several steps takes the worst
outcome, because two of three passing does not make a stage green.

Frameworks and governance per stage came almost free: `_ENGINE` in
`sentinel/ui/govflow.py` already held it, and it is what the Run screen's
engine bar renders. The nine-stage routes read it directly so the two surfaces
cannot drift, and a test asserts equality. The other two routes declare their
own, grounded in what those modules import. Printing govflow's duckdb sandbox
against a credit-risk run that trains a scikit-learn model would be a plain
falsehood.

## Two Streamlit traps

Keyed containers reconcile by key. Keying audit rows on `run_id` meant the
moment a filter changed the row set, nine visible rows rendered as twelve
containers, three of them stale copies showing the wrong data under the wrong
ids. On an audit screen that is a correctness bug, not a cosmetic one.
Positional keys shrink cleanly from the tail.

And Streamlit discards the state of a widget it did not render. Drilling into a
run unmounted the filter widgets, so Back returned to an unfiltered ledger,
which is the opposite of going back. Durable underscore-prefixed copies re-seed
them.

Both were found by clicking, not by reading. Neither would have failed a test I
would have thought to write.

## Housekeeping I got wrong

I claimed the merge would be clean because `git merge-tree <base> HEAD main`
reported zero conflict hunks. The real merge conflicted immediately. The 3-arg
form on git 2.35 uses the older algorithm and does not agree with the merge git
actually performs. Dry-run with a real merge on a throwaway branch instead.

The conflicts were benign, both in `app.py`'s import block, additive on each
side.

## Where this leaves the demo

The strongest thing on the screen is not a number. It is that a govflow run
refused at Ask reports **Ask**, not the `blocked_at_gate` constant the code
carries, and that the run below it shows the Gate arming eight checks and
tripping none. The controls are legible as controls rather than as labels.

The weakest thing is still the four-eyes column. Only the credit pipeline has a
human gate at all. govflow and L3, the routes with every interesting refusal,
have none, and `sign_evidence_pack()` is dead code with a working CTL-SOD-01
refusal inside it. The screen names that gap rather than designing around it,
which is the best a reporting surface can do about a product hole.
