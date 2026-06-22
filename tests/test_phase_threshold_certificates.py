from __future__ import annotations

from percolation_inversion_compiler.phase_lab import (
    ASIProxyThresholdSpec,
    build_collective_phase_certificate_candidate,
    build_effective_packet_graph,
    build_threshold_status,
    build_window_index,
    event_from_payload,
    observe_phase_window,
)


def test_phase_certificate_abstains_when_evidence_is_missing() -> None:
    event = event_from_payload(
        {"accepted": False, "report_id": "candidate", "workflow_usable": True},
        window_id="phase-window:test",
        sequence=0,
    )
    window = build_window_index("phase-window:test", 0, [event])
    graph = build_effective_packet_graph([event]).graph
    observation = observe_phase_window(window, [event], graph)
    threshold_status = build_threshold_status(observation, ASIProxyThresholdSpec())
    candidate = build_collective_phase_certificate_candidate(threshold_status, graph)

    assert candidate.certificate_status == "abstain"
    assert candidate.proves_real_asi is False
    assert candidate.settled is False

