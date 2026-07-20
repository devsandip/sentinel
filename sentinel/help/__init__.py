"""Help: the FAQ and Ask me, both grounded in the User Manual.

The manual screen (`sentinel/ui/manual.py`) is the reference. This package adds
the two lookup surfaces beside it: an FAQ that routes a common question to the
chapter answering it, and Ask me, which answers a typed question from the
manual corpus or refuses.
"""

from .ask import ANSWERED, IRRELEVANT, UNSUPPORTED, Answer, ask
from .corpus_loader import CorpusChunk, CorpusPage, load_chunks, load_pages, page_by_id
from .faq import FAQ_ENTRIES, FaqEntry, topics
from .retriever import Hit, search

__all__ = [
    "ANSWERED",
    "FAQ_ENTRIES",
    "IRRELEVANT",
    "UNSUPPORTED",
    "Answer",
    "CorpusChunk",
    "CorpusPage",
    "FaqEntry",
    "Hit",
    "ask",
    "load_chunks",
    "load_pages",
    "page_by_id",
    "search",
    "topics",
]
