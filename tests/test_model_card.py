"""Tests for the model card generator: required sections, render, PDF."""

from __future__ import annotations

from sentinel.harness.model_card import (
    REQUIRED_SECTIONS,
    build_model_card,
    render_markdown,
    render_pdf,
)
from sentinel.ml.fairness import compute_fairness
from sentinel.ml.pipeline import run_pipeline


def _card(protected="age_band", seed=42):
    result = run_pipeline(protected_attribute=protected, seed=seed)
    fairness = compute_fairness(protected_attribute=protected, seed=seed)
    return build_model_card(result, fairness, generated_at="2026-07-12 00:00 UTC"), result


def test_card_has_all_required_sections():
    card, _ = _card()
    d = card.to_dict()
    for section in REQUIRED_SECTIONS:
        assert section in d, f"missing section: {section}"
        assert d[section], f"empty section: {section}"


def test_card_values_come_from_run():
    card, result = _card()
    # Performance metrics must match the real run, not be hard-coded.
    assert card.performance["metrics"] == result.metrics
    assert card.performance["confusion_matrix"] == result.confusion
    assert card.data_lineage["n_rows"] == 1000
    # Protected attribute must be recorded as excluded.
    assert "age_years" in card.governance["protected_attribute_excluded"]


def test_fairness_flag_propagates_to_card():
    # age_band is known to flag; the card must reflect that verdict.
    card, _ = _card(protected="age_band")
    assert card.fairness["verdict"] == "FLAGGED for review"
    card_sex, _ = _card(protected="sex")
    assert card_sex.fairness["verdict"] == "within tolerance"


def test_render_markdown_contains_key_sections():
    card, _ = _card()
    md = render_markdown(card)
    assert "# Model Card" in md
    assert "## Fairness" in md
    assert "## Data lineage" in md
    assert "Confusion matrix" in md


def test_render_pdf_writes_file(tmp_path):
    card, _ = _card()
    out = render_pdf(card, tmp_path / "card.pdf")
    assert out.exists()
    assert out.stat().st_size > 2000
    # PDF magic header.
    assert out.read_bytes()[:4] == b"%PDF"


def test_render_pdf_creates_the_directory_it_writes_into(tmp_path):
    """The bug this catches only ever appeared in prod.

    The UI writes model-card PDFs under `runtime/`, which is gitignored and so
    is absent from the deploy bundle. Every local checkout has one, prod never
    did, and the Registry's download raised FileNotFoundError on the live site
    while the whole suite stayed green. The old test passed a `tmp_path` that
    pytest had already created, which is exactly the condition prod does not
    meet."""
    card, _ = _card()
    missing = tmp_path / "runtime" / "nested"
    assert not missing.exists()

    out = render_pdf(card, missing / "card.pdf")

    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"
