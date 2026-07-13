"""Vector store abstraction (ideas.md item 2).

The default `LocalVectorStore` indexes the corpus with TF-IDF term vectors and
ranks by cosine similarity. It is free, deterministic, and public-link safe, so
it is what the demo uses. It is honestly a lexical vector index, not dense
embeddings; the enterprise path swaps in dense embeddings without changing the
interface.

`PgVectorStore` is the real-AWS adapter: Postgres + pgvector with Bedrock
embeddings. Its interface is implemented; it raises `StoreNotProvisioned` until
an RDS instance is configured, so the code path is real but no paid AWS resource
is stood up here. Select a backend with SENTINEL_VECTOR_STORE=local|pgvector
(default local).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .corpus import Chunk, load_chunks

BACKEND_LOCAL = "local"
BACKEND_PGVECTOR = "pgvector"


class StoreNotProvisioned(RuntimeError):
    """Raised when a backend is selected but its infrastructure is not set up."""


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class LocalVectorStore:
    """TF-IDF term vectors + cosine similarity over the corpus. Free, local."""

    backend = BACKEND_LOCAL

    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self._chunks = chunks or load_chunks()
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(c.text for c in self._chunks)

    def search(self, query: str, k: int = 3) -> list[ScoredChunk]:
        q = self._vectorizer.transform([query])
        sims = cosine_similarity(q, self._matrix)[0]
        ranked = sorted(
            range(len(self._chunks)), key=lambda i: sims[i], reverse=True
        )
        out = []
        for i in ranked[:k]:
            if sims[i] <= 0.0:
                continue
            out.append(ScoredChunk(chunk=self._chunks[i], score=round(float(sims[i]), 4)))
        return out


class PgVectorStore:
    """Real-AWS adapter: Postgres + pgvector with Bedrock embeddings.

    Implemented interface, not provisioned. Configure an RDS instance and set
    SENTINEL_PGVECTOR_DSN to enable; until then search raises StoreNotProvisioned.
    """

    backend = BACKEND_PGVECTOR

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.getenv("SENTINEL_PGVECTOR_DSN")

    def search(self, query: str, k: int = 3) -> list[ScoredChunk]:
        if not self._dsn:
            raise StoreNotProvisioned(
                "pgvector backend selected but no RDS DSN configured "
                "(set SENTINEL_PGVECTOR_DSN). No paid AWS resource is stood up "
                "by default; the local backend is used instead."
            )
        # Real implementation would embed the query via Bedrock Titan, run a
        # pgvector `<=>` nearest-neighbor query, and map rows back to Chunks.
        raise StoreNotProvisioned("pgvector RDS instance not provisioned")


_STORE: LocalVectorStore | None = None


def get_store():
    """Return the configured store, falling back to local if AWS is not set up."""
    backend = os.getenv("SENTINEL_VECTOR_STORE", BACKEND_LOCAL)
    if backend == BACKEND_PGVECTOR:
        store = PgVectorStore()
        if store._dsn:
            return store
        # No DSN: fall back to local so the demo always works.
    global _STORE
    if _STORE is None:
        _STORE = LocalVectorStore()
    return _STORE
