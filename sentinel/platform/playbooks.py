"""AI Playbook loader (ideas.md item 10).

Playbooks are opinionated, end-to-end guides for a use-case class. They live as
markdown files with a YAML frontmatter block under playbooks/, so they are both
human-readable (rendered in the UI, downloadable as a pack) and machine-readable
(the frontmatter drives the Platform surface and the "this run follows Playbook X"
indicator).

Frontmatter contract (all keys required):
  id, title, jtbd, pattern, status, implemented_by
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

PLAYBOOK_DIR = Path(__file__).resolve().parent / "playbooks"

_REQUIRED_KEYS = ("id", "title", "jtbd", "pattern", "status", "implemented_by")


@dataclass(frozen=True)
class Playbook:
    id: str
    title: str
    jtbd: str
    pattern: str
    status: str
    implemented_by: str
    body: str  # the markdown after the frontmatter
    source: str  # filename, for the download pack

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "jtbd": self.jtbd,
            "pattern": self.pattern,
            "status": self.status,
            "implemented_by": self.implemented_by,
            "source": self.source,
        }


def _split_frontmatter(text: str, source: str) -> tuple[dict, str]:
    """Parse a leading `---\\n...\\n---\\n` YAML frontmatter block."""
    if not text.startswith("---"):
        raise ValueError(f"{source}: missing frontmatter block")
    parts = text.split("---", 2)
    # parts[0] is empty (before the first ---), parts[1] is the yaml, parts[2] body.
    if len(parts) < 3:
        raise ValueError(f"{source}: malformed frontmatter block")
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    missing = [k for k in _REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"{source}: frontmatter missing keys {missing}")
    return meta, body


def _load_one(path: Path) -> Playbook:
    meta, body = _split_frontmatter(path.read_text(), path.name)
    return Playbook(
        id=str(meta["id"]),
        title=str(meta["title"]),
        jtbd=str(meta["jtbd"]).strip(),
        pattern=str(meta["pattern"]),
        status=str(meta["status"]),
        implemented_by=str(meta["implemented_by"]),
        body=body,
        source=path.name,
    )


@cache
def load_playbooks() -> list[Playbook]:
    """All playbooks, sorted with implemented ones first, then by title."""
    books = [_load_one(p) for p in sorted(PLAYBOOK_DIR.glob("*.md"))]
    return sorted(books, key=lambda b: (b.status != "implemented", b.title))


def get_playbook(playbook_id: str) -> Playbook | None:
    for book in load_playbooks():
        if book.id == playbook_id:
            return book
    return None
