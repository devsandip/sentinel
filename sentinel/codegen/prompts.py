"""The code-generation prompt: what the model is told it may write (Stage 4).

The model is given the question, the granted column list, and the fenced API. It
is not given the dataset, a network, or a filesystem. Generating is not
dangerous; running is, and the gate reads the code before anything runs. The
prompt teaches the fence so a cooperative model stays inside it; the gate is the
backstop for when it does not.
"""

from __future__ import annotations

from ..codegen.allowlist import ALLOWED_IMPORTS

SYSTEM_PROMPT = """You are a data-science code generator inside a governed bank platform.
You write a single short Python analysis that runs inside a fence. You never see \
the data; you write code that the platform runs for you.

Rules, enforced by a static gate that reads your code before it runs:
- Use ONLY the `ctx` API to reach data and return results:
    df = ctx.table(name)     # a pandas DataFrame, already scoped to granted columns
    v  = ctx.param(name)     # a typed parameter from the analysis spec
    ctx.emit(obj)            # the ONLY way to return a result (a DataFrame or dict)
- Import ONLY from this allowlist: {allowlist}.
- No network of any kind (no requests, urllib, httpx, sockets).
- No filesystem or process access (no os, sys, subprocess, pathlib, open in write mode).
- No eval, exec, compile, __import__, importlib, pickle.
- Reference ONLY the granted columns. Do not select columns you were not granted.
- Return exactly one result via ctx.emit. For a grouped result, emit a DataFrame \
with a group column and an integer count column named 'n'.

Output only the Python code. No prose, no markdown fences."""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(allowlist=", ".join(sorted(ALLOWED_IMPORTS)))


def build_user_prompt(
    question: str,
    table: str,
    granted_columns: list[str],
    protected_attribute: str,
    analysis: str,
) -> str:
    """The per-request instruction: the question and the exact scope it runs in."""
    cols = ", ".join(granted_columns)
    return (
        f"Question: {question}\n"
        f"Analysis: {analysis}\n"
        f"Table: ctx.table({table!r})\n"
        f"Granted columns (the only columns that exist on the table): {cols}\n"
        f"Protected attribute for fairness: {protected_attribute}\n"
        "Write the analysis. Group by the protected attribute where relevant and "
        "emit a DataFrame with a count column named 'n'."
    )
