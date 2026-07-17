# The rethink is accepted. Building starts.

Date: 2026-07-17 21:02
Previous: [2026-07-17-1940-govern-the-llm-not-sklearn.md](2026-07-17-1940-govern-the-llm-not-sklearn.md)

Two hours after the proposal, it is accepted. The debate about whether to govern
the LLM instead of scikit-learn is over. The next work is code, not documents.

Before greenlighting, a clarification pass. I wrote the PRD in a hurry and had not
read it back, so I asked eight questions about my own document: what "every control
fires on a logistic regression" means, what "cheaper" claims, what the scaffolding
actually is, which allowlist, what the L3 data fence means, the Ask stage,
disparate treatment versus disparate impact, and whether the whole toolkit gets
built. Nothing in the plan changed. It is worth recording that the plan survived a
cold read by its owner, because that is the cheapest validation there is.

One confusion is worth keeping, because it is a product risk. I misread "L3,
synthetic and public data only" as a ban on working with such data. It is the
opposite: it is the fence that says improvisation is only permitted there. If the
author can misread the autonomy ladder that way, a first-time analyst can too. The
tier a request lands in has to be shown with its reason, not just its name.

The model-card question resolved cleanly. It already exists in
`harness/model_card.py` and it survives. In the new design it is absorbed into the
Attest evidence pack: the same card, plus a provenance chain, an explicit "what
this does not say" block, and the segregation-of-duties and lineage controls firing
at that stage. Nothing is thrown away. It gets a frame.

The build order is set. v0 first: the segregation-of-duties fix. It is independent
of the reframe, it is an afternoon, and it makes a false docstring true. Then v1,
the vertical slice that is the whole thesis: Generate to Gate to Execute to Screen
at L2, on `german_credit`, with fairlearn doing the maths and `CTL-PROXY-01` the one
control that earns its way in. Everything else stays out of v1. The risk is v1
sprawling into v4, and the discipline is to refuse.

Two execution decisions locked, so they are not reopened. The code-generation step
calls the live model from the start of development, not mocked fixtures. Real
generations throughout, the token cost accepted, the cumulative spend cap already
in place as the backstop. Fixtures would harden the gate against code I wrote, not
against code the model writes, which is the wrong target. And the work goes on a
feature branch, `feat/governed-codegen`, with a PR per slice, because a clean
reviewable history is worth more on a credibility artifact than a fast one.

Status: the branch exists off `b447e80`. No code changed this session. The next
session builds v0.
