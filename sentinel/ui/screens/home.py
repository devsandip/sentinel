"""The command-center landing (ui-spec 3.2): every tile is a live count."""

from __future__ import annotations

# Imports are absolute rather than the package-relative style used next door in
# sentinel/ui/. This code moved here wholesale from app.py, which is absolute,
# so keeping them meant the move changed no import line and could not silently
# repoint one.
import streamlit as st

from sentinel.datasets import all_datasets
from sentinel.platform import (
    adoption_metrics,
    reuse_metrics,
)
from sentinel.platform.certification import all_entries as cert_entries
from sentinel.ui.shell import nav_to


# --------------------------------------------------------------------------
# Command-center landing (ui-spec 3.2)
# --------------------------------------------------------------------------
def render_home(persona) -> None:  # noqa: ANN001
    """The tile dashboard: four live-number tiles + the Start-a-governed-run CTA.
    Every number comes from the same helpers the surfaces themselves render."""
    from sentinel.govflow import matrix_rows, resolve_tier_for_dataset
    from sentinel.platform.certification import status_of

    st.markdown(
        "<div class='dashhead'><span class='eyebrow'>Governance command center</span>"
        "<div class='h2'>The whole governed platform, at a glance</div>"
        "<div class='lede'>Every surface is a live tile: data under classification, "
        "analyses under certification, agents under templates, adoption trending up. "
        "Start a governed run and watch one request flow through all of it.</div></div>",
        unsafe_allow_html=True,
    )

    tier = resolve_tier_for_dataset(
        "german_credit", persona.tier_role, persona.attestations
    ).tier
    with st.container(border=True):
        cta_l, cta_r = st.columns([8, 3], vertical_alignment="center")
        cta_l.markdown(
            f"<div><div class='cta-t'>Start a governed run</div>"
            f"<div class='cta-d'>german_credit · fair-lending review · resolves to "
            f"{tier} · nine controls arm before any code runs</div></div>",
            unsafe_allow_html=True,
        )
        if cta_r.button(
            "Launch walkthrough →", key="cta_run", type="primary", use_container_width=True
        ):
            nav_to("Run")

    ds = all_datasets()
    cls_counts: dict[str, int] = {}
    for r in matrix_rows():
        cls_counts[r["classification"]] = cls_counts.get(r["classification"], 0) + 1
    cert_status: dict[str, int] = {}
    for entry in cert_entries():
        s = status_of(entry)
        cert_status[s] = cert_status.get(s, 0) + 1
    reuse = reuse_metrics()
    m = adoption_metrics()

    def _tile(col, title, section_target, key, body_html):  # noqa: ANN001
        with col, st.container(border=True):
            h_l, h_r = st.columns([7, 3], vertical_alignment="center")
            h_l.markdown(f"**{title}**")
            if h_r.button("Open →", key=key, use_container_width=True):
                nav_to(section_target)
            st.markdown(body_html, unsafe_allow_html=True)

    cls_chips = "".join(
        f"<span class='cls {name.lower()}'>{name} {cls_counts[name]}</span> "
        for name in ("Restricted", "Confidential", "Internal", "Public")
        if name in cls_counts
    )
    cert_badges = (
        f"<span class='badge ok'>{cert_status.get('certified', 0)} certified</span> "
        f"<span class='badge warn'>{cert_status.get('candidate', 0)} candidate</span> "
        f"<span class='badge danger'>{cert_status.get('refused', 0)} refused</span>"
    )
    avail_templates = reuse["templates_total"] - reuse["templates_live"]
    plat_badges = (
        f"<span class='badge ok'>{reuse['agents_covered']}/{reuse['agents_total']} "
        f"agents covered</span> "
        f"<span class='badge warn'>{avail_templates} available</span>"
    )
    weekly = m["weekly"]
    peak = max((n for _, n in weekly), default=1)
    # The value rides inside the bar as an absolutely-positioned label (ui-spec
    # 4.10, "printed above each bar"), not as a sibling above it. As a sibling
    # it consumed column height, which is what squashed every bar to the same
    # 17px; see the .barchart rules for the full account.
    bars = "".join(
        f"<div class='bcol'>"
        f"<div class='bar' style='height:{max(6, int(n / peak * 46))}px'>"
        f"<span class='v'>{n}</span></div>"
        f"<span class='bcap'>{wk.split('-')[-1]}</span></div>"
        for wk, n in weekly
    )

    row1 = st.columns(2)
    _tile(
        row1[0],
        "Datasets",
        "Datasets",
        "tile_open_datasets",
        f"<div class='tile-stat'><span class='big'>{len(ds)}</span>"
        "<span class='unit'>datasets under classification</span></div>"
        f"<div class='breakrow'>{cls_chips}</div>",
    )
    _tile(
        row1[1],
        "Registry",
        "Registry",
        "tile_open_registry",
        f"<div class='tile-stat'><span class='big'>{len(cert_entries())}</span>"
        "<span class='unit'>analyses in the certification lifecycle</span></div>"
        f"<div class='breakrow'>{cert_badges}</div>",
    )
    row2 = st.columns(2)
    _tile(
        row2[0],
        "Platform",
        "Platform",
        "tile_open_platform",
        f"<div class='tile-stat'><span class='big'>{reuse['templates_total']}</span>"
        f"<span class='unit'>agent templates · {reuse['templates_live']} live</span></div>"
        f"<div class='breakrow'>{plat_badges}</div>",
    )
    _tile(
        row2[1],
        "Adoption",
        "Adoption",
        "tile_open_adoption",
        f"<div class='tile-stat'><span class='big'>{m['total_runs']}</span>"
        f"<span class='unit'>runs · {m['promoted']} of {m['credit_risk_runs']} "
        "models promoted</span></div>"
        f"<div class='barchart'>{bars}</div>",
    )
    st.caption(
        "Run history is seeded demo telemetry from actually executed runs, plus "
        "live runs this session; every seeded row is labeled on its surface."
    )
