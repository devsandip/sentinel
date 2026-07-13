"""Bedrock Titan text embeddings for the AWS vector store (ideas.md item 2).

Dense embeddings via Amazon Bedrock Titan Embed Text v2 (1024 dims, normalized),
used by the pgvector store. boto3 is imported lazily so the default local store
never needs AWS. The corpus is small and queries are derived from run state, so
the embedding spend is negligible.
"""

from __future__ import annotations

import json
from functools import lru_cache

TITAN_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_DIMS = 1024


def _client():
    import boto3  # lazy: only when the AWS path is used

    return boto3.client("bedrock-runtime")


def embed(text: str, dimensions: int = EMBED_DIMS) -> list[float]:
    body = json.dumps(
        {"inputText": text, "dimensions": dimensions, "normalize": True}
    )
    resp = _client().invoke_model(modelId=TITAN_MODEL, body=body)
    payload = json.loads(resp["body"].read())
    return payload["embedding"]


@lru_cache(maxsize=256)
def embed_cached(text: str) -> tuple[float, ...]:
    """Cache query embeddings; queries are a small derived set."""
    return tuple(embed(text))
