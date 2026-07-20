# A list that granted what nothing installed

2026-07-20 13:10. Previous: [2026-07-20-1121-chrome-recedes-and-an-audit-finds-the-landmine.md](2026-07-20-1121-chrome-recedes-and-an-audit-finds-the-landmine.md)

Sandip asked what was remaining. The answer was the five findings from this morning's cold-visit audit, none of them touched. We closed all five in one session. Four were fixed and one was closed by a decision.

The first one was the only place prod was actually broken, and it was worse than the morning's note said. The L2 allowlist advertised `statsmodels.api`, `statsmodels.formula.api`, `lifelines`, `shap`, `dowhy` and `econml`. This morning I wrote that statsmodels was installed locally as a transitive dependency and only died on the instance. That was wrong. None of the six were installed anywhere, including in a local venv, which is better news than the alternative because it means the fault reproduces on a laptop.

The allowlist is interpolated verbatim into the codegen system prompt. Every name on it is an instruction to the model to use that package. So the model takes the instruction, the gate reads the imports and stamps "imports on the tier's allowlist, clear", and the sandbox dies with `ModuleNotFoundError`. I reproduced it at the seam before touching anything:

```
GATE passed: True | controls fired: []
EXEC ok: False | error: ModuleNotFoundError: No module named 'statsmodels'
```

The crash is the small half. The governance half is that a control approved something the environment refuses. That is not a control that held. It is a control that guessed.

I fixed it the wrong way first. I dropped the four packages nothing in the build uses, on the reasoning that a grant should describe the environment rather than an aspiration for it. Sandip reversed it: install them, and find a dataset that uses them later. He was right that the defect was never which side moved, only that the two sides disagreed.

Installing them cost more than I expected, and both costs are worth keeping. The resolver pinned the numerical stack down a major version, because econml and numba cap the ceilings: pandas 3.0.3 to 2.3.3, scikit-learn 1.9 to 1.6.1, numpy 2.5.1 to 2.4.6, scipy 1.18 to 1.15.3. The suite passes on the older stack so I took it rather than fought it, but an allowlist entry is not only a package, it is that package's constraints on everything else.

The second cost was time. The sandbox is a fresh subprocess per run, so importing what the allowlist grants is charged to every analysis before a line of it executes. Warm, that is 0.66s of bare subprocess overhead, 1.0s with pandas, and 4.2 to 4.6s with shap. Cold it is far worse: 15.5s after a clean install, and 48s in the worst case I saw. Both ends broke the 10s wall clock in different ways, so there are two fixes. A warm-up at boot runs one throwaway subprocess importing everything the allowlist grants, which works because the caches involved are on disk rather than in the process, and which uses a child rather than the app process so numba's memory is released instead of held for the life of a 2GB instance. And the wall clock went from 10s to 30s, on the reasoning that an infinite loop dies at 30s exactly as it dies at 10s, so nothing about the control's real purpose is weakened, while it stops firing on the imports rather than on the analysis.

That is the general form worth keeping: **an import grant is also a time budget.**

I also got the mechanism wrong in public before checking it. I told Sandip the 48s was numba compiling bytecode. Purging `__pycache__` only took it to 6.4s, so that explanation was mostly wrong; the real cost is reading a few hundred MB off cold disk. I re-measured with a clean reinstall and corrected the code comments and the docs rather than leaving a plausible-sounding wrong reason in them. Second time this week that a theory which explained the symptom was wrong and the measurement was cheaper than the second guess.

The second finding was the adoption bars, four identical rectangles for four different weeks. The inline heights were correct the whole time, 30, 30, 46 and 38. The layout threw them away. The value label was a flex sibling above the bar, so each column spent 16.8px on the value and 16px on the caption and 6px on gaps, out of the 56px a fixed 70px chart height left it, and the bar was the only child with no intrinsic height, so it absorbed the entire 23px deficit. Every column carries identical text, so every column left an identical remainder, and the remainder was the bar.

The part I did not expect: ui-spec 4.10 already specified the fix. It says the value is printed above each bar and that the bars are gradient. The implementation had drifted from both, and printing the value as an out-of-flow label over the bar is exactly what stops it eating the column. My first attempt grew the chart to 99px to make room for the theft, which worked and was the wrong shape. Following the spec fixes the cause. The rule generalises: **an element whose size encodes data must be out of the flex-shrink pool, and anything decorating it must be out of flow.**

Third was one line of copy telling an L0 persona to switch persona in the sidebar. Identity moved to the topbar chip in v7, so for three versions the only instruction a stuck visitor got pointed at somewhere the control had left.

Fourth was the six seconds of blank white, and it was not an EB cold start: TTFB against prod measures 1.8s. Streamlit's front end is 61 files and 2.5MB, and CloudFront was serving all of it uncompressed and uncached. The main chunk alone is 908KB and gzips 3.4x. The distribution had a single behavior with `Compress: false` and the CachingDisabled policy, which is correct for the app, because the WebSocket needs every viewer header passed through, and wrong for the bundle. `/static/*` gets its own behavior now. The non-obvious half: `Compress: true` alone would have done nothing, because CloudFront compresses what it caches and CachingDisabled also drops `Accept-Encoding` from the cache key. It needed both.

The fifth finding is the interesting one, because it dissolved under a question. I had it down as the biggest gap: on the default path the gate clears nine checks and never refuses, so the most compelling thing in the build is asserted rather than shown. Sandip asked what the question actually was. Should the gate not clear, or do we want it to stop so the feature can be demonstrated?

Neither, once I looked. The gate is right to clear: the benign request generates benign code, and blocking it would be a false positive, which this build treats as costing as much as a missed block. And the refusal is not missing at all. Three adversarial requests are wired into the L2 analysis dropdown and three more at L3, each real code with a real violation the gate genuinely catches. Nothing seeded. The whole finding reduces to one line: the default selection is the benign one, and a visitor clicking the obvious path never changes it.

So it was never a controls question. It was a demo-choreography question. Sandip's answer: he drives two demos, the happy path and then an adversarial one. Nothing to build. I had written the finding up as the largest hole in the product, and it was a note about which option is selected by default.

The thread through all five is one thing. This build states claims in prose that nothing holds it to. The allowlist named packages nothing installed. The Execute panel claimed a 15s wall clock while the code enforced 10, which I found only because I was changing that number. The stepper doc listed DoWhy, lifelines and SHAP as permitted directly beneath its own sentence saying to claim only libraries that actually run. Three instances of the same bug wearing different clothes, and the fix in each case was to make the claim read from the thing that enforces it: the allowlist reconciles against `requirements.txt` in a test, the caption interpolates the constant, the permitted column renders from `ALLOWED_IMPORTS`.

423 tests, 2 skipped, ruff clean. Four commits on PR #17. Nothing is deployed yet: the CloudFront change needs `enable-https.sh` and is unverifiable until it runs.
