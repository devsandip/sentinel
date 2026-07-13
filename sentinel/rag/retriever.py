"""Retrieval + citation (ideas.md item 2).

`retrieve(query, k)` returns ranked corpus passages with similarity scores and a
citation for each. `retrieve_policy` is the governed tool an agent calls; it also
records the retrieval to the audit trail so the grounding is inspectable. Every
retrieval carries the store backend used, so the UI can show whether it ran on
the local vector index or the AWS pgvector store.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..harness.audit import AuditLog
from .store import BACKEND_PGVECTOR, ScoredChunk, get_store, local_store


@dataclass(frozen=True)
class Citation:
    citation: str
    provenance: str
    text: str
    score: float

    def to_dict(self) -> dict:
        return {
            "citation": self.citation,
            "provenance": self.provenance,
            "text": self.text,
            "score": self.score,
        }


@dataclass(frozen=True)
class Retrieval:
    query: str
    backend: str
    citations: list[Citation]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "backend": self.backend,
            "citations": [c.to_dict() for c in self.citations],
        }

    @property
    def top(self) -> Citation | None:
        return self.citations[0] if self.citations else None


def _to_citation(sc: ScoredChunk) -> Citation:
    return Citation(
        citation=sc.chunk.citation,
        provenance=sc.chunk.provenance,
        text=sc.chunk.text,
        score=sc.score,
    )


def retrieve(query: str, k: int = 3) -> Retrieval:
    store = get_store()
    try:
        results = store.search(query, k=k)
        backend = store.backend
    except Exception:  # noqa: BLE001
        # Resilience: if pgvector is unreachable at runtime (RDS down, Bedrock
        # throttle, network), fall back to the local index so the public link
        # never breaks. Only the AWS path may fall back; a local failure is a bug.
        if store.backend != BACKEND_PGVECTOR:
            raise
        fallback = local_store()
        results = fallback.search(query, k=k)
        backend = "pgvector-unavailable->local"
    return Retrieval(
        query=query,
        backend=backend,
        citations=[_to_citation(r) for r in results],
    )


def retrieve_policy(
    query: str,
    audit: AuditLog | None = None,
    agent: str = "validator",
    k: int = 3,
) -> Retrieval:
    """The governed retrieval tool: retrieve and log the grounding."""
    result = retrieve(query, k=k)
    if audit is not None:
        top = result.top
        audit.record(
            agent=agent,
            action="policy_retrieved",
            inputs_summary=f"query='{query}' via {result.backend} vector store",
            data_touched=[c.citation for c in result.citations],
            output_summary=(
                f"Retrieved {len(result.citations)} passage(s); "
                + (f"top: {top.citation}" if top else "no match")
            ),
        )
    return result
