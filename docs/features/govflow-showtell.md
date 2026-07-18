# Governed codegen: the show-and-tell rework (v5)

Brief: `docs/more_ideas.md` (Sandip, 2026-07-18). The tool works but does not
demo well: the stages flash past, the controls are chips with no story, and
the interviewer cannot see what each control did. This rework makes the
Governed codegen surface a step-through experience where every stage is
explicit and every control explains itself.

## What changes

1. **Stage stepper.** The nine stages become a walkthrough. Ask and Plan are
   interactive configuration (three obvious sub-steps in Ask: import dataset,
   declare purpose, pick a prebuilt question; Plan shows the model and a
   populated parameter form). Run executes the whole governed flow as before,
   then the user steps through Access to Attest, one stage per panel, with
   Back/Next and a status strip.
2. **Controls explain themselves.** New `sentinel/govflow/controls_info.py`:
   one entry per control id (what it is, why it exists, what firing means,
   what it does). Every control chip in the UI opens a popover with that info
   plus what the control did in this specific run.
3. **Show the data decisions.** Access shows the scoped sample plus the full
   column inventory: withheld columns struck out in red, values masked, with
   a reason per column. Screen shows the result before and after screening;
   the suppressed band stays visible as a struck-through red row.
4. **Fix it at the Gate.** On a gate block, a Fix it button asks the model to
   repair the refusal and resubmit; the gate genuinely re-reads the repaired
   code. Live mode feeds the violations back to the model (the existing
   regeneration seam). Scripted mode uses a seeded repaired sample per
   adversarial intent, labeled as seeded; the re-review is real.
5. **Header chips are real.** The top-right chips open popovers naming the
   controls each one stands for; the Admin persona can toggle a control from
   the popover (same audited, UNGOVERNED-marking mechanics as before).
6. **Interpret shows the writing.** The narration types out (labeled
   "scripted narration" in scripted mode, real model output in live mode),
   followed by the CTL-EVAL-01 faithfulness verdict.
7. **Polish.** One CSS pass across the app: cards, tables, chips, spacing.

## Decisions

- **The stepper is a walkthrough over a completed run, not partial
  execution.** `run_governed_analysis` stays one call; the UI steps through
  the result. No resumable flow machinery; the flow module remains the
  single authority on stage order and stop behavior.
- **UI code lives in `sentinel/ui/govflow.py`.** The deploy bundle ships
  only `app.py` + `sentinel/`, so the UI module cannot be a new root file.
  app.py keeps the section router and delegates.
- **Screen shows the suppressed row struck out, values kept.** The before
  view is the analyst-side demo view; the caption states that the narration
  model and downstream consumers receive only the screened frame. "Removed,
  not masked" still holds where it matters: nothing downstream sees the row.
- **Repair is a new run linked to the blocked one.** `repaired_from` carries
  the blocked run id; the audit trail records the repair request. In
  scripted mode the repaired sample is the same analysis minus the violating
  line, so the diff reads as "the model removed line N."
- **to_public_dict grows, nothing is removed.** New keys: `execution`,
  `generation_attempts`, `access`, `tier_decision`, `repaired_from`. The
  existing key set is pinned by tests and untouched. This also fixes the L3
  gap where the numeric effect lived only in the unserialized
  ExecutionResult.
- **Doc-only control ids stay doc-only.** CTL-RBAC-01/02, CTL-PURP-02,
  CTL-TIER-01, CTL-INJECT-01, CTL-COST-01, CTL-DISC-04, CTL-LIN-01,
  CTL-PII-01 are in the PRD but not implemented; controls_info marks them
  `implemented=False` and the UI never shows them as live controls.

## Review findings and decisions (2026-07-19, overnight build)

A multi-agent adversarial review of the diff produced 18 confirmed findings;
all are fixed in this branch. The decisions worth keeping:

- **The repair linkage is earned, not stamped.** `repaired_from` is set iff
  the repair machinery actually engaged at Generate (`repair_engaged`), so an
  L0/L1 route, a tier-blocked L3 attempt, or a stray `repair_of` on a plain
  run never claims a repair it did not perform. Invariant: `repaired_from`
  set iff a `repair_requested` audit record exists. Pinned by tests.
- **Audit and banner wording follow the actual author.** Scripted repairs
  say "seeded repaired sample substituted and re-gated"; only live runs say
  the model addressed the refusal. Same for the Gate banner.
- **The narration is a deterministic template in this flow** (no
  gateway.narrate call in govflow), so the Interpret panel never labels it
  "live model narration"; the live/scripted toggle governs code generation
  only. The hero pipeline remains the live-narration demo.
- **L1 is not sandboxed and the Execute panel says so**: trusted platform
  code, in-process; the sandbox explainer is shown as what L2/L3 generated
  code faces.
- **The tier gates the Run button from the current persona**, recomputed at
  render, never from a draft written under a previous persona.
- **Stale Admin toggles do not degrade other personas.** `_control_settings`
  returns clean settings unless the persona holds toggle authority; badge
  and chip labels reflect what the next run would actually get.
- **Markdown emphasis is escaped alongside HTML** (`_md_esc`) wherever gate
  messages or dunder names reach st.markdown, so `__import__` renders as
  itself, not bold "import".
- **sql_star's seeded repair is a rewrite, not a minus-one-line edit** (a
  column-explicit dump would fail the Execute shape check); the comment in
  generate.py says so instead of overclaiming.

## The design-system adoption (2026-07-19, after Sandip's mid-build review)

Sandip pointed the build at the unified-app mockup and its written spec
(`docs/ui-spec.md`, brought onto this branch together with
`docs/features/demo-stepper-ux.md` and `docs/features/unified-app-build.md`
and the mockups). The stepper and app chrome now implement the spec's design
system: the full light-token set, hidden Streamlit chrome, the topbar command
frame (brand lockup + live context chips + one Controls popover replacing the
six vanity chips), the sidebar styled as the nav rail, the stage rail with
numbered nodes and connectors, per-stage phead + In/Does/Out + engine bar,
spec tables, the syntax-colored code block with violation rows, and the
Architecture tenth stop.

Decisions and known deviations, for the morning review:

- **The rail is the styled stage radio, not custom HTML.** A custom HTML
  rail's links would reload the page and drop the Streamlit session (losing
  the run), so the radio stays the interactive layer, CSS-transformed into
  the mockup's rail (CSS counters for the node numbers, `data-selected` for
  the active state). Node numbers stay numbers; done-state ✓ shows in the
  label text, and connectors do not fill on done. Tests keep driving the
  radio unchanged.
- **The control drawer is a popover.** Streamlit has no right-edge
  slide-over; the drawer's three-block content (what it is / why / what it
  did here) renders in the existing control popovers.
- **Deferred to the build plan's own phases** (docs/features/
  unified-app-build.md): the login persona gate (S1), the grouped sidebar +
  command-center landing (S2, S3), the transition overlay, dark mode and the
  theme toggle, and the D (datasets) and H (seeded history) workstreams.
  These are structural additions the plan sequences separately; nothing
  tonight forecloses them.
- **Engine-bar honesty.** Library chips list only what actually runs at that
  stage in this build (e.g. Screen lists pandas + numpy because the
  association measures are hand-rolled there; the mockup's fairlearn chip
  belongs to Generate/Execute where the generated code uses it). CTL-TIER-01
  is not shown as a live control because no code emits it.

## Out of scope

- OPA externalisation (open PRD question, Sandip's call).
- Any change to gate/screen/sandbox semantics. The governance behavior is
  untouched; this is presentation plus the repair path.
- Prod deploy. This ships as a PR for morning review.
