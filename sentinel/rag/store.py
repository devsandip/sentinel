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


_TABLE = "policy_chunks"


def _vec_literal(vec: list[float]) -> str:
    """pgvector text input format, e.g. '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def _password_from_secret(secret_arn: str) -> str:
    import json

    import boto3

    sm = boto3.client("secretsmanager")
    raw = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
    return json.loads(raw)["password"]


def _connect():
    """Open a psycopg connection. Password comes from Secrets Manager, never
    from plaintext config. Falls back to SENTINEL_PGVECTOR_DSN if provided.

    The configuration check runs before any import so an unconfigured backend
    raises StoreNotProvisioned without needing psycopg installed.
    """
    dsn = os.getenv("SENTINEL_PGVECTOR_DSN")
    host = os.getenv("SENTINEL_PGVECTOR_HOST")
    secret_arn = os.getenv("SENTINEL_PGVECTOR_SECRET_ARN")
    if not (dsn or (host and secret_arn)):
        raise StoreNotProvisioned(
            "pgvector backend selected but not configured. Set "
            "SENTINEL_PGVECTOR_HOST and SENTINEL_PGVECTOR_SECRET_ARN (or "
            "SENTINEL_PGVECTOR_DSN). No paid AWS resource is required for the "
            "default local backend."
        )

    import psycopg

    if dsn:
        return psycopg.connect(dsn)
    return psycopg.connect(
        host=host,
        dbname=os.getenv("SENTINEL_PGVECTOR_DBNAME", "sentinel"),
        user=os.getenv("SENTINEL_PGVECTOR_USER", "sentinel_admin"),
        password=_password_from_secret(secret_arn),
        port=os.getenv("SENTINEL_PGVECTOR_PORT", "5432"),
        sslmode="require",
    )


class PgVectorStore:
    """Real-AWS store: RDS PostgreSQL + pgvector, Bedrock Titan embeddings.

    Connection params come from the environment; the password is read from
    Secrets Manager at connect time. `index()` embeds and loads the corpus (used
    by the ingestion script); `search()` runs a pgvector nearest-neighbor query.
    """

    backend = BACKEND_PGVECTOR

    def index(self, chunks: list[Chunk] | None = None) -> int:
        from .embeddings import EMBED_DIMS, embed

        chunks = chunks or load_chunks()
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"DROP TABLE IF EXISTS {_TABLE}")
            cur.execute(
                f"CREATE TABLE {_TABLE} ("
                "id serial PRIMARY KEY, doc_id text, title text, citation text, "
                "provenance text, source text, text text, "
                f"embedding vector({EMBED_DIMS}))"
            )
            for c in chunks:
                cur.execute(
                    f"INSERT INTO {_TABLE} "
                    "(doc_id, title, citation, provenance, source, text, embedding) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s::vector)",
                    (
                        c.doc_id,
                        c.title,
                        c.citation,
                        c.provenance,
                        c.source,
                        c.text,
                        _vec_literal(embed(c.text)),
                    ),
                )
            conn.commit()
        return len(chunks)

    def search(self, query: str, k: int = 3) -> list[ScoredChunk]:
        from .embeddings import embed_cached

        # _connect() validates configuration (and raises StoreNotProvisioned)
        # before we spend a Bedrock embedding call.
        with _connect() as conn, conn.cursor() as cur:
            qvec = _vec_literal(list(embed_cached(query)))
            cur.execute(
                "SELECT doc_id, title, citation, provenance, source, text, "
                f"1 - (embedding <=> %s::vector) AS score FROM {_TABLE} "
                "ORDER BY embedding <=> %s::vector LIMIT %s",
                (qvec, qvec, k),
            )
            rows = cur.fetchall()
        out = []
        for doc_id, title, citation, provenance, source, text, score in rows:
            out.append(
                ScoredChunk(
                    chunk=Chunk(
                        doc_id=doc_id,
                        title=title,
                        citation=citation,
                        provenance=provenance,
                        source=source,
                        text=text,
                        ordinal=0,
                    ),
                    score=round(float(score), 4),
                )
            )
        return out


_STORE: LocalVectorStore | None = None


def get_store():
    """Return the configured store, falling back to local if AWS is not set up."""
    backend = os.getenv("SENTINEL_VECTOR_STORE", BACKEND_LOCAL)
    if backend == BACKEND_PGVECTOR:
        if os.getenv("SENTINEL_PGVECTOR_HOST") or os.getenv("SENTINEL_PGVECTOR_DSN"):
            return PgVectorStore()
        # Selected but unconfigured: fall back to local so the demo still works.
    global _STORE
    if _STORE is None:
        _STORE = LocalVectorStore()
    return _STORE
