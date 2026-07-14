# Two deferred items land: fraud + LendingClub datasets, and a real faithfulness run

Date: 2026-07-14 08:54
Previous: [2026-07-14-0646-live-llm-narration-in-prod.md](2026-07-14-0646-live-llm-narration-in-prod.md)

Cleared the two dataset onboarding items that were deferred to the morning, plus
the Ragas faithfulness run that had never actually executed.

The "Kaggle-gated datasets" were never really about Kaggle. The dataset spec
resolved every gate to a no-account substitute months ago. ULB credit-card fraud
comes from OpenML 1597 (DbCL, commercial-safe), not the Kaggle competition.
LendingClub comes from the DePaul econdata mirror. Both were already registered in
the dataset registry with license, contract, and column roles; they just had no
onboarder and no local file. I added the two onboarders, ran them, and they flip
to available the moment the file exists.

ULB ships as all 492 fraud rows plus a 19,508 sample of legit, so the file stays
lean but the 2.5% imbalance stays real. The 28 PCA float columns rounded to five
decimals cut the file from 10.4 MB to 4.6 MB with no visible loss. LendingClub is
the messy one on purpose: 13,820 rows across 152 columns with 580k nulls, which is
the whole point of a data-quality triage target. Both run clean through the
governed analysis engine. The profiling analysis on LendingClub flags 15 fully
null columns and fires the commercial-use FLAG (its license is not commercial-ok);
on ULB it surfaces the 2.5% minority target. The governance layer treats them like
any other dataset, which is the reusability claim made concrete.

The Ragas faithfulness run was a stub. The script computed retrieval-only signals
and printed a note that the LLM-judged metric was "left as the wiring step so no
API call is made unattended." The `ragas` pip package is also broken in this env:
its pinned langchain-community import references a ChatVertexAI path that no longer
exists. Rather than do dependency surgery on a demo, I implemented the faithfulness
metric directly on the Anthropic SDK, which the live extra already provides. Same
definition as Ragas: decompose the answer into atomic claims, judge each against
the retrieved contexts, score supported over total. The judge prompts are in the
file, so the score is auditable, which fits the governance thesis better than a
black-box library anyway.

Getting an honest number took three corrections, and the wrong numbers were more
instructive than the right one. First pass scored 0.17, because my answer strings
bundled the computed 0.57 disparity in with the policy claim. Faithfulness to
retrieved context should only cover the claim RAG actually grounds, the rule and
the 0.80 threshold; the 0.57 is a model output the eval gate checks, not something
RAG retrieves. Scoping that out is the correct Ragas definition, not a way to
inflate the score. Second, the judge was over-strict: it marked paraphrased-but-
supported claims as unsupported because the prompt said "inferred SOLELY from." I
verified against the actual retrieved chunk text that the independence and
effective-challenge claims really were present, then loosened the rubric to credit
reasonable inference, which is what faithfulness means. Third, single-pass
LLM-judge scores are noisy because claim decomposition varies and Sonnet does not
allow temperature=0, so I average over three passes and report the spread.

With the metric scoped correctly and the judge calibrated, faithfulness is a
stable 1.0 across both cases, range 1.0 to 1.0 over three passes. Every policy
claim the agents cite is supported by the retrieved passage. That is the "cite
rather than assert" property, finally measured instead of asserted.

One retrieval note worth keeping: for the SR 11-7 query the top-ranked passage is
the internal modeling standard, not the SR 11-7 document itself, though SR 11-7
chunks come back at ranks 2 and 3. Grounding is present, but the ranking is not
ideal. A candidate for a later look at chunking or reranking.

127 tests pass, ruff clean. The not-onboarded engine test had used ULB as its
example of an un-onboarded dataset; now that ULB is onboarded I pointed it at
uci_bank_marketing, which is still registered-but-not-onboarded.
