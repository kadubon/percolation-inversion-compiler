from __future__ import annotations

from percolation_inversion_compiler.bit_engine import diagnose_bottlenecks, invert_bottlenecks
from percolation_inversion_compiler.phase_lab import build_effective_packet_graph


def test_bit_inversion_candidates_are_recommendation_only() -> None:
    graph = build_effective_packet_graph(
        [
            {
                "accepted": False,
                "candidate_only": True,
                "candidate_only_reasons": ["missing verifier route"],
                "report_id": "candidate:blocked",
                "residual_summary": {"missing_verifier": 1.0},
                "workflow_usable": True,
            }
        ]
    ).graph
    report = invert_bottlenecks(diagnose_bottlenecks(graph))

    assert report.inversion_candidates
    candidate = report.inversion_candidates[0]
    assert candidate.recommendation_only is True
    assert candidate.mutates_repositories_shells_networks_or_models is False
    assert candidate.settled is False
