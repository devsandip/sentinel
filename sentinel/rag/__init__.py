"""Retrieval-augmented grounding: the governed knowledge layer.

Agents cite the bank's governing knowledge (SR 11-7, ECOA/Reg B, the four-fifths
rule, internal standards) instead of asserting compliance claims. Default backend
is a free local vector index; a real-AWS pgvector adapter is available behind a
config switch (see store.py).
"""

from __future__ import annotations

from .corpus import Chunk, corpus_summary, load_chunks
from .retriever import Citation, Retrieval, retrieve, retrieve_policy

__all__ = [
    "Chunk",
    "load_chunks",
    "corpus_summary",
    "Citation",
    "Retrieval",
    "retrieve",
    "retrieve_policy",
]
