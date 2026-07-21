# Build instructions: the Sentinel portfolio page

Read this before creating, rebuilding, or editing the public Sentinel case study
at **https://sandip.dev/portfolio/Sentinel/**.

Named `CLAUDE.md` rather than `README.md` so Claude Code loads it automatically
when work touches this folder. `README.md` next to it describes what the folder
holds; this file describes how to build the page from it.

## The two repos

The page spans two repos and neither one alone is the whole picture.

| Repo | Path | Role |
| --- | --- | --- |
| `~/Developer/sentinel` | `docs/portfolio/` | Source of truth. Copy, diagram, video outline. Lives on `main` only, never on a feature branch. |
| `~/Developer/sandip.dev` | `portfolio/Sentinel/` | The rendered page. Static HTML, served from `main` by GitHub Pages, live on push. |

Edit the copy here first, then mirror it into the HTML. Do not let the two drift.
If you only have time to do one, do the source, and say so.

## What already exists

```
sentinel/docs/portfolio/
  CLAUDE.md                  this file
  README.md                  what the folder is, where each number came from
  page-copy.md               the full page text, six numbered sections
  architecture-diagram.svg   the system diagram, 1200x872
  video-outline.md           shot list for the walkthrough that fills the video slot

sandip.dev/portfolio/Sentinel/
  index.html                 the page, diagram inlined at the figure
  sentinel.css               ludllm.css plus a Sentinel block from line ~940
  sentinel.js                verbatim copy of ludllm.js
  assets/sentinel-architecture.svg   standalone copy for the "open full size" link
```

If any of these are missing, rebuild them in that order. `page-copy.md` before
`index.html`, always.

## Building the page from scratch

1. **Start from LudLLM, not from a blank file.** `portfolio/LudLLM/index.html` is
   the pattern. Copy its header, footer, palette switcher, and `.page` /
   `.lud-hero` / `.article` / `.prose` skeleton verbatim. The two case studies
   must read as one system. Copy `ludllm.css` to `sentinel.css` and append the
   Sentinel-specific block at the end rather than editing the shared rules.
   Copy `ludllm.js` to `sentinel.js` unchanged.
2. **Render `page-copy.md` into the prose column.** Section order on the page:
   lede and what it is, stat strip, walkthrough, architecture, build versus buy,
   the numbers, what it is not, closing CTA panel.
3. **Inline the diagram.** Paste the contents of `architecture-diagram.svg`
   inside `<figure class="sn-figure sn-bleed"><div class="sn-frame">`. Inline,
   not `<img>` or `<object>`, so it inherits the palette variables and re-themes
   with the switcher. Copy the same file to `assets/` for the full-size link.
4. **Reserve the video slot.** See below.
5. **Add the row to the portfolio list** in `sandip.dev/index.html`: date,
   `Sentinel`, links to the case study, the live app, and the repo, tagged
   `ai · governance`.
6. **Verify in the browser before committing.** See the verification section.

## Design system

Do not invent classes that already exist. From `ludllm.css`:

`.page`, `.crumb`, `.lud-hero`, `.article` (grid `200px minmax(0,1fr)`, gap 64),
`.article-rail`, `.prose` (max-width 680), `.table-wrap` with `table.lud`,
`.cta-panel`, `.card-link`, `.download-btn`, `.cta-link`, `.tlink`, `.mono`,
`.label`, `.lede`, `figure.lud`, `.palette-switcher`.

Sentinel-specific additions, all prefixed `sn-`:

| Class | What it does |
| --- | --- |
| `.sn-wide` | Widens a table out of the 680px prose column into the rail. |
| `figure.sn-figure.sn-bleed` | Full-bleed diagram figure. |
| `.sn-frame` | Bordered, padded, horizontally scrollable box around the SVG. |
| `.sn-video` | 16:9 dashed placeholder that becomes the YouTube embed. |
| `.sn-stats` | Four-up number strip, two-up under 880px. |
| `.sn-thesis` | Pull quote above the build versus buy table. |
| `.sn-pill` `.buy` `.build` | The verdict chip in the build versus buy table. |
| `.sn-limits` | The honest-limits box under "what it is not". |
| `.sn-bg` | Opaque background rect inside the SVG. Never remove it. |

Colours come from CSS custom properties only: `--paper`, `--paper-2`, `--ink`,
`--ink-soft`, `--ink-softer`, `--rule`, `--accent`, `--accent-soft`. No hex
literals in page CSS. Inside the SVG, use `var(--x, #fallback)` so the standalone
file still renders when opened on its own.

### The full-bleed maths, which is easy to get wrong

`left: 50%; transform: translateX(-50%)` does not work here. It resolves against
the grid area, not the 680px prose box, and pushes the page into horizontal
overflow. The prose column's left edge is `50vw - 244px`, so:

```css
figure.sn-figure.sn-bleed { width: calc(100vw - 80px); margin-left: calc(284px - 50vw); }
@media (max-width: 1080px) { figure.sn-figure.sn-bleed { margin-left: -256px; } }
@media (max-width: 880px)  { figure.sn-figure.sn-bleed { width: 100%; margin-left: 0; } }
```

Under 880px the SVG gets a fixed `width: 900px; min-width: 900px` inside the
scrollable `.sn-frame` so it stays legible and pans instead of shrinking to
unreadable. Do not "fix" mobile by letting the SVG scale to the viewport.

Check `document.documentElement.scrollWidth` against the viewport width after any
change to this figure. They must match.

## The video slot

The slot is reserved and empty on purpose until the walkthrough is recorded. The
markup already holds a commented-out iframe next to the placeholder. To publish:
delete the three placeholder `<span>` elements, uncomment the iframe, drop the
YouTube id into the `src`. Nothing else on the page changes.

Keep `youtube-nocookie.com`, `loading="lazy"`, and
`referrerpolicy="strict-origin-when-cross-origin"`.

`video-outline.md` holds the shot list. Its rule: every beat shows a control
refusing, because a run where everything goes green is indistinguishable from a
pipeline with a log bolted on.

## Facts, and where they come from

Never write a number from memory. Every figure on the page traces to this repo.
`README.md` records the current sourcing. The traps:

- The README at the sentinel repo root says **36 tests**. It is stale. The real
  number comes from `uv run pytest --collect-only -q | tail -1` and was 676.
- **26 controls, 23 enforced, 3 declared**, from
  `sentinel/govflow/controls_info.py`. Declared controls render dashed in the app
  and must never be described as live.
- Model metrics move with seed. The page says "about 0.5 to 0.57" for the
  disparity ratio rather than pinning one run. Keep it that way.
- The four-agent LangGraph route has **no UI screen**. Say so. Do not let the
  page imply a visitor can run it.

If a claim is not in the repo, do not put it on the page. This includes
comparisons and rationales: the build versus buy section covers only decisions
the repo actually records. Two rows are "not yet" rather than decided, and that
is the honest state, not a gap to fill in with a plausible story.

## Voice

First person where the page speaks, declarative, short sentences. No em-dashes.
No emojis anywhere, including headings. No "production-ready", "robust",
"comprehensive", "seamlessly", "leverage". Name limits plainly. The whole
argument of the page is that the controls are real, and overselling is the fastest
way to lose it.

## Verification before committing

Serve the site locally and check it in the browser. Do not push unverified.

```bash
cd ~/Developer/sandip.dev && python3 -m http.server 8899
```

Then open `http://localhost:8899/portfolio/Sentinel/` via `preview_start` and:

1. Console clean, no 404s in the network log.
2. `document.documentElement.scrollWidth` equals the viewport width. No
   horizontal overflow.
3. Cycle all four palettes (fog, white, paper, ink). The diagram must re-theme
   with the page and stay legible in every one.
4. Resize to 375px. The diagram pans inside its frame, tables scroll, the stat
   strip goes two-up.
5. No image anywhere has a transparent background.

Screenshots of a page this tall can come back blank. That is a tooling artifact,
not a layout bug. Measure with `getBoundingClientRect()` instead of assuming the
page is broken.

## Updating an existing page

1. Edit `page-copy.md` here, and `architecture-diagram.svg` if the system changed.
2. Mirror into `portfolio/Sentinel/index.html`. A diagram change means replacing
   the entire `<svg>` block inside `.sn-figure` verbatim, and updating
   `assets/sentinel-architecture.svg` with the same file.
3. Verify, then commit both repos. `sandip.dev` deploys on push to `main`.
4. Poll the live URL until it serves the change. GitHub Pages takes a minute.
