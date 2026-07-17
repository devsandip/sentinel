# The harness audits scikit-learn, not the LLM

Date: 2026-07-17 19:40
Previous: [2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md](2026-07-14-0854-datasets-onboarded-and-ragas-faithfulness.md)

I asked for a rethink of the whole thing before building anything else. Nothing
shipped today except documents. The documents are the point.

The finding that reframes the project: the governance layer is not governing the
language model. It is governing scikit-learn. Every control fires on a logistic
regression. Turn the LLM off and the audit log, the RBAC denial, the PII
redaction, the eval gate, and the human gate all still pass. The model sits at
the end of the pipeline writing prose about numbers that were already computed.
It never touches anything, so the controls never touch it.

That matters because the question in the interview room is whether I can deploy
LLMs to help data scientists. The honest answer to how LLMs help data scientists
is that they write the code. Databricks Assistant, Hex Magic, Snowflake Copilot.
So the artifact has to govern generated code, before it executes, against
customer data. Today the build proves I can put an audit log around an ML
pipeline. It should prove I can put a language model between a data scientist and
a bank's customer data without losing the licence.

The second problem is that a linear pipeline has nowhere to put the platform
story. Registry, templates, and scaffolding are half of what I said I wanted to
demonstrate, and a pipeline diagram demonstrates none of it. Those words are a
claim that the tenth analysis is cheaper than the first and that a central team
knows what is deployed. That needs a lifecycle, not a diagram.

The idea the rethink is built around is an autonomy ladder. Do not pick one
level of freedom for the model and defend it. Ship four, and let policy decide
which one this person gets on this data right now. L0 explains finished numbers.
L1 picks a certified analysis and fills typed parameters. L2 writes code against
a fenced API. L3 improvises in a sandbox. The tier is computed from who you are
times how sensitive the data is, never chosen. A junior on customer PII gets L1.
A certified analyst on internal data gets L2. Nobody gets L3 outside synthetic
data. It is a product decision rather than an engineering one, it is defensible
to a regulator, and it makes the governance layer visibly decide something
instead of only writing to a log.

The ladder turns out to be the same design as the SR 11-7 question. Is the LLM a
model under SR 11-7? My position: a model that proposes code a qualified human
reviews is a tool and inherits no validation burden, because an accountable
person stands between it and any consequence. A model that autonomously produces
a number driving a decision is a model and inherits the full burden. That
distinction is architecture, not philosophy. It tells you exactly where the human
gate sits: at the last point where a person still meaningfully reviews before a
number becomes a decision. L0 through L2 keep a human in that position, so they
stay tools. L3 without review would cross the line, which is why L3 is fenced to
synthetic data where no decision is downstream. The credit-risk pipeline keeping
its LangGraph interrupt is now justified by this principle rather than by
convenience.

Fact-checking the proposal against the code found a real defect, and it is the
embarrassing kind: a governance gap in the governance demo. `approve()` checks
`actor.can_approve`. That is a role check, asking whether somebody with promotion
authority approved. It is not segregation of duties, which asks whether the
approver was a different person from the author. It cannot be, because
`RunState` never stores who started the run. The actor passed to `start()` is
used for one audit line and discarded. Combined with `mrm_approver` holding both
`can_run` and `can_approve`, the same persona can approve its own run. So can
admin. The docstring calls it "the role-aware, segregation-of-duties control." It
is role-aware. It is not segregation of duties, and SR 11-7 requires exactly the
property that is missing. Persisting `started_by` and comparing it is an
afternoon. I filed it as v0, to do whether or not the rest of the proposal
survives.

The sharpest new control came out of pushing back on external review. Gemini
flagged prompt injection and suggested screening the prompt before generation.
The threat is real but the framing and the layer are both wrong. The
bank-specific name for it is proxy discrimination. `CTL-COL-01` asks whether a
column is permitted. It cannot ask whether a permitted column reconstructs a
protected one. Zip code proxies race. A model built entirely from granted columns
can still be redlining, and every control in the deck passes it. That is not an
edge case. Proxy discrimination is the problem in fair lending, and it is why
disparate impact exists as a legal test separate from disparate treatment.
Screening the prompt is the intuitive fix and the wrong one: intent is easy to
disguise, the analyst's intent is usually innocent, and the output discriminates
regardless of what was asked. The control has to be empirical and
post-execution. Measure association between granted features and the protected
attribute at Screen. Roughly twenty lines. And it flags rather than refuses,
because a proxy can survive a business-necessity defence and that call is Legal's.
It is the one addition I let into v1, because v1 is a fair lending demo and "what
about zip code" is the first question a reviewer asks.

I also rejected one suggestion outright. Thumbs up/down on generated code
measures the wrong thing and creates the wrong pressure. In a governance product
a thumbs-down usually means the gate blocked me, which may be the system working.
An instrument that cannot separate "this is bad" from "this correctly stopped me"
is noise. Worse, optimising a control layer for satisfaction points in one
direction: loosen the controls. Measure abandonment after a block, grouped by
control ID, instead. Behavioural rather than self-reported, and it points at the
real fix, which is usually the wording of the refusal.

fairlearn is back in. I ruled it out on 2026-07-13 to hand-roll the metrics for
auditability. Under the new thesis that inverts. If the pitch is that I govern
off-the-shelf tools, hand-rolling the one metric a regulator cares most about
undercuts it. Governing fairlearn is more on-message than reimplementing it.

The last thing is the one I nearly did not write down. The role's KRAs are
organisational: partner with Risk, Compliance and Technology to land a framework,
and champion adoption across a large data science population. No amount of
building closes that gap. The artifact proves I know what such a framework must
contain. It proves nothing about getting three second-line functions to agree on
it. A working demo is not an undeniable hire signal for an SVP, and believing it
is would be the actual trap. It buys the right to a more serious conversation. It
does not win one. The question it cannot answer for me is how I got Compliance to
sign off when they wanted stricter and Engineering wanted looser, and that gets
answered with a story, not with code.

Everything above is a proposal. No code changed. 127 tests pass, ruff clean. The
docs are on main: the PRD at `docs/features/governed-codegen.md`, and the
15-slide argument beside it as HTML and PDF.
