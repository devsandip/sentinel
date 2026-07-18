"""The `sentinel` CLI. The scaffold is the only path to an agent (section 10.6).

    sentinel new-agent cohort-retention --template read-only-analysis
    sentinel registry
    sentinel certify deposit-elasticity --validator dana.okafor

`new-agent` writes the spec/test/eval stubs and registers a draft entry, printing
the gates it cannot yet pass. `registry` lists every agent with its computed
status pill. `certify` assigns an independent validator and reports the recomputed
decision, refusing a self-signoff with CTL-SOD-01.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .platform.certification import (
    CertificationError,
    all_entries,
    assign_validator,
    evaluate,
    get_entry,
)
from .platform.scaffold import TEMPLATES, ScaffoldError, scaffold_agent


def _cmd_new_agent(args: argparse.Namespace) -> int:
    try:
        result = scaffold_agent(
            args.name,
            args.template,
            base_dir=Path(args.into),
            author=args.author,
        )
    except ScaffoldError as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 2
    print(result.report())
    return 0


def _cmd_registry(_: argparse.Namespace) -> int:
    for entry in all_entries():
        decision = evaluate(entry)
        print(f"  {decision.status:10s} {entry.label():28s} owner={entry.owner}")
    return 0


def _cmd_certify(args: argparse.Namespace) -> int:
    entry = get_entry(args.agent)
    if entry is None:
        print(f"error: no registry entry {args.agent!r}", file=sys.stderr)
        return 2
    try:
        decision = assign_validator(entry, args.validator)
    except CertificationError as ex:
        print(f"refused: {ex}", file=sys.stderr)
        return 1
    print(decision.summary())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel", description="Sentinel governance CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    new_agent = sub.add_parser("new-agent", help="scaffold a new analysis-agent (draft)")
    new_agent.add_argument("name", help="agent id, e.g. cohort-retention")
    new_agent.add_argument(
        "--template", default="read-only-analysis", choices=sorted(TEMPLATES),
        help="scaffold template",
    )
    new_agent.add_argument("--author", default="UNKNOWN", help="the scaffolding author")
    new_agent.add_argument(
        "--into", default=".", help="repo root to write files under (default: cwd)"
    )
    new_agent.set_defaults(func=_cmd_new_agent)

    registry = sub.add_parser("registry", help="list agents and their certification status")
    registry.set_defaults(func=_cmd_registry)

    certify = sub.add_parser("certify", help="assign an independent validator to an agent")
    certify.add_argument("agent", help="registry entry id")
    certify.add_argument("--validator", required=True, help="the independent validator")
    certify.set_defaults(func=_cmd_certify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
