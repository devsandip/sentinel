# Refuse first, then retrieve

**2026-07-20 20:45**
Previous: [2026-07-20-2010-the-guard-checks-head-the-bundle-is-the-tree.md](2026-07-20-2010-the-guard-checks-head-the-bundle-is-the-tree.md)

Sentinel has an FAQ and a chat under Help. PR #33, merged, deployed as bundle
`sentinel-20260720-200636.zip`, application version
`sentinel-eb-applicationversion-pnysewhnfcn2`, EB Ready and Green. Health 200,
WebSocket 101. `main` at `7ac3dde`. 606 tests, 2 skipped, ruff clean.

Sandip asked for two things under Help: an FAQ, and an "Ask me" where anyone
can type a question and an LLM answers from the manual, but only after a test
decides the question is even relevant. His example was "Who is the PM of
India?".

That ordering is the whole feature and it is worth saying why. The obvious
build is to retrieve first and let the model decline if the passages do not
support an answer. It fails on exactly the question he picked. A model handed
five passages about governance stages and a question about Indian politics
will try to bridge the two, because bridging is what the next-token objective
rewards, and the bridge is where a confident falsehood gets built. Gating
first means the answer stage is never asked to reconcile a question it has no
business answering. On prod, the live gate refuses the India question for 175
tokens and $0.0002, and no answer call is made at all.

## Three verdicts, not two

Off topic and on-topic-but-uncovered are different facts about a question, and
collapsing them into one "cannot help" hides the second. `IRRELEVANT` says
this is not about the product. `UNSUPPORTED` says it is, and the manual does
not cover it, which is a gap in the manual and should read like one. Same
reasoning that keeps `NOT_IN_ROUTE` distinct from `skipped` in the audit
stages, and I did not notice the parallel until I had written both.

## The corpus is a second source of truth, on purpose

The manual is `sentinel/ui/manual.py`, a screen. Right shape for a reader,
wrong shape for retrieval. I offered Sandip three ways to get text out of it:
render each chapter under a recording stand-in for `st` and capture the prose,
refactor the chapters to emit structured content, or write a parallel markdown
corpus. I recommended the first because it cannot drift. He picked the third.

His call, and it is the simpler thing to read and edit. But the manual's whole
doctrine is that every enforced number reads from the module that enforces it,
and markdown can read nothing. So the corpus is forbidden from stating one. A
page names the cap and points at the chapter that prints it: "the sandbox
enforces a wall clock and a memory ceiling, and the Autonomy levels chapter
prints the enforced values." `test_corpus_states_no_enforced_number` reads the
sandbox caps, the disclosure floor and the control and persona counts live off
their modules and fails any page that retypes one. Same shape as
`test_no_screen_hardcodes_the_wall_clock`, which is the guard that fired on my
own docstring three hours ago.

A corpus that may not carry numbers can still drift in its prose. That
degradation is survivable: a dated description of what a chapter covers is a
worse answer, not a false claim about what the sandbox enforces. Choosing
which drift you can live with is most of what this decision was.

## The gate needed a second test

Both stages work with no model, because the public link has no key. The
scripted gate started as a TF-IDF cosine floor over the corpus, and it passed
every test I wrote until I wrote "Write me a poem about the sea." Answered.
One incidental term cleared the floor: a corpus that talks at length about
writing code has plenty of "write" in it.

Cosine asks whether any passage looks like an answer. It does not ask whether
the question is in our vocabulary at all. So the gate is now two tests, and a
question must pass both: cosine, plus the fraction of the question's own
content words that appear anywhere in the corpus. "Poem" and "sea" are foreign,
so coverage is a third, and the poem is refused. Seven off-topic questions and
seven real ones are parametrised now, because the quiet failure mode is the
opposite one: a gate that refuses real questions makes the feature useless
without ever looking broken.

## Small things

`ModelGateway.complete()` is new. Narration is templated by step, code
generation has canned code to fall back to, and neither shape fits a question a
visitor typed, so the caller supplies both prompt and fallback. Everything else
is the existing machinery: stakes routing, the cache, the process cost cap, a
ledger row per call. Help does not get a private path to a model, because
nothing does.

The chapter hand-off buttons were `on_click` callbacks at first, and `_nav_to`
ends in `st.rerun()`, which is a no-op inside a callback. Streamlit printed a
warning banner on the page and the tests passed anyway, because the rerun that
follows a callback made the navigation work regardless. Only visible by
driving it in a browser.

I also wasted a build before this one. Sandip's first message said "add two
more things under help", and there was no Help section on the branch I was
standing on: the manual was still an unmerged PR I never checked for. I wrote
a twelve-page manual, a loader, a retriever and a gate against a product that
already had all of it, and he stopped me. The instruction was accurate and I
read it as mistaken. Checking `origin/main` costs one command.

Two guards from this morning held on the deploy: primary checkout on `main` at
exactly `origin/main`, and `git status --porcelain` empty before the bundle was
built.
