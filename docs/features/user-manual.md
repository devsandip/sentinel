# User Manual

**Status:** built — one screen, ten chapters, the first of which is a deck
**Nav:** Help group, last in the sidebar
**Owner surface:** `render_manual()` in `sentinel/ui/manual.py`
**Doctrine:** editorial prose is written here; every enforced number is imported

---

## 1. What this is

One screen that documents the whole product: what Sentinel is, how it is
governed, and how to drive it. The first chapter is a presentation covering the
product, the architecture, the governance, the tools and libraries, the autonomy
levels and the nine steps. The nine chapters after it are the reference the deck
points at.

It exists because the product outgrew the ability of any single screen to
explain it. There are nine governance stages, four autonomy tiers, twenty-six
named controls, eight classified datasets, six personas, three registries, ten
screens and ten tabs inside one of them. A visitor who lands on Overview can see
that the platform is large; nothing on that screen tells them what it is for or
in what order to look at it.

The Run screen already teaches the nine stages one panel at a time, and it
remains the best way to *see* the product work. It is a poor way to answer "what
is L2", "which controls can refuse", or "what is the difference between the
three things called a registry". Those are lookup questions, and until now they
had no surface.

---

## 2. Structure

| Chapter | What it answers |
|---|---|
| Presentation | Everything, at deck altitude. Nine slides. |
| Quick start | What do I click, in what order, in five minutes. |
| The nine stages | What each stage does, and which controls act there. |
| Autonomy levels | The tier arithmetic, the import allowlists, the sandbox caps. |
| Controls | The full catalogue: id, stage, action, what firing means. |
| Screens | Every screen and every tab, and what each is for. |
| Roles & access | Six personas, column-level RBAC, the purpose matrix. |
| Data | Eight datasets, and what a data contract does and does not publish. |
| Architecture | Module map, patterns, enforced numbers, deployment. |
| Glossary | The words this product uses in a specific way. |

Chapter navigation is a horizontal radio plus a Back/Next footer, matching the
Run screen's stage rail. Same interaction, same muscle memory, and the counter
reads "Chapter N / 10" the way the stepper reads "Stage N / 9".

### The deck, slide by slide

0. Cover. Always-dark, the login gate's surface treatment, five live stat chips.
1. What it does, and what it deliberately is not. Two panels, green and red.
2. Architecture. The two-plane diagram: pipeline versus control plane.
3. The nine steps. A three-by-three rail, each card carrying its controls.
4. Autonomy levels. The `min()` formula, the L0-L3 ladder, the two ceilings.
5. Governance. Controls grouped by stage, plus the five switchable ones.
6. Tools and libraries. Bought versus built, with live installed versions.
7. Roles. Six personas and the disjointness invariant.
8. The map. Nine screen cards, each with a button that navigates there.

---

## 3. The one rule this screen follows

**Every number reads from the module that enforces it.**

The stage list comes from `platform.audit_stages.CANONICAL_STAGES`. The tier
ceilings come from `govflow.tiers`. The control catalogue comes from
`govflow.controls_info`, including the split between enforced and declared. The
import allowlists come from `codegen.allowlist`. The sandbox caps come from
`sandbox.execute`. The personas come from `harness.identity`. The datasets come
from `datasets.registry`. The library versions come from `importlib.metadata`,
which is what is installed rather than what was declared.

This is not stylistic. This repo has twice shipped a claim that nothing held it
to: an allowlist that named five packages installed nowhere, and an Execute
panel whose stated wall clock had not matched the enforced one for several
versions. A manual is the highest-leverage place for that failure, because it is
the one surface a reader treats as authoritative.

Two consequences worth stating:

- **A missing package renders as missing.** The Bought table asks
  `importlib.metadata` for each distribution's version. A package on the L2
  allowlist that is absent prints "not installed here" rather than a version
  read from a file. That is the same signal `tests/test_allowlist_env.py`
  exists to raise, surfaced where a human will see it.
- **Doc-only controls can never render as live.** The Controls chapter walks
  `CONTROLS_INFO` and styles an id dashed, with a "declared, not implemented"
  badge, whenever it is absent from `implemented_ids()`. A control that gains an
  implementation changes appearance here with no edit.

`tests/test_app_smoke.py` pins this: `test_user_manual_deck_reads_its_numbers_from_the_modules`
asserts the five cover stats against the live collections, and
`test_user_manual_control_chapter_separates_enforced_from_declared` asserts the
badge count equals the doc-only count.

---

## 4. Decisions

**A screen, not a markdown file.** The alternative was `docs/user-manual.md`.
Rejected because a file cannot read the modules, cannot link to a screen, and is
not where a visitor to `sentinel.sandip.dev` is standing when they need it. The
repo already keeps foundational docs at `/docs`; this is a product surface that
happens to be documentation, which is a different thing.

**Help sits last in the sidebar.** Nothing in the product routes through it. A
Help group above Platform would imply it is a step in a workflow.

**`nav_to` is injected, not imported.** `app.py` imports `sentinel.ui.manual`,
so the manual importing `_nav_to` back would be a cycle. `render_manual(nav_to)`
takes the callable as a parameter. That is what the deck's screen-map buttons
and the quick start's "Go to Run" use.

**The shield moved to `sentinel/ui/brand.py`.** The cover draws the same mark as
the login gate and the topbar. It was a private constant in `app.py`; a logo
pasted into a second file goes stale in one of them.

**The manual states known drift rather than papering over it.** The Architecture
chapter says out loud that the README still describes a six-tab UI and a
plain-Python orchestrator, neither of which is true. Documenting the gap is
cheaper than a stale README quietly outranking the manual in a reader's head.

---

## 5. What this changed outside the manual

Writing the sandbox chapter surfaced a live drift. `DEFAULT_WALL_CLOCK_S` is
30s and is what every surface printed, but both governed routes passed a bare
`wall_clock_s=15` literal. So the number a reader saw was not the number a run
got, and the literal was duplicated across `govflow/flow.py` and `govflow/l3.py`
with no name either surface could read.

`GOVFLOW_WALL_CLOCK_S = 15.0` now lives in `sandbox/execute.py` and both call
sites use it. No behaviour changed; the value is identical. What changed is that
the number is nameable, so the manual can say "15 seconds on the governed
routes, 30s is the fallback for a caller that names no cap" and have both halves
be true. `test_governed_routes_pass_the_named_wall_clock_not_a_literal` pins it.

Worth recording how this was caught. The existing guard,
`test_no_screen_hardcodes_the_wall_clock`, scans every file in `sentinel/ui/`
for a retyped wall clock. It failed on this manual's own module docstring, which
was recounting the original defect and named the numbers to do it. The check
cannot tell prose from copy, and that bluntness is correct: nothing in
`sentinel/ui/` gets to restate the number, including the paragraph explaining
why nothing gets to restate the number. The docstring lost its numbers.

---

## 6. Known gaps

- **The deck is vertical scroll, not slides.** There is no full-screen or
  presenter mode. Streamlit has no primitive for it that would not be a fight,
  and the scroll version is what a reader wants anyway.
- **No print or PDF export.** The evidence pack has one because a bank needs to
  file it. Nobody needs to file the manual.
- **Screen and tab descriptions are editorial.** Unlike the numbers, they are
  hand-written and can drift from a renamed tab. The nine-screen map is asserted
  against nav targets by the link-out test; the ten tab descriptions are not.
- **The purpose matrix renders as a markdown table**, so its classification
  cells are not the clickable CTL-PURP-01 popovers the Datasets screen uses.
  Popovers inside a documentation table would be a lot of widgets for little
  gain, and the control is explained in full one chapter earlier.
