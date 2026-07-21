# Sentinel walkthrough — video outline

For the reserved slot on https://sandip.dev/portfolio/Sentinel/. Target 6 to 8
minutes. Screen recording of the live app at sentinel.sandip.dev, voice over, no
slides.

The rule for the whole thing: show a control refusing. A walkthrough where
everything goes green proves nothing, because a pipeline with a log next to it
looks identical.

## Beats

**0:00 — the claim, in one sentence.** Agentic AI in a bank is not a capability
problem, it is a controls problem. Here is a run where the controls are real.

**0:30 — Ask.** Pick a persona, a dataset, a purpose, a prebuilt request. Say why
there is no prompt box: this is a public link, and a governed surface does not
take free text from strangers. Then pick a request whose purpose does not match
the dataset and let the purpose matrix refuse it, before any tokens are spent.

**1:30 — Access.** Open the granted-columns panel. Show the denied column. Make
the point that it is not filtered at read time, it is never on the object the
generated code receives. Show the dataset SHA pin.

**2:15 — Generate.** The model writes the analysis. Show the gateway ledger and
the mode label, and say plainly that scripted is the default and why.

**2:45 — Gate.** The centrepiece. Open the generated code, then the nine checks
and their verdicts. Point at a check that returned "nothing to judge" and one
that returned "not armed" and explain why those are different facts from
"passed". Then trigger a refusal and show the regenerate loop.

**4:00 — Execute.** The subprocess, the caps, what is not reachable.

**4:30 — Screen.** Show the raw emitted table and the screened one side by side.
Small cells removed, not masked. Say that the model writing the interpretation
never sees the removed values. Show proxy discovery flagging and explain why it
flags rather than refuses.

**5:30 — Interpret and Attest.** The narration built from screened numbers only.
Then try to sign your own run and get refused by segregation of duties. Switch
identity, sign, open the evidence pack and the model card PDF.

**7:00 — the audit log.** One run, every stage, every control, in order. Close on
the line that the run is explicable to someone who did not write it.

## Do not

- Do not claim compliance. Controls answer to principles.
- Do not imply the narration is live reasoning when the mode chip says scripted.
- Do not show the four-agent LangGraph route as if a visitor can run it.
- Do not skip the refusals. They are the video.

## After recording

Replace the placeholder card in `portfolio/Sentinel/index.html` with the
commented-out `<iframe>` sitting next to it and paste the video id into the
`src`. Nothing else on the page changes.
