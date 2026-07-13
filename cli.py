"""P1 CLI: run the real analysis and print structured results.

Usage:
    uv run python cli.py                       # default: age_band, seed 42
    uv run python cli.py --protected sex
    uv run python cli.py --seed 7 --json
"""

from __future__ import annotations

import argparse
import json

from sentinel.ml.fairness import compute_fairness
from sentinel.ml.pipeline import run_pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="Sentinel ML core (P1)")
    ap.add_argument(
        "--protected",
        default="age_band",
        choices=["age_band", "sex", "foreign_worker"],
        help="Protected attribute (excluded from model features)",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json", action="store_true", help="Emit raw JSON only")
    args = ap.parse_args()

    result = run_pipeline(protected_attribute=args.protected, seed=args.seed)
    fairness = compute_fairness(protected_attribute=args.protected, seed=args.seed)

    if args.json:
        print(
            json.dumps(
                {"model": result.to_dict(), "fairness": fairness.to_dict()},
                indent=2,
            )
        )
        return

    p = result.profile
    print("=" * 64)
    print("SENTINEL — German Credit default-risk analysis")
    print("=" * 64)
    print(f"Rows: {p.n_rows}  Features used: {p.n_features}  Seed: {args.seed}")
    print(f"Class balance: {p.class_balance}  (default rate {p.positive_rate:.3f})")
    print(f"Protected attribute: {result.protected_attribute} "
          f"(excluded from features: {', '.join(result.excluded_features)})")
    print("-" * 64)
    print("PERFORMANCE (held-out test)")
    for k, v in result.metrics.items():
        print(f"  {k:>10}: {v}")
    c = result.confusion
    print(f"  confusion : tn={c['tn']} fp={c['fp']} fn={c['fn']} tp={c['tp']}")
    print("-" * 64)
    print("TOP FEATURES (|coefficient|)")
    for f in result.top_features[:6]:
        print(f"  {f['coefficient']:+.3f}  {f['name']}  ({f['direction']})")
    print("-" * 64)
    print(f"FAIRNESS across {fairness.protected_attribute}")
    for g in fairness.groups:
        print(
            f"  {g.group:>6}  n={g.n:<4} sel_rate={g.selection_rate:.3f} "
            f"tpr={g.tpr:.3f} fpr={g.fpr:.3f} base={g.base_rate:.3f}"
        )
    verdict = "PASS" if fairness.passes else "FLAG"
    print(f"  disparity ratio: {fairness.disparity_ratio}  "
          f"(threshold {fairness.threshold}) -> {verdict}")
    print("=" * 64)


if __name__ == "__main__":
    main()
