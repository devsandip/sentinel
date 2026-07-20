# The caption was the bug

**2026-07-20 17:58**
Previous: [2026-07-20-1655-what-counts-as-a-refusal.md](2026-07-20-1655-what-counts-as-a-refusal.md)

Two follow-ups from the Audit Log session, both merged as PR #25. Per-stage
event attribution, and access control over the Audit Log itself.

## An honest caption is still a gap

The Audit Log printed a line on every govflow and L3 run saying its events
could not be filed under a stage, because the emitting agent does not identify
which one it came from. That was true. `flow.py` records `agent="govflow"` from
Ask, Plan and Access alike, so grouping by agent would have put Access events
under Ask.

I had shipped that caption feeling reasonably good about it. Saying what you
cannot do beats faking it. But the effect was that the governance-heaviest
route in the product, the nine-stage one, was the only route whose evidence
read as an undifferentiated stream, while a linear analysis got neat per-step
grouping. The honest caption made the gap tolerable enough that I stopped
looking at it. Sandip asked for the real fix and he was right to.

The cheap version was to infer the stage from the action string. `tier_block`
means Ask, `gate_pass` means Gate. It works today and it is a trap. It needs a
second mapping table that has to stay in step with 30 call sites, and its
failure mode is silent: a new action nobody adds to the table lands under the
default and nothing complains. Quiet misfiling on an audit surface is worse
than an admitted absence. That is the whole argument, and it is why the
expensive option was the correct one.

So `AuditEvent` carries a `stage` and the call site writes it, because the call
site is the only place that knows. 22 edits in `flow.py`, 8 in `l3.py`. I
considered a context manager on the log so a stage could be set once and
inherited, which would have been 9 edits instead of 30, but flow.py's stages
are sequential top-level code with early returns and wrapping them meant
re-indenting 300 lines into `with` blocks. Explicit at each site also reads
better in a governance file: every record states its own stage instead of
inheriting one from a cursor set somewhere above.

The field defaults to empty and the routes with no stage spine leave it that
way. A test asserts they do. Empty means "this route has no stages", not "we
lost it", and those are different claims.

## The screen about access control had none

The Audit Log let any persona read every run, and the "Ran by" filter offered
every actor to everyone. On the one screen whose subject is who may do what.

Entitlement is now `can_view_all_runs` in `personas.yaml`, defaulting to deny,
rather than a list of role names in Python. Oversight roles read the whole
ledger because reading other people's work is the job. The first line reads its
own runs. One predicate, `visible_runs()`, and three surfaces go through it:
the rows, the filter options, and the drill-down. The drill-down matters most.
`?run=<id>` is a real address, so checking only on the ledger would have made
the deep link the way around the check rather than a link to a run.

Two calls I want to remember making. **The scope is announced, not silently
applied.** A filtered ledger that does not say it is filtered reads as the
whole record, and the four KPI tiles above it become quiet understatements. And
**a withheld run says it exists**, naming who ran it. Hiding existence is the
stronger control and I would do that on anything external. Here the reader is a
colleague holding a link someone sent them, and "no such run" sends them
chasing a bug instead of asking for access.

None of this is authentication. The identity chip is a demo sign-in with no
credential, so anyone can switch to the Auditor and see everything. The screen
says so where it announces the scope. It demonstrates the policy. It does not
enforce it.

## Keeping the run ids

Re-seeding was the awkward tail. Every run mints a fresh uuid, so regenerating
the corpus would have renumbered all 24 runs and turned every shared `?run=`
link into a 404, on the exact surface whose workflow is "send me the evidence
for that run". The seeder now reads the ids already on file, keyed by the plan
slot, and keeps them. The 249-event corpus gained a field instead of being
renumbered. Nothing else carries over: status, metrics and events are always
the new execution's own.

Worth noticing that the fix was five lines and the alternative was quietly
breaking every link an auditor had bookmarked. I nearly shipped the re-seed
without thinking about it.

## Where the worktrees stand

I checked the other ten worktrees before merging, expecting to have to
sequence around parallel work. There is none. Nine are idle, clean or dirty
only with a `launch.json`. Two branches are ahead of main and both are dead:
one carries docs main already has, the other diffs against an `app.py` from
before v7 that used `st.sidebar.radio`.

That is its own finding. Long-lived worktrees over a 3,400 line `app.py` do not
produce parallel work, they produce abandoned branches. Splitting the screens
out of `app.py` is what would make parallelism real, and it is still not done.
