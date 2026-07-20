"""The code-generation prompt: what the model is told it may write (Stage 4).

The model is given the question, the granted column list, and the fenced API. It
is not given the dataset, a network, or a filesystem. Generating is not
dangerous; running is, and the gate reads the code before anything runs. The
prompt teaches the fence so a cooperative model stays inside it; the gate is the
backstop for when it does not.

The same discipline applies to the result. The allowlist, the SQL rules and the
result contract are interpolated from the modules that enforce them rather than
restated here, so a prompt that teaches one fence and a platform that checks
another cannot drift apart. That drift is exactly what broke the live path
before v11: the prompt asked for a count column, the platform required a count
column *and* a selection-rate column, and nothing reconciled the two.

The other half of that defect was a fence the prompt never mentioned at all.
`ctx.sql` has been gated by sqlglot since v2, but it was absent from this
prompt, so a live model wrote pandas for every question -- including the two the
UI offers *because* they ask for SQL. The sqlglot half of the gate could not fire
on a live run, and the "SELECT * refused by the SQL gate" demo quietly became a
pandas run that nothing refused. An unreachable control is not a control.
"""

from __future__ import annotations

from ..codegen.allowlist import ALLOWED_IMPORTS
from ..codegen.result_contract import contract_clause
from ..codegen.sql_gate import sql_clause

SYSTEM_PROMPT = """You are a data-science code generator inside a governed bank platform.
You write a single short Python analysis that runs inside a fence. You never see \
the data; you write code that the platform runs for you.

Rules, enforced by a static gate that reads your code before it runs:
- Use ONLY the `ctx` API to reach data and return results:
    df = ctx.table(name)     # a pandas DataFrame, already scoped to granted columns
    df = ctx.sql(query)      # a SQL read of the same scoped table (see below)
    v  = ctx.param(name)     # a typed parameter from the analysis spec
    ctx.emit(df)             # the ONLY way to return a result (see the result contract)
- Import ONLY from this allowlist: {allowlist}.
- No network of any kind (no requests, urllib, httpx, sockets).
- No filesystem or process access (no os, sys, subprocess, pathlib, open in write mode).
- No eval, exec, compile, __import__, importlib, pickle.
- Reference ONLY the granted columns. Do not select columns you were not granted.

{sql}

{contract}

Output only the Python code. No prose, no markdown fences."""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(
        allowlist=", ".join(sorted(ALLOWED_IMPORTS)),
        sql=sql_clause(),
        contract=contract_clause(),
    )


def build_user_prompt(
    question: str,
    table: str,
    granted_columns: list[str],
    protected_attribute: str,
    analysis: str,
) -> str:
    """The per-request instruction: the question and the exact scope it runs in.

    The contract is repeated here against the actual protected attribute, because
    the question is free text and can pull the analysis away from the shape the
    platform reads. "Does the model decline older applicants more often, holding
    income constant?" invites a regression whose output is a coefficient table;
    the answer still has to arrive as one row per band.
    """
    cols = ", ".join(granted_columns)
    return (
        f"Question: {question}\n"
        f"Analysis: {analysis}\n"
        f"Table: ctx.table({table!r}), or in SQL: FROM {table}\n"
        f"Granted columns (the only columns that exist on the table): {cols}\n"
        f"Protected attribute for fairness: {protected_attribute}\n"
        f"Write the analysis. Answer the question, but the result you emit must be "
        f"the grouped table below, one row per {protected_attribute}. Put any "
        f"further work (adjusted odds, controls, tests) in extra columns on that "
        f"same table.\n"
        + contract_clause(protected=protected_attribute)
    )
