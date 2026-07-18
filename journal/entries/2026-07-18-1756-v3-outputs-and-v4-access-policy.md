# v3 secondary outputs shipped, v4 Access policy started

2026-07-18 17:56

Previous: [2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md](2026-07-18-0750-prod-crashed-on-missing-deps-fixed.md)

Two threads today, both off `main` on a new branch `feat/govcodegen-v4`. First,
the two v3 secondary outputs that were deferred. Second, the start of v4, the
breadth claim, limited to the two items that need no external infrastructure.

The v3 outputs close a real gap. The PRD defends the Streamlit choice by claiming
three surfaces: Streamlit for the console and gate, marimo for the data
scientist, Quarto for leadership. Only the Streamlit surface existed, and Quarto
was markdown only. Now both are built. The marimo notebook is a real, loadable
`marimo.App` in plain `.py`: a markdown cell carries the finding, provenance,
controls, and the negative statement, and a second cell holds the generated
analysis as an ordinary `def analysis(ctx)` a colleague reviews in a pull request
like any other change. It is not auto-run, because reaching data outside the
fenced `ctx` would itself be ungoverned. The Quarto path writes the `.qmd` and
renders the PDF only where the `quarto` binary is present; the public instance
has none, so it ships the source and says so rather than fake a PDF. The evidence
pack now offers both downloads.

v4 got two items, both genuine, both verified in the browser. The
purpose-by-dataset matrix is the showpiece: you may not use credit data for
marketing. Not because the role lacks permission, but because the reason is
wrong. Access asks not who, but why. The matrix is transcribed cell for cell
from the PRD, the classification is labelled simulated because every dataset is
really public, and the flow now runs the purpose gate first at Access: a
marketing request on german_credit is refused with CTL-PURP-01 before any code
is generated, and everything downstream is skipped. A permitted-but-unwired
purpose stops honestly without CTL-PURP-01, so the two stop-reasons never blur.

The second v4 item is autonomy tier resolution: the tier is computed, never
chosen, as the minimum of two ceilings, one for the data classification and one
for the person's role and attestations. Both ceilings bind. A permissive dataset
never elevates a person, and a trusted person never elevates a dataset. Built as
a tested unit against the five worked examples in the PRD, and demonstrated live
in the Access tab, which now shows both Access-time computations side by side:
purpose (why) and tier (how much rope).

What I did not build, on purpose. OPA externalisation needs an external server,
which is a PRD open question and Sandip's call. The L3 sandbox needs
`synthetic_its` onboarded first, which does not exist yet. And I stopped short of
rewriting the flow's frozen L2 to compute the tier from the live persona, and of
the L1 and L3 execution routes, which is the largest remaining v4 piece and would
roughly double the govflow surface. The tier resolver is real and seen firing;
wiring it into the running flow is the next slice, scoped and named rather than
half-built.

Three commits on `feat/govcodegen-v4`, pushed, no PR opened yet. 293 tests pass
(up from 251), ruff clean. Prod is untouched and still on v0-v3; any deploy needs
a fresh go-ahead.
