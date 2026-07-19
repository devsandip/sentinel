# 2026-W28: Sentinel goes from nothing to a working governed app in one day

Week of Mon 2026-07-06 through Sun 2026-07-12. Previous week: none (first
weekly summary).

## The week in one paragraph

Sentinel did not exist until Sunday. By Sunday night it was a working governed
agentic data-science app: a real logistic regression on German Credit, a
four-agent pipeline behind a six-module governance harness, a human approval
gate, and a six-tab Streamlit UI. The founding thesis was set on day one and
held all day: the ML stays deliberately small, the governance harness gets the
real effort, and a control is only credible if you can see it fire. Two
controls fire on every run and the fairness check flags a real disparity on
its own, not a staged one.

## What happened

Everything happened on 2026-07-12, in two sittings.

Morning: the project started and P1 (the real ML) landed first, skipping
scaffolding ceremony so there were genuine numbers in the first hour.
Logistic regression on UCI German Credit, AUC 0.80. The fairness check
flagged unprompted: young applicants flagged risky at 0.333 versus 0.190 for
the 41-60 band, disparity ratio 0.569 under the four-fifths rule, while sex
passes at 0.82. Both real. The protected attribute is excluded from model
features and the code says so.

Midday: the rest of the app in one push. The six harness modules (audit,
rbac, pii, guardrails, eval gate, cost), thin agents that touch nothing
except through the harness, a plain-Python state-machine orchestrator with a
human gate, and the UI. An RBAC denial and a PII redaction land in the audit
log on every run by design. The product brief came last, mapping every
control to a bank KRA.

## State at end of week

The build was done but local only: no deploy, no domain, no live-LLM run.
36 tests passing at that point. Two fights were recorded: Streamlit
inheriting browser dark mode (fixed with a forced light theme) and a macOS
segfault when training sklearn inside Streamlit's script-runner thread,
attributed that day to OpenBLAS threading and worked around with
threadpool_limits(1).

## Beliefs that changed

The week was too short for reversals; the founding beliefs were set rather
than changed. Two calls made on day one that shaped everything after:
Streamlit over Next.js plus FastAPI (one language, one deploy target, half
the effort), and P1 before P0 (real numbers before ceremony). One belief
formed under pressure: that the segfault was an OpenBLAS threading problem.
The week ended holding that belief.

## Carry-overs into W29

- Deployment and a domain.
- A live-LLM run with a real key.
- The segfault attribution deserved more scrutiny than a Sunday allowed.

## Daily entries from this week

- [2026-07-12-1015-p1-ml-core-lands.md](../entries/2026-07-12-1015-p1-ml-core-lands.md)
- [2026-07-12-1145-full-governed-app-lands.md](../entries/2026-07-12-1145-full-governed-app-lands.md)
