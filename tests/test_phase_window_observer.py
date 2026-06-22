from __future__ import annotations

from percolation_inversion_compiler.phase_lab import (
    ASIProxyThresholdSpec,
    build_effective_packet_graph,
    build_threshold_status,
    build_window_index,
    event_from_payload,
    observe_phase_window,
)


def test_candidate_only_external_reports_do_not_pass_thresholds() -> None:
    event = event_from_payload(
        {
            "accepted": False,
            "candidate_only": True,
            "candidate_only_reasons": ["external candidate"],
            "report_id": "external:candidate",
            "residual_summary": {"missing_evidence": 1.0},
            "source_kind": "general-intake",
            "workflow_usable": True,
        },
        window_id="phase-window:test",
        sequence=0,
    )
    window = build_window_index("phase-window:test", 0, [event])
    graph = build_effective_packet_graph([event]).graph
    observation = observe_phase_window(window, [event], graph)
    status = build_threshold_status(observation, ASIProxyThresholdSpec())

    assert observation.effective_node_count == 0
    assert status.certificate_status == "abstain"
    assert status.settled is False
