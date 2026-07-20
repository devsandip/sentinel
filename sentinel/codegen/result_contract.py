"""The result contract: the shape Execute requires, written down once.

The gate says what generated code may *do*. This says what it must *return*.
Until v11 only the first half was written down. The prompt asked for "a count
column named 'n'", the flow then required a DataFrame with `n` on it, and the
Interpret stage silently required a `selection_rate` column on top of that. Three
different contracts, none of them stated in full to the model, with no feedback
path between them. Scripted mode never noticed because the canned sample was
written against the checks; live mode failed on both halves at once. A model that
emitted a dict, a MultiIndex from `.agg({...})`, the raw table, or a count column
called `count` died at Execute with "emitted result must be a DataFrame with an
'n' count column" and no retry. A model that got `n` right but called the rate
`decline_rate` or `approval_rate` -- which every sampled live generation did,
because the question does not contain the words "selection rate" -- completed a
run whose narration read "no comparable groups after screening". A mute run and a
dead run from the same missing sentence.

So the contract lives here, in one object, and is used twice: `contract_clause()`
is interpolated verbatim into the codegen prompt, and `check_result()` enforces
the same thing after the sandbox returns. Prompt and check cannot drift, for the
same reason the import allowlist is interpolated rather than restated.

Nothing here rewrites the model's output. Renaming `count` to `n` on the model's
behalf would be a silent transform inside a platform whose whole argument is that
transforms are visible, so a miss is fed back to the model as feedback and
regenerated (the Stage-5 loop, widened past the gate) or reported as a failure.
The platform does not quietly fix the result; it asks again, in public.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# The two columns the platform reads off a grouped fair-lending result. `n` is
# what the Screen stage suppresses on (CTL-DISC-02); `selection_rate` is what the
# Interpret stage narrates and the evidence pack states a finding about.
COUNT_COLUMN = "n"
RATE_COLUMN = "selection_rate"


def group_column(df: pd.DataFrame, count_col: str = COUNT_COLUMN) -> str | None:
    """The band column of a grouped result: the first non-numeric column that is
    not the count. One definition, used by the contract check, the Screen call
    and the narration, so "which column is the band" is answered the same way
    everywhere."""
    for c in df.columns:
        if c != count_col and not pd.api.types.is_numeric_dtype(df[c]):
            return str(c)
    return None


@dataclass(frozen=True)
class ContractResult:
    """The verdict on one emitted result."""

    passed: bool
    violations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "result contract satisfied"
        return "; ".join(self.violations)

    def refusal_summary(self) -> str:
        if self.passed:
            return "Result contract satisfied."
        return "The emitted result does not satisfy the result contract:\n" + "\n".join(
            f"  - {v}" for v in self.violations
        )

    def feedback_for_regeneration(self) -> str:
        """A terse instruction the model can act on, in the shape the gate's
        feedback already takes, so the regenerate loop reads the same either
        way."""
        if self.passed:
            return ""
        return (
            "Your code ran, but the result it emitted is not readable by the "
            "platform. Fix each and regenerate:\n"
            + "\n".join(f"  - {v}" for v in self.violations)
            + "\n"
            + contract_clause()
        )


def _is_integer_valued(s: pd.Series) -> bool:
    if not pd.api.types.is_numeric_dtype(s):
        return False
    if s.isna().any():
        return False
    return bool((s.astype("float64") % 1 == 0).all())


def check_result(
    emitted: Any,
    *,
    count_col: str = COUNT_COLUMN,
    rate_col: str = RATE_COLUMN,
) -> ContractResult:
    """Check what the sandbox emitted against the contract.

    Checks stop where a later one would be meaningless (there is nothing to say
    about the columns of an object that is not a DataFrame), so the feedback the
    model gets names the real problem rather than a cascade from it.
    """
    if emitted is None:
        return ContractResult(
            False,
            [
                "nothing was emitted: call ctx.emit(result) exactly once, with the "
                "grouped DataFrame as the argument"
            ],
        )
    if not isinstance(emitted, pd.DataFrame):
        return ContractResult(
            False,
            [
                f"ctx.emit received a {type(emitted).__name__}; a grouped result must "
                f"be a pandas DataFrame. Emit the frame itself, not a dict wrapping it "
                f"and not a summary of it"
            ],
        )

    if isinstance(emitted.columns, pd.MultiIndex) or any(
        not isinstance(c, str) for c in emitted.columns
    ):
        return ContractResult(
            False,
            [
                "the emitted DataFrame has MultiIndex or non-string column names "
                f"({list(emitted.columns)[:4]}...); flatten them to plain strings. "
                "Prefer named aggregation -- .agg(n=(col, 'size'), "
                f"{rate_col}=(col, 'mean')) -- which never produces a MultiIndex"
            ],
        )

    violations: list[str] = []
    cols = list(emitted.columns)

    if emitted.empty:
        violations.append("the emitted DataFrame has no rows")

    if count_col not in cols:
        violations.append(
            f"no column named {count_col!r}: the group size must be an integer column "
            f"named exactly {count_col!r} (found {cols})"
        )
    elif not _is_integer_valued(emitted[count_col]):
        violations.append(
            f"column {count_col!r} is not an integer count (dtype "
            f"{emitted[count_col].dtype}); it must be the whole number of rows in "
            f"each group"
        )

    if rate_col not in cols:
        violations.append(
            f"no column named {rate_col!r}: the rate under review must be a float "
            f"column named exactly {rate_col!r}, the share of applicants in the band "
            f"the model predicts positive (mean of pred). Name it {rate_col!r} even if "
            f"you also report its complement (found {cols})"
        )
    elif not pd.api.types.is_numeric_dtype(emitted[rate_col]):
        violations.append(
            f"column {rate_col!r} is not numeric (dtype {emitted[rate_col].dtype})"
        )

    if group_column(emitted, count_col) is None:
        violations.append(
            "no group column: emit one row per band, with the band label in its own "
            "non-numeric column (reset_index() after a groupby, so the band is a "
            "column and not the index)"
        )

    return ContractResult(not violations, violations)


def contract_clause(
    count_col: str = COUNT_COLUMN,
    rate_col: str = RATE_COLUMN,
    protected: str = "the protected attribute",
) -> str:
    """The contract in the words the prompt uses. Interpolated verbatim into the
    codegen system prompt, so what the model is told and what the platform checks
    are the same sentence."""
    return (
        "Return exactly one result via ctx.emit(result). It must satisfy this "
        "result contract, which the platform checks after your code runs:\n"
        "  * a pandas DataFrame -- not a dict, not a Series, not a scalar, and not "
        "a dict wrapping the frame\n"
        "  * plain string column names (no MultiIndex; use named aggregation)\n"
        f"  * one row per group of {protected}, with the group label in its own "
        "column\n"
        f"  * an integer count column named exactly {count_col!r} (the group size)\n"
        f"  * a float column named exactly {rate_col!r} (the share of the group the "
        "model predicts positive, i.e. the mean of pred). Use that name even if the "
        "question is phrased as declines or approvals; report the complement as an "
        "extra column if you want it\n"
        "  * any additional columns you find useful are fine\n"
        "Required shape (extra columns may follow these three):\n"
        f"    {protected:<12} | {count_col:<4} | {rate_col}\n"
        f"    {'26-35':<12} | {'190':<4} | 0.62\n"
        f"    {'36-45':<12} | {'154':<4} | 0.71"
    )
