# v0 shipped, v1 core built, fairlearn reinstated.

Date: 2026-07-17 22:03
Previous: [2026-07-17-2102-build-greenlit-v0-then-v1.md](2026-07-17-2102-build-greenlit-v0-then-v1.md)

The first real code since the rethink. v0 is done and four v1 increments are on
the branch, all green, all pushed to the one PR.

v0 made the docstring true. `approve()` claimed to be a segregation-of-duties
control while only checking whether the actor could approve at all, a role check.
`RunState` never recorded who started the run, so it could not compare author to
approver. Now it persists `started_by`, and `CTL-SOD-01` refuses when the approver
is the author. The persona model changed underneath it: the second line lost
`can_run` and the admin lost `can_approve`, so run authority and promotion
authority are held by disjoint people. The control is the backstop, the persona
model is the structural guarantee. The resume named only `mrm_approver` for the
`can_run` drop; the PRD said the whole second line, so `model_validator` lost it
too. The doc is the source of truth.

Then the v1 core, deliberately the deterministic half first, because it is the
demonstrable half and it needs no model. The gate reads generated Python with the
stdlib `ast` and refuses it before anything runs, naming the control and the line.
A generated webhook is caught as `CTL-EGRESS-01` whether or not it was imported,
which is the first half of the v1 done-when. The Screen removes a small cell before
the number reaches the narration model, which is the second half: an n=3 band is
gone from the result, not masked in the UI. `CTL-PROXY-01` rides along, flagging a
granted feature that reconstructs the protected attribute without refusing it,
because business necessity is Legal's call. The sandbox runs gated code in a
subprocess with a wall-clock cap and states its own limit out loud: it bounds a
dumb model, not a determined attacker.

The fairlearn reversal is the one worth recording, because it overturns something
this journal already argued. On 2026-07-13 I hand-rolled the fairness metrics and
wrote that doing so was "for auditability." Under the platform thesis that inverts.
If the whole pitch is that I can govern off-the-shelf tools inside a fence, then
reimplementing the one metric a fair lending reviewer cares most about is the least
on-message thing in the build. So `ml/fairness.py` now governs a fairlearn
`MetricFrame` instead of computing selection rate and TPR by hand. The public shape
is unchanged, every fairness test still passes, and the numbers match. What changed
is the message: the maths is bought, the governance is mine.

One dependency added, `fairlearn`, now a base requirement rather than optional,
because the deployed app runs the analysis and the generated code imports it.

Status: v0 plus gate, screen, sandbox, and the fairlearn wrapper are on
`feat/governed-codegen`, 164 tests green. Still to come in v1: the live
code-generation step and the gateway repoint, the orchestrator rewiring into
Ask to Interpret, the two Streamlit screens, and the seeded adversarial set.
Prod is untouched.
