"""Ragas-style RAG evaluation for Sentinel's citations (ideas.md item 8).

Measures whether the retrieved passages actually support the fairness claim, so
"agents cite rather than assert" is a measured property, not a slogan.

Two layers:
  1. Retrieval signals (no LLM) - was a relevant, correctly-attributed passage
     retrieved for each governing question. Always runs.
  2. Faithfulness (LLM judge) - decompose the answer the Validator grounds into
     atomic claims, then check each claim against the retrieved contexts. This is
     the Ragas faithfulness definition (supported_claims / total_claims). It needs
     an LLM judge (an API key). Implemented directly on the Anthropic SDK rather
     than the `ragas` package, whose pinned langchain-community import is broken in
     this env; the metric is the same and the judge is auditable (prompts below).

It never fabricates a score. No key -> layer 2 is skipped with a clear note.

Run: uv run --extra live python evals/ragas_eval.py
"""

from __future__ import annotations

import json
import os
import sys

# Make the repo root importable when run as a standalone script from evals/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.rag import retrieve  # noqa: E402

# The judge model. Sonnet (capable tier) for reliable claim verification; the
# whole run is a handful of small calls, so cost is negligible.
JUDGE_MODEL = "claude-sonnet-5"

# Each case is a (question, answer) the system actually grounds. Faithfulness
# measures whether the retrieved policy passages support the POLICY claim the
# agent cites - the rule/threshold it grounds, not the run-specific numbers the
# model computes (e.g. the 0.57 disparity). Those computed facts come from the
# model step and are checked by the eval gate, not RAG; scoping them out of the
# faithfulness answer is the correct Ragas definition, not a way to inflate it.
CASES = [
    {
        "query": "four-fifths rule disparate impact fairness across age_band in a credit decision",
        "expect_citation_contains": "Four-Fifths",
        "answer": (
            "Under the four-fifths rule, a selection rate for a protected group that "
            "is less than 80 percent of the highest group's rate is generally "
            "regarded as evidence of adverse impact. Applied to a credit model, a "
            "disparity ratio below 0.80 is a signal that warrants review."
        ),
    },
    {
        "query": "model risk management validation documentation independent review",
        "expect_citation_contains": "SR 11-7",
        "answer": (
            "SR 11-7 expects effective validation performed independently of model "
            "development, an effective challenge. Effective validation covers "
            "conceptual soundness, ongoing monitoring, and outcomes analysis."
        ),
    },
]


def _has_llm_judge() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def retrieval_signals() -> list[dict]:
    print("== Retrieval signals (no LLM judge required) ==")
    rows = []
    for case in CASES:
        r = retrieve(case["query"], k=3)
        top = r.top
        hit = bool(top and case["expect_citation_contains"].lower() in top.citation.lower())
        print(
            f"query: {case['query'][:60]}...\n"
            f"  backend: {r.backend}  top: {top.citation if top else 'NONE'}  "
            f"score: {round(top.score, 4) if top else 0.0}  expected-source-retrieved: {hit}"
        )
        rows.append({"query": case["query"], "top": top.citation if top else None, "hit": hit})
    return rows


def _judge(client, prompt: str, max_tokens: int = 1024) -> str:  # noqa: ANN001
    """One judge call."""
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _parse_json(text: str):  # noqa: ANN001, ANN202
    """Extract the first complete JSON array/object from a judge reply.

    Tolerates code fences and trailing prose by scanning for the matching close
    bracket (ignoring brackets inside strings) rather than parsing to end-of-text.
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    start = min((i for i in (t.find("["), t.find("{")) if i != -1), default=-1)
    if start == -1:
        raise ValueError(f"no JSON in judge reply: {text[:120]}")
    open_ch = t[start]
    close_ch = "]" if open_ch == "[" else "}"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return json.loads(t[start : i + 1])
    return json.loads(t[start:])  # let json raise a clear error if unbalanced


def _decompose(client, answer: str) -> list[str]:  # noqa: ANN001
    prompt = (
        "Break the following answer into its atomic factual claims. Each claim must "
        "stand alone and assert exactly one fact. Return ONLY a JSON array of "
        f"strings.\n\nAnswer:\n{answer}"
    )
    claims = _parse_json(_judge(client, prompt))
    return [str(c) for c in claims]


def _verify(client, claims: list[str], contexts: list[str]) -> list[dict]:  # noqa: ANN001
    ctx = "\n\n".join(f"[Context {i + 1}]\n{c}" for i, c in enumerate(contexts))
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
    prompt = (
        "You are a faithfulness judge. A claim is SUPPORTED (verdict 1) if it is "
        "stated in the contexts or can be reasonably inferred from them, even if "
        "paraphrased or worded differently. Mark it UNSUPPORTED (verdict 0) only if "
        "the contexts do not contain or imply it, or contradict it. Do not require "
        "verbatim wording. Return ONLY a compact JSON array of objects with no "
        'prose: [{"claim": <n>, "verdict": 0|1}].'
        f"\n\nContexts:\n{ctx}\n\nClaims:\n{numbered}"
    )
    return _parse_json(_judge(client, prompt))


def faithfulness() -> dict | None:
    if not _has_llm_judge():
        print(
            "\n== Faithfulness (LLM judge): SKIPPED ==\n"
            "No ANTHROPIC_API_KEY set. Faithfulness needs an LLM judge. Set the key "
            "and install the extra (uv sync --extra live) to compute it."
        )
        return None
    try:
        import anthropic
    except ImportError:
        print(
            "\n== Faithfulness: anthropic SDK not installed ==\n"
            "Install with: uv sync --extra live"
        )
        return None

    client = anthropic.Anthropic()
    # LLM-judge faithfulness is noisy per draw (claim decomposition varies, and
    # Sonnet does not allow temperature=0). Average over a few passes and report
    # the spread so the number is an estimate with error bars, not one lucky draw.
    passes = 3
    print(f"\n== Faithfulness (Ragas-style, Anthropic judge, {passes} passes) ==")
    per_case = []
    for case in CASES:
        retrieval = retrieve(case["query"], k=3)
        contexts = [c.text for c in retrieval.citations]
        scores, first_detail = [], None
        for _p in range(passes):
            claims = _decompose(client, case["answer"])
            verdicts = _verify(client, claims, contexts)
            supported = sum(1 for v in verdicts if int(v.get("verdict", 0)) == 1)
            total = len(claims)
            scores.append(supported / total if total else 0.0)
            if first_detail is None:
                first_detail = (claims, verdicts)
        mean_s = round(sum(scores) / len(scores), 3)
        lo, hi = round(min(scores), 3), round(max(scores), 3)
        print(
            f"query: {case['query'][:55]}...\n"
            f"  backend: {retrieval.backend}  faithfulness: {mean_s}  "
            f"(range {lo}-{hi} over {passes} passes)"
        )
        claims, verdicts = first_detail
        for v in verdicts:
            n = int(v.get("claim", 0)) - 1
            mark = "OK " if int(v.get("verdict", 0)) == 1 else "NO "
            claim_txt = claims[n] if 0 <= n < len(claims) else "?"
            print(f"    [{mark}] {claim_txt[:80]}")
        per_case.append(
            {"query": case["query"], "faithfulness": mean_s, "range": [lo, hi]}
        )

    mean = round(sum(c["faithfulness"] for c in per_case) / len(per_case), 3)
    print(f"\n  mean faithfulness across {len(per_case)} cases: {mean}")
    return {
        "model": JUDGE_MODEL,
        "passes": passes,
        "mean_faithfulness": mean,
        "cases": per_case,
    }


if __name__ == "__main__":
    retrieval_signals()
    result = faithfulness()
    if result is not None:
        print("\n" + json.dumps(result, indent=2))
