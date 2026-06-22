from __future__ import annotations

from percolation_inversion_compiler.phase_lab import (
    build_effective_packet_graph,
    detect_execution_available_paths,
)


def test_execution_available_paths_do_not_grant_authority_or_execute() -> None:
    graph = build_effective_packet_graph(
        [
            {
                "accepted": True,
                "edges": [
                    {
                        "accepted": True,
                        "edge_id": "edge:self",
                        "evidence_refs": ["evidence:self"],
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

    report = detect_execution_available_paths(graph)

    assert report.accepted_path_count == 1
    assert report.executed_path_count == 0
    assert report.paths[0].authority_status.grants_execution is False
    assert report.paths[0].not_executed is True
