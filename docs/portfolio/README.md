# docs/portfolio

Source of truth for the public Sentinel case-study page at
**https://sandip.dev/portfolio/Sentinel/**.

The page itself is static HTML and lives in the `sandip.dev` repo
(`portfolio/Sentinel/index.html`, plus `sentinel.css` and `sentinel.js` copied
from the LudLLM page so the two case studies share the design system). This
folder holds the writing and the diagram that the page renders, so the copy can
be edited and reviewed here rather than inside markup.

## Files

| File | What it is |
| --- | --- |
| `CLAUDE.md` | Build instructions. Read it before creating or rebuilding the page: repo layout, the design system, the full-bleed maths, the video slot, the facts that are easy to get wrong, and the verification pass. |
| `page-copy.md` | The full page copy: description, architecture, build vs buy, honest limits. The HTML is a rendering of this. |
| `architecture-diagram.svg` | The system diagram. Inlined into the page (not linked) so it inherits the site's palette variables and re-themes with the palette switcher. |
| `video-outline.md` | Shot list and script beats for the YouTube walkthrough that fills the reserved slot on the page. |

## Facts on the page

Every number on the page is sourced from this repo, not from memory. The ones
that move:

- **676 tests.** `uv run pytest --collect-only -q | tail -1`. The README's "36"
  is stale and predates the platform build-out.
- **26 controls, 23 enforced, 3 declared.** `sentinel/govflow/controls_info.py`.
  Declared controls render dashed in the app and are never claimed as live.
- **AUC 0.8018, disparity ratio 0.569.** `docs/sample_model_card.md`, seed 42.
  A later prod run recorded 0.496. The number moving with data and seed is the
  point, so the page says "about 0.5 to 0.57" rather than pinning one figure.
- **26,650 LOC** under `sentinel/`, 8,054 under `tests/`.

If you change a number in the app, change it here and on the live page in the
same pass.

## Updating the live page

1. Edit `page-copy.md` (and `architecture-diagram.svg` if the system changed).
2. Mirror the edit into `~/Developer/sandip.dev/portfolio/Sentinel/index.html`.
   The diagram is inlined, so a diagram change means replacing the `<svg>` block
   inside the `.sn-figure` element with the new file contents verbatim.
3. Commit both repos. `sandip.dev` is served from `main` on GitHub Pages, so the
   page is live on push.

## The video slot

The page reserves a 16:9 slot immediately under the intro, marked up as
`.sn-video` with a placeholder card. To fill it, replace the placeholder div
with the commented-out `<iframe>` already sitting next to it in the markup and
drop the YouTube video id into the `src`. Nothing else changes.
