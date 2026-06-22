from __future__ import annotations

from percolation_inversion_compiler.phase_lab import build_effective_packet_graph
from percolation_inversion_compiler.sqot_controller import (
    build_queue_rebalance_plan,
    diagnose_queue_occupation,
)


def test_sqot_rebalance_plan_does_not_execute_or_delete() -> None:
    graph = build_effective_packet_graph(
        [
            {
                "accepted": False,
                "candidate_only": True,
                "candidate_only_reasons": ["stale packet pressure"],
                "report_id": "candidate:stale",
                "residual_summary": {"stale": 1.0},
                "workflow_usable": True,
            }
        ]
    ).graph

    occupation = diagnose_queue_occupation(graph)
    plan = build_queue_rebalance_plan(graph)

    assert occupation.settled is False
    assert plan.executes_actions is False
    assert plan.deletes_packets is False
    assert all(not decision.applied for decision in plan.quarantine_decisions)

