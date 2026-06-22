from __future__ import annotations

from percolation_inversion_compiler.phase_lab import build_effective_packet_graph


def test_raw_candidate_volume_does_not_increase_positive_phase_components() -> None:
    payloads = [
        {
            "accepted": False,
            "candidate_only": True,
            "candidate_only_reasons": ["raw external volume"],
            "report_id": f"candidate:{index}",
            "residual_summary": {"missing_evidence": 1.0},
            "source_kind": "general-intake",
            "workflow_usable": True,
        }
        for index in range(5)
    ]

    report = build_effective_packet_graph(payloads)

    assert report.graph.accepted_packet_capital == 0
    assert report.graph.candidate_only_packets == 5
    assert report.graph.non_contributing_volume == 5
    assert report.raw_volume_positive_contribution == 0
    assert report.settled is False
