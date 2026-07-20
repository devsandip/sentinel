# Nine ticks over nine unequal checks

**2026-07-20 19:30**
Previous: [2026-07-20-1813-prod-carries-the-scope.md](2026-07-20-1813-prod-carries-the-scope.md)

Sandip said the Gate stage does not really say anything. It should show what
was gated, what tests were performed and why, and why the verdict went the way
it did. He was right and the fix was not on the screen.

## The screen could not have done better

The Gate panel printed a nine-row table: check, verdict, control. On the benign
path every row read "clear". That is the shape of evidence with none of the
substance, and I had already written down why the previous session: the audit
tiles had to learn that a control being consulted is not the control saying no.
This is the same error one layer down.

`gate_code` recorded only its refusals. `GateResult` was `passed` plus a list of
violations, so a run it cleared produced literally nothing. The screen printed
nine ticks because nine ticks was all there was to print. Every richer thing I
could have built on top would have been decoration over the same void.

So the gate now records what it read. Each check returns the constructs it
judged, the rule it judged them against, and a verdict. The benign sample stops
being nine identical clears and becomes: one import against a 14-module
allowlist, three column references against a six-column grant, sixteen names
swept against twelve denied network modules, eight attribute accesses against
fourteen denied dunders.

## Four verdicts, because there are four facts

The obvious version has two states. It is wrong, and wrong in the direction
that flatters the system.

A check that judged sixteen constructs and permitted all of them has cleared
the code. A check with nothing in this code to judge has cleared nothing: there
is no SQL, so no table can be out of scope. A check whose rule was never
supplied did not run at all. Painting those three the same green is claiming an
assurance nobody established, which is exactly what a control screen exists not
to do.

So: `cleared`, `refused`, `no_subject`, `not_armed`. Only the first two are
verdicts on the code. The last two are verdicts on the check.

That distinction paid for itself the hour it shipped. `l3.py` called
`gate_code` without `allowed_tables`, so `CTL-PURP-01` had no scope to test
against and could not fire on any L3 run, while the old screen ticked it. A
generated L3 program reaching for another table would have met nothing. It is
armed now, and a test fails if any check ever loses its rule again.

## What the visualization is for

Nine cells, one per check, each carrying the count of constructs that check
judged. Cleared is green, refused is red, nothing-to-read is dashed grey,
not-armed is amber. The count is the whole point: a tick cannot tell sixteen
from zero, and a number can. Run to run the shape changes, which is what makes
it a reading rather than a badge.

Under it, the read drawn on the code itself: a gutter counting the constructs
judged on each line. Tinting the refused line shows where the gate said no. It
does not show where the gate looked, and "I read all of it" is the one claim a
reviewer otherwise has to take entirely on trust.

And the verdict states a reason in both directions. A refusal that names its
control was already halfway there. An approval that says "no violations" is an
assertion, and this stage exists to replace assertions.

## The screen was keeping its own copy

The nine checks were declared in `ui/govflow.py` as a list of labels the screen
asserted the gate performs. Nothing held the gate to it. That is the fault this
build keeps finding in itself, four times now: the allowlist naming packages
nothing installed, the Execute panel claiming a wall clock the code did not
enforce, the stepper doc listing libraries that could not run, and now a gate
screen listing checks it had no way to confirm. The catalogue lives in
`gate.py` and the screen renders whatever the gate reports.

## Caught myself doing the same thing

The verdict read "the nine checks judged 61 constructs". The gutter directly
below it added up to 27. Both numbers were computed correctly; 61 is
judgements, because one import is judged by the allowlist and three deny lists,
and 27 is constructs. Printing one under the other's name on the one screen
whose argument is that its numbers can be checked would have been the whole
feature undone by its own headline. Both are stated now, and a test fails if
they are ever the same number.

PR #29, merged. 525 tests green.
