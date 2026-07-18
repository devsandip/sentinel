"""The L3 route: near-arbitrary code in a broad sandbox on Public data (4.5).

L3 widens the analytical allowlist but not the hard safety boundary. The core
claim, tested here: at L3 a broad analysis passes and runs, but egress,
filesystem, and dynamic code are refused exactly as at L2. More rope, same hard
limits. And only a persona that resolves to L3 (certified analyst + sandbox
waiver, on Public data) may run here.
"""

from __future__ import annotations

import ast

from sentinel.codegen.allowlist import ALLOWED_IMPORTS, L3_ALLOWED_IMPORTS
from sentinel.codegen.gate import gate_code
from sentinel.evidence import render_quarto, to_marimo_notebook
from sentinel.govflow import run_l3_analysis
from sentinel.govflow.flow import STATUS_BLOCKED, STATUS_COMPLETED
from sentinel.harness.identity import get_persona

# -- the gate: broad allowlist, same hard deny lists -----------------------


def test_l3_allowlist_is_a_superset_of_l2():
    assert ALLOWED_IMPORTS <= L3_ALLOWED_IMPORTS
    # Whole packages and safe stdlib compute that L2 does not grant.
    for extra in ("sklearn", "statsmodels", "statistics", "math", "itertools"):
        assert extra in L3_ALLOWED_IMPORTS
        assert extra not in ALLOWED_IMPORTS


def test_l3_gate_admits_broad_imports_l2_refuses():
    code = "import sklearn\nimport statistics\nx = statistics.mean([1,2])\nctx.emit({'e': x})\n"
    # L2 refuses the whole-package/stdlib imports.
    assert not gate_code(code).passed
    # L3 admits them.
    assert gate_code(code, allowed_imports=L3_ALLOWED_IMPORTS).passed


def test_l3_gate_still_blocks_the_hard_limits():
    egress = "import requests\nrequests.post('http://x', json={})\nctx.emit({'effect': 0})\n"
    fs = "open('/tmp/x', 'w').write('hi')\nctx.emit({'effect': 0})\n"
    dyn = "eval('1+1')\nctx.emit({'effect': 0})\n"
    assert "CTL-EGRESS-01" in gate_code(egress, allowed_imports=L3_ALLOWED_IMPORTS).controls_fired
    assert "CTL-CODE-02" in gate_code(fs, allowed_imports=L3_ALLOWED_IMPORTS).controls_fired
    assert "CTL-CODE-03" in gate_code(dyn, allowed_imports=L3_ALLOWED_IMPORTS).controls_fired


# -- the flow: only L3 personas run; the analysis recovers the ground truth --


def test_admin_runs_l3_and_recovers_the_injected_effect():
    r = run_l3_analysis("estimate the intervention effect", persona=get_persona("admin"))
    assert r.tier == "L3"
    assert r.status == STATUS_COMPLETED
    assert all(s.status == "ok" for s in r.stages)
    # The DiD estimate is close to the synthetic ground truth of +12.
    effect = float(r.execution.emitted["effect"])
    assert 10.5 < effect < 13.5
    assert r.evidence is not None
    lo, hi = r.evidence.confidence_interval
    assert lo < effect < hi
    assert "CTL-TIME-01" in r.controls_fired


def test_l3_negative_statement_is_causal_and_honest():
    r = run_l3_analysis("estimate", persona=get_persona("admin"))
    text = " ".join(r.evidence.negative_statement)
    assert "parallel-trends" in text
    assert "synthetic" in text
    assert "not a proven causal effect" in text
    assert "not an approved conclusion" in text


def test_l3_blocks_egress_at_the_gate_in_the_flow():
    r = run_l3_analysis("exfiltrate the series", persona=get_persona("admin"), intent="exfiltrate")
    assert r.status == STATUS_BLOCKED
    assert "CTL-EGRESS-01" in r.controls_fired
    gate_stage = next(s for s in r.stages if s.stage == "Gate")
    assert gate_stage.status == "blocked"
    for s in ("Execute", "Screen", "Interpret", "Attest"):
        assert next(st for st in r.stages if st.stage == s).status == "skipped"


def test_l3_blocks_filesystem_and_dynamic_code():
    fs = run_l3_analysis("dump", persona=get_persona("admin"), intent="file_write")
    assert fs.status == STATUS_BLOCKED
    assert "CTL-CODE-02" in fs.controls_fired
    dyn = run_l3_analysis("eval", persona=get_persona("admin"), intent="dynamic")
    assert dyn.status == STATUS_BLOCKED
    assert "CTL-CODE-03" in dyn.controls_fired


def test_lower_tiers_may_not_run_l3():
    # The certified analyst resolves to L2 on Public data (no waiver), the junior
    # to L1, the validator to L0. None reach L3, so none run in the L3 sandbox.
    for pid, expected_tier in [
        ("analyst", "L2"),
        ("junior_analyst", "L1"),
        ("model_validator", "L0"),
    ]:
        r = run_l3_analysis("x", persona=get_persona(pid))
        assert r.tier == expected_tier
        assert r.status == STATUS_BLOCKED
        ask = next(s for s in r.stages if s.stage == "Ask")
        assert ask.status == "blocked"


def test_l3_evidence_makes_valid_downstream_outputs(tmp_path):
    r = run_l3_analysis("estimate", persona=get_persona("admin"))
    nb = to_marimo_notebook(r.evidence)
    ast.parse(nb)
    assert "statistics" in nb  # the broad import shows up in the reviewable notebook
    res = render_quarto(r.evidence, tmp_path)
    assert res.qmd_path.exists()
    assert "parallel-trends" in res.qmd_path.read_text()
