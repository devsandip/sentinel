# v1 is done. The slice runs, and the gate blocks for real.

Date: 2026-07-17 22:30
Previous: [2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md](2026-07-17-2203-v0-shipped-v1-core-fairlearn-reversed.md)

Half an hour after the core, the whole v1 slice is built and verified in the
browser. The thesis is no longer a document. It runs.

The remaining half was integration. The Generate stage calls the model to write
the analysis, and the generate-then-gate loop feeds a refusal back and retries.
The gateway learned a second job: it generated narration before, now it generates
code too, routed to the capable model, same cost cap and ledger. I ran it live
once to be sure the path works, not just the scripted fallback. Sonnet wrote clean
fairlearn code that referenced only granted columns and passed the gate, 819
tokens, under half a cent. The live path is real.

Then the flow: Ask to Access to Generate to Gate to Execute to Screen to Interpret,
each stage with a control that can stop it and an audit line. Two constructions in
the Access stage are worth defending, because both look like staging and neither
is. The age band is finer than the hero pipeline's, so 71-75 is genuinely six
applicants in the real data, small enough to suppress. And a synthetic proxy column
is granted, because the real german_credit features proxy age at most 0.35 and the
fair lending claim needs a proxy to catch. Both are disclosed, and both follow the
pattern already in the codebase, where synthetic PII columns exist only to make the
redaction control fire. The control does real arithmetic on honest data. The data
is labelled synthetic. That is the line, and it holds.

The two screens went in as a new section of the app. I did not trust the tests
alone for the UI, so I drove it in a browser. The benign request completes: the
71-75 band is gone from the screened table, a warning says it was suppressed at n=6
before narration, the synthetic proxy is flagged at a correlation ratio of 0.92,
and the narration talks about the surviving bands and names the suppressed one only
as removed. The adversarial request blocks: the Gate tab shows the generated code
with line 10, the webhook, and the refusal reads CTL-EGRESS-01, network egress not
permitted. The code never ran. Both halves of the done-when, on screen, not in a
test log.

Last, the numbers the artifact claims, as tests. A seeded set of fourteen
adversarial samples, every one blocked on the control it should be. Eight benign
analyses, none falsely blocked. Suppression exact across a swept range of cell
sizes. The gate's true-block rate is 100 percent and its false-block rate is zero,
which is the whole falsifiable claim.

v0 and v1 are one PR, nine commits, 183 tests green, ruff clean. Prod is still
untouched: none of this has shipped, by design, until it is reviewed. What is
deliberately still out: ctx.sql and its sqlglot gate, the registry and
certification lifecycle, the evidence pack with OpenLineage and Quarto, and the
breadth across the other datasets. Those are v2 through v4. v1 was one sentence,
and it stayed one sentence.
