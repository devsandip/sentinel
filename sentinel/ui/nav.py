"""The sidebar's groups, keys and icons: one definition, two readers.

This lived in `app.py` until the manual had to describe it. The manual's screens
chapter opened with "Nine screens in the sidebar", typed by hand, which is the
shape of drift this build keeps finding in itself: a screen keeping its own copy
of what another module does. Adding a tenth nav item made the sentence false and
nothing failed. It is computed from this list now, so the sentence cannot be
wrong again.

Two things are deliberately not in here. Drill-downs (a dataset's contract, a
run's audit detail, a template's editor) are reachable by opening a row and are
not nav items, so counting them as screens would overstate the sidebar. And the
`Deploy` action in the topbar is a control, not a destination.
"""

from __future__ import annotations

from .agent_templates import SECTION as SECTION_TEMPLATES

# The grouped sidebar (ui-spec 2.2): Overview, then Workspace / Governance /
# Platform groups, and Help last. Buttons write st.session_state.section; the
# active item renders as the primary variant (styled as the nav active state).
# Help sits at the bottom because it is a reference surface, not a step in any
# workflow: nothing in the product routes through it, and putting it above
# Platform would imply otherwise.
NAV_GROUPS: list[tuple[str | None, list[str]]] = [
    (None, ["Overview"]),
    ("Workspace", ["Run", "Analyses"]),
    # Governance reads in lifecycle order: the data you may use, the blueprint
    # you build from, the inventory of what got built.
    ("Governance", ["Datasets", SECTION_TEMPLATES, "Registry"]),
    ("Platform", ["Platform", "Adoption", "Audit Log"]),
    ("Help", ["User Manual", "FAQ", "Ask me"]),
]

NAV_KEYS: dict[str, str] = {
    "Overview": "nav_home",
    "Run": "nav_run",
    "Analyses": "nav_analyses",
    "Datasets": "nav_datasets",
    SECTION_TEMPLATES: "nav_templates",
    "Registry": "nav_registry",
    "Platform": "nav_platform",
    "Adoption": "nav_adoption",
    "Audit Log": "nav_auditlog",
    "User Manual": "nav_manual",
    "FAQ": "nav_faq",
    "Ask me": "nav_ask",
}

# Nav icons (ui-spec 2.2, sentinel-stepper-mockup.html sidenav). Material
# Symbols, rounded/outline style, matching the mockup's stroked SVG set:
# home, play, database, verified-check, grid, bar-chart. Analyses is an
# app-only item not in the mockup; it gets the nearest matching glyph (a stats
# magnifier).
NAV_ICONS: dict[str, str] = {
    "Overview": ":material/home:",
    "Run": ":material/play_arrow:",
    "Analyses": ":material/query_stats:",
    "Datasets": ":material/database:",
    SECTION_TEMPLATES: ":material/dashboard_customize:",
    "Registry": ":material/verified:",
    "Platform": ":material/grid_view:",
    "Adoption": ":material/bar_chart:",
    "Audit Log": ":material/gavel:",
    "User Manual": ":material/menu_book:",
    "FAQ": ":material/quiz:",
    "Ask me": ":material/forum:",
}

# Drill-downs: reachable by opening a row, never a nav item. Named here so the
# manual can say how many there are without counting them by hand either.
DRILL_DOWNS: tuple[str, ...] = (
    "a dataset's contract",
    "a single run's audit detail",
    "a template's editor",
)


HELP_GROUP = "Help"


def nav_items() -> list[str]:
    """Every sidebar destination, in sidebar order."""
    return [item for _group, items in NAV_GROUPS for item in items]


def product_screens() -> list[str]:
    """The screens the manual documents: everything outside Help.

    Help is excluded because the manual, the FAQ and Ask me are the manual
    describing itself, and a screens chapter that counted them would be telling
    a reader there are three more places to do work than there are."""
    return [
        item for group, items in NAV_GROUPS if group != HELP_GROUP for item in items
    ]


def screen_count() -> int:
    return len(product_screens())
