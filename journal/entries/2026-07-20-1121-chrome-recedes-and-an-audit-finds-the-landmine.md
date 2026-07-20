# The chrome recedes, and an audit finds the landmine

2026-07-20 11:21. Previous: [2026-07-20-1055-the-row-becomes-the-control-v9.md](2026-07-20-1055-the-row-becomes-the-control-v9.md)

Sandip opened with demo prep for the hiring manager. I asked what shape the deliverable should take and he dismissed the question, which was the right call, because what he actually wanted was to point at things that were wrong. Before that started I sent an agent to walk the live site cold, as a first-time visitor with no guidance. That turned out to be the most valuable thing in the session.

The first thing he pointed at: mousing over Run hides "Workspace". Same for the other groups.

The cause is worth writing down because I got it wrong twice before measuring. Streamlit puts `margin-bottom:-16px` on every `stMarkdownContainer`. That exists to cancel the 16px bottom margin a markdown `<p>` carries, so a paragraph does not leave a gap under itself. The sidebar group label is not a paragraph. It is a bare `div` with a 6px bottom margin. So the -16px does not cancel anything. It over-pulls by 10px, and drags the next nav row up over the label's text. The row then paints its hover and active background across the group name, which is why the label vanished exactly when a row was hovered or selected and not otherwise.

The label was never sitting 6px above the row. It was sitting 10px underneath it, and had been since the rail was built.

My first instinct was margin collapsing, and my first fix was to move the spacing to padding, since padding is included in an element's measured box and margin is not. That made it worse: the overflow went from 10px to 16px, because the container's height was pinned and padding did not change it. Only walking the whole parent chain and reading the computed styles found the negative margin four levels up. The lesson is the boring one. I had a theory that explained the symptom and it was wrong, and the measurement cost less than the second guess.

Then I checked whether the same thing bites elsewhere. Six other custom divs in the app sit in the same over-pulled state. None of them are occluded. I checked by probing what is actually painted at the bottom edge of each one, and in every case nothing is: the element pulled up over them has a transparent background. So this is one bug, not seven. A nav row is the only thing in the app that paints a background over the element above it. Worth keeping as the rule rather than as seven tickets.

Next he wanted the topbar context chips gone: Data, Purpose, and the identity chip. All three, every screen. I did it, and flagged the one consequence that mattered, which is that the identity chip was the only in-app way to switch persona. Without it a persona change means editing the URL or starting a fresh session, and switching persona is precisely how the autonomy ladder is demonstrated: the same request resolves to L2 for a certified analyst and L1 for a junior and L0 for second line. He put it back.

That is the right outcome and it is worth naming why. Data and Purpose restated globally what the Run flow already states where it is actionable, and since v9 the Ask stage's dataset row carries the classification and the permitted purposes on the row itself. They were duplication. The identity chip is not duplication. It is a control.

The merge was the awkward part. v9 landed from a concurrent session while I was working, and it had touched the same regions: it deleted `_CLS_MD` and `cls_label` and moved classification rendering into `sentinel/ui/tables.py`. GitHub reported the PR as conflicting across three commits. Rather than resolve markers in a file I had already restructured, I reset onto `origin/main` and re-applied the three changes cleanly, so what landed is a single fast-forward commit. Two things fell out of that. The helper cleanup had to follow main's shape rather than the one I branched from. And v9's test expecting the purpose caption from two surfaces, the topbar chip and the new Ask table, now expects one, so it became a test of the Ask table rather than of a chip that no longer exists.

Merged and deployed. Bundle `sentinel-20260720-111254.zip`, EB Green, live-LLM on, verified on the live site by loading it and clicking through rather than by probing health.

Now the audit, which is the part that matters.

The Live LLM path fails every time in prod and prints a Python traceback on screen. `sentinel/codegen/allowlist.py` advertises `statsmodels.api`, `statsmodels.formula.api`, `lifelines`, `shap`, `dowhy`, and `econml` as allowed at L2. None of them are in `requirements.txt`. `statsmodels` happens to be installed in my local environment as a transitive dependency, so generated code using it passes here and dies on the instance. The Gate stamps "imports on the tier's allowlist, clear" and then Execute throws `ModuleNotFoundError: No module named 'statsmodels'`.

The crash is the small half of that. The governance half is that the gate passed code the sandbox could not run. The allowlist is a promise about the environment, and nothing checks that the environment keeps it. A control that approves something the machine then refuses is not a control that held, it is a control that guessed.

This is the third instance of one pattern. On 2026-07-18 prod crashed because `requirements.txt` had drifted from `uv.lock`. The fix then was to regenerate it, and there is a guard in `deploy.sh` now. This is the same shape one level up: the allowlist is a third dependency list, and nothing reconciles it with the second. The guard that exists would not catch it, because `requirements.txt` and `uv.lock` agree perfectly. They are just both missing what the allowlist promises.

The audit found other things. The Adoption bar chart on the landing tile renders four identical flat rectangles: the column needs about 78px for the value, the bar and the caption, the chart gives it 56px, and the bar has default `flex-shrink`, so every bar squashes to the same 17px regardless of its value. An L0 persona is told to "switch persona in the sidebar", which has been wrong since v7 moved identity to the topbar. Six seconds of blank white on a cold load, which is Streamlit's bundle and not an EB cold start, since TTFB is under a second.

The sharpest observation is not a bug. On the default path the gate never refuses anything. Nine checks, all clear, every time. The single most compelling thing in this build is a static gate reading generated code and refusing it by name, and a visitor following the obvious path never sees it happen. The claim is asserted rather than shown. That is a product gap, and it is worth more than the rest of the polish combined.

None of the audit findings are fixed. That is the next session's work, and the allowlist one should go first, because the Live LLM toggle sits in plain sight on the Plan screen and a curious hiring manager will click it.

One loose end from this morning tied itself off. The v9 entry recorded an open question about concurrent sessions, and named `claude/demo-prep-hiring-manager-5c0866` as a real fix from another session that Sandip chose not to ship. That branch is this one. It shipped four hours later, after he looked at it. The question stands, but the specific instance resolved the ordinary way: the human looked and decided.
