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

Needs Python and an LLM judge (an API key) for the faithfulness metric:

```bash
uv run --extra evals python evals/ragas_eval.py
```

Without a key the script computes the retrieval-only signals it can (context
relevance over the local corpus) and skips the LLM-judged metrics, printing what
it skipped. It never fabricates a score.

## Note

promptfoo and Ragas are not wired into `pytest` (they need Node and an API key
respectively). They are runnable artifacts, kept honest: the OpenTelemetry
tracing in `sentinel/harness/tracing.py` is the always-on observability layer and
is covered by the test suite.
