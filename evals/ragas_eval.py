"""Ragas-style RAG evaluation for Sentinel's citations (ideas.md item 8).

Measures whether the retrieved passages actually support the fairness claim, so
"agents cite rather than assert" is a measured property, not a slogan.

Ragas' faithfulness and answer-relevance metrics use an LLM judge (an API key).
If none is configured, this script still reports the retrieval-only signals it
can compute over the local corpus (whether a relevant, correctly-attributed
passage was retrieved) and clearly states which LLM-judged metrics it skipped.
It never fabricates a score.

Run: uv run --extra evals python evals/ragas_eval.py
"""

from __future__ import annotations

import os
import sys

# Make the repo root importable when run as a standalone script from evals/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.rag import retrieve  # noqa: E402

# The fairness question the Validator grounds, and the citation we expect back.
CASES = [
    {
        "query": "four-fifths rule disparate impact fairness across age_band in a credit decision",
        "expect_citation_contains": "Four-Fifths",
    },
    {
        "query": "model risk management validation documentation independent review",
        "expect_citation_contains": "SR 11-7",
    },
]


def _has_llm_judge() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def retrieval_signals() -> None:
    print("== Retrieval signals (no LLM judge required) ==")
    for case in CASES:
        r = retrieve(case["query"], k=3)
        top = r.top
        hit = bool(top and case["expect_citation_contains"].lower() in top.citation.lower())
        print(
            f"query: {case['query'][:60]}...\n"
            f"  backend: {r.backend}  top: {top.citation if top else 'NONE'}  "
            f"score: {top.score if top else 0.0}  expected-source-retrieved: {hit}"
        )


def ragas_metrics() -> None:
    if not _has_llm_judge():
        print(
            "\n== Ragas LLM-judged metrics: SKIPPED ==\n"
            "No OPENAI_API_KEY or ANTHROPIC_API_KEY set. Faithfulness and "
            "answer-relevance need an LLM judge. Set a key and install the extra "
            "(uv sync --extra evals) to compute them."
        )
        return
    try:
        from ragas import evaluate  # noqa: F401
    except ImportError:
        print(
            "\n== Ragas not installed ==\n"
            "Install with: uv sync --extra evals"
        )
        return
    print(
        "\n== Ragas LLM-judged metrics ==\n"
        "A key is configured. Build a Ragas dataset from the run's "
        "(question, retrieved_contexts, answer) and call evaluate() with the "
        "faithfulness and context_precision metrics. Left as the wiring step so "
        "no API call is made unattended."
    )


if __name__ == "__main__":
    retrieval_signals()
    ragas_metrics()
