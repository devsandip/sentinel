# Three registries under one heading

2026-07-20 13:45. Previous: [2026-07-20-1338-the-catalogue-is-not-a-data-browser.md](2026-07-20-1338-the-catalogue-is-not-a-data-browser.md)

Sandip asked two things about the Registry screen. The agents are just listed, so what does each one actually do. And what is the difference between Models, Agents, and Analysis-agents.

The second question is the finding. He commissioned this build, he has read every entry in this journal, and he could not tell three registries apart on a page he owns. A hiring manager gets one pass and no context. The page had one subtitle covering all three sections, and the subtitle described two of them.

The three are not variations of one idea. A model is what a run produces. An agent is a worker inside a run. An analysis-agent is what a run is allowed to be. That last one is the least obvious and the most important: it is the certified unit the Plan stage binds, and the four agents execute whichever analysis-agent Plan picked. Written that way the page holds together. The section for analysis-agents now opens by saying it is not the four agents above, because that is the collision that caused the question.

For what each agent does, the description lives on the agent class as a `does` attribute and the registry reads it off the class. The alternative was a dict of descriptions in `registry.py`, which is a second copy of something the code already knows, and a copy of a fact drifts from the fact. This is the same rule the model rows already follow: the popover under a model's status is computed from that row's numbers rather than written next to them. An inventory that describes the code has to be derived from the code or it is just a document about the code.

Two things I noticed and left alone. The eda agent's tools column reads `read_columns, profile_dataset` because it inherits the `data_analysis` template's allow-list, and eda never calls `profile_dataset`. That is honest as a scope and misleading as a description; the fix is either a per-agent scope or a column renamed to say it is the template's. And `AGENT_LINEAGE` duplicates the `template` attribute every agent class already carries, but deduping it means importing the agent classes into `templates.py`, which `agents/runtime.py` imports from, so it would close an import cycle. I imported the classes inside the registry function instead, which keeps the platform package importable without pulling in the ML stack.

Two traps on the way, both about verification rather than code.

The launch config runs Streamlit with `--server.fileWatcherType none`. With the watcher off, Streamlit never recompiles the script, so a browser reload starts a fresh session that re-runs the *old* compiled source. I changed a column width, reloaded, saw no change, changed it again, reloaded, saw no change, and was two edits deep into treating a layout constant as ineffective before I restarted the server and both edits appeared at once. A page that reloads without picking up your change looks exactly like a change that does nothing.

The layout itself: at laptop width Streamlit shrinks a column to its content's min-width, and because the header CSS allows word breaking, the min-width of "VERSION" is a fragment. The header rendered as "VERSI ON". Widening the column did not fix it, since the other columns' content had already claimed the space. The header is "ver" now.

The second trap: I ran the full suite while the Streamlit app was still running and got six failures across govflow, l1, evidence and lineage, in 651 seconds. Every one of them passed in isolation. I stopped the server and the same suite ran green in 116 seconds. A suite that takes five times its usual wall clock is not reporting on your diff, it is reporting on your machine. Read the runtime before reading the failures.

PR #18, merged as `a924ffe`. 391 passed, 2 skipped. Not deployed; prod is still v10, and every finding from this morning's cold-visit audit is still open.

A note on the traffic. Another session landed PR #19 and PR #20 while I was working, so main moved twice under me. That is the third day running this has happened. It cost nothing this time because the changes did not overlap, but the branch list is still not a reliable picture of what is in flight.
