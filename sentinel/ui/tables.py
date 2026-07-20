"""Hand-laid catalog tables: a header band plus one `st.columns` row per record.

`st.dataframe` renders every cell as plain text, so a cell can carry neither a
classification chip nor a popover (ui-spec 4.3 and 4.4). These helpers are the
alternative, and they are what lets a cell hold the thing you click to find out
why the cell says what it says.

They live here rather than in `app.py` because the run walkthrough needs the
same table the platform surfaces use: the Ask stage's dataset picker puts a
radio and a classification popover in the same row. The skin is CSS in `app.py`
keyed off the container names (`tblhead_*` / `tblrow_*`), so anything built
with these helpers is styled without further work.
"""

from __future__ import annotations

import html

import streamlit as st


def table_head(labels: tuple[str, ...], widths: tuple[float, ...], key: str) -> None:
    head = st.container(key=f"tblhead_{key}")
    for col, label in zip(
        head.columns(widths, vertical_alignment="center"), labels, strict=True
    ):
        col.markdown(f"<span class='th'>{label}</span>", unsafe_allow_html=True)


def table_row(widths: tuple[float, ...], key: str) -> list:
    row = st.container(key=f"tblrow_{key}")
    return row.columns(widths, vertical_alignment="center")


def td(col, value: object, mono: bool = False, num: bool = False) -> None:  # noqa: ANN001
    cls = "td mono" if mono or num else "td"
    style = "text-align:right" if num else ""
    col.markdown(
        f"<span class='{cls}' style='{style}'>{html.escape(str(value))}</span>",
        unsafe_allow_html=True,
    )
