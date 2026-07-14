# Sentinel offline eval suites (ideas.md item 8)

Two offline eval suites complement the in-run eval gate (which is the release
control). These run pre-release, with recognized OSS tools.

- **promptfoo** — asserts on the agent narration produced by the model gateway.
  Uses the gateway as a custom provider, so it exercises the real code path.
- **Ragas** — scores the RAG citations for groundedness / context relevance, so
  the "agents cite rather than assert" claim is measured, not asserted.

The in-run eval gate stays the promotion gate (`sentinel/harness/eval_gate.py`);
these are the quality bench that runs before shipping a change.

## promptfoo (narration quality)

Needs Node. From the repo root:

```bash
npx promptfoo@latest eval -c evals/promptfoo.yaml
npx promptfoo@latest view          # open the results UI
```

`promptfoo.yaml` drives `evals/narration_provider.py`, which calls
`ModelGateway.narrate` in scripted mode (zero cost). Assertions check that each
step's narration is non-empty, mentions the expected facts, and never contains
raw PII.

## Ragas (RAG groundedness)

Needs Python and an LLM judge (an `ANTHROPIC_API_KEY`) for the faithfulness
metric:

```bash
uv run --extra live python evals/ragas_eval.py
```

Two layers. Layer 1 (retrieval signals) always runs, no key: for each governing
question it checks whether a relevant, correctly-attributed passage was
retrieved. Layer 2 (faithfulness) needs the key: it decomposes the policy claim
each agent grounds into atomic claims and judges each against the retrieved
contexts, scoring supported/total (the Ragas faithfulness definition). It
averages over 3 passes and reports the spread, since an LLM-judge score is noisy
per draw. Faithfulness is scoped to the policy claim RAG grounds (the rule and
threshold), not the run-specific numbers the model computes; those are the eval
gate's job, not RAG's.

Implemented directly on the Anthropic SDK rather than the `ragas` pip package,
whose pinned `langchain-community` import is broken in this env. The metric is
the same and the judge prompts are in `ragas_eval.py`, so the score is
auditable. Without a key, layer 2 is skipped with a clear note. It never
fabricates a score.

## Note

promptfoo and Ragas are not wired into `pytest` (they need Node and an API key
respectively). They are runnable artifacts, kept honest: the OpenTelemetry
tracing in `sentinel/harness/tracing.py` is the always-on observability layer and
is covered by the test suite.
