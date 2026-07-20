# A fixture more generous than prod

**2026-07-21 01:28**
Previous: [2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md](2026-07-21-0044-ten-tabs-nine-stages-one-vocabulary.md)

Three carried-over follow-ups done: the two-clause deploy guard, `stash@{0}`
dropped, and `app.py` split from 3,208 lines to 157. The last one led to a
deploy, and clicking through prod after it found a bug that had been live since
roughly the first deploy. `main` at `b810557`, bundle
`sentinel-20260721-012204.zip`, EB Green, 674 tests and 2 skipped.

## The guard, three sessions late

`deploy.sh` zips the working tree, so the artifact is what is on disk and `HEAD`
is only where a label points. The near-miss on 2026-07-20 was a checkout sitting
on `main` at exactly `origin/main` with a full revert staged in its index, and
every check I had passed it.

Two clauses now, and the second is the one that fires. Untracked files count,
because a new module under `sentinel/` is inside the zip's file list and would
ship having never been in git. Being behind main is allowed: an old commit is
still a commit main reviewed, and refusing it would block the one deploy you
least want to argue with.

The tests slice the guard out of `deploy.sh` and run it in a throwaway repo, so
they exercise the shipped shell rather than a copy of it, and the slice fails
loudly if either anchor line moves. One case reproduces the near-miss exactly.
It ran for real an hour later and printed `clean, and HEAD is on origin/main.`

## The split, and what it removed that I did not expect

`app.py` was the stylesheet, eleven screens, the chrome and the router. It is
the router now, 157 lines. The stylesheet is `theme.py`, the chrome is
`shell.py`, and every screen is its own module under `screens/`.

I drove the move off the AST rather than by line ranges, so each function
carried its leading comment block with it, and asserted both CSS strings
byte-identical before and after. That part was mechanical.

The part that was not mechanical is what fell out. Three renderers took a
`nav_to` callback, each with a comment explaining that `app.py` imports this
module so importing back would be a cycle. All three comments were true and all
three cycles were manufactured by the file itself: `app.py` owned `nav_to` and
also imported the manual, so the manual could not reach it. Move `nav_to` into
`shell.py` and there is nothing to work around. Three signatures lose a
parameter and three explanations get deleted.

**A file large enough to own everything creates cycles that only exist because
it owns everything.** The injection pattern read like a design decision for
months. It was scaffolding around a problem the file was causing.

One injection survived, which is the useful control on that claim: the audit
screen imports govflow's control popover, so govflow importing `audit_open`
back is a real cycle, and that one still goes through session state.

Two other things the split forced. The analysis engine was a module-level
singleton, which worked only because `app.py` re-executes top to bottom on
every rerun; a screen module is imported once, so it reads session state at call
time. And `ACCENT` was defined and used nowhere, duplicating a token the
stylesheet already owns, so it went rather than moved.

Two ratchet tests, because the file will grow back otherwise. `app.py` may
define no function or class and may carry no `<style>`. And every sidebar screen
must have a dispatch branch, which checks the router rather than filenames:
where a screen's code lives is a judgement, whether it is routed is not.

## The bug the deploy found

I deployed, then clicked every screen on prod. The Registry threw:

    FileNotFoundError: 'runtime/model_card_credit-lr-298ba5.pdf'

`runtime/` is gitignored, so it is not in the deploy bundle. Every local
checkout has one, because something has always written there. Prod never did.

The bug predates yesterday's Model Card move to the Registry. The retired
Pipeline screen wrote `runtime/model_card_download.pdf` the same way, so the
download has likely been broken on the live site since the first deploy, and
nobody clicked it there.

The interesting part is why the suite could not see it. The existing test called
`render_pdf(card, tmp_path / "card.pdf")`, and pytest creates `tmp_path` before
handing it over. So the test asserted the PDF renders given a directory that
exists, which is a weaker claim than the one the code needed to satisfy, and
the difference is invisible in the test's own text.

**A fixture more generous than production is a fixture that cannot fail.** The
new test writes into a nested path that does not exist, and I checked it in both
directions: it fails with the prod traceback when the `mkdir` is removed, and
passes when it is there. Fixed in `render_pdf` rather than at the call site, so
the CLI cannot hit it either.

That is the third time on this build that local hid an environment difference
the suite could not: the `sqlglot` import crash behind a health 200, the
codegen allowlist granting five packages nothing installed, and now a directory
that exists everywhere except where it matters. The shape is always the same.
The development environment is more permissive than prod, and every test runs in
the permissive one.
