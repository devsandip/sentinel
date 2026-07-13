"""Eval-as-CI-gate.

Runs a golden set of checks (evals.yaml) against the assembled run payload.
Each check inspects a dotted path into the payload. If any check fails, the
run is "blocked from promotion". Mirrors treating evals as a release gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..config import load_evals
from .audit import LEVEL_GATE, AuditLog


@dataclass
class CheckResult:
    id: str
    description: str
    passed: bool
    detail: str


@dataclass
class EvalReport:
    results: list[CheckResult]
    passed: int
    failed: int
    promoted: bool  # True only if every check passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [asdict(r) for r in self.results],
            "passed": self.passed,
            "failed": self.failed,
            "promoted": self.promoted,
            "pass_rate": round(self.passed / max(1, self.passed + self.failed), 4),
        }


def _resolve(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
    """Follow a dotted path; return (found, value)."""
    node: Any = payload
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False, None
    return True, node


def _evaluate(check: dict[str, Any], payload: dict[str, Any]) -> CheckResult:
    ctype = check["type"]
    path = check.get("path", "")
    found, value = _resolve(payload, path)
    cid, desc = check["id"], check["description"]

    if ctype == "metric_present":
        ok = found and value is not None
        return CheckResult(cid, desc, ok, f"{path} = {value}" if found else "missing")

    if ctype == "non_empty":
        ok = bool(found and value)
        return CheckResult(cid, desc, ok, f"{path} = {value}" if found else "missing")

    if ctype == "metric_min":
        ok = found and isinstance(value, (int, float)) and value >= check["min"]
        return CheckResult(
            cid, desc, ok, f"{path} = {value} (min {check['min']})"
        )

    if ctype == "keys_present":
        keys = check["keys"]
        if not found or not isinstance(value, dict):
            return CheckResult(cid, desc, False, f"{path} missing or not a mapping")
        missing = [k for k in keys if k not in value]
        return CheckResult(
            cid, desc, not missing,
            "all keys present" if not missing else f"missing keys: {missing}",
        )

    return CheckResult(cid, desc, False, f"unknown check type: {ctype}")


def run_eval_gate(
    payload: dict[str, Any],
    audit: AuditLog | None = None,
    agent: str = "validator",
    config: dict | None = None,
) -> EvalReport:
    checks = (config or load_evals())["checks"]
    results = [_evaluate(c, payload) for c in checks]
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    report = EvalReport(results, passed, failed, promoted=failed == 0)

    if audit is not None:
        level = LEVEL_GATE
        audit.record(
            agent=agent,
            action="eval_gate",
            level=level,
            inputs_summary=f"{len(checks)} golden checks",
            output_summary=(
                f"{passed}/{len(checks)} passed; "
                + ("promotion allowed" if report.promoted else "BLOCKED from promotion")
            ),
            extra={"failed": [r.id for r in results if not r.passed]},
        )
    return report
