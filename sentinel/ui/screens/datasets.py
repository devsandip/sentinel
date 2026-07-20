"""The Datasets screen and a dataset's data contract.

The contract is a drill-down, not a nav item: it publishes schema, roles,
relationships and provenance, and deliberately no values. Anything computed
from values is data access and belongs to the governed profiling analysis."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import html

import streamlit as st

from sentinel.datasets import all_datasets, get_dataset, role_note, schema
from sentinel.datasets import available as dataset_available
from sentinel.govflow.purpose_matrix import PURPOSE_LABEL, PURPOSES, matrix_rows
from sentinel.govflow.tiers import CLASSIFICATION_CEILING
from sentinel.ui.govflow import (
    cls_label,
    control_popover,
    purpose_extra,
)
from sentinel.ui.shell import classification_of, nav_to
from sentinel.ui.tables import table_head, table_row, td

_DS_COLS = (2.0, 2.8, 1.9, 1.0, 0.8, 1.8, 1.2, 1.2, 1.6)


_DS_HEAD = (
    "id",
    "name",
    "classification",
    "rows",
    "tables",
    "license",
    "commercial",
    "onboarded",
    "",
)




def _open_contract(ds_id: str) -> None:
    st.session_state.ds_contract = ds_id




def render_datasets() -> None:
    # The registry is the list; the contract is the detail. Same screen, so the
    # sidebar nav item stays lit and the app's Back stack is not spent on a
    # drill-down that belongs to this page.
    if st.session_state.get("ds_contract"):
        render_dataset_contract(st.session_state.ds_contract)
        return
    st.subheader("Dataset registry")
    st.markdown(
        "<span class='muted'>The onboarded-dataset inventory. Each dataset carries "
        "its classification (which sets the autonomy ceiling), its license (and a "
        "commercial-use flag the platform enforces), the capabilities it provides, "
        "and its provenance. Analyses match against these via data "
        "contracts.</span>",
        unsafe_allow_html=True,
    )
    # The class-count breakdown row above the table (ui-spec 3.4), same chips
    # the dashboard tile uses.
    counts: dict[str, int] = {}
    for d in all_datasets():
        cls = classification_of(d.id)
        counts[cls] = counts.get(cls, 0) + 1
    st.markdown(
        "".join(
            f"<span class='cls {name.lower()}'>{name} {counts[name]}</span> "
            for name in ("Restricted", "Confidential", "Internal", "Public")
            if name in counts
        ),
        unsafe_allow_html=True,
    )
    table_head(_DS_HEAD, _DS_COLS, "ds")
    for d in all_datasets():
        classification = classification_of(d.id)
        cols = table_row(_DS_COLS, f"ds_{d.id}")
        td(cols[0], d.id, mono=True)
        td(cols[1], d.name)
        with cols[2]:
            # The classification is the one cell here that is a governance
            # decision rather than a fact about the file, so it is the cell that
            # explains itself: same CTL-PURP-01 popover as the topbar Data chip,
            # carrying this dataset's ceiling and permitted purposes.
            control_popover(
                "CTL-PURP-01",
                label=cls_label(classification) if classification else "n/a",
                key=f"dscls_{d.id}",
                extra=purpose_extra(d.id),
            )
        td(cols[3], f"{d.rows:,}", num=True)
        td(cols[4], d.tables, num=True)
        td(cols[5], d.license)
        cols[6].markdown(
            "<span class='badge ok'>yes</span>"
            if d.commercial_ok
            else "<span class='badge danger'>flagged</span>",
            unsafe_allow_html=True,
        )
        cols[7].markdown(
            "<span class='badge ok'>yes</span>"
            if dataset_available(d.id)
            else "<span class='badge neutral'>registered</span>",
            unsafe_allow_html=True,
        )
        cols[8].button(
            "Contract",
            key=f"dsopen_{d.id}",
            use_container_width=True,
            on_click=_open_contract,
            args=(d.id,),
            help="Schema, column dictionary, roles and relationships. Metadata "
            "only: no values.",
        )
    st.caption(
        "All 8 registered datasets ship onboarded (scripts/onboard_datasets.py "
        "produces their local files). 'flagged' commercial status means the "
        "license restricts commercial use and the platform blocks it; no control "
        "id is claimed for it, because the enforcement lives in the dataset "
        "registry rather than in the control catalogue."
    )




_UNDOC = "<span class='undoc'>not documented</span>"




def _compact(n: int) -> str:
    """A row count that fits a metric tile. 2,260,000 truncates to '2,260,...'
    at this tile width, which reads as broken rather than as a big number."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M".replace(".00M", "M")
    return f"{n:,}"




def _role_chip(role: str) -> str:
    return f"<span class='role {html.escape(role)}'>{html.escape(role)}</span>"




def _role_legend(sch) -> str:  # noqa: ANN001
    """What each role in this dataset costs a requester at Access, once.

    The consequence belongs next to the chip that carries it, but repeating it
    on every protected column turns a dictionary into a lecture. One legend,
    listing only the roles this dataset actually uses.
    """
    seen: list[str] = []
    for table in sch.tables:
        for col in table.columns:
            if col.role not in seen:
                seen.append(col.role)
    return "<div class='rleg'>" + "".join(
        f"<div class='r'>{_role_chip(r)}"
        f"<span class='v'>{html.escape(role_note(r))}</span></div>"
        for r in seen
    ) + "</div>"




def _dict_table(table) -> str:  # noqa: ANN001
    """The column dictionary for one table, as one HTML table.

    There is deliberately no value column, no example, and no distribution. A
    reader learns what a column *is* and what requesting it will cost them at
    Access; what it *contains* is data, and data needs a purpose.
    """
    rows = []
    for c in table.columns:
        drv = "<span class='drv'>derived</span>" if c.derived else ""
        desc = html.escape(c.description) if c.documented else _UNDOC
        rows.append(
            f"<tr><td class='cn'>{html.escape(c.name)}{drv}</td>"
            f"<td class='ty'>{html.escape(c.dtype)}</td>"
            f"<td>{_role_chip(c.role)}</td>"
            f"<td>{desc}</td></tr>"
        )
    return (
        "<table class='dict'><thead><tr><th>column</th><th>type</th><th>role</th>"
        "<th>description</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )




def _close_contract() -> None:
    st.session_state.ds_contract = ""




def render_dataset_contract(ds_id: str) -> None:
    """The data contract for one dataset: schema, dictionary, roles, foreign
    keys, and the purposes the matrix permits on it.

    This is a catalogue, not a data browser, and the distinction is the whole
    point. A bank publishes metadata far more widely than data: you read the
    catalogue to decide what to ask for, then declare a purpose to get values.
    An "explore the data" button on this page would hand out values with no
    declared purpose, no resolved tier, no column grant and no disclosure
    screen, quietly undoing four controls the rest of the app spends its time
    proving. So the page shows the contract, and the route to values is the Run
    flow, where those controls are.
    """
    spec = get_dataset(ds_id)
    if spec is None:
        st.error(f"Unknown dataset {ds_id!r}.")
        st.button("Back to registry", on_click=_close_contract)
        return

    sch = schema(ds_id)
    classification = classification_of(ds_id)
    ceiling = CLASSIFICATION_CEILING.get(classification, "n/a")

    st.button(
        "Dataset registry",
        key="ds_contract_back",
        icon=":material/arrow_back:",
        on_click=_close_contract,
    )
    st.subheader(f"Data contract · {spec.name}")
    st.markdown(
        f"<span class='muted'><code>{html.escape(ds_id)}</code> · "
        f"{html.escape(spec.license)} · "
        f"<a href='{html.escape(spec.source_url)}'>provenance</a></span>",
        unsafe_allow_html=True,
    )
    if spec.notes:
        st.markdown(
            f"<span class='muted'>{html.escape(spec.notes)}</span>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div class='cnotice'><b>Metadata only.</b> This page publishes the "
        "schema, the column dictionary, roles and foreign keys. It shows no cell "
        "values, no distributions and no samples, because reading values is data "
        "access and data access needs a declared purpose "
        "(<span class='ids'>CTL-PURP-01</span>), a resolved autonomy tier, a "
        "column grant (<span class='ids'>CTL-COL-01</span>) and a disclosure "
        "screen (<span class='ids'>CTL-DISC-02</span>). Read the contract here; "
        "request the values in Run.</div>",
        unsafe_allow_html=True,
    )

    if not sch.onboarded:
        st.warning(
            "Registered but not onboarded: the local file is not present, so the "
            "schema cannot be published yet. Run "
            f"`uv run python scripts/onboard_datasets.py {ds_id}`."
        )
        return

    local_rows = sum(t.rows for t in sch.tables)
    m = st.columns(5)
    m[0].metric("Rows at source", _compact(spec.rows))
    m[1].metric("Tables", len(sch.tables))
    m[2].metric("Columns", sch.n_columns)
    m[3].metric("Documented", f"{sch.coverage:.0%}")
    m[4].metric("Sensitive columns", len(sch.sensitive_columns()))
    if local_rows != spec.rows:
        # The registry counts the source; the file on disk is a sample for the
        # big sets. Publishing both is the honest option, and a row count is a
        # shape fact, not a value.
        st.caption(
            f"Onboarded as a sample: {local_rows:,} rows locally against "
            f"{spec.rows:,} at source. Analyses run on the sample."
        )
    st.markdown(
        f"<div class='cov'><i style='width:{sch.coverage * 100:.0f}%'></i></div>"
        f"<span class='muted'>{sch.n_documented} of {sch.n_columns} columns carry a "
        "description. Coverage is reported rather than smoothed over: an "
        "undocumented column is one nobody can request responsibly, so the gap is "
        "a governance metric, not a cosmetic one.</span>",
        unsafe_allow_html=True,
    )

    st.markdown("**What this dataset may be used for**")
    row = next((r for r in matrix_rows() if r["dataset"] == ds_id), {})
    st.markdown(
        "<div class='pgrid'>"
        + "".join(
            f"<span class='pcell {'allow' if row.get(p) else 'deny'}'>"
            f"<span class='mk'>{'✓' if row.get(p) else '✕'}</span>"
            f"{html.escape(PURPOSE_LABEL[p])}</span>"
            for p in PURPOSES
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='muted'>Classified <b>{html.escape(classification)}</b>, which "
        f"caps autonomy on this data at <b>{html.escape(ceiling)}</b> however "
        "trusted the requester is. A refused purpose is refused at Access before "
        "any code is generated: same person, same role, different reason, "
        "different answer.</span>",
        unsafe_allow_html=True,
    )

    if len(sch.tables) > 1:
        st.markdown("**Tables**")
        st.markdown(
            "<table class='dict'><thead><tr><th>table</th><th>rows</th>"
            "<th>columns</th><th>description</th></tr></thead><tbody>"
            + "".join(
                f"<tr><td class='cn'>{html.escape(t.name)}</td>"
                f"<td class='ty'>{t.rows:,}</td>"
                f"<td class='ty'>{len(t.columns)}</td>"
                f"<td>{html.escape(t.description) or _UNDOC}</td></tr>"
                for t in sch.tables
            )
            + "</tbody></table>",
            unsafe_allow_html=True,
        )

    if sch.relationships:
        st.markdown("**Relationships**")
        st.markdown(
            "".join(
                f"<div class='fk'><span class='e'>"
                f"{html.escape(r.from_table)}.{html.escape(r.from_column)}"
                f"<span class='ar'>-&gt;</span>"
                f"{html.escape(r.to_table)}.{html.escape(r.to_column)}</span>"
                f"<span class='c'>{html.escape(r.cardinality)}</span>"
                + (f"<span class='n'>{html.escape(r.note)}</span>" if r.note else "")
                + "</div>"
                for r in sch.relationships
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "Foreign keys as the catalogue publishes them. A join is where "
            "minimisation leaks: two individually harmless tables can re-identify "
            "a person once joined, which is why the relationship map is metadata "
            "an analyst should see before requesting either side."
        )

    st.markdown("**Column dictionary**")
    st.markdown(_role_legend(sch), unsafe_allow_html=True)
    if len(sch.tables) > 1:
        for t in sch.tables:
            with st.expander(f"{t.name} · {len(t.columns)} columns · {t.rows:,} rows"):
                st.markdown(_dict_table(t), unsafe_allow_html=True)
    else:
        st.markdown(_dict_table(sch.tables[0]), unsafe_allow_html=True)

    # Table-qualified, because on a relational dataset a bare `account` or
    # `birth_number` does not say which table it is a risk in.
    qualified = [
        f"{t.name}.{c.name}" if len(sch.tables) > 1 else c.name
        for t in sch.tables
        for c in t.columns
        if c.role in ("pii", "protected")
    ]
    if qualified:
        n = len(qualified)
        st.caption(
            f"{n} column{'' if n == 1 else 's'} carr{'ies' if n == 1 else 'y'} a "
            "PII or protected role: "
            + ", ".join(f"`{q}`" for q in qualified)
            + ". PII is never granted and is redacted before any text reaches a "
            "model; a protected attribute is granted only to the purpose whose "
            "axis it is, and is excluded from model features."
        )

    st.divider()
    st.markdown("**To see values, take this dataset through a control**")
    a, b = st.columns(2)
    # Imperative rather than on_click: nav_to reruns, and a rerun belongs in
    # the script body, not in a widget callback.
    if a.button(
        "Declare a purpose in Run",
        key="ds_contract_to_run",
        icon=":material/play_arrow:",
        use_container_width=True,
        help="The governed route: declare a purpose, resolve a tier, take the "
        "column grant, and let the disclosure screen run on the output.",
    ):
        _close_contract()
        nav_to("Run")
    if b.button(
        "Profile it under governance",
        key="ds_contract_to_analyses",
        icon=":material/query_stats:",
        use_container_width=True,
        help="The data_profiling analysis computes distributions, missingness "
        "and cardinality as a certified analysis, audited and gated.",
    ):
        _close_contract()
        nav_to("Analyses")
    st.caption(
        "Missingness, cardinality and distributions look like metadata but are "
        "computed from values, so they are profile outputs rather than catalogue "
        "entries. The catalogue knows the shape; the profile knows the contents; "
        "only the profile is data access."
    )
