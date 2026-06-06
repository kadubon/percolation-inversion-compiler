from __future__ import annotations

import pytest

from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.trc import compile_frontier


def test_main_frontier_requires_trace_normal_form() -> None:
    with pytest.raises(ValueError, match="accepted trace normal forms"):
        compile_frontier(
            [
                FrontierRecord(
                    record_id="bad-main",
                    benefits={"future_freedom": 1.0},
                    stratum="main",
                )
            ]
        )


def test_main_frontier_rejects_self_declared_trace_flag() -> None:
    with pytest.raises(ValueError, match="accepted trace normal forms"):
        compile_frontier(
            [
                FrontierRecord(
                    record_id="forged-main",
                    benefits={"future_freedom": 1.0},
                    stratum="main",
                    trace_id="trace",
                    metadata={"trace_normal_form_accepted": True},
                )
            ]
        )
