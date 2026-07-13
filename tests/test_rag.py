"""Tests for the RAG layer: corpus, store, retrieval, and citation wiring."""

from __future__ import annotations

from sentinel.orchestrator import Orchestrator
from sentinel.rag import corpus_summary, load_chunks, retrieve
from sentinel.rag.store import (
    LocalVectorStore,
    PgVectorStore,
    StoreNotProvisioned,
)


def test_corpus_loads_with_provenance():
    chunks = load_chunks()
    assert chunks
    provenances = {c.provenance for c in chunks}
    assert provenances == {"public", "synthetic"}
    # The synthetic disclaimer paragraph is not indexed.
    assert not any(c.text.upper().startswith("NOTE:") for c in chunks)
    # Corpus summary has one row per document.
    summ = corpus_summary()
    assert {"sr-11-7", "reg-b-ecoa", "four-fifths-rule"} <= {d["doc_id"] for d in summ}


def test_retrieval_ranks_relevant_passage_first():
    r = retrieve("four-fifths rule adverse impact disparity", k=3)
    assert r.backend == "local"
    assert r.citations
    # The four-fifths passage should be the top hit for that query.
    assert "Four-Fifths" in r.top.citation or "four-fifths" in r.top.text.lower()
    # Scores are sorted descending.
    scores = [c.score for c in r.citations]
    assert scores == sorted(scores, reverse=True)


def test_local_store_returns_scored_chunks():
    store = LocalVectorStore()
    hits = store.search("model risk management validation documentation", k=2)
    assert hits and hits[0].score > 0
    assert any("SR 11-7" in h.chunk.citation for h in hits)


def test_pgvector_not_provisioned_raises():
    store = PgVectorStore(dsn=None)
    try:
        store.search("anything")
        raise AssertionError("expected StoreNotProvisioned")
    except StoreNotProvisioned:
        pass


def test_validator_attaches_citations_and_audits_retrieval():
    orch = Orchestrator()
    state = orch.start_run("build_model")
    orch.approve(state.run_id, approved=True)
    pub = state.to_public_dict()
    assert pub["citations"], "fairness review should be grounded with citations"
    assert pub["retrieval"]["backend"] == "local"
    actions = [e.action for e in state.deps.audit.events()]
    assert "policy_retrieved" in actions
