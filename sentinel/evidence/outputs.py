"""The two audience outputs of a completed run (section 1.10).

Two audiences, two artifacts, from the same signed-or-pending evidence pack:

  - For the data scientist: a **marimo notebook**. Plain ``.py``, a real
    ``marimo.App`` whose cells carry the governance context and the generated
    analysis as an ordinary reviewable function, so a colleague code-reviews it
    in a pull request like any other change (1.10). It is not auto-run: the
    analysis reaches data only through the fenced ``ctx`` the platform builds,
    and re-running it outside that fence would itself be ungoverned, which is the
    thing this platform refuses.
  - For leadership: a **Quarto document**. ``EvidencePack.to_markdown`` already
    emits Quarto front-matter and the non-negotiable "what this does not say"
    block; here we write it to a ``.qmd`` and render it to the filed PDF when the
    ``quarto`` binary is present. When it is not (the public instance has no
    binary), we write the ``.qmd`` source and say so, rather than fake a PDF.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .pack import EvidencePack

_MARIMO_VERSION_TAG = "sentinel-evidence"
_CODE_INDENT = " " * 8  # cell body (4) + nested def body (4)


def _md_header(pack: EvidencePack) -> str:
    """The leadership context, as markdown, for the notebook's first cell. The
    same four parts as the pack: finding, provenance, controls, and the negative
    statement that a reviewer must see next to the code."""
    p = pack.provenance
    ci = (
        f" (95% CI {pack.confidence_interval[0]:.2f} to {pack.confidence_interval[1]:.2f})"
        if pack.confidence_interval
        else ""
    )
    lines = [
        f"# Evidence: {p.analysis}",
        "",
        f"**Finding.** {pack.finding}{ci}",
        "",
        "**Provenance.**",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Analysis | {p.analysis} |",
        f"| Dataset | {p.dataset} (sha:{p.dataset_sha}) |",
        f"| Tier | {p.tier} |",
        f"| Purpose | {p.purpose} |",
        f"| Author | {p.author} |",
        f"| Run | {p.run_id} |",
        "",
        "**Controls attested.** " + (", ".join(f"`{c}`" for c in pack.controls_attested) or "none"),
        "",
        "**What this does not say.**",
        "",
    ]
    lines += [f"- {s}" for s in pack.negative_statement]
    return "\n".join(lines)


def _wrap_generated_code(code: str) -> tuple[str, bool]:
    """Wrap the generated analysis as ``def analysis(ctx):`` for a clean PR diff.

    Returns (cell_body, wrapped). Prefers a real function so the code reads like
    ordinary Python in review. Falls back to a byte-faithful string constant if
    indenting the code would not parse (e.g. an unusual multiline literal), so we
    never emit a notebook that a colleague cannot open.
    """
    body = code.rstrip("\n") or "pass"

    def _string_constant() -> str:
        # Byte-faithful, held as a repr string. Used when indenting the code into a
        # function body would silently alter a multiline literal.
        return (
            "    # The generated analysis, verbatim. Held as a string because it\n"
            "    # contains a multiline literal that indenting would alter; review\n"
            "    # it as source.\n"
            f"    generated_analysis = {body!r}\n"
            "    return (generated_analysis,)\n"
        )

    # A triple-quoted literal (e.g. a multiline ctx.sql query) would have its inner
    # lines shifted by indentation; that still parses, so ast will not catch it.
    # Detect it directly and keep the code byte-faithful instead.
    if '"""' in body or "'''" in body:
        return _string_constant(), False

    indented = "\n".join(
        (_CODE_INDENT + line if line.strip() else "") for line in body.splitlines()
    )
    candidate = (
        "    def analysis(ctx):\n"
        '        """The generated analysis, exactly as the gate cleared it and the\n'
        "        sandbox ran it. It reaches data only through the fenced ctx API\n"
        "        (ctx.table / ctx.param / ctx.sql / ctx.emit). Not called here:\n"
        "        reproducing it means handing it a governed ctx.\"\"\"\n"
        f"{indented}\n"
        "    return (analysis,)\n"
    )
    # Validate the whole cell parses as a function definition; fall back if not.
    try:
        ast.parse("def _():\n" + candidate)
        return candidate, True
    except SyntaxError:
        return _string_constant(), False


def to_marimo_notebook(pack: EvidencePack) -> str:
    """Render the evidence pack as a loadable marimo notebook (``.py``).

    The notebook has three cells: the marimo import, a markdown cell with the
    governance context (finding, provenance, controls, negative statement), and
    the generated analysis as a reviewable function. The result is valid Python
    and a valid ``marimo.App``; this function asserts it parses before returning.
    """
    header_md = _md_header(pack)
    code_cell, _wrapped = _wrap_generated_code(pack.provenance.code)

    parts = [
        f"# Sentinel evidence notebook -- run {pack.provenance.run_id}.",
        f"# Generated for {pack.provenance.author} from a governed {pack.provenance.tier} run.",
        "# Plain .py on purpose: review the generated analysis in a PR like any other change.",
        "",
        "import marimo",
        "",
        f'__generated_with = "{_MARIMO_VERSION_TAG}"',
        "app = marimo.App()",
        "",
        "",
        "@app.cell",
        "def _():",
        "    import marimo as mo",
        "    return (mo,)",
        "",
        "",
        "@app.cell",
        "def _(mo):",
        "    mo.md(",
        '        r"""',
        # Markdown sits at column 0 inside the string: 4+ leading spaces would make
        # Markdown render it as an indented code block. Valid Python regardless.
        header_md,
        '        """',
        "    )",
        "    return",
        "",
        "",
        "@app.cell",
        "def _():",
        code_cell.rstrip("\n"),
        "",
        "",
        'if __name__ == "__main__":',
        "    app.run()",
        "",
    ]
    notebook = "\n".join(parts)
    # Fail loudly here rather than hand a broken file to the download button.
    ast.parse(notebook)
    return notebook


@dataclass
class QuartoRender:
    """The result of rendering the leadership document. ``rendered`` is False when
    the ``quarto`` binary is absent; the ``.qmd`` source is written regardless."""

    qmd_path: Path
    pdf_path: Path | None
    rendered: bool
    detail: str


def render_quarto(pack: EvidencePack, outdir: str | Path, *, timeout_s: int = 120) -> QuartoRender:
    """Write the ``.qmd`` and render it to PDF when Quarto is installed.

    The ``.qmd`` is ``pack.to_markdown()`` verbatim (it already carries the Quarto
    front-matter and the negative statement). If the ``quarto`` binary is on PATH,
    shell out to render the filed PDF; otherwise return the source and an honest
    reason. Never fabricates a PDF.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    qmd = out / f"evidence_pack_{pack.request_id}.qmd"
    qmd.write_text(pack.to_markdown(), encoding="utf-8")

    quarto = shutil.which("quarto")
    if quarto is None:
        return QuartoRender(
            qmd_path=qmd,
            pdf_path=None,
            rendered=False,
            detail=(
                "quarto binary not found on PATH; wrote the .qmd source only. "
                "Install Quarto (quarto.org) to render the filed PDF."
            ),
        )

    try:
        subprocess.run(
            [quarto, "render", qmd.name, "--to", "pdf"],
            check=True,
            capture_output=True,
            cwd=out,
            timeout=timeout_s,
        )
    except subprocess.CalledProcessError as ex:
        stderr = (ex.stderr or b"").decode("utf-8", "replace").strip()
        return QuartoRender(qmd, None, False, f"quarto render failed: {stderr[-500:]}")
    except subprocess.TimeoutExpired:
        return QuartoRender(qmd, None, False, f"quarto render timed out after {timeout_s}s")

    pdf = qmd.with_suffix(".pdf")
    if pdf.exists():
        return QuartoRender(qmd, pdf, True, f"rendered {pdf.name}")
    return QuartoRender(qmd, None, False, "quarto exited cleanly but produced no PDF")
