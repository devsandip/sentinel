"""The two audience outputs of a completed run (section 1.10).

A marimo notebook for the data scientist (plain .py, reviewable in a PR) and a
Quarto document for leadership (the .qmd source, rendered to PDF only where the
quarto binary is present). Neither is faked: the notebook is real, loadable
Python, and the PDF is produced only when Quarto can actually render it.
"""

from __future__ import annotations

import ast
import subprocess

import pandas as pd
import pytest

from sentinel.evidence import (
    build_evidence_pack,
    render_quarto,
    to_marimo_notebook,
)
from sentinel.evidence import outputs as outputs_mod
from sentinel.govflow import run_governed_analysis

BENIGN_Q = "Does the model decline older applicants more often, holding income constant?"


def _pack(code: str = "df = ctx.table('t')\nctx.emit(df)\n"):
    screened = pd.DataFrame(
        {"age_band": ["26-35", "56-65"], "selection_rate": [0.42, 0.19], "n": [180, 44]}
    )
    return build_evidence_pack(
        run_id="abc123def456",
        analysis="fair-lending v1.4",
        dataset="german_credit",
        dataset_sha="deadbeef",
        tier="L2",
        purpose="fair_lending_review",
        author="priya",
        code=code,
        screened=screened,
        controls_attested=["CTL-PROXY-01", "CTL-DISC-02", "CTL-SOD-01"],
        suppressed=[],
        proxy_flags=[],
        cell_floor=10,
    )


# -- marimo notebook -------------------------------------------------------


def test_marimo_notebook_is_valid_python():
    nb = to_marimo_notebook(_pack())
    ast.parse(nb)  # raises SyntaxError if the notebook is not loadable


def test_marimo_notebook_has_the_app_structure():
    nb = to_marimo_notebook(_pack())
    assert "import marimo" in nb
    assert "app = marimo.App()" in nb
    assert "@app.cell" in nb
    assert 'if __name__ == "__main__":' in nb
    assert "app.run()" in nb


def test_marimo_notebook_embeds_the_generated_code_as_a_function():
    nb = to_marimo_notebook(_pack(code="df = ctx.table('german_credit')\nctx.emit(df)\n"))
    assert "def analysis(ctx):" in nb
    # The generated statements appear verbatim, indented into the function body.
    assert "df = ctx.table('german_credit')" in nb
    assert "ctx.emit(df)" in nb


def test_marimo_notebook_carries_the_governance_context():
    pack = _pack()
    nb = to_marimo_notebook(pack)
    assert "What this does not say" in nb
    assert pack.provenance.run_id in nb
    assert "fair_lending_review" in nb
    # The finding's lead clause is present for the reviewer.
    assert pack.finding.split(",")[0] in nb


def test_marimo_notebook_falls_back_for_triple_quoted_code():
    # Code with a triple-quoted literal would shift if indented into a function;
    # the byte-faithful string-constant fallback keeps the notebook loadable.
    tricky = 'q = """\nSELECT age_band, count(*) AS n\nFROM t\n"""\ndf = ctx.sql(q)\nctx.emit(df)\n'
    nb = to_marimo_notebook(_pack(code=tricky))
    ast.parse(nb)
    assert "generated_analysis =" in nb
    assert "def analysis(ctx):" not in nb


def test_public_dict_carries_the_notebook():
    r = run_governed_analysis(BENIGN_Q, intent="fair_lending")
    pub = r.to_public_dict()
    nb = pub["evidence"]["marimo_notebook"]
    ast.parse(nb)
    assert "import marimo" in nb


@pytest.mark.parametrize("code", ["ctx.emit(1)\n", "df = ctx.table('t')\nctx.emit(df)\n"])
def test_marimo_notebook_loads_under_marimo_if_installed(code):
    marimo = pytest.importorskip("marimo")
    nb = to_marimo_notebook(_pack(code=code))
    # Executing our own generated notebook must yield a real marimo.App.
    ns: dict = {}
    exec(compile(nb, "<notebook>", "exec"), ns)  # noqa: S102 - our own generated file
    assert isinstance(ns["app"], marimo.App)


# -- Quarto ----------------------------------------------------------------


def test_quarto_without_binary_writes_qmd_and_is_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(outputs_mod.shutil, "which", lambda _name: None)
    res = render_quarto(_pack(), tmp_path)
    assert res.rendered is False
    assert res.pdf_path is None
    assert res.qmd_path.exists()
    assert res.qmd_path.suffix == ".qmd"
    assert "quarto binary not found" in res.detail
    # The .qmd is the leadership document, negative statement included.
    text = res.qmd_path.read_text()
    assert "What this does not say" in text
    assert 'title:' in text


def test_quarto_renders_pdf_when_binary_present(tmp_path, monkeypatch):
    monkeypatch.setattr(outputs_mod.shutil, "which", lambda _name: "/usr/local/bin/quarto")

    def fake_run(cmd, **kwargs):
        # Simulate quarto producing the PDF next to the .qmd.
        cwd = kwargs["cwd"]
        qmd_name = cmd[2]
        (cwd / qmd_name).with_suffix(".pdf").write_bytes(b"%PDF-1.7 fake")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(outputs_mod.subprocess, "run", fake_run)
    res = render_quarto(_pack(), tmp_path)
    assert res.rendered is True
    assert res.pdf_path is not None
    assert res.pdf_path.exists()
    assert res.pdf_path.suffix == ".pdf"


def test_quarto_render_failure_is_reported_not_raised(tmp_path, monkeypatch):
    monkeypatch.setattr(outputs_mod.shutil, "which", lambda _name: "/usr/local/bin/quarto")

    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, output=b"", stderr=b"LaTeX not found")

    monkeypatch.setattr(outputs_mod.subprocess, "run", fake_run)
    res = render_quarto(_pack(), tmp_path)
    assert res.rendered is False
    assert res.pdf_path is None
    assert res.qmd_path.exists()  # source still written
    assert "render failed" in res.detail
    assert "LaTeX not found" in res.detail
