"""The Ask-me corpus: the User Manual rendered as retrievable prose.

The manual itself is `sentinel/ui/manual.py`, a screen rather than a document.
That is the right shape for a reader and the wrong shape for retrieval, so the
prose under `corpus/` restates the manual's editorial content in markdown that
can be chunked and ranked.

Two sources of truth is a real cost, and this module is where the cost is paid
down. The manual's doctrine is that every enforced number reads from the module
that enforces it, so the corpus is not allowed to restate one: a page names the
control or the cap and points at the chapter that prints the live value.
`tests/test_help_corpus.py` scans the corpus for retyped constants and fails the
build, the same way `test_no_screen_hardcodes_the_wall_clock` guards the UI. A
corpus that may not carry numbers cannot go stale in the way that matters.

Pages are what the FAQ links to. Chunks, one per paragraph, are what Ask me
retrieves, so a citation points at a passage rather than a whole chapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

_REQUIRED = ("id", "title", "chapter", "summary")


@dataclass(frozen=True)
class CorpusChunk:
    page_id: str
    page_title: str
    chapter: str  # the manual chapter this passage renders
    heading: str  # nearest preceding "## " heading, "" above the first one
    text: str
    ordinal: int

    @property
    def anchor(self) -> str:
        """Citation label, e.g. 'The nine stages > Not in route'."""
        return f"{self.page_title} > {self.heading}" if self.heading else self.page_title


@dataclass(frozen=True)
class CorpusPage:
    id: str
    title: str
    chapter: str
    summary: str
    body: str


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
def load_pages() -> tuple[CorpusPage, ...]:
    pages = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        meta, body = _split_frontmatter(path.read_text(), path.name)
        pages.append(
            CorpusPage(
                id=str(meta["id"]),
                title=str(meta["title"]),
                chapter=str(meta["chapter"]),
                summary=str(meta["summary"]).strip(),
                body=body,
            )
        )
    ids = [p.id for p in pages]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate corpus page ids: {dupes}")
    return tuple(pages)


@cache
def load_chunks() -> tuple[CorpusChunk, ...]:
    chunks: list[CorpusChunk] = []
    for page in load_pages():
        heading = ""
        ordinal = 0
        for raw in page.body.split("\n\n"):
            block = raw.strip()
            if not block:
                continue
            if block.startswith("#"):
                # A heading labels the passages under it. On its own it is a
                # retrieval hit with no answer in it, so it is not a chunk.
                heading = block.lstrip("#").strip()
                continue
            chunks.append(
                CorpusChunk(
                    page_id=page.id,
                    page_title=page.title,
                    chapter=page.chapter,
                    heading=heading,
                    text=block,
                    ordinal=ordinal,
                )
            )
            ordinal += 1
    return tuple(chunks)


def page_by_id(page_id: str) -> CorpusPage | None:
    for page in load_pages():
        if page.id == page_id:
            return page
    return None
