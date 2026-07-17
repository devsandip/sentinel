"""Assemble, sign, and render the evidence pack (sections 1.9, 4.8, 10.5, 12).

The pack has four parts:
  - the finding, in one sentence, with a confidence interval;
  - the provenance chain (analysis, dataset SHA, tier, purpose, code/query);
  - the controls attested, as chips;
  - the negative statement: what this finding does not say.

The negative statement is assembled from what the run actually did, not from
boilerplate: a suppressed band becomes a sentence that the finding says nothing
about that band; a flagged proxy becomes a sentence that its use is Legal's call
and is not resolved here. The pack ships pending, and signing it requires an
approver who is not the author (CTL-SOD-01), the same segregation of duties the
approval gate enforces.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

CTL_SOD_01 = "CTL-SOD-01"

STATUS_PENDING = "pending"
STATUS_SIGNED = "signed"


class SignoffError(Exception):
    """Raised when a signoff is refused (e.g. the approver is the author)."""


@dataclass
class ProvenanceChain:
    """The chain a reviewer follows from finding back to data (section 1.9)."""

    run_id: str
    analysis: str  # the certified agent Plan bound, e.g. "fair-lending v1.4"
    dataset: str
    dataset_sha: str | None
    tier: str
    purpose: str
    author: str
    code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "analysis": self.analysis,
            "dataset": self.dataset,
            "dataset_sha": self.dataset_sha,
            "tier": self.tier,
            "purpose": self.purpose,
            "author": self.author,
        }


@dataclass
class EvidencePack:
    """The leadership output. Pending until an independent approver signs."""

    request_id: str
    finding: str
    confidence_interval: tuple[float, float] | None
    provenance: ProvenanceChain
    controls_attested: list[str]
    negative_statement: list[str]
    author: str
    approver: str | None = None
    signed_at: str | None = None
    status: str = STATUS_PENDING

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "finding": self.finding,
            "confidence_interval": list(self.confidence_interval)
            if self.confidence_interval
            else None,
            "provenance": self.provenance.to_dict(),
            "controls_attested": self.controls_attested,
            "negative_statement": self.negative_statement,
            "author": self.author,
            "approver": self.approver,
            "signed_at": self.signed_at,
            "status": self.status,
        }

    def to_markdown(self) -> str:
        """A self-contained, Quarto-renderable leadership document.

        This is the markdown Quarto would render to a filed PDF. Rendering to PDF
        needs the Quarto binary and is an optional downstream step; the content,
        including the non-negotiable negative statement, is produced here.
        """
        p = self.provenance
        ci = (
            f" (95% CI {self.confidence_interval[0]:.2f} to {self.confidence_interval[1]:.2f})"
            if self.confidence_interval
            else ""
        )
        lines = [
            "---",
            f'title: "Evidence pack: {p.analysis}"',
            f'subtitle: "{p.purpose} on {p.dataset}"',
            "---",
            "",
            "## Finding",
            "",
            f"{self.finding}{ci}",
            "",
            "## Provenance",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Analysis | {p.analysis} |",
            f"| Dataset | {p.dataset} (sha:{p.dataset_sha}) |",
            f"| Tier | {p.tier} |",
            f"| Purpose | {p.purpose} |",
            f"| Author | {p.author} |",
            f"| Run | {p.run_id} |",
            "",
            "## Controls attested",
            "",
            " ".join(f"`{c}`" for c in self.controls_attested) or "_none_",
            "",
            "## What this does not say",
            "",
        ]
        lines += [f"- {s}" for s in self.negative_statement]
        lines += [
            "",
            "## Signoff",
            "",
            (
                f"Signed by {self.approver} at {self.signed_at}."
                if self.status == STATUS_SIGNED
                else "Pending independent signoff (approver must not be the author, CTL-SOD-01)."
            ),
        ]
        return "\n".join(lines)


def _band_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if c != "n" and not pd.api.types.is_numeric_dtype(df[c]):
            return c
    return None


def _selection_rate_ci(screened: pd.DataFrame) -> tuple[str, tuple[float, float] | None]:
    """A Wald 95% CI on the selection-rate gap between the two extreme surviving
    bands, from the screened counts (which are all at or above the floor)."""
    band_col = _band_column(screened)
    if band_col is None or "selection_rate" not in screened.columns or len(screened) < 2:
        return "The analysis produced no comparable groups after screening.", None
    df = screened.set_index(band_col)
    rates = df["selection_rate"].astype(float)
    hi_band, lo_band = rates.idxmax(), rates.idxmin()
    p1, p2 = float(rates.max()), float(rates.min())
    n1 = float(df.loc[hi_band, "n"]) if "n" in df.columns else 0.0
    n2 = float(df.loc[lo_band, "n"]) if "n" in df.columns else 0.0
    diff = p1 - p2
    finding = (
        f"Applicants in {hi_band} are flagged at a {p1:.2f} selection rate versus "
        f"{p2:.2f} for {lo_band}, a gap of {diff:.2f}"
    )
    if n1 <= 0 or n2 <= 0:
        return finding, None
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return finding, (round(diff - 1.96 * se, 4), round(diff + 1.96 * se, 4))


def build_negative_statement(
    dataset: str,
    purpose: str,
    tier: str,
    suppressed: list,
    proxy_flags: list,
    cell_floor: int,
) -> list[str]:
    """Assemble the 'what this does not say' block from what the run actually did."""
    out = [
        f"This is a selection-rate comparison on {dataset} under the {purpose} "
        f"purpose at tier {tier}. It is not a causal claim, and it is not a model "
        f"validation.",
    ]
    for cell in suppressed:
        label = cell.label() if hasattr(cell, "label") else str(cell)
        n = getattr(cell, "n", "?")
        out.append(
            f"The {label} group was excluded because it fell below the disclosure "
            f"floor (n={n} < {cell_floor}); this finding says nothing about that group."
        )
    for flag in proxy_flags:
        feature = getattr(flag, "feature", "a feature")
        protected = getattr(flag, "protected", "the protected attribute")
        out.append(
            f"{feature} was flagged as a candidate proxy for {protected}; whether "
            f"its use is a business necessity is a Legal determination and is not "
            f"resolved here."
        )
    out.append(
        "This pack is evidence, not an approved conclusion, until an approver who "
        "is not the author signs it."
    )
    return out


def build_evidence_pack(
    *,
    run_id: str,
    analysis: str,
    dataset: str,
    dataset_sha: str | None,
    tier: str,
    purpose: str,
    author: str,
    code: str,
    screened: pd.DataFrame,
    controls_attested: list[str],
    suppressed: list,
    proxy_flags: list,
    cell_floor: int,
) -> EvidencePack:
    """Assemble a pending evidence pack from a completed run (Stage 9, Attest)."""
    finding, ci = _selection_rate_ci(screened)
    negative = build_negative_statement(
        dataset, purpose, tier, suppressed, proxy_flags, cell_floor
    )
    provenance = ProvenanceChain(
        run_id=run_id,
        analysis=analysis,
        dataset=dataset,
        dataset_sha=dataset_sha,
        tier=tier,
        purpose=purpose,
        author=author,
        code=code,
    )
    return EvidencePack(
        request_id=run_id,
        finding=finding,
        confidence_interval=ci,
        provenance=provenance,
        controls_attested=controls_attested,
        negative_statement=negative,
        author=author,
    )


def sign_evidence_pack(pack: EvidencePack, approver: str, when: str) -> EvidencePack:
    """Sign the pack. Refuses a self-signoff (CTL-SOD-01): the approver of a
    finding cannot be its author, the same rule the approval gate enforces."""
    if approver == pack.author:
        raise SignoffError(
            f"CTL-SOD-01: approver {approver!r} is the author of this evidence pack; "
            "self-signoff refused. An independent approver must sign."
        )
    pack.approver = approver
    pack.signed_at = when
    pack.status = STATUS_SIGNED
    return pack
