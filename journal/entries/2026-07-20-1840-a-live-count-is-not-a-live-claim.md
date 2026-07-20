# A live count is not a live claim

**2026-07-20 18:40**
Previous: [2026-07-20-1813-prod-carries-the-scope.md](2026-07-20-1813-prod-carries-the-scope.md)

Sentinel has a User Manual. It sits under a new Help group in the sidebar, it
opens on a nine-slide presentation, and behind that it runs ten chapters: quick
start, the nine stages, autonomy levels, controls, screens, roles, data,
architecture, glossary. PR #28, merged as `3e15f84`, deployed and live.

## Why a screen and not a markdown file

A file in `docs/` would have been an hour of work. It would also have been the
one document in this repo that nobody could check. The manual describes 26
controls, 14 allowed imports, 8 datasets, 4 tiers, 6 personas and 9 stages, and
every one of those numbers is a thing the code already knows. Written down by
hand, they are correct for about a week.

So the manual is a screen, and the rule is the one the audit findings taught in
the morning: make the claim read from the thing that enforces it. The module
imports `controls_info`, `allowlist`, `all_datasets`, `PURPOSE_MATRIX`, the tier
table, `CONTROL_CATALOG`, `FAITHFULNESS_FLOOR`, the sandbox limits and the
persona set. The cover slide's five stat chips are computed from those
collections at render time. Editorial prose is owned by the manual. Numbers are
borrowed.

The other reason it is a screen: it can link. Every screen the manual describes
has a button that navigates there, and `render_manual` takes `nav_to` as an
argument rather than importing it back out of `app.py`, because `app.py` imports
the manual and the cycle would be immediate.

## Where the rule leaks

Then main moved under me. PR #25 had added `can_view_all_runs` to `Persona` and
used it to scope the audit ledger. I merged main into the branch before merging
the PR, which is the whole reason I found it: the manual rendered six personas,
the count was right, and the new entitlement was invisible.

That is the gap in the rule, stated plainly. **Reading a collection live keeps
the count honest for free and says nothing about a field.** Add a persona and
the manual notices. Add a property to every persona and it does not, because
nothing in the render enumerates properties. The manual would have gone on
describing five entitlements while the product enforced six, which is the exact
failure mode the screen exists to prevent.

Fixed in the deck's persona line, the Roles chapter and the Audit Log entry in
the Screens chapter. Then pinned: a test counts the rendered entitlement
verdicts against the persona set, so the next field added to `Persona` fails
there instead of going quietly missing. A test is the only thing that makes a
live read a live claim.

## Two smaller things it flushed out

Writing the architecture chapter meant looking up the wall clock, and the
sandbox default is 30 seconds while both governed routes passed a literal 15.
Every surface in the app printed 30. Neither number was wrong; the second one
just had no name. It is `GOVFLOW_WALL_CLOCK_S` now, used at both call sites,
behaviour identical, pinned by a test that the routes pass the constant and not
a literal.

And the manual tripped the guard test that says no screen may hardcode the wall
clock, because my module docstring quoted the morning's finding, "claimed a 15s
wall clock while the code enforced 10", in prose. The guard greps
`sentinel/ui/` for a number and cannot tell a caption from a sentence about a
caption. I rewrote the docstring without the numbers rather than teach the guard
to parse English. A blunt guard that fires on a false positive costs one edit; a
clever one that misses a real caption costs the claim.

## Live

509 tests, 2 skipped, ruff clean on the merged tree. Deployed, EB Ready and
Green, application version `sentinel-eb-applicationversion-4dgkmqial0qf`. Health
200, static assets served gzipped through the `/static/*` behaviour, no console
errors. The manual renders and all six personas show their ledger scope, four
reading every run and two reading their own, which matches #25.

One thing prod confirmed that local could not. The Bought table prints the
installed version of each library and falls back to "not installed here" when
`importlib.metadata` finds nothing. On the instance there are zero of those:
shap 0.48.0, dowhy 0.14 and the rest are genuinely present. The manual is now a
second, independent check that the allowlist matches the environment, on the
box where the mismatch would actually matter.

PR #29 merged after this deploy and is not on the instance.
