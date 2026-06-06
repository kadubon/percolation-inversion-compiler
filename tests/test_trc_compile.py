from __future__ import annotations

from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.trc import compile_frontier


def test_invalid_main_frontier_returns_diagnostic_partial_debt_by_default() -> None:
    result = compile_frontier(
        [
            FrontierRecord(
                record_id="bad-main",
                benefits={"future_freedom": 1.0},
                stratum="main",
            )
        ]
    )
    assert result.main_frontier == []
    assert result.failed_main_records == ["bad-main"]
    assert "trace-normal-form:bad-main" in result.missing_trace_obligations
    assert result.diagnostic_archive[0].record_id == "bad-main"
    assert result.trace_residual_ledger.burden_sum() >= 1.0


def test_main_frontier_fail_fast_is_still_available() -> None:
    try:
        compile_frontier(
            [FrontierRecord(record_id="bad-main", stratum="main")],
            fail_on_invalid_main_trace=True,
        )
    except ValueError as exc:
        assert "accepted trace normal forms" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("fail-fast compile mode did not raise")


def test_main_frontier_rejects_self_declared_trace_flag_as_diagnostic() -> None:
    result = compile_frontier(
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
    assert result.failed_main_records == ["forged-main"]
    assert result.diagnostic_archive[0].status.value == "diagnostic"
