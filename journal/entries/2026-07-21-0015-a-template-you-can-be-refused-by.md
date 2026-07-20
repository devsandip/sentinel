# A template you can be refused by

**2026-07-21 00:15**
Previous: [2026-07-20-2045-refuse-first-then-retrieve.md](2026-07-20-2045-refuse-first-then-retrieve.md)

Sentinel has an Agent Templates screen under Governance. Editable specs, eleven
checks, and a deploy that registers a draft in the certification registry. 654
tests, 2 skipped, ruff clean. Not deployed yet.

Sandip asked for a section called Agent Templates under Governance with editable
and deployable templates, and asked what shape it should take and what format
the template should be. Both questions had answers already sitting in the repo,
which is the useful thing about a codebase that has been consistent with itself.

## The format was already decided

YAML, and not because YAML is nicer. `sentinel/config/` is five YAML files, and
`scaffold.py::_spec_yaml` already writes an agent spec in YAML when you run
`sentinel new-agent`. A JSON template would have meant the CLI and the screen
emitting two different artifacts for the same object. One format, two doors.

The looseness gets answered by the schema check rather than by the format. And
serialization goes through `json.dumps` for every scalar, because JSON is a
subset of YAML that PyYAML reads back identically, which means I never had to
think about a name with a colon in it or a version that looks like a float.

## Editing has to be refusable or it is decoration

This is the part that mattered. An editable template that always saves is a
text box with extra steps, and this build's whole argument is that nothing here
is decorative.

The way out is that a template names nothing of its own. A purpose is a column
in the matrix. An import is a name on the codegen allow-list. A tool is in
`agents.yaml`. A tier is a rung in `tiers.py`. A column is inside a grant in
`access.py`. So the editor keeps no policy: it reads the enforcing modules and
refuses whatever they would refuse. Eleven checks, reusing `CheckReading` and
`Observation` straight out of `codegen/gate.py` so the panel speaks the Gate
stage's language and the two cannot drift apart.

The fourth verdict earned its keep again, unprompted. `fair_lending` is the only
purpose with a defined column grant in this build, so I set the column check to
report `not_armed` on any other purpose. Then in the browser I flipped a
template's purpose from `fair_lending` to `marketing` to check the refusal, and
the column cell went from green to amber in the same rerun. That is the check
telling me the policy has a hole in it, on a screen I built to check templates.
A green tick there would have claimed an assurance nobody established.

## What deploy means when there is nothing to deploy to

Sandip said the button could be a dummy. The honest version is better and it was
already written: `certification.register()`, which is what the scaffolding CLI
does. So Deploy computes the dataset's content SHA now, pins it into the
contract, and puts a real `RegistryEntry` in the inventory at draft, where the
four gates decide what it may become. I verified it end to end in the browser:
deployed the validation template, then opened Registry and found
`validation v1.0 — DRAFT · owner UNASSIGNED` sitting under Analysis-agents.

The simulated part gets named on the screen rather than implied: nothing written
to disk, no process started, an enterprise deployment would push the spec to the
agent runtime from here.

## Two kinds of refusal, kept apart

This is the distinction I am most sure about. Policy checks are the fence and a
refusal disables the deploy, because an illegal blueprint should not reach the
registry. Certification gates are not the fence: they block `certified` and they
do not block the draft.

Every shipped template fails two certification gates, because all five carry
`owner: UNASSIGNED`. That is not an omission I should fix. A blueprint cannot
own the instances made from it; the owner is named when someone deploys one, and
`scaffold.py` registers a new agent unowned for the same reason. Had I made
those refusals block the deploy, the CLI and the screen would disagree about
what a new agent looks like on its first day.

It is the same mistake as painting `no_subject` green, in a new place: a screen
that shows "not yet owned" in the same red as "reaches for the network" is not
telling a reviewer which one is a policy violation.

## The tenth screen found a stale number

Adding the nav item made `manual.py` wrong. It opened its screens chapter with a
hand-typed "Nine screens in the sidebar" and nothing failed when that stopped
being true.

Same defect this build keeps finding in itself: a screen keeping its own copy of
what another module does. The Gate panel had it with the nine checks. The
Registry had it. So the nav definition moved out of `app.py` into
`sentinel/ui/nav.py`, both files read it, and the count is computed.
`product_screens()` excludes the Help group, because the manual, the FAQ and Ask
me are the manual describing itself and counting them would tell a reader there
are three more places to do work than there are. A test fails if anyone types a
number back into the prose.

I did not go looking for that. It fell out of adding a nav item, which is the
argument for computing counts rather than typing them: the typed one does not
fail, it just quietly stops being true.
