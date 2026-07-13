"""PII detection and redaction.

Regex-based detection of emails, phone numbers, and government-style IDs
(SSN-shaped). Applied to any text before it would be sent to an LLM. Every
redaction is logged to the audit trail. German Credit carries little PII, so
data.py injects synthetic applicant_email / applicant_ssn columns purely to
demonstrate this control firing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .audit import LEVEL_REDACTION, AuditLog

_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}

_PLACEHOLDER = {
    "email": "[REDACTED_EMAIL]",
    "ssn": "[REDACTED_SSN]",
    "phone": "[REDACTED_PHONE]",
}


@dataclass
class RedactionResult:
    original_length: int
    redacted_text: str
    findings: dict[str, int]  # pii_type -> count

    @property
    def total(self) -> int:
        return sum(self.findings.values())


def scan(text: str) -> RedactionResult:
    findings: dict[str, int] = {}
    redacted = text
    # SSN before phone: an SSN pattern must not be mistaken for a phone.
    for kind in ("email", "ssn", "phone"):
        pattern = _PATTERNS[kind]
        matches = pattern.findall(redacted)
        if matches:
            findings[kind] = len(matches)
            redacted = pattern.sub(_PLACEHOLDER[kind], redacted)
    return RedactionResult(
        original_length=len(text), redacted_text=redacted, findings=findings
    )


def redact(text: str, agent: str, audit: AuditLog, enabled: bool = True) -> str:
    """Redact PII and log the event if anything was found.

    If PII redaction is disabled for the run (demo toggle), the text passes
    through unchanged. The disabling itself is audited at run start.
    """
    if not enabled:
        return text
    result = scan(text)
    if result.total:
        audit.record(
            agent=agent,
            action="pii_redacted",
            level=LEVEL_REDACTION,
            inputs_summary=f"{result.original_length} chars scanned before LLM",
            data_touched=sorted(result.findings),
            output_summary=(
                f"Redacted {result.total} PII item(s): "
                + ", ".join(f"{k}x{v}" for k, v in result.findings.items())
            ),
            extra={"findings": result.findings},
        )
    return result.redacted_text
