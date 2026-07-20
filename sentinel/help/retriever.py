"""Retrieval over the Help corpus.

Same construction as `sentinel/rag/store.py`'s LocalVectorStore: TF-IDF term
vectors and cosine similarity. Free, deterministic, and public-link safe, so
Help works with no key and no spend. It is honestly a lexical index, not dense
embeddings, and the corpus is ten pages, so the fit costs milliseconds and there
is nothing to persist.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .corpus_loader import CorpusChunk, load_chunks


@dataclass(frozen=True)
class Hit:
    chunk: CorpusChunk
    score: float

    def to_dict(self) -> dict:
        return {
            "page_id": self.chunk.page_id,
            "chapter": self.chunk.chapter,
            "anchor": self.chunk.anchor,
            "text": self.chunk.text,
            "score": self.score,
        }


class _Index:
    def __init__(self, chunks: tuple[CorpusChunk, ...]) -> None:
        self._chunks = chunks
        # Bigrams matter here: "nine stages", "autonomy tier" and "audit log"
        # are the terms users type, and unigrams alone rank them apart.
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        # The heading is prepended because it carries the vocabulary of the
        # passage beneath it. The page title is not, or a title word would
        # outrank a body that actually answers the question.
        self._matrix = self._vectorizer.fit_transform(
            f"{c.heading}. {c.text}" if c.heading else c.text for c in chunks
        )

    def coverage(self, query: str) -> float:
        """Fraction of the query's content words the corpus has any word for.

        Cosine score alone is a poor off-topic test on a short query: one
        incidental term ("write me a poem") can carry a passage over the floor
        while every word that made the question what it is ("poem", "sea") is
        absent from the corpus entirely. Coverage asks the blunter question,
        how much of this sentence is even in our vocabulary, and it is what
        separates a badly-phrased product question from a question about
        something else.
        """
        analyze = self._vectorizer.build_analyzer()
        # Unigrams only: a bigram is absent whenever either half is, which
        # would drag coverage down on any phrasing the corpus does not share.
        terms = [t for t in analyze(query) if " " not in t]
        if not terms:
            return 0.0
        vocab = self._vectorizer.vocabulary_
        return sum(1 for t in terms if t in vocab) / len(terms)

    def search(self, query: str, k: int) -> list[Hit]:
        q = self._vectorizer.transform([query])
        sims = cosine_similarity(q, self._matrix)[0]
        ranked = sorted(range(len(self._chunks)), key=lambda i: sims[i], reverse=True)
        return [
            Hit(chunk=self._chunks[i], score=round(float(sims[i]), 4))
            for i in ranked[:k]
            if sims[i] > 0.0
        ]


@cache
def _index() -> _Index:
    return _Index(load_chunks())


def search(query: str, k: int = 4) -> list[Hit]:
    """Top-k corpus passages for a query, best first. Empty if nothing matches."""
    if not query.strip():
        return []
    return _index().search(query, k)


def coverage(query: str) -> float:
    """Fraction of the query's content words that appear in the corpus at all."""
    if not query.strip():
        return 0.0
    return _index().coverage(query)
