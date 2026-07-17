# v2 and v3 are built. The platform claim and the oversight claim both run.

Date: 2026-07-17 23:32
Previous: [2026-07-17-2230-v1-slice-complete-and-verified.md](2026-07-17-2230-v1-slice-complete-and-verified.md)

An hour after v1, v2 and v3 are built and verified in the browser. What was held
for later slices is now most of the way built. The two claims the PRD names after
v1, the platform claim and the oversight claim, both run.

v2 is the platform claim, and it is four things. The SQL half of the gate: ctx.sql
now parses with sqlglot, refuses an ungranted column or a SELECT star or an
out-of-scope table or a Cartesian join, injects the identity row filter the model
never sees, and runs on DuckDB. The gate runs two parsers now, ast for the Python
and sqlglot for the SQL, which is the distinction a technical interviewer checks
for. The certification lifecycle: an analysis-agent earns the right to run through
four gates, and only a certified agent is visible to Plan, so an uncertified
analysis cannot reach a user. The status is computed from the gates, never stored,
so a pill cannot lie about the gates behind it. The scaffolding CLI: sentinel
new-agent is the only path to an agent, which is what makes an ungoverned agent
structurally impossible rather than discouraged. And the drift control,
CTL-CONTRACT-01, built honestly: on static CSVs drift cannot happen, so the
mechanism is real and proven in a test, the fair-lending contract is pinned to the
real dataset SHA, and nothing manufactures a fake drift to show the control firing.

The refused-certification demo is the differentiator, and it holds. cohort-retention
v0.3 is refused on two independent grounds, a faithfulness of 0.72 below the floor
and an author trying to validate their own work. Assigning the author as validator
is refused live with CTL-SOD-01, the same segregation of duties from v0, now at
certification time. An independent validator clears that gate but the eval floor
still blocks it. Governance is not one checkbox, and the demo says so.

v3 is the oversight claim, and its centre is the negative statement. The Attest
stage assembles an evidence pack from a completed run: the finding with a Wald
confidence interval, the provenance chain, the controls attested as chips, and,
set apart, what the finding does not say. That last block is assembled from what
the run actually did. The suppressed n=6 band becomes a sentence that the finding
says nothing about that band. The flagged proxy becomes a sentence that its use is
Legal's call and is not resolved here. The pack ships pending, and signing it
refuses a self-signoff, CTL-SOD-01 a third time. The provenance is also emitted as
OpenLineage events, a START at Access and a COMPLETE at Attest, schema-valid, the
kind a bank's lineage tooling already ingests. The leadership document exports as
Quarto-ready markdown; rendering it to a PDF needs the Quarto binary and is left
as the optional step it is, because nothing should claim a PDF it cannot produce.

All of it verified in the browser, not just in tests. The SQL analysis runs on
DuckDB and the n=6 band is still suppressed before the narration. The adversarial
SELECT star is refused at the gate on line one and never runs. The Registry shows
one certified agent and one refused one with its two reasons. The self-signoff is
refused on screen. The evidence pack shows its four-clause negative statement, its
pending status, and its two OpenLineage events. Nine commits on feat/govcodegen-v2,
251 tests green, ruff clean. Prod is untouched.

What is deliberately still out. The DS-facing marimo notebook and the Quarto PDF
render are secondary output surfaces; the leadership pack, the differentiator, is
done. All of v4 is breadth, and two pieces of it are forks I will not take alone:
externalising policy to OPA needs an external server and is an open question in the
PRD, and the L3 improvise path needs synthetic_its onboarded first. I built the two
remaining claims in full and stopped at the fork boundary, because the PRD's own
warning is that breadth is worth less than depth, and a control layer that grows by
guessing at architecture is the thing this project is supposed to argue against.
