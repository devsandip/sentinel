"""The evidence pack: the leadership output and the oversight claim (section 10.5).

A dashboard shows a number. An evidence pack shows the number, the whole chain
that produced it, the controls that were attested along the way, and, as its
non-negotiable differentiator, what the number is not allowed to claim. The last
part is the "what this does not say" block: the difference between an artifact a
bank can file and a chart it cannot.
"""

from __future__ import annotations

from .outputs import QuartoRender, render_quarto, to_marimo_notebook
from .pack import (
    EvidencePack,
    ProvenanceChain,
    SignoffError,
    build_evidence_pack,
    sign_evidence_pack,
)

__all__ = [
    "EvidencePack",
    "ProvenanceChain",
    "QuartoRender",
    "SignoffError",
    "build_evidence_pack",
    "render_quarto",
    "sign_evidence_pack",
    "to_marimo_notebook",
]
