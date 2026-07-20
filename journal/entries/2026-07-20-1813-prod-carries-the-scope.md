# Prod carries the scope

**2026-07-20 18:13**
Previous: [2026-07-20-1758-the-caption-was-the-bug.md](2026-07-20-1758-the-caption-was-the-bug.md)

Deployed PR #25. Bundle `sentinel-20260720-180457.zip`, stack `sentinel-eb`
updated, EB Health Green. Health 200, root 200 in 0.66s, WebSocket 101,
live-LLM key present. Prod is in sync with `main` at `174df5e`.

## Deploying one change at a time

Sandip asked whether he could deploy once after merging the other worktrees.
The answer was that there is nothing to merge, so the batch would never have
fired. But the question is worth recording because the reasoning generalises.

The deploy is not incremental. `deploy.sh` zips the repo root and hands EB a
fresh bundle, so one deploy after five merges costs exactly what one deploy
after one merge costs. Batching is free in effort. What it costs is bisection.
The last deploy carried four things at once and prod had been three sessions
stale before it; if that one had broken, there were four suspects. This one
carried a single tested change, so a failure would have had one.

That is the argument for deploying on merge rather than on a schedule, and it
only holds while each merge is small. It is the same reason the `app.py` split
matters: big merges make big deploys make slow diagnosis.

## Verified the way that proves something

Health 200 would have passed on the old bundle. It always does, because
Streamlit answers that endpoint before `app.py` runs, which is how the very
first prod deploy returned 200 while every page was broken.

So the check was the behaviour that only exists in this build. Signed in as the
Data Scientist: the Audit Log reads 20 runs with the "Scoped to your runs"
banner and 4 withheld, the KPI tiles scoped with it, and "Ran by" disabled
while Kind and Control stay live. Opened the completed govflow run: events
filed under Ask, Plan, Access, Gate, Execute, Screen, Interpret and Attest,
every stage that emitted one, and no caption apologising for the ones it could
not place. Pre-#25 that same screen showed all 24 runs, no banner, an enabled
filter and the apology.

Each of those is a thing that cannot be true unless the new code is running. A
deploy is verified when the change is visible, not when the instance is up.
