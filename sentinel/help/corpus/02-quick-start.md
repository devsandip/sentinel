---
id: quick-start
title: Quick start
chapter: Quick start
summary: What to click, in what order, to see a governed run end to end, plus the refusal demo and how to run the app locally.
---

## In order, from a cold start

Pick an identity first. The topbar shows who you are acting as, and every screen recomputes against that identity, including the resolved autonomy tier. Start as the Data Scientist: that persona is the one certified to write code, and the Run walkthrough is built for it.

Open the Run screen. Run is the nine-stage governed walkthrough and the centre of the product. Stage one asks you to confirm a dataset, declare a purpose, and pick an analysis, in that order and as three explicit steps rather than one form.

Watch the tier resolve at Ask. Ask prints the arithmetic on screen: the ceiling the data's classification allows, the ceiling your persona and its attestations allow, and which of the two bound the result. Change persona and the printed arithmetic changes with it, which is the fastest way to see that the autonomy tier is computed rather than chosen.

Review the Plan. Plan binds a certified analysis and checks its data contract against the current dataset fingerprint before anything runs. Plan is also where you choose scripted generation or live generation, so it is where you decide whether a real model writes the code on this run.

Click Run governed analysis. All nine stages execute, and the rail marks each stage clear, refused or skipped as the run proceeds. A refused run records the remaining stages as skipped rather than pretending they ran.

Walk the stages after the run finishes. Access shows which columns were withheld and why. Gate shows each static check with a verdict on each and highlights the offending line when there is one. Execute shows the sandbox spelled out. Screen shows the result table before and after suppression, so you can see exactly what the disclosure control removed.

Read Attest last. Attest carries the finding, its provenance, the controls attested, and the negative statement saying what the finding does not say. From Attest you can download the Quarto source, which is the leadership-facing rendering, or the marimo notebook, which is the data-scientist-facing one.

Open the Audit Log when you are done. The run you just performed now sits in the cross-run ledger next to every earlier run, replayed as the same nine stages, and it survives the session.

## Drive two demos, not one

The default selection at Ask is benign, and a gate that clears a benign request is doing its job. Blocking a clean request would be a false positive, and this build treats a false positive as costing as much as a missed block, so the happy path is a result rather than an anticlimax.

The happy-path demo is a fair lending review: selection rate by age band. The static checks clear, the sandbox runs the code, the disclosure screen suppresses the small bands, and the narration is checked against what survived the screen. The run ends in an evidence pack that is pending a signature, because the author cannot sign it.

To see the gate refuse, pick one of the adversarial entries in the analysis dropdown at Ask. Each adversarial entry is real code with a real violation, and nothing about the refusal is seeded. Exfiltrating results to a webhook catches on CTL-EGRESS-01. Writing results to a file catches on CTL-CODE-02. Evaluating an untrusted metric spec catches on CTL-CODE-03. A SELECT star passed through ctx.sql catches on CTL-COL-01 in the SQL half of the gate.

After a refusal, click Fix it. The repaired code faces exactly the same gate as the original, and nothing about the earlier attempt is whitelisted. Watching a repair pass the same checks that just refused is the point of the button.

## Other things worth trying

Switch to the Junior Analyst and run the same request. The Junior Analyst holds no certification attestation, so the same request drops to the L1 autonomy tier. Generate and Gate are skipped at L1, and the reviewed surface becomes the typed parameters of a certified analysis instead of generated code.

Switch to the Internal Auditor. The Auditor is read-only everywhere, so the Run button disappears. If you reach the flow another way, CTL-TIER-01 refuses at Ask, because the tier gate lives in the flow rather than in the user interface.

Switch to the Platform Admin. The Controls popover in the topbar becomes editable for the Platform Admin only. Turn a control off and every surface marks the next run UNGOVERNED, and the act of disabling is itself written to the audit log before the run starts.

Open a data contract. Go to the Datasets screen and click Contract on any row. A contract is metadata only and says so on its own face: schema, column roles, relationships and coverage, with no cell values, no distributions and no sample rows.

Read a model card. Open Registry, then the card on any promoted row in Models. It is an SR 11-7 style model-risk document generated from that run, not written by hand, and it exports to PDF.

Watch four eyes refuse. Open Audit Log and pick a credit-risk run whose author signed it themselves. The refusal is CTL-SOD-01, and it compares identities rather than roles: an administrator who authored a run cannot approve it either. That is what author-is-not-approver means in practice.

## Running it locally

Sync the environment with uv, including the dev extra, then run the data preparation script to build the named CSV. From there you can run the test suite with pytest, run the machine learning core on its own from cli.py, run the governed pipeline in a terminal from demo.py, or start the app.

Start the app with the run.sh launcher rather than a bare streamlit run. The launcher sets the Arrow default memory pool to system, which is the one mitigation needed for a pyarrow allocator crash on macOS. Bypassing the launcher works until it does not, and the failure mode is a crash rather than a warning.
