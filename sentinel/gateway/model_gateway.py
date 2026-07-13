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

import hashlib
import os
from dataclasses import dataclass
from typing import Any

from ..harness.tracing import span

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


# Routing tiers. The gateway classifies each call by stakes and routes to a tier:
# elevated-stakes narration (model performance, promotion) to a capable model,
# routine narration to a cheap model, and in scripted mode to a template. This is
# the "route easy queries to cheap models, hard ones to capable models" pattern.
TIER_TEMPLATED = "templated"
TIER_CHEAP = "cheap"
TIER_CAPABLE = "capable"

# Steps whose narration describes model performance or a promotion decision are
# treated as elevated stakes.
_ELEVATED_STEPS = {"modeler", "validator", "summary"}

# Per-provider model for each tier.
_TIER_MODELS = {
    ANTHROPIC: {TIER_CHEAP: "claude-haiku-4-5-20251001", TIER_CAPABLE: "claude-sonnet-5"},
    OPENAI: {TIER_CHEAP: "gpt-4o-mini", TIER_CAPABLE: "gpt-4o"},
}

# Process-level response cache, shared across runs so an identical call (same
# step + context + route) is a cache hit rather than a repeat spend.
_RESPONSE_CACHE: dict[str, str] = {}


@dataclass
class LedgerEntry:
    """One row of the Gateway Ledger: the centralized record of every model call."""

    seq: int
    call_kind: str  # the pipeline step
    stakes: str  # "low" | "elevated"
    routed_tier: str  # templated | cheap | capable
    routed_model: str
    provider: str  # what actually executed
    executed_live: bool
    tokens: int
    cost_usd: float
    cache: str  # "miss" | "hit"
    policy: str  # policy actions applied at the gateway boundary

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "call_kind": self.call_kind,
            "stakes": self.stakes,
            "routed_tier": self.routed_tier,
            "routed_model": self.routed_model,
            "provider": self.provider,
            "executed_live": self.executed_live,
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
            "cache": self.cache,
            "policy": self.policy,
        }


def _render_template(step: str, context: dict[str, Any]) -> str:
    template = _TEMPLATES.get(step)
    if template is None:
        return f"[{step}] step complete."
    return template.format_map(_SafeDict(context))


def _cache_key(step: str, context: dict[str, Any], route: str) -> str:
    payload = f"{route}|{step}|{sorted(context.items(), key=lambda kv: kv[0])}"
    return hashlib.sha256(payload.encode()).hexdigest()


class ModelGateway:
    """The central control point for model access.

    Every call routes through here: the gateway classifies it, routes it to a
    model tier, checks the cache, enforces the cost-cap policy, executes, and
    records a ledger row. This is where multi-model access, cost governance, and
    observability are centralized, so nothing calls a model directly.
    """

    def __init__(
        self,
        provider: str = TEMPLATED,
        model: str | None = None,
        monthly_cap_usd: float | None = None,
        _spent_usd: float = 0.0,
        run_id: str = "",
    ) -> None:
        self.provider = provider
        self.run_id = run_id
        self.model = model or _default_model(provider)
        # Hard dollar ceiling for live mode; env override if not passed.
        cap_env = os.getenv("LIVE_MODE_MONTHLY_CAP")
        self.monthly_cap_usd = (
            monthly_cap_usd
            if monthly_cap_usd is not None
            else (float(cap_env) if cap_env else 5.0)
        )
        self._spent_usd = _spent_usd
        self.ledger: list[LedgerEntry] = []

    @property
    def is_live(self) -> bool:
        return self.provider in (ANTHROPIC, OPENAI)

    def ledger_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.ledger]

    def _route(self, step: str) -> tuple[str, str, str]:
        """Classify a call by stakes and route it to a tier + model."""
        stakes = "elevated" if step in _ELEVATED_STEPS else "low"
        if not self.is_live:
            return stakes, TIER_TEMPLATED, TEMPLATED
        tier = TIER_CAPABLE if stakes == "elevated" else TIER_CHEAP
        model = _TIER_MODELS.get(self.provider, {}).get(tier, self.model)
        return stakes, tier, model

    def _log(
        self,
        step: str,
        stakes: str,
        tier: str,
        model: str,
        provider: str,
        live: bool,
        tokens: int,
        cost: float,
        cache: str,
        policy: str,
    ) -> None:
        self.ledger.append(
            LedgerEntry(
                seq=len(self.ledger),
                call_kind=step,
                stakes=stakes,
                routed_tier=tier,
                routed_model=model,
                provider=provider,
                executed_live=live,
                tokens=tokens,
                cost_usd=round(cost, 6),
                cache=cache,
                policy=policy,
            )
        )

    def narrate(self, step: str, context: dict[str, Any]) -> Generation:
        if self.run_id:
            with span(f"gateway.{step}", self.run_id, **{"gateway.provider": self.provider}):
                return self._narrate(step, context)
        return self._narrate(step, context)

    def _narrate(self, step: str, context: dict[str, Any]) -> Generation:
        stakes, tier, model = self._route(step)
        key = _cache_key(step, context, f"{self.provider}:{model}")

        # Cache check: an identical call is a hit, no spend.
        if key in _RESPONSE_CACHE:
            self._log(
                step, stakes, tier, model, self.provider, self.is_live,
                tokens=0, cost=0.0, cache="hit", policy="served from cache",
            )
            return Generation(
                text=_RESPONSE_CACHE[key], tokens=0, cost_usd=0.0,
                provider=self.provider if self.is_live else TEMPLATED,
                live=False,
            )

        if not self.is_live:
            text = _render_template(step, context)
            _RESPONSE_CACHE[key] = text
            self._log(
                step, stakes, tier, model, TEMPLATED, False,
                tokens=0, cost=0.0, cache="miss", policy="scripted (zero cost)",
            )
            return Generation(
                text=text, tokens=0, cost_usd=0.0, provider=TEMPLATED, live=False
            )

        # Live path: enforce the cost-cap policy, then execute with fallback.
        if self._spent_usd >= self.monthly_cap_usd:
            gen = self._fallback(step, context, "monthly cost cap reached")
            self._log(
                step, stakes, tier, model, TEMPLATED, False,
                tokens=0, cost=0.0, cache="miss",
                policy="cost cap reached -> fallback to scripted",
            )
            return gen
        try:
            text, tokens, cost = self._call_live(step, context, model)
        except Exception as exc:  # noqa: BLE001 - any live failure degrades safely
            gen = self._fallback(step, context, f"live call failed: {exc}")
            self._log(
                step, stakes, tier, model, TEMPLATED, False,
                tokens=0, cost=0.0, cache="miss",
                policy="live call failed -> fallback to scripted",
            )
            return gen
        self._spent_usd += cost
        _RESPONSE_CACHE[key] = text
        self._log(
            step, stakes, tier, model, self.provider, True,
            tokens=tokens, cost=cost, cache="miss", policy="cost cap ok",
        )
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

    def _call_live(
        self, step: str, context: dict, model: str
    ) -> tuple[str, int, float]:
        prompt = _build_prompt(step, context)
        if self.provider == ANTHROPIC:
            return _call_anthropic(prompt, model)
        if self.provider == OPENAI:
            return _call_openai(prompt, model)
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
