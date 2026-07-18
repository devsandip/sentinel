"""The L1 route: pick a certified analysis, fill typed params, write no code (4.5).

At L2 the model writes code and a static gate reads it before it runs. At L1 the
model does not write code at all: it selects a certified analysis and fills its
typed parameters, and the human reviews the parameters, not code. There is
nothing to statically gate because nothing was generated; the safety comes from
the analysis being pre-certified and the parameters being typed and bounded.

This module is the certified fair-lending selection-rate analysis as fixed,
reviewed code plus its editable parameters. The engine runs it in-process,
because it is trusted platform code rather than model-written code; the sandbox
and its wall-clock control exist to contain the untrusted L2/L3 path, not this
one. The output schema is the same grouped table (a band column, `selection_rate`,
and an `n` count) the Screen, narration, and evidence pack already consume.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..analyses.spec import P_CHOICE, P_INT, ParamSpec

# The certified analysis L1 binds. Same id the registry certifies and Plan binds
# for fair lending, so L1 and L2 draw on the same certified lineage.
L1_ANALYSIS_ID = "fair-lending"

# The typed, bounded parameters the model fills at L1. These are the reviewed
# surface: an analyst (or a reviewer) checks these values, not code.
L1_PARAMS: tuple[ParamSpec, ...] = (
    ParamSpec(
        name="min_band_size",
        label="Minimum band size",
        kind=P_INT,
        default=0,
        minimum=0,
        maximum=500,
        help=(
            "Drop age bands with fewer than this many applicants before the "
            "analysis reports them. An analyst focus knob, distinct from the "
            "disclosure floor, which is a privacy control applied later at Screen."
        ),
    ),
    ParamSpec(
        name="sort_by",
        label="Sort output by",
        kind=P_CHOICE,
        default="age_band",
        choices=("age_band", "selection_rate"),
        help="Order the resulting bands by label or by selection rate.",
    ),
)


def resolve_l1_params(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate and coerce the L1 parameters (typed, bounded, defaulted)."""
    overrides = dict(overrides or {})
    unknown = set(overrides) - {p.name for p in L1_PARAMS}
    if unknown:
        raise ValueError(f"unknown L1 parameter(s): {', '.join(sorted(unknown))}")
    return {p.name: p.coerce(overrides.get(p.name)) for p in L1_PARAMS}


def run_l1_analysis(scoped: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    """The certified analysis: selection rate by age band, with typed params.

    Fixed, reviewed code. The model chose to run this and supplied the params; it
    did not write this. Returns the grouped table the Screen expects.
    """
    g = (
        scoped.groupby("age_band")
        .agg(selection_rate=("pred", "mean"), n=("pred", "size"))
        .reset_index()
    )
    min_band = int(params.get("min_band_size", 0))
    if min_band > 0:
        g = g[g["n"] >= min_band]
    if params.get("sort_by") == "selection_rate":
        g = g.sort_values("selection_rate", ascending=False)
    else:
        g = g.sort_values("age_band")
    return g.reset_index(drop=True)


def l1_code_descriptor(params: dict[str, Any]) -> str:
    """A short, honest stand-in for the 'code' of an L1 run, for the evidence pack
    and the notebook. No code was generated; this records what was chosen."""
    kv = ", ".join(f"{k}={v!r}" for k, v in params.items())
    return (
        f"# L1 route: no code was generated.\n"
        f"# The model selected the certified analysis {L1_ANALYSIS_ID!r} and filled\n"
        f"# typed parameters, which are the reviewed surface at L1:\n"
        f"#   {kv}\n"
        f"# The analysis itself is pre-certified platform code (see govflow/l1.py)."
    )
