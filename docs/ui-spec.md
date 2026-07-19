# Sentinel UI spec — the design system

This is the written record of what the unified-app mockup
(`docs/mockups/sentinel-stepper-mockup.html`) actually looks like: tokens,
layout, components, screen-by-screen structure. `docs/features/demo-stepper-ux.md`
and `docs/features/unified-app-build.md` describe *what the screens do and in what
order to build them*; this doc describes *what they are rendered as*, extracted
directly from the mockup's CSS and markup so the look survives even if the mockup
file is lost, edited, or unavailable. If this doc and the mockup ever disagree,
the mockup is the source of truth for pixels — but update this doc in the same
commit, don't let it drift silently again.

Foundational per repo convention: this belongs at `/docs` root (`ui-spec.md`),
alongside `prd.md`-equivalent docs (`docs/features/*`).

---

## 1. Design tokens

All colors are CSS custom properties on `:root`, redefined under
`@media (prefers-color-scheme: dark)` and again under `:root[data-theme="dark"]` /
`:root[data-theme="light"]` (the in-app theme toggle overrides the OS preference in
both directions). Every component styles through the tokens, never a literal hex,
except a small list of always-dark surfaces called out in Section 1.5.

### 1.1 Core palette

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--canvas` | `#e9edf4` | `#0a1220` | page background |
| `--surface` | `#ffffff` | `#0f1a2c` | cards, panels, modals |
| `--surface-2` | `#f4f7fb` | `#14223a` | table headers, subtle fills, icard |
| `--border` | `#dde4ee` | `#22334f` | hairlines |
| `--border-strong` | `#c4d0e2` | `#30456a` | stronger dividers, disabled radio rings |
| `--ink` | `#0f1b2d` | `#e7edf8` | primary text |
| `--muted` | `#57647a` | `#9aa8c0` | secondary text |
| `--faint` | `#66717f` | `#8291ab` | tertiary/label text (AA-checked against surface) |
| `--accent` | `#1e50a0` | `#5b8def` | primary brand blue |
| `--accent-strong` | `#17417f` | `#7aa6f5` | hover/active accent |
| `--accent-ink` | `#ffffff` | `#08121f` | text on filled-accent buttons |
| `--accent-soft` / `--accent-soft-border` | `#e8eef9` / `#cddbf1` | `#152743` / `#2a4576` | selected states, info notes |

### 1.2 Semantic status colors (independent of the accent hue)

Three-part pattern per status: base / soft-background / border / ink-on-soft.

| Status | Light base/soft/border/ink | Dark base/soft/border/ink |
|---|---|---|
| `ok` (pass/certified/promoted/live) | `#1b7f3b` / `#e6f5ec` / `#bfe3cc` / `#12692f` | `#4ec27a` / `#122a1c` / `#1f4a30` / `#8fe0a9` |
| `warn` (fired/candidate/flagged) | `#b26a00` / `#fbf0dc` / `#f0d9ad` / `#8a5200` | `#e2a03a` / `#2a2110` / `#4d3a17` / `#f0c274` |
| `danger` (block/refused/caught) | `#b3261e` / `#fdeceb` / `#f3ccc9` / `#8f1d17` | `#e5675e` / `#2a1513` / `#552420` / `#f2a39c` |

### 1.3 App-chrome tokens (topbar / sidebar / stepper rail — theme-aware)

These exist as a **separate** set from `--rail` because `--rail`/`--rail-2` are
deliberately always-dark (used by the login and the dashboard CTA before its
theming fix). The chrome must flip with the theme, so it gets its own tokens:

| Token | Light | Dark |
|---|---|---|
| `--chrome-bg` | `#ffffff` | `#070e1a` |
| `--chrome-bg-2` | `#eef2f8` | `#0c1728` |
| `--chrome-ink` | `#0f1b2d` | `#eef3fc` |
| `--chrome-muted` | `#5b6a82` | `#8194b4` |
| `--chrome-border` | `#d6deea` | `#1b2b47` |
| `--chrome-hover` | `#e3e9f3` | `rgba(255,255,255,.06)` |
| `--chrome-abg` (active nav bg) | `#e8eef9` | `rgba(91,141,239,.16)` |
| `--chrome-aink` (active nav text) | `#1e50a0` | `#cfe0fb` |
| `--chrome-aborder` | `#cddbf1` | `#2f4d7e` |

### 1.4 Code-block tokens (Generate stage syntax highlighting — theme-aware)

| Token | Light | Dark |
|---|---|---|
| `--code-bg` | `#f4f7fc` | `#0c1626` |
| `--code-ink` | `#2a3852` | `#c7d3e6` |
| `--code-cm` (comments) | `#8a94a6` | `#6b7d9c` |
| `--code-kw` (keywords) | `#1e50a0` | `#7aa6f5` |
| `--code-str` (strings) | `#1b7f3b` | `#8fd6a0` |
| `--code-fn` (functions) | `#a35a00` | `#e2c07a` |
| `--code-ln` (line numbers) | `#aab4c6` | `#4d5f7d` |
| `--code-viol-bg` / `--code-viol-ln` (the violating line) | `rgba(179,38,30,.08)` / `#b3261e` | `rgba(229,103,94,.14)` / `#e5675e` |

### 1.5 Deliberately always-dark surfaces (not theme-tokenized)

Two things stay dark in both themes on purpose — a considered choice, not a gap:
- `--rail` / `--rail-2` (`#0d1a30` / `#12233f` light-mode values, `#070e1a` /
  `#0c1728` dark) — the login overlay background and the dashboard's original CTA
  (CTA was later moved to theme-aware `--surface`; `--rail` itself remains used
  only by the login).
- The **login screen** (`.login`): a fixed full-screen radial gradient
  `radial-gradient(1100px 560px at 50% -8%, #16274a, var(--rail))`, always dark,
  regardless of theme. This is a considered "sign-in moment" choice, not a bug —
  do not theme it without a deliberate design decision to do so.

### 1.6 Typography

- Sans (UI text): `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`.
- Mono (ids, SHAs, control codes, code blocks, tabular numbers): `"SF Mono", "JetBrains Mono", "Fira Code", "Cascadia Code", ui-monospace, Menlo, Consolas, monospace`.
- Base body: 15px / line-height 1.5. Headings: weight 650, letter-spacing -0.011em, `text-wrap: balance`.
- `.eyebrow` label pattern (used everywhere as a section kicker): 11px, weight 700, letter-spacing .13em, uppercase, `--faint`.
- `.mono` utility class adds `font-variant-numeric: tabular-nums` so numeric columns align.

### 1.7 Shape, elevation, spacing

- Radii: `--r-sm: 7px` (buttons), `--r-md: 11px` (cards, chips, inputs), `--r-lg: 16px` (panels, modals, tiles).
- Shadows: `--shadow-sm` (resting card), `--shadow-md` (elevated card / CTA / modal), `--shadow-lg` (drawer / modal backdrop-level). Dark-mode shadows use pure-black rgba at higher opacity, not the light-mode navy-tinted rgba.
- Content max-widths: stepper stage content `--stage-max: 1060px`; surface pages `1040px`; dashboard `1120px`; login card block `860px`.
- Sidebar fixed width: `238px`.

---

## 2. Layout: the app shell

The shell is a single CSS grid wrapping every screen:

```
.shell { display:grid; grid-template-columns: 238px minmax(0,1fr); grid-template-rows: auto 1fr; min-height:100vh; }
```

- **Row 1, full width:** `.topbar`, `position:sticky; top:0`. Command frame: brand
  mark (left) + a flexible spacer + a right-aligned cluster of context chips and
  icon buttons.
- **Row 2, column 1:** `.sidenav`, `position:sticky; top:var(--topbar-h)`
  (measured live via a `ResizeObserver` on the topbar, not hardcoded — the topbar's
  real height can vary if its chip row wraps). Persistent on every screen.
- **Row 2, column 2:** `.content`, holding three mutually-exclusive `.view`
  containers (`display:none` / `.show { display:block }`), toggled by JS, never
  by page navigation: `#view-home` (dashboard), `#view-run` (the stepper), and
  `#view-surface` (a single reusable container the four platform surfaces render
  into).

**No responsive/mobile layout.** By explicit decision (2026-07-18) this is a fixed
desktop layout only — every `max-width` media query was removed. The only
remaining `@media` queries are `prefers-color-scheme` and
`prefers-reduced-motion`. Do not reintroduce a mobile breakpoint without asking.

### 2.1 Topbar (`.topbar`)

Row: `[brand] [spacer] [ctx-chip: persona] [ctx-chip: dataset+classification] [ctx-chip: purpose] [ctx-chip: tier] [iconbtn: Stack] [iconbtn: Controls] [iconbtn: theme toggle]`.

- **Brand** (`.brand`): inline SVG shield glyph (a rounded-shield outline with a
  checkmark, accent-colored) + wordmark "SENTINEL" (700 weight, .22em
  letter-spacing, 15px) + a divider + subtitle "Governed Agentic Analysis"
  (11px, muted, border-left separator).
- **Context chips** (`.ctx-chip`): pill-shaped (`border-radius:999px`), chrome-bg-2
  fill, chrome-border outline, 12px text. Each carries a small `.k` label prefix
  in muted color (e.g. "Data", "Purpose", "Tier") followed by the live value.
  Four chips today: persona (with a colored status dot, e.g. `#5fdc8a` for
  certified), dataset name + a classification `.badge.danger` inline, purpose,
  and tier (accent-colored badge). All chips are clickable buttons that jump to
  the relevant stage/control.
  **As built (2026-07-19), the chips are run-scoped.** Data and Purpose describe
  a run, so they render only on a screen that has one in scope: the Run
  walkthrough (from the published run, else the draft config) and the credit
  pipeline once a run has started (Data only; an orchestrator run declares no
  purpose). The dashboard and the catalog screens show no chips rather than
  inheriting a german_credit / fair-lending default that describes nothing on
  the page. Persona and tier left the topbar earlier: identity is the header's
  "Acting as" popover, and the tier is run-scope, shown in the Run flow. The
  only always-on element is the UNGOVERNED warning badge, which is global state.
- **Icon buttons** (`.iconbtn`): transparent bg, chrome-border outline, 8px
  radius. Three: "▦ Stack" (jumps to the Architecture stop), "▤ Controls" (opens
  the control-plane modal), and a theme toggle (◑/◐ depending on state,
  `aria-pressed`).

### 2.2 Sidebar (`.sidenav`)

Grouped nav, no icons-only mode, always full width (238px), always all items
visible (no persona-based hiding — a deliberate decision):

```
(no group label) Overview
Workspace         Run
Governance        Datasets [8]   Registry [3]
Platform          Platform [5]   Adoption
```

- Group label (`.navgroup .gl`): 9.5px, 700 weight, .11em letter-spacing,
  uppercase, chrome-muted, 14px bottom margin per group.
- Nav item (`.navitem`): full-width button, 10px icon+label gap, 9px/11px
  padding, 9px radius. Rest state: transparent bg, chrome-muted text. Hover:
  chrome-hover bg, chrome-ink text. Active (`aria-current="page"`): chrome-abg
  bg, chrome-aink text, chrome-aborder 1px border.
- Optional trailing count badge (`.cnt`): small mono pill, chrome-bg fill,
  chrome-border outline, right-aligned via `margin-left:auto`. Present on
  Datasets ("8") and Registry ("3") and Platform ("5"); absent on Overview, Run,
  Adoption.
- Icons are inline SVG (17×17, `aria-hidden`), one stroke-style linework glyph
  per section: home (roof+base), play (triangle), database (stacked ellipse
  cylinder), check (rounded square + checkmark), grid (2×2 squares), bar-chart
  (axis + three bars).

**As built (2026-07-19).** Rail width is 222px, not 238px: left-aligning the
labels under their group headers freed the difference. Rows stack flush (the
9px/11px padding is the row height, ~37px); the only vertical air in the rail is
the 14px above a group label and the 6px under it. Streamlit's 16px default gap
between block elements is zeroed inside the sidebar, since it doubled that
rhythm and left the rail loose. Icons are Material Symbols at 16px rather than
inline SVG, since the nav items are `st.button(icon=...)`. An in-app Back
control sits above Overview, pinned (`position:sticky`) to the top of the
scrolling rail with a 1px rule under it, so it stays reachable on a long screen.

### 2.3 Stepper rail (`.rail`, inside the Run view only)

A horizontal 10-node rail (nine governed stages + the Architecture overview
appended as a 10th, visually distinct stop): `chrome-bg-2` background, sits below
the topbar, full width, horizontally scrollable if it overflows (`overflow-x:auto`).

Per node (`.step`): a connector line to the previous node, a circular `.node`
(30px, 2px border, mono index number), a label, and an optional status tag pill
below the label.

- **Node states:** default (chrome-bg fill, chrome-border, chrome-muted number) →
  `.done` (ok-soft fill, ok-border, ok-ink, shows a ✓ instead of the number) →
  `.active` (filled accent, white text, `box-shadow: 0 0 0 4px` accent-tinted
  ring, `scale(1.06)`).
- **Status tags** under the label: `.tag.quiet` (a muted middot, nothing fired),
  `.tag.fired` (amber pill, e.g. "3 FIRED"), `.tag.caught` (red pill, e.g.
  "1 CAUGHT"), `.tag.meta` (accent-tinted pill, "OVERVIEW" — only on the 10th
  stop).
- **The 10th (Architecture) node is visually distinct from the nine governed
  stages**, on purpose — it is an appendix, not a tenth "stage": dashed connector
  line (vs solid), dashed node border, a glyph (▦) instead of a number that never
  becomes a ✓, and the counter reads "Architecture" instead of "Stage 10 / 9".

### 2.4 Footer nav bar (`.navbar`, Run view only)

Fixed to viewport bottom, offset by the sidebar width (`left:238px`), translucent
blurred surface (`color-mix` 88% surface + backdrop-blur). Contents:
`[← Back] [flex-grow caption text] [mono step counter, e.g. "Stage 5 / 9"] [Next → / Done ✓]`.

### 2.5 Stage transition overlay (`.transition`)

A full-viewport, blurred, semi-opaque scrim with a centered small card
(spinner + a verb + a message), shown briefly on every stage change — including
the scripted (non-LLM) path, so the platform visibly "does something" on every
transition. Verb is **"Governing"** for deterministic stages (a real control is
computing), **"Thinking"** only for Generate and Interpret (the two LLM-touching
stages), and **"Zooming out"** for the Architecture stop. Skipped entirely under
`prefers-reduced-motion`.

---

## 3. Screen-by-screen

### 3.1 Login (`.login`, shown before anything else)

Full-viewport fixed overlay, z-index 100, `role="dialog" aria-modal="true"`,
always-dark radial-gradient background regardless of theme (see 1.5). Centered
column, max-width 860px:

1. Brand lockup (shield SVG + "SENTINEL" wordmark + subtitle), larger than the
   in-app topbar version.
2. Eyebrow "ACTING AS" (accent-tinted, uppercase).
3. H1 "Choose an identity" (28px, white).
4. One sentence of subtext: "Every persona is governed differently. Your role
   and attestations set how much machine autonomy the platform grants, computed
   as the lower of the two."
5. A 3-column grid of six persona cards (`.persona-grid`, `.pcard`).
6. Footer microcopy: "Faux sign-in for the demo. No credentials, no auth. Pick
   anyone to enter."

**Persona card** (`.pcard`): dark translucent card (`rgba(255,255,255,.04)`),
18px/16px padding, 14px radius, hover lifts (`translateY(-3px)`) and brightens
border/bg. Each card shows: a top-right tier badge pill (e.g. "L2"), a 46×46
rounded icon tile (accent-tinted bg, a linework SVG glyph), the persona name
(15px, white, 650 weight), a role line (11.5px, muted), and a one-line capability
description (12px). The hero card (Data Scientist / Analyst) has a visibly
brighter border/bg and an extra green "RUNS THIS WALKTHROUGH" tag.

**The six personas, in card order:**

| id | Name | Role | Tier badge | Resolved tier | Icon | Capability line |
|---|---|---|---|---|---|---|
| `analyst` (hero) | Data Scientist | First line · certified | L2 | L2 | person-with-check | "Writes gated code against the fenced API. Runs this walkthrough." |
| `junior` | Junior Analyst | First line · uncertified | L1 | L1 | plain person | "Picks a certified analysis and fills typed params. Writes no code." |
| `validator` | Model Validator | Second line · MRM | L0 | L0 | magnifying glass | "Independently reviews fairness and evals. Does not run." |
| `approver` | MRM Approver | Second line · sign-off | L0 | L0 | stamp | "Holds the promotion sign-off. Four-eyes, never self-approves." |
| `auditor` | Internal Auditor | Third line | L0 | L0 | eye | "Read-only across the audit trail, evidence, and lineage." |
| `admin` | Platform Admin | Platform | L3 | L2 (caps here) | gear | "May toggle a control (audited). L3 on Public data, caps at L2 here." |

Picking a persona sets the topbar persona/tier chips, fades the login out
(`opacity` transition, 280ms, skipped under reduced-motion), and lands on the
dashboard (not directly into the run). Picking a non-analyst persona shows an
amber identity banner (`.idbanner`, warn-soft/warn-border/warn-ink) explaining
what tier they actually resolve to and that they're viewing the certified
Analyst's L2 run.

### 3.2 Command-center dashboard (`.dash`, the landing after login)

Max-width 1120px, centered.

1. Eyebrow "GOVERNANCE COMMAND CENTER".
2. H2 "The whole governed platform, at a glance" + one lede sentence.
3. **CTA banner** (`.cta-run`): a full-width elevated card (theme-aware surface,
   `shadow-md`, strong border), not a colored banner. Left: bold title "Start a
   governed run" + a one-line context caption (dataset · purpose · resolved tier
   · control count). Right: a large primary button "Launch walkthrough →".
4. **Tile grid** (`.tilegrid`), 2×2, one tile per platform surface (Datasets,
   Registry, Platform, Adoption). Each tile (`.tile`): header row (icon + surface
   name + a right-aligned "Open →" link-button) over a divider, then a body with
   a big stat number + unit caption, then a row of small status/breakdown chips
   or a mini bar chart. Clicking "Open →" (or the matching sidebar item) routes
   to that surface across the full content area — the sidebar stays visible,
   nothing is a modal.

Live tile numbers (verified against the repo, not invented): Datasets "8" under
classification with a class breakdown row (Restricted 2 / Confidential 2 /
Internal 3 / Public 1); Registry "3" analyses in the certification lifecycle
with certified/candidate/refused chips; Platform "5" agent templates · 3 live,
with "4/4 agents covered" and "2 available" chips; Adoption "19" runs · "2 of 3
models promoted" (the promotion rate is scoped to the credit pipeline, the only
run kind that promotes a model), with a 4-bar mini weekly chart (W26/W27/W28/W29).

The Adoption numbers changed with the H phase (2026-07-19): the fabricated
hardcoded weekly series (29 runs across W26-W28) was replaced by the 19
actually-executed seed runs in sentinel/data/seed_runs.jsonl, so the tile now
reads 19 runs over four weeks. The mockup's WEEKLY constant (29) predates this
and is illustrative; the app renders the seeded truth.

### 3.3 The nine-stage run + Architecture (`#view-run`)

Structure per stage, inside `.stage-wrap` (max-width 1060px): an identity banner
slot (only visible for non-L2 personas), the **engine bar** (`.enginebar` — see
3.5), then a `.phead` (eyebrow "Stage N of 9" + a neutral badge + h2 stage name +
one-sentence lede), then an `.iodid` 3-column In/Does/Out card row, then the
stage's specific body (tables, code blocks, control chips, narration, etc., all
built from the shared component set in Section 4), inside `.card` containers.

Ask (stage 1) additionally has a 3-item `.substeps` row (Import dataset / Select
purpose / Pick question) with its own `.subpane` panels underneath — see 4.3.

The 10th stop (Architecture) reuses the same `.phead`/`.card` shell but the
engine bar is hidden (the panel *is* the full engine) and its content is the two-
column bought/built stack described in Section 4.6.

### 3.4 The four platform surfaces (`#view-surface`, reused container)

Each surface renders into the same `.surfwrap` (max-width 1040px): a `.surfhead`
(eyebrow + h2 title) then surface-specific body — tables (`.tbl-wrap` + classic
`<table>`), `.metric` tiles, `.card` groups, and `.rowflex` layouts of
side-by-side cards. Datasets: one table (id/name/class/rows/tables/license/
commercial/onboarded) with a `.cls` chip per row and a class-count breakdown row
above it. Registry: certification-lifecycle cards (one `.card` per analysis,
with a gates checklist and control chips) + a models table + an agents table.
Platform: 4 metric tiles + template cards + a playbooks table + a pattern-badge
row. Adoption: 4 metric tiles + two `.barchart` cards side by side.

---

## 4. Shared components (used across stages and surfaces)

### 4.1 Card (`.card` / `.card-h` / `.card-b`)

The base content container everywhere: white/dark surface, 1px border, 16px
radius, `shadow-sm`. Optional header row (`.card-h`) with a title + a
right-aligned eyebrow tag, separated by a hairline; body padding 16/18px.
Stacked cards get 16px top margin automatically (`.card + .card`).

### 4.2 Badges, tags, classification chips

- `.badge` — pill, 11px/700, five semantic variants (`ok`/`warn`/`danger`/
  `info`/`neutral`), each with a soft background + matching border + ink color.
  Used for status words: certified/candidate/refused, promoted/blocked, live/
  available, in-use/planned/avoided.
- `.cls` — smaller, sharper-cornered (5px radius), uppercase, 800-weight
  classification chip: `public`/`internal`/`confidential`/`restricted`, same
  four-part soft/border/ink pattern as badges but visually distinct (not pill-
  shaped) so classification reads as a different axis from status.
- `.tag` (rail-only) — see 2.3.

### 4.3 Control chip (`.ctl`)

The recurring "a control fired here, click to explain" affordance: mono, 11.5px,
700, a small leading status dot, pill-ish 8px radius. Four states matching the
semantic palette: `.pass` (ok), `.fired` (warn), `.block` (danger), `.armed`
(neutral/inert, control exists but hasn't been evaluated in this context). Every
control chip is a button that opens the control drawer (4.7) explaining what it
is, why it fired, what it did.

### 4.4 Tables (`.tbl-wrap` + `<table>`)

Bordered, radius-clipped wrapper with internal horizontal scroll. Uppercase
11px muted column headers on a `--surface-2` band. Numeric columns get `.num`
(right-aligned, mono, tabular-nums). Special row/cell states: `.suppressed`
(struck-through, danger-tinted background — used for a disclosure-suppressed
row, never actually deleted from the DOM, shown struck not hidden per the
project's "suppressed, not deleted" principle), `.col-denied` (struck-through
column header/cell for an access-denied column), `.row-sel` (accent-tinted
selected row), `.rowgood`/`.rowbad` (a left accent bar or full-row danger tint
for e.g. the selected dataset or a failed model).

### 4.5 In/Does/Out card row (`.iodid`)

A fixed 3-column grid appearing at the top of every stage: three `.iocard`s
labeled In / Does / Out. The middle "Does" card is visually distinct
(`.iocard.does`, accent-soft background) to draw the eye to the stage's action.

### 4.6 Engine bar (`.enginebar`) — "Framework & Tools used" / "Governance implemented"

A single-row strip atop every stage (hidden on the Architecture stop), split by
a vertical divider into two labeled halves:
`FRAMEWORK & TOOLS USED  [lib chip] [lib chip] │ GOVERNANCE IMPLEMENTED  [ctl chip] [ctl chip]`.
Library chips (`.lib`): mono, small teal status dot, dashed-border italic
variant (`.lib.none`) when a stage is "policy only, no external library" (Ask,
Plan). Clicking any library chip jumps to the Architecture stop. Renamed
2026-07-18 from "Buy the maths" / "Build the governance" to the current plainer
labels; the underlying two-column bought/built framing on the Architecture stop
itself uses the same renamed language.

### 4.7 Control drawer (`.drawer`, right-side slide-over)

A 440px right-edge panel (`translateX` slide, 260ms), scrim behind it. Header:
mono control id + title + an action-type pill. Body: three labeled blocks — "What
it is", "Why it fired on this run", "What it did" — each a short paragraph. This
is the single mechanism for explaining every control in the system; every `.ctl`
chip anywhere in the app opens the same drawer keyed by control id.

### 4.8 Controls modal (`.modal`, center-screen, "Control plane")

A centered card (680px) listing every control on the run, grouped by stage,
admin-only toggle switches (`.toggle`, a pill switch) for two controls
(CTL-DISC-02, CTL-PROXY-01) with a segmented "Analyst / Platform Admin"
viewing-as switch above the list.

### 4.9 Code block (`.code`, Generate stage)

A bordered, radius-clipped, scrollable block styled as a small code editor: mono
line numbers (muted, non-selectable) beside syntax-colored code (comments,
keywords, strings, function names each their own token color per 1.4), with a
`.viol` row highlight (tinted background + colored line number) marking the
line a control will catch (e.g. an unsanctioned network call).

### 4.10 Metrics + bar charts (`.metric`, `.barchart`)

Metric tile: bordered card, a big tabular-nums number (26px/700), an uppercase
muted label, an optional small detail line. Bar chart: flexbox columns of
height-proportional gradient bars (accent gradient, or an ok-gradient variant
for "agent utilization"), value printed above each bar, a mono caption below.

### 4.11 Buttons (`.btn`)

Two variants: default (bordered, surface background, hovers to accent border)
and `.primary` (filled accent, white/accent-ink text, darkens on hover). A `.lg`
modifier for the dashboard CTA (13px/22px padding, 15px text).

### 4.12 Notes (`.note`, four semantic variants)

A bordered, soft-tinted callout row with a small circular icon glyph, used for
inline governance commentary ("this control fired because…", "on the roadmap,
not yet wired…"). Variants mirror the semantic palette: `info` (accent),
`warn`, `ok`, `danger`.

---

## 5. Iconography

All icons are inline SVG, stroke-based (1.7–1.8px stroke width, round caps/
joins), no icon font, no external icon library. One consistent linework style
throughout: the shield brand mark (filled accent shield + white checkmark
stroke), and six persona/nav glyphs (person, person+check, magnifying glass,
stamp, eye, gear) plus five nav-section glyphs (home, play triangle, database
cylinder, checked square, 2×2 grid, bar chart). Decorative icons are
`aria-hidden="true"`.

---

## 6. Accessibility notes baked into the design

- One persistent `<h1>` (sr-only) at the shell/content level, not duplicated per
  view.
- `:focus-visible` gets a 2px accent outline globally; interactive controls that
  sit on the always-dark login use a lighter, more visible outline color
  (`#5b8def`) since the default accent doesn't have enough contrast against a
  dark card.
- The active sidebar item gets `aria-current="page"`.
- The four dashboard tile "Open" buttons each carry a distinguishing
  `aria-label` ("Open Datasets", "Open Registry", …) since their visible text is
  identical ("Open →").
- The login is a real `role="dialog" aria-modal="true" aria-labelledby="login-h"`.
- Reduced motion turns off: the stage-transition overlay entirely (jumps
  straight to the stage), the panel rise-in animation, the shimmer loading
  state, the login-persona-card hover lift, and smooth scrolling.

---

## 7. What is NOT yet designed / open

- **Mobile / narrow-viewport layout**: explicitly out of scope (removed by
  decision). If ever revisited, it is new design work, not a restoration.
- **B-style contextual drawers** (opening a platform surface as a slide-over
  from the exact run-stage that consumes it, e.g. Datasets from Access) were
  explored in `docs/mockups/sentinel-platform-surfaces.html` Option B but are
  NOT part of the built design. Only the command-center (Option C) + persistent
  sidebar (Option A) combination is specified above.
- **RBAC-gated sidebar** (hiding nav items a given persona shouldn't see) is
  explicitly deferred; all sidebar items show for every persona today.
- Modal focus-trap, login focus-on-load, and promoting surface `.eyebrow`
  section labels to real headings are known small a11y polish items, not yet
  done (see the review findings folded into commit `82ceac5`/`98aba34` for what
  *was* fixed).
