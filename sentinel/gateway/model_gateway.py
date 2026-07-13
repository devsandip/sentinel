"""Provider-agnostic model gateway.

Interface: narrate(step, context) -> Generation. Providers:
  - templated (default): returns deterministic, pre-written narration keyed by
    step. Zero external calls, zero cost. This is what the public link uses.
  - anthropic / openai: real LLM calls, lazily imported so scripted mode never
    loads an SDK. Cost-capped and rate-aware; on any failure or cap breach the
    gateway falls back to templated narration and records why.

Honesty rule (build spec §1.2): in templated mode the UI must say "scripted
narration over a live analysis". `Generation.live` carries that flag.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

TEMPLATED = "templated"
ANTHROPIC = "anthropic"
OPENAI = "openai"

# Deterministic narration, keyed by pipeline step. format_map over the run
# context; missing keys degrade gracefully via _SafeDict.
_TEMPLATES: dict[str, str] = {
    "profiler": (
        "Profiled {n_rows} applicants across {n_features} candidate features. "
        "Target is credit default; class balance is {class_balance} "
        "(default rate {default_rate}). No missing values detected. "
        "Access to proxy and PII columns was mediated by RBAC."
    ),
    "eda": (
        "Reviewed feature distributions and encoded categoricals. Numeric "
        "features standardized. Flagged that the protected attribute "
        "'{protected_attribute}' will be excluded from model inputs before "
        "training, per responsible-AI policy."
    ),
    "modeler": (
        "Trained a logistic-regression baseline on {n_train} applicants and "
        "evaluated on {n_test}. Held-out AUC {auc}, accuracy {accuracy}. "
        "Proposing this model for promotion; pausing for human approval."
    ),
    "validator": (
        "Ran the fairness review across '{protected_attribute}' and the eval "
        "gate. Disparity ratio {disparity_ratio} against a {threshold} "
        "threshold: {fairness_verdict}. Eval gate: {eval_summary}."
    ),
    "summary": (
        "Run complete. Model AUC {auc}; fairness {fairness_verdict}; "
        "promotion {promotion_state}. Full audit trail and model card attached."
    ),
}


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # noqa: D401
        return "n/a"


@dataclass
class Generation:
    text: str
    tokens: int
    cost_usd: float
    provider: str
    live: bool
    fell_back: bool = False
    fallback_reason: str = ""


def _render_template(step: str, context: dict[str, Any]) -> str:
    template = _TEMPLATES.get(step)
    if template is None:
        return f"[{step}] step complete."
    return template.format_map(_SafeDict(context))


class ModelGateway:
    """Selects a provider and enforces the cost cap for live mode."""

    def __init__(
        self,
        provider: str = TEMPLATED,
        model: str | None = None,
        monthly_cap_usd: float | None = None,
        _spent_usd: float = 0.0,
    ) -> None:
        self.provider = provider
        self.model = model or _default_model(provider)
        # Hard dollar ceiling for live mode; env override if not passed.
        cap_env = os.getenv("LIVE_MODE_MONTHLY_CAP")
        self.monthly_cap_usd = (
            monthly_cap_usd
            if monthly_cap_usd is not None
            else (float(cap_env) if cap_env else 5.0)
        )
        self._spent_usd = _spent_usd

    @property
    def is_live(self) -> bool:
        return self.provider in (ANTHROPIC, OPENAI)

    def narrate(self, step: str, context: dict[str, Any]) -> Generation:
        if not self.is_live:
            return Generation(
                text=_render_template(step, context),
                tokens=0,
                cost_usd=0.0,
                provider=TEMPLATED,
                live=False,
            )
        # Live path with graceful fallback.
        if self._spent_usd >= self.monthly_cap_usd:
            return self._fallback(step, context, "monthly cost cap reached")
        try:
            text, tokens, cost = self._call_live(step, context)
        except Exception as exc:  # noqa: BLE001 - any live failure degrades safely
            return self._fallback(step, context, f"live call failed: {exc}")
        self._spent_usd += cost
        return Generation(
            text=text, tokens=tokens, cost_usd=round(cost, 6),
            provider=self.provider, live=True,
        )

    def _fallback(self, step: str, context: dict, reason: str) -> Generation:
        return Generation(
            text=_render_template(step, context),
            tokens=0,
            cost_usd=0.0,
            provider=TEMPLATED,
            live=False,
            fell_back=True,
            fallback_reason=reason,
        )

    def _call_live(self, step: str, context: dict) -> tuple[str, int, float]:
        prompt = _build_prompt(step, context)
        if self.provider == ANTHROPIC:
            return _call_anthropic(prompt, self.model)
        if self.provider == OPENAI:
            return _call_openai(prompt, self.model)
        raise ValueError(f"unknown provider {self.provider}")


def _default_model(provider: str) -> str:
    return {
        ANTHROPIC: "claude-haiku-4-5-20251001",
        OPENAI: "gpt-4o-mini",
    }.get(provider, TEMPLATED)


def _build_prompt(step: str, context: dict[str, Any]) -> str:
    return (
        "You are a data-science agent narrating one step of a governed credit-risk "
        "analysis for a bank audit trail. Be factual, 2-3 sentences, no markdown.\n"
        f"Step: {step}\n"
        f"Facts (already computed, do not invent): {context}"
    )


def _call_anthropic(prompt: str, model: str) -> tuple[str, int, float]:
    import anthropic  # lazy: only imported in live mode

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=180,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    tokens = msg.usage.input_tokens + msg.usage.output_tokens
    # Rough Haiku pricing; exact accounting is not the point of the demo.
    cost = (msg.usage.input_tokens * 1e-6) + (msg.usage.output_tokens * 5e-6)
    return text.strip(), tokens, cost


def _call_openai(prompt: str, model: str) -> tuple[str, int, float]:
    from openai import OpenAI  # lazy

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        max_tokens=180,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
    cost = (usage.prompt_tokens * 1.5e-7 + usage.completion_tokens * 6e-7) if usage else 0.0
    return text.strip(), tokens, cost
