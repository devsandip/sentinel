"""Section 16 metrics on the gate and the Screen.

The core numbers the artifact claims:
  - Gate true-block rate on the seeded adversarial set: 100%.
  - Gate false-block rate on benign analyses: < 5%.
  - Small-cell suppression correctness: 100% on cells n < floor.

These run against the seeded corpus in codegen.adversarial and against a swept
range of cell sizes. They are the falsifiable claim, so they live as tests.
"""

from __future__ import annotations

import pandas as pd

from sentinel.codegen.adversarial import ADVERSARIAL, BENIGN, GRANT
from sentinel.codegen.gate import gate_code
from sentinel.disclosure.screen import DEFAULT_CELL_FLOOR, suppress_small_cells


def test_gate_true_block_rate_is_100_percent():
    blocked = 0
    for sample in ADVERSARIAL:
        result = gate_code(sample.code, granted_columns=GRANT)
        assert not result.passed, f"{sample.name!r} slipped through the gate"
        assert sample.expected_control in result.controls_fired, (
            f"{sample.name!r} blocked on {result.controls_fired}, "
            f"expected {sample.expected_control}"
        )
        blocked += 1
    assert blocked == len(ADVERSARIAL)
    assert blocked / len(ADVERSARIAL) == 1.0


def test_gate_false_block_rate_is_under_5_percent():
    false_blocks = [
        s.name
        for s in BENIGN
        if not gate_code(s.code, granted_columns=GRANT).passed
    ]
    rate = len(false_blocks) / len(BENIGN)
    assert rate < 0.05, f"benign code falsely blocked: {false_blocks}"


def test_every_adversarial_sample_names_a_control_and_line():
    # The refusal must be reviewer-readable: a control id and a line for each.
    for sample in ADVERSARIAL:
        result = gate_code(sample.code, granted_columns=GRANT)
        assert result.violations
        for v in result.violations:
            assert v.control.startswith("CTL-")
            assert v.line >= 1


def test_suppression_correctness_across_cell_sizes():
    # Every cell below the floor is removed; every cell at or above it survives.
    floor = DEFAULT_CELL_FLOOR
    sizes = [1, 3, 5, 9, 10, 11, 25, 100, 408]
    grouped = pd.DataFrame(
        {"band": [f"b{i}" for i in range(len(sizes))], "n": sizes}
    )
    screened, suppressed, _, _ = suppress_small_cells(
        grouped, count_col="n", group_cols=["band"]
    )
    assert all(cell.n < floor for cell in suppressed)
    assert all(int(n) >= floor for n in screened["n"])
    # Partition is exact: nothing lost, nothing duplicated.
    assert len(suppressed) + len(screened) == len(sizes)
    expected_suppressed = sum(1 for s in sizes if s < floor)
    assert len(suppressed) == expected_suppressed
