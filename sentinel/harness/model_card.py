"""Model-risk documentation generator (SR 11-7 style).

Builds a model card from a real run: purpose, data lineage, methodology,
performance, fairness, assumptions, limitations, intended use. Renders to
Markdown (for the UI) and PDF (the downloadable showpiece). Every value comes
from the live run objects; nothing here is hard-coded.

References the framing of the U.S. Federal Reserve's SR 11-7 supervisory
guidance on model risk management (conceptual soundness, ongoing monitoring,
outcomes analysis) without reproducing its text.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..ml.fairness import FairnessReport
from ..ml.pipeline import ModelResult

# Static data lineage for the bundled dataset.
DATASET_NAME = "UCI Statlog German Credit"
DATASET_SOURCE = "https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data"
DATASET_VERSION = "statlog-1994"
MODEL_VERSION = "0.1.0"
MODEL_ID = "sentinel-german-credit-logreg"


@dataclass
class ModelCard:
    model_id: str
    model_version: str
    model_name: str
    generated_at: str
    question: str
    purpose: str
    intended_use: str
    out_of_scope_use: list[str]
    data_lineage: dict[str, Any]
    methodology: dict[str, Any]
    performance: dict[str, Any]
    fairness: dict[str, Any]
    assumptions: list[str]
    limitations: list[str]
    governance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REQUIRED_SECTIONS = [
    "purpose",
    "intended_use",
    "data_lineage",
    "methodology",
    "performance",
    "fairness",
    "assumptions",
    "limitations",
    "governance",
]


def build_model_card(
    result: ModelResult,
    fairness: FairnessReport,
    question: str = "Build a credit-default risk model and report performance.",
    generated_at: str = "",
    model_version: str = MODEL_VERSION,
) -> ModelCard:
    profile = result.profile
    transforms = [
        "Stratified train/test split "
        f"({result.n_train} train / {result.n_test} test, seed {result.seed})",
        "Numeric features standardized (zero mean, unit variance)",
        "Categorical features one-hot encoded (unknown categories ignored)",
        f"Protected attribute '{fairness.protected_attribute}' excluded from "
        f"model features ({', '.join(result.excluded_features)})",
    ]

    fairness_verdict = "within tolerance" if fairness.passes else "FLAGGED for review"

    return ModelCard(
        model_id=MODEL_ID,
        model_version=model_version,
        model_name="German Credit default-risk baseline (logistic regression)",
        generated_at=generated_at,
        question=question,
        purpose=(
            "Estimate the probability that a retail credit applicant defaults "
            "('bad' credit risk), to support a loan adjudication decision. "
            "Baseline model for demonstration of a governed analysis workflow."
        ),
        intended_use=(
            "Decision support only, under human review. Outputs a calibrated "
            "risk score for a credit officer; does not auto-decline."
        ),
        out_of_scope_use=[
            "Fully automated adverse action without human review",
            "Use on populations outside the training distribution",
            "Any use of the excluded protected attribute as a decision input",
        ],
        data_lineage={
            "dataset": DATASET_NAME,
            "source": DATASET_SOURCE,
            "version": DATASET_VERSION,
            "n_rows": profile.n_rows,
            "n_features_used": profile.n_features,
            "class_balance": profile.class_balance,
            "default_rate": round(profile.positive_rate, 4),
            "transforms": transforms,
        },
        methodology={
            "algorithm": "Logistic regression (scikit-learn, L2, max_iter=1000)",
            "target": "y = 1 if credit_risk == 'bad' (default event), else 0",
            "numeric_features": profile.numeric_features,
            "categorical_features": profile.categorical_features,
            "validation": "Single stratified holdout; metrics on the test split",
            "seed": result.seed,
        },
        performance={
            "metrics": result.metrics,
            "confusion_matrix": result.confusion,
            "top_features": result.top_features,
        },
        fairness={
            "protected_attribute": fairness.protected_attribute,
            "disparity_metric": fairness.disparity_metric,
            "disparity_ratio": fairness.disparity_ratio,
            "threshold": fairness.threshold,
            "verdict": fairness_verdict,
            "groups": [asdict(g) for g in fairness.groups],
            "note": fairness.note,
        },
        assumptions=[
            "Training data is representative of the applicant population.",
            "Historical labels are unbiased ground truth for default.",
            "Feature relationships are stable over the decision horizon.",
        ],
        limitations=[
            "Single holdout split; no cross-validation or temporal validation.",
            "Baseline model, not tuned; intended to demonstrate the workflow.",
            "Fairness assessed on one protected attribute at a time, not jointly.",
            "German Credit is a small (1000-row) benchmark, not live bank data.",
        ],
        governance={
            "human_in_the_loop": "Model proposal requires explicit approval "
            "before promotion (approval gate).",
            "audit": "Every agent action emits an immutable audit event.",
            "eval_gate": "Golden-set checks must pass before promotion.",
            "protected_attribute_excluded": result.excluded_features,
            "framework": "Framed against SR 11-7 model risk management guidance.",
        },
    )


def render_markdown(card: ModelCard) -> str:
    m = card.performance["metrics"]
    c = card.performance["confusion_matrix"]
    lines: list[str] = []
    a = lines.append

    a(f"# Model Card — {card.model_name}")
    a("")
    a(f"**Model ID:** {card.model_id}  ")
    a(f"**Version:** {card.model_version}  ")
    a(f"**Generated:** {card.generated_at or 'n/a'}  ")
    a(f"**Question:** {card.question}")
    a("")
    a("## Purpose")
    a(card.purpose)
    a("")
    a("## Intended use")
    a(card.intended_use)
    a("")
    a("**Out-of-scope use:**")
    for x in card.out_of_scope_use:
        a(f"- {x}")
    a("")
    a("## Data lineage")
    dl = card.data_lineage
    a(f"- **Dataset:** {dl['dataset']} ({dl['version']})")
    a(f"- **Source:** {dl['source']}")
    a(f"- **Rows:** {dl['n_rows']}  **Features used:** {dl['n_features_used']}")
    a(f"- **Class balance:** {dl['class_balance']}  "
      f"(default rate {dl['default_rate']})")
    a("- **Transforms:**")
    for t in dl["transforms"]:
        a(f"  - {t}")
    a("")
    a("## Methodology")
    me = card.methodology
    a(f"- **Algorithm:** {me['algorithm']}")
    a(f"- **Target:** {me['target']}")
    a(f"- **Validation:** {me['validation']} (seed {me['seed']})")
    a("")
    a("## Performance (held-out test)")
    a("| Metric | Value |")
    a("| --- | --- |")
    for k, v in m.items():
        a(f"| {k} | {v} |")
    a("")
    a(f"Confusion matrix: TN={c['tn']} FP={c['fp']} FN={c['fn']} TP={c['tp']}")
    a("")
    a("**Top features (|coefficient|):**")
    for f in card.performance["top_features"][:8]:
        a(f"- `{f['name']}` {f['coefficient']:+.3f} ({f['direction']})")
    a("")
    a("## Fairness")
    fr = card.fairness
    a(f"- **Protected attribute:** {fr['protected_attribute']} "
      f"(excluded from features)")
    a(f"- **Disparity ratio:** {fr['disparity_ratio']} "
      f"(threshold {fr['threshold']}) — **{fr['verdict']}**")
    a("")
    a("| Group | n | Selection rate | TPR | FPR | Base rate |")
    a("| --- | --- | --- | --- | --- | --- |")
    for g in fr["groups"]:
        a(f"| {g['group']} | {g['n']} | {g['selection_rate']:.3f} | "
          f"{g['tpr']:.3f} | {g['fpr']:.3f} | {g['base_rate']:.3f} |")
    a("")
    a(f"_{fr['note']}_")
    a("")
    a("## Assumptions")
    for x in card.assumptions:
        a(f"- {x}")
    a("")
    a("## Limitations")
    for x in card.limitations:
        a(f"- {x}")
    a("")
    a("## Governance")
    for k, v in card.governance.items():
        a(f"- **{k}:** {v}")
    a("")
    return "\n".join(lines)


def _pdf_safe(text: str) -> str:
    """fpdf2 core fonts are latin-1; drop anything outside it."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def render_pdf(card: ModelCard, path: str | Path) -> Path:
    from fpdf import FPDF

    path = Path(path)
    # Create the parent, because the caller's directory may not exist. The UI
    # writes under `runtime/`, which is gitignored and therefore absent from the
    # deploy bundle: every local checkout has one and prod never did, so the
    # Registry's model-card download raised FileNotFoundError on the live site
    # while passing every test. Fixed here rather than at the call site so the
    # CLI (scripts/generate_model_card.py) cannot hit it either.
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    epw = pdf.w - 2 * pdf.l_margin

    def h1(text: str) -> None:
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(epw, 8, _pdf_safe(text))
        pdf.ln(1)

    def h2(text: str) -> None:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 60, 120)
        pdf.multi_cell(epw, 6, _pdf_safe(text))
        pdf.set_text_color(20, 20, 20)

    def body(text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(epw, 5, _pdf_safe(text))

    def bullet(text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(epw, 5, _pdf_safe(f"  - {text}"))

    def kv_row(k: str, v: str) -> None:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(45, 6, _pdf_safe(k), border=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _pdf_safe(v), border=1, new_x="LMARGIN", new_y="NEXT")

    h1(f"Model Card: {card.model_name}")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    body(f"Model ID: {card.model_id}   Version: {card.model_version}   "
         f"Generated: {card.generated_at or 'n/a'}")
    body(f"Question: {card.question}")
    pdf.set_text_color(20, 20, 20)

    h2("Purpose")
    body(card.purpose)
    h2("Intended use")
    body(card.intended_use)
    for x in card.out_of_scope_use:
        bullet(f"Out of scope: {x}")

    h2("Data lineage")
    dl = card.data_lineage
    kv_row("Dataset", f"{dl['dataset']} ({dl['version']})")
    kv_row("Rows / features", f"{dl['n_rows']} rows, {dl['n_features_used']} features")
    kv_row("Class balance", f"{dl['class_balance']} (default {dl['default_rate']})")
    pdf.ln(1)
    for t in dl["transforms"]:
        bullet(t)

    h2("Methodology")
    me = card.methodology
    kv_row("Algorithm", me["algorithm"])
    kv_row("Target", me["target"])
    kv_row("Validation", f"{me['validation']} (seed {me['seed']})")

    h2("Performance (held-out test)")
    for k, v in card.performance["metrics"].items():
        kv_row(k, str(v))
    c = card.performance["confusion_matrix"]
    kv_row("Confusion", f"TN={c['tn']} FP={c['fp']} FN={c['fn']} TP={c['tp']}")
    pdf.ln(1)
    body("Top features by |coefficient|:")
    for f in card.performance["top_features"][:6]:
        bullet(f"{f['name']}  {f['coefficient']:+.3f}  ({f['direction']})")

    h2("Fairness assessment")
    fr = card.fairness
    kv_row("Protected attribute", f"{fr['protected_attribute']} (excluded)")
    kv_row("Disparity ratio",
           f"{fr['disparity_ratio']} (threshold {fr['threshold']}) - {fr['verdict']}")
    pdf.ln(1)
    # group table header
    pdf.set_font("Helvetica", "B", 8)
    widths = [30, 18, 32, 30, 30, 30]
    headers = ["Group", "n", "Selection rate", "TPR", "FPR", "Base rate"]
    for w, hd in zip(widths, headers, strict=True):
        pdf.cell(w, 6, _pdf_safe(hd), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for g in fr["groups"]:
        cells = [
            g["group"], str(g["n"]), f"{g['selection_rate']:.3f}",
            f"{g['tpr']:.3f}", f"{g['fpr']:.3f}", f"{g['base_rate']:.3f}",
        ]
        for w, val in zip(widths, cells, strict=True):
            pdf.cell(w, 6, _pdf_safe(val), border=1)
        pdf.ln()
    pdf.ln(1)
    body(fr["note"])

    h2("Assumptions")
    for x in card.assumptions:
        bullet(x)
    h2("Limitations")
    for x in card.limitations:
        bullet(x)
    h2("Governance")
    for k, v in card.governance.items():
        bullet(f"{k}: {v}")

    pdf.output(str(path))
    return path
