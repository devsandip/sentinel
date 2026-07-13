"""Governed knowledge corpus loader (ideas.md item 2).

The corpus grounds agents in the bank's governing knowledge so they cite rather
than assert. Documents live as markdown with a YAML frontmatter block under
corpus/. Provenance is explicit: public regulation (SR 11-7, ECOA/Reg B, the
four-fifths rule) versus synthetic internal standards authored for the demo and
labeled as such. Each document is split into paragraph chunks so a citation
points at a passage, not a whole file.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

_REQUIRED = ("id", "title", "source", "provenance", "citation")

# Frontmatter NOTE lines in synthetic docs are kept in the body; the loader
# strips a leading "NOTE:" paragraph from the indexable text so it does not
# dominate retrieval, but keeps it available on the document.


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    citation: str
    provenance: str  # "public" | "synthetic"
    source: str
    text: str
    ordinal: int  # paragraph index within the doc


def _split_frontmatter(text: str, name: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError(f"{name}: missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{name}: malformed frontmatter")
    meta = yaml.safe_load(parts[1]) or {}
    missing = [k for k in _REQUIRED if k not in meta]
    if missing:
        raise ValueError(f"{name}: frontmatter missing {missing}")
    return meta, parts[2].strip()


@cache
def load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        meta, body = _split_frontmatter(path.read_text(), path.name)
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            # Do not index the synthetic-doc disclaimer paragraph.
            if para.upper().startswith("NOTE:"):
                continue
            chunks.append(
                Chunk(
                    doc_id=str(meta["id"]),
                    title=str(meta["title"]),
                    citation=str(meta["citation"]),
                    provenance=str(meta["provenance"]),
                    source=str(meta["source"]),
                    text=para,
                    ordinal=i,
                )
            )
    return chunks


def corpus_summary() -> list[dict]:
    """One row per document, for the Knowledge surface."""
    seen: dict[str, dict] = {}
    for c in load_chunks():
        if c.doc_id not in seen:
            seen[c.doc_id] = {
                "doc_id": c.doc_id,
                "title": c.title,
                "provenance": c.provenance,
                "source": c.source,
                "citation": c.citation,
            }
    return list(seen.values())
