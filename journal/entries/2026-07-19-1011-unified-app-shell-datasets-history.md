# The unified app is real: login, sidebar, command center, 8/8 datasets, seeded history

2026-07-19 10:11. Previous: [2026-07-19-0113-showtell-stepper-and-design-system.md](2026-07-19-0113-showtell-stepper-and-design-system.md)

The mockup is now the app. Three workstreams shipped on branch
`claude/resume-md-continuation-05f7fe`, in build order from
docs/features/unified-app-build.md.

First the housekeeping. PR #4 (the v5 show-and-tell stepper) merged to main,
and I deployed v5 to prod: bundle `sentinel-20260719-094651.zip`, EB green,
verified the right way by loading the page and running a governed flow on the
instance (run f7b5e5da5394 reached the human gate). Prod is v5.

Then the build. **D**: I deleted `DatasetSpec.onboarded`. It was hardcoded
True for two of seven onboarded datasets and nothing in production read it, so
it was pure misinformation. Availability is a disk fact now, via
`available()`. Onboarded `uci_bank_marketing` from the UCI 222 zip (a
zip-of-zips, semicolon CSV, 20k of 41188 rows sampled), so all eight datasets
ship their data. Gave `synthetic_its` CAP_TABULAR since it is a plain 365-row
CSV, which makes profiling legal on it.

**H**: the seeded run history. The surfaces were reading a hand-written weekly
list that summed to 29 while the registry held two fictional rows. I replaced
both with a real store. `sentinel/platform/run_history.py` is an append-only
JSONL file, and `scripts/seed_runs.py` fills it by actually executing 19 runs,
all scripted and free. The store keeps two timestamps per record: when the run
really executed, and the demo-timeline date the UI renders. The model registry
now seeds from the executed credit_risk records: two promoted, one rejected,
real AUC 0.8018. The old seed row said fairness_age was blocked; the real run
promotes it, so the fiction is gone. This is the honesty rule doing its job.
The L3 causal seed run recovered the injected +12 effect at 11.87.

**S**: the shell. A login persona gate now stands before any chrome: six cards,
always dark, the analyst as the hero. Picking one lands on the command center.
The flat section radio became a grouped sidebar with live count badges. The
command center is four live-number tiles plus a CTA into the run, every number
read from the same helpers as the surface it opens.

Then a 25-agent adversarial review of the whole diff. Six finder dimensions,
two refuters per finding, 9 confirmed of 31 raw. The sharpest catch: the
Adoption tile said "19 governed runs, 67% promoted" where the rate is over
three credit-pipeline runs, not nineteen, so a reader would infer thirteen
promotions that never happened. Now it reads "19 runs, 2 of 3 models promoted."
A governance demo that fudges its own adoption number has no business shipping.
Also fixed: re-clicking the active sidebar item was silently resetting the
open section's widgets; the login cards used config names instead of the
spec's shorter card names; a percent was truncating 66.7 to 66 where the spec
says 67; and a CTA style rule was dead. All nine landed with tests.

374 tests pass, ruff clean. PR #5 is open for review. Prod is v5; v6 deploys
after the merge.
