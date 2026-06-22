from __future__ import annotations

from percolation_inversion_compiler.phase_lab import (
    build_effective_packet_graph,
    detect_autocatalytic_closure,
)


def test_closure_abstains_without_evidence_supported_edge() -> None:
    graph = build_effective_packet_graph(
        [
            {
                "accepted": True,
                "edges": [
                    {
                        "accepted": True,
                        "edge_id": "edge:unsupported",
                        "source_packet_ids": ["packet:alpha"],
                        "target_packet_id": "packet:alpha",
                    }
                ],
                "packet_ref": "packet:alpha",
                "report_id": "report:alpha",
                "residual_summary": {},
                "workflow_usable": True,
            }
        ]
    ).graph

    report = detect_autocatalytic_closure(graph)

    assert report.certificate_candidate.certificate_status == "abstain"
    assert report.closure_witnesses == []
    assert report.settled is False
