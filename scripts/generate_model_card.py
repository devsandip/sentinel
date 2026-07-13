"""Generate the sample model card (Markdown + PDF) committed to the repo.

Usage:
    uv run python scripts/generate_model_card.py [--protected age_band] [--seed 42]
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel.harness.model_card import (  # noqa: E402
    build_model_card,
    render_markdown,
    render_pdf,
)
from sentinel.ml.fairness import compute_fairness  # noqa: E402
from sentinel.ml.pipeline import run_pipeline  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "docs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protected", default="age_band")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    result = run_pipeline(protected_attribute=args.protected, seed=args.seed)
    fairness = compute_fairness(protected_attribute=args.protected, seed=args.seed)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    card = build_model_card(result, fairness, generated_at=generated_at)

    OUT_DIR.mkdir(exist_ok=True)
    md_path = OUT_DIR / "sample_model_card.md"
    pdf_path = OUT_DIR / "sample_model_card.pdf"
    md_path.write_text(render_markdown(card))
    render_pdf(card, pdf_path)
    print(f"Wrote {md_path}")
    print(f"Wrote {pdf_path} ({pdf_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
