"""Headless smoke test that the Streamlit app renders without exceptions.

Uses Streamlit's AppTest harness (no browser). Guards against import errors and
render-time exceptions in both top-level sections.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

# pyarrow's mimalloc allocator segfaults on macOS when Streamlit serializes a
# DataFrame; route to the system allocator before anything imports pyarrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def test_run_analysis_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    # Pre-run, the analysis section prompts the user to start a run.
    assert any("click Run" in i.value for i in at.info)


def test_platform_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Platform").run()
    assert not at.exception
    assert any(s.value == "Platform assets" for s in at.subheader)
    # Three playbooks, each in an expander, plus the download pack button.
    assert len(at.expander) == 3
    assert any("playbook pack" in b.label for b in at.download_button)


def test_governed_codegen_section_renders():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Governed codegen").run()
    assert not at.exception
    assert any(s.value == "Governed code generation" for s in at.subheader)
    # Pre-run, the console prompts the user to run.
    assert any("click Run" in i.value for i in at.info)


def test_registry_section_shows_certification_lifecycle():
    at = AppTest(script_path=APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Registry").run()
    assert not at.exception
    # The certification lifecycle section and its visible refusal both render.
    assert any("certification lifecycle" in m.value for m in at.markdown)
    assert any("cohort-retention" in e.label for e in at.expander)
