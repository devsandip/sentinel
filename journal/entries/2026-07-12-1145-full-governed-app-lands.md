# The whole governed app lands in one sitting

Previous: [2026-07-12-1015-p1-ml-core-lands.md](2026-07-12-1015-p1-ml-core-lands.md).

Held the line and built the rest end to end: the governance harness, the agents,
the orchestrator, and the six-tab UI. Sentinel now does the whole thing. Pick a
question, run a real analysis, pause at a human gate, approve, get a model card.

The harness is the part that matters and it is the part that got the effort.
Six modules, each small and named: audit, rbac, pii, guardrails, eval gate,
cost. The rule I held to is that a control is only credible if you can see it
fire. So two of them fire on every run. The Profiler gets denied a
proxy-for-sex column and the denial lands in the audit log. An applicant email
gets scrubbed before it would reach a model and the redaction lands too. Neither
is staged. The age fairness check still flags on its own at 0.57.

The agents are thin by design. Each one reads through RBAC, calls tools through
guardrails, redacts before narrating, emits an audit event, and accounts for
cost. Nothing touches data or tools except through the harness. The orchestrator
is a plain Python state machine, no LangGraph. It runs Profiler, EDA, Modeler,
then stops and waits for a human. Approve resumes into the Validator. The audit
log makes the whole flow inspectable, so I did not need a graph framework to
prove it.

Two things fought me. Streamlit inherited the browser dark mode and washed out
the text, fixed with a forced light theme. Then the real one: training sklearn
inside Streamlit's script-runner thread segfaulted on macOS, because OpenBLAS is
not safe to call multi-threaded off the main thread. Setting env vars at process
launch worked but would not survive a deploy. The honest fix is
threadpoolctl.threadpool_limits(1) around the sklearn calls, so it is
host-independent. Verified: the app runs a full pipeline with no env vars and no
crash.

Wrote the product brief last, because that is the artifact that separates a PM
candidate from an engineer. It maps every control to a bank KRA, lays out the
metric tree, and describes how each stubbed piece hardens into a platform.

What is left is deployment and a domain, and maybe a live-LLM run with a real
key. The build is done.
