from __future__ import annotations

from percolation_inversion_compiler.trc import adapt_trc_trace


def test_trc_trace_adapter_treats_tool_calls_as_data() -> None:
    report = adapt_trc_trace(
        {
            "trace_id": "trace:test",
            "events": [
                {
                    "event_id": "event:1",
                    "tool_name": "shell-like-text",
                    "input": {"command": "do not execute"},
                }
            ],
        }
    )

    assert report.content_treated_as_data is True
    assert report.executed_action_count == 0
    assert report.proves_physical_truth is False
    assert report.settled is False

