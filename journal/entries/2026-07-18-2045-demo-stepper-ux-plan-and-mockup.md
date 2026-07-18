# Demo stepper UX: plan and clickable mockup

2026-07-18 20:45

Previous: [2026-07-18-1859-v4-merged-and-deployed-to-prod.md](2026-07-18-1859-v4-merged-and-deployed-to-prod.md)

Sandip's note in `docs/more_ideas.md`: Sentinel has every control it claims, but
the demo hides them. The governed run computes behind one spinner and the nine
stages land as a static ribbon that flashes by. It reads like a tool a data
scientist would use, not a demonstration of how AI gets governed in a bank. And
the UI needs to prove I can build product, because "internal-tools builder, no UI
sense" is a hiring-manager hangup. The machinery does not change. The surfacing
of the machinery changes.

So this session is a plan and a design artifact, not shipped code. Nothing was
deployed. Nothing about the running app changed.

The plan is at `docs/features/demo-stepper-ux.md`. Three decisions. The stepper
becomes the primary governed-codegen surface, with the one-shot run kept as a
fast fallback. The six vanity header chips (bound to nothing today) get replaced
by live run-context chips plus one Controls button that opens the full control
plane grouped by stage, with admin-only audited toggles. And the run still
computes once; the stepper walks the finished `GovernedRunResult` one stage at a
time rather than re-running. A fan-out read of the codebase first established
which stages already carry their data: six of nine do. Only Ask, Plan, and Access
discard what the new screens need (the tier computation, the contract SHAs, the
scoped table and the denied-column set), so those get small additive fields. The
plan phases it v5.0 through v5.4.

The mockup is at `docs/mockups/sentinel-stepper-mockup.html`, a self-contained
clickable prototype of all nine stages on the real hero-run numbers. A midnight
command frame with a shield wordmark over a light content stage. The nine-stage
rail is the hero, with a "caught" marker on Gate and a "fired" marker on Screen so
the eye lands on the moments that sell it. Every CTL chip opens a drawer with what
the control is, why it fired here, and what it did. Ask is split into import
dataset, select purpose, pick question. Access shows denied columns struck red and
masked. Screen shows before and after with the 71-75 band struck through, not
deleted, and the real proxy association bars. Gate has a working Fix-it loop.
Interpret has scripted-shimmer and live-streamed modes. And the admin can flip
CTL-DISC-02 off and watch the n=6 band survive into the result on Screen, which is
the "prove the run changes" moment the toggle exists for. Light and dark both
themed.

I ran the mockup through three adversarial critics: fact-accuracy against the
code, coverage against Sandip's brief, and design quality. The fact-check earned
its keep. It caught things I had invented: a team shown as the certification owner
(which violates the owner-must-be-a-person gate), fabricated proxy association
values, invented personnel names, an attested-controls row that listed 13 of 18,
and an overstated row-filter claim. All fixed against the real seeded data. The
two coverage gaps it flagged, a missing Plan parameters form and a control toggle
that could not actually be operated, are both now built.

The fact-check also surfaced two genuine repo inconsistencies, and I fixed both.
The PRD placed CTL-PURP-01 at Ask while the code enforces it at Access; the doc
now says Access in the Stage 1 note, the Stage 3 controls, and the catalogue, with
the honest framing that purpose is bound at Ask and enforced at Access before any
rows are read. And the seeded cohort-retention comment in `certification.py`
described the author validating their own work, when the entry actually has no
validator assigned (the SoD gate blocks on "no validator," and the entry is
distinct from deposit-elasticity, which passes evals and only awaits one). Comment
corrected. 316 tests pass, ruff clean. Both were caught by grounding the mockup in
the code rather than trusting the PRD.

What is not done: none of this is built into the app. The mockup is the design
target; the Streamlit rework follows it, starting with the chrome and design
system (v5.0) and the stepper shell (v5.1).
