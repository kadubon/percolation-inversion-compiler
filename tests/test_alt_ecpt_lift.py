from __future__ import annotations

from percolation_inversion_compiler.alt import verify_alt_ecpt_lift
from percolation_inversion_compiler.phase_lab import build_effective_packet_graph


def test_alt_ecpt_lift_fails_closed_without_ecpt_component() -> None:
    graph = build_effective_packet_graph(
        [{"accepted": False, "report_id": "candidate", "workflow_usable": True}]
    ).graph
    report = verify_alt_ecpt_lift(
        [{"packet_id": "alt:demo", "accepted": False, "operationally_usable": False}],
        graph,
    )

    assert report.accepted is False
    assert report.diagnostic_only_lift_failure is True
    assert report.settled is False
    assert report.affected_ecpt_components == []
