# The show-and-tell stepper lands, then gets the mockup's skin

2026-07-19 01:13. Previous: [2026-07-18-1859-v4-merged-and-deployed-to-prod.md](2026-07-18-1859-v4-merged-and-deployed-to-prod.md)

Overnight build session against the brief in docs/more_ideas.md: the tool
worked but did not demo. The stages flashed past in a spinner. The controls
were chips that said nothing. Two commits fix that, on branch
claude/resume-review-build-20aab7, PR pending morning review. Prod untouched.

First commit: the walkthrough itself. The Governed codegen surface is now a
stepper. Ask is three explicit sub-steps: import a dataset from a table,
declare a purpose with a live CTL-PURP-01 check, pick a prebuilt question.
Plan shows the model and a populated parameter form. Run executes all nine
stages as before, then the user walks Access to Attest one panel at a time.
Access shows the scoped sample plus every source column, withheld ones struck
out in red with masked values and a reason each. Screen shows the result
before and after, the 71-75 band flagged amber on the left and struck through
on the right. Every control chip opens an explainer: what it is, why it
exists, what it did on this run, from a new controls_info registry that keeps
doc-only PRD controls honestly marked unimplemented. The Gate grew the Fix it
button: a blocked run gets repaired and resubmitted, the same gate re-reads
it, and the diff shows the violating line gone. Scripted repairs are seeded
samples and say so. repaired_from links the runs and is set only when the
repair actually engaged, with a repair_requested audit record always beside
it. A 25-agent adversarial review confirmed 18 findings, mostly honesty of
copy and state bugs; all fixed.

Second commit: Sandip reviewed mid-build and pointed at the unified-app
mockup and its written spec, docs/ui-spec.md, drafted in the other worktree.
The stepper and chrome now wear that design system. Topbar with the SENTINEL
shield lockup and live context chips. Sidebar as a nav rail. The stage radio
CSS-transformed into the numbered node-and-connector rail; custom HTML links
would have dropped the Streamlit session, so the radio stays the interactive
layer underneath. Per-stage phead, In/Does/Out cards, and an engine bar that
names the framework and tools used beside the governance implemented, only
where they actually run. A syntax-colored code block with violation rows. An
Architecture tenth stop closing the walkthrough on the bought-versus-built
stack.

Deferred, on purpose: the login persona gate, the grouped sidebar, the
command-center landing, dark mode, and the datasets and seeded-history
workstreams. Those belong to the phased plan in
docs/features/unified-app-build.md and change app structure; nothing tonight
forecloses them. OPA externalisation still waits on Sandip.

355 tests pass, up from 316. Ruff clean. Verified in the browser end to end:
benign L2 walk, marketing refusal, L1 typed-params route, L3 repair, admin
toggle, and the redesigned rail, panels, and Architecture stop.
