"""Control settings: which governance controls are enabled for a run (item 7).

The headline demo device. A reviewer (Admin persona) can disable a control for a
run and watch the run break: turn off RBAC and the sex-proxy column leaks into
profiling; turn off PII redaction and an applicant email reaches the narration;
turn off the eval gate and a failing model can promote. It proves the controls
are load-bearing, not decoration.

Two honesty rules enforced by the callers:
  1. Disabling a control is itself audited (the orchestrator records it).
  2. Any run with a disabled control is marked UNGOVERNED in the UI, so it can
     never be mistaken for a real governed run.
"""

from __future__ import annotations

from dataclasses import dataclass

CONTROL_RBAC = "rbac"
CONTROL_PII = "pii"
CONTROL_GUARDRAILS = "guardrails"
CONTROL_EVAL_GATE = "eval_gate"
CONTROL_HUMAN_GATE = "human_gate"

# (id, display name, one-line description, what breaks if you disable it)
CONTROL_CATALOG: list[tuple[str, str, str, str]] = [
    (
        CONTROL_RBAC,
        "RBAC",
        "Per-agent column access control.",
        "The sex-proxy column leaks into the Profiler's view.",
    ),
    (
        CONTROL_PII,
        "PII redaction",
        "Scrub PII before any text reaches a model.",
        "An applicant email reaches the narration unredacted.",
    ),
    (
        CONTROL_GUARDRAILS,
        "Guardrails",
        "Tool allow-list sandbox.",
        "Agents may call tools outside their allow-list.",
    ),
    (
        CONTROL_EVAL_GATE,
        "Eval gate",
        "Golden-set checks before promotion.",
        "A model can promote without passing the golden checks.",
    ),
    (
        CONTROL_HUMAN_GATE,
        "Human gate",
        "Human approval before promotion.",
        "The model auto-promotes with no human review.",
    ),
]

CONTROL_IDS = [c[0] for c in CONTROL_CATALOG]
CONTROL_NAMES = {c[0]: c[1] for c in CONTROL_CATALOG}


@dataclass(frozen=True)
class ControlSettings:
    """The set of controls disabled for a run. Empty means fully governed."""

    disabled: frozenset[str] = frozenset()

    def is_enabled(self, control: str) -> bool:
        return control not in self.disabled

    @property
    def any_disabled(self) -> bool:
        return bool(self.disabled)

    def disabled_names(self) -> list[str]:
        return [CONTROL_NAMES.get(c, c) for c in CONTROL_IDS if c in self.disabled]


ALL_ENABLED = ControlSettings()


def from_disabled(ids: list[str]) -> ControlSettings:
    valid = frozenset(i for i in ids if i in CONTROL_IDS)
    return ControlSettings(disabled=valid)
