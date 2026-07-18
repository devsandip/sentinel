# 2026-07-18 23:02 — The mockup became the whole app, then got a theme pass

Previous: [2026-07-18-2045-demo-stepper-ux-plan-and-mockup.md](2026-07-18-2045-demo-stepper-ux-plan-and-mockup.md)

This session turned the nine-stage stepper mockup into a mockup of the whole
governed platform, then made it hold up under review and in both themes. Still a
mockup. Nothing built into `app.py`, nothing deployed. Prod is unchanged, still v4.

What happened, in order.

I promoted the "buy the maths, build the governance" Stack surface from a top-bar
modal to a real tenth stop on the stepper rail, an Architecture overview after
Attest. It reads as an appendix, not a tenth governed stage: a glyph node, a dashed
connector, an "overview" tag, and the counter says "Architecture" not "Stage 10 / 9".

I renamed the two engine-bar labels. "Buy the maths" became "Framework & Tools used"
and "Build the governance" became "Governance implemented". Plainer, more enterprise.

Then the real question. Prod has four surfaces the stepper never showed: Datasets,
Registry, Platform, and Adoption. They are not stages, they are the platform the run
lives in. I mapped what each actually is from the code, then built three genuinely
different ways to incorporate them into a comparison mockup
(`docs/mockups/sentinel-platform-surfaces.html`): A, the four surfaces as sidebar
peers of the run; B, the run as hero with each surface as a drawer opened from the
stage that consumes it; C, a command-center dashboard landing that tiles the four
surfaces then launches the run.

Sandip chose C on top of A, with the tile dashboard as the landing. So I built the
unified app into `docs/mockups/sentinel-stepper-mockup.html`, which is no longer the
stepper mockup but the whole app: a faux persona login first, then the command-center
dashboard, then a persistent left sidebar (Overview / Run / Datasets / Registry /
Platform / Adoption) that stays visible on every screen including the nine-stage run.
Tiles and sidebar items both open a surface across the full content area. All sidebar
items show regardless of persona, for now.

I ran an adversarial review as a three-dimension workflow (data fidelity, interaction
coverage, a11y and responsive), with an independent verify pass on every major. It
found eleven confirmed majors and I fixed all of them. Real repo mismatches in the
surface data (the retrieval-QA template's pattern, tools, and RBAC; two playbook
patterns; three agent RBAC scopes; two dataset licenses). A demo-replay bug: relaunching
the run left the Gate "Fix it" and the narration pre-completed, so I added a resetRun.
The grid blowing out at narrow widths, fixed with minmax(0,1fr) tracks. A missing
persistent h1, four identical "Open" button names, and the login without a dialog role.

Last, the theme pass Sandip asked for. The topbar, sidebar, and rail were dark navy in
both themes because they used the always-dark --rail tokens. I added theme-aware
--chrome-* tokens so the chrome is light in light mode. The Ask sub-step labels were
invisible in dark mode because .substep is a button and its text inherited the default
black. The "Start a governed run" CTA was an always-dark banner, and the generated-code
block was hardcoded dark; both are theme-aware now (--code-* tokens for the code). And
Sandip does not want a mobile UI, so I removed every max-width media query and made it a
fixed desktop layout.

Where this leaves things: the design is settled and fully clickable. The next session
starts building it into the real Streamlit app, onboarding the datasets that are only
registered, and seeding runs so Adoption and the Registry have real history.
