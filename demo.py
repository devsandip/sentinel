"""End-to-end demo of the governed pipeline from the terminal.

Usage:
    uv run python demo.py                       # build_model, scripted, approve
    uv run python demo.py --question fairness_age
    uv run python demo.py --reject
"""

from __future__ import annotations

import argparse

from sentinel.orchestrator import Orchestrator


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default="build_model")
    ap.add_argument("--mode", default="scripted", choices=["scripted", "live"])
    ap.add_argument("--reject", action="store_true")
    args = ap.parse_args()

    orch = Orchestrator()
    state = orch.start_run(args.question, narration_mode=args.mode)

    print("=" * 70)
    print(f"RUN {state.run_id}  |  {state.question_label}")
    print(f"Governance: ON  ({', '.join(state.to_public_dict()['governance_controls'])})")
    print("=" * 70)
    for s in state.steps:
        tag = "LIVE" if s.live else "scripted"
        print(f"[{s.status:>16}] {s.title} ({tag})")
        print(f"    {s.narration}")
    print("-" * 70)
    print(f">>> PAUSED: {state.status}. Human decision required.")

    approved = not args.reject
    print(f">>> Human {'APPROVES' if approved else 'REJECTS'} the model.\n")
    orch.approve(state.run_id, approved=approved)

    pub = state.to_public_dict()
    if approved:
        for s in state.steps[3:]:
            print(f"[{s.status:>16}] {s.title}")
            print(f"    {s.narration}")
        print(f"    summary: {state.shared.get('summary_narration', '')}")
        print("-" * 70)
        m = pub["model"]["metrics"]
        fr = pub["fairness"]
        ev = pub["evals"]
        print(f"Final status: {pub['status'].upper()}")
        print(f"  AUC {m['auc']}  accuracy {m['accuracy']}")
        print(f"  Fairness disparity {fr['disparity_ratio']} "
              f"(threshold {fr['threshold']}) -> "
              f"{'PASS' if fr['passes'] else 'FLAG'}")
        print(f"  Eval gate: {ev['passed']}/{ev['passed'] + ev['failed']} "
              f"-> {'PROMOTED' if ev['promoted'] else 'BLOCKED'}")
    else:
        print(f"Final status: {pub['status'].upper()}")

    print("-" * 70)
    c = pub["cost"]
    print(f"Cost/KPIs: tokens={c['tokens']} cost=${c['cost_usd']} "
          f"cycle={c['cycle_time_s']}s eval_pass_rate={c['eval_pass_rate']} "
          f"human_overrides={c['human_overrides']}")
    print("-" * 70)
    print("Audit trail:")
    for e in pub["audit"]:
        flag = {"blocked": "[BLOCK]", "redaction": "[REDACT]", "gate": "[GATE]"}.get(
            e["level"], "       "
        )
        print(f"  {flag} {e['agent']:>14}  {e['action']:<22} {e['output_summary']}")


if __name__ == "__main__":
    main()
