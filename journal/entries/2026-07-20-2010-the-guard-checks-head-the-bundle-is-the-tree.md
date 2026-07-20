# The guard checks HEAD, the bundle is the tree

**2026-07-20 20:10**
Previous: [2026-07-20-1930-nine-ticks-over-nine-unequal-checks.md](2026-07-20-1930-nine-ticks-over-nine-unequal-checks.md)

Deployed three merges: PR #29 (the Gate read), #30 (the Live LLM path), #32
(the session record). Bundle `sentinel-20260720-191009.zip`, EB Ready and
Green. Health 200, root 200 in 0.74s, static gzipped, WebSocket 101.

But the interesting part happened before the deploy ran.

## The checkout passed every check I had and was still wrong

The rule I have been carrying since the v6 near-miss is: do not deploy from a
checkout that is not on `main`. There is an open question in this journal about
making `deploy.sh` refuse when `HEAD` is not an ancestor of `origin/main`.

I ran that check. It passed. `HEAD` was `29ad22b`, exactly `origin/main`, on
branch `main`, tracking cleanly.

Then `git status` showed nineteen files staged: 116 insertions, 2,699
deletions. The index held a full revert of all three merges. Every "insertion"
was old content coming back, the pre-`CheckReading` gate, an INDEX header
pointing at 18:13, the pre-#30 prompts. `result_contract.py` deleted. Both
journal entries deleted.

`deploy.sh` zips the repo root. It does not archive `HEAD`, it archives the
working tree. So the deploy would have built a bundle without the Gate read and
without the Live LLM fix, uploaded it, gone Green, and reported success. I
would have verified health 200 and written it up as shipped.

**The guard I had been designing checks the wrong noun.** `HEAD` is where the
branch points. The bundle is what is on disk. Those are the same thing only
when the tree is clean, and nothing was checking that. The correct guard is two
clauses: `HEAD` is an ancestor of `origin/main`, *and* `git status --porcelain`
is empty. The second one is the one that would have fired today.

I stashed rather than reset, because "nothing here is new" was a conclusion I
had reached by reading a diff, and a hard reset would have made me right by
force. `stash@{0}` holds it. Nothing untracked was present, so nothing was at
risk either way; the stash costs nothing and keeps the conclusion falsifiable.

I do not know how the checkout got into that state. It was not this session.

## Verified by the thing that cannot render on the old bundle

Health 200 proves nothing here; Streamlit answers it before `app.py` runs.

So: signed in as the Data Scientist, ran the benign L2 analysis, opened Gate.
Nine cells, seven green, two dashed grey, eleven gutter rows. "The nine checks
made 61 judgements over the 27 constructs in 11 lines." Then ran the SQL
wildcard adversarial request and the strip changed shape: CTL-CODE-01 goes to
nothing-to-read because the SQL sample imports nothing, CTL-PURP-01 and
CTL-COMPLEX-01 light up at 1 judged each because there is finally SQL to read,
and CTL-COL-01 goes red at "1 judged, 1 refused" with the chip reading
`SELECT *`.

That second run is the better proof, and not only because it is a refusal. The
same nine cells drew a different shape on different code, which is the whole
claim the panel makes: it is a reading, not a badge. A screen that renders
identically on both runs is the thing I replaced this afternoon.

No console errors.

## What I did not verify

PR #30 is deployed and its code is live, but I checked it only through the
scripted path. Confirming the Live LLM fix behaviourally means a real model
call against the cap, on someone else's change, so I left it. It is shipped,
not demonstrated. Worth one live run next session.
