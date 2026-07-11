"""SQOT controller diagnostics over effective packet graphs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import isfinite

from percolation_inversion_compiler.phase_lab.records import EffectivePacketGraph
from percolation_inversion_compiler.sqot_controller.records import (
    AttentionBudgetLedger,
    DiagnosticReserveReport,
    PacketQuarantineDecision,
    QueueItemCost,
    QueueOccupationReport,
    QueueRebalancePlan,
    ReversibleSalienceSovereigntyCertificate,
    SalienceObstructionDiagnosis,
    VerificationQueuePressure,
)


def diagnose_queue_occupation(
    graph: EffectivePacketGraph,
    *,
    attention_budget: float = 1.0,
    reserve_fraction: float = 0.1,
    item_costs: Mapping[str, QueueItemCost] | None = None,
) -> QueueOccupationReport:
    """Diagnose queue pressure without applying queue actions."""

    candidate_nodes = [node for node in graph.nodes if node.contribution.candidate_only]
    stale_nodes = [node for node in graph.nodes if not node.eligibility.not_stale]
    unsafe_nodes = [
        node
        for node in graph.nodes
        if not node.eligibility.authority_valid or not node.eligibility.hash_valid
    ]
    costs = item_costs or {}
    unknown_item_ids: list[str] = []
    measured_costs: list[QueueItemCost] = []
    occupied = 0.0
    for node in candidate_nodes:
        cost = costs.get(node.node_id)
        if not _queue_cost_known(cost):
            unknown_item_ids.append(node.node_id)
            continue
        if cost is None:
            continue
        measured_costs.append(cost)
        occupied += sum(
            value
            for value in (
                cost.attention_cost,
                cost.verification_cost,
                cost.age_cost,
                cost.hazard_cost,
            )
            if value is not None
        )
    occupied = min(attention_budget, occupied)
    reserve_required = max(0.0, attention_budget * reserve_fraction)
    reserve_available = max(0.0, attention_budget - occupied)
    repeated = _repeated_candidate_nodes(candidate_nodes)
    blocked_high_value = [
        node.node_id
        for node in candidate_nodes
        if "verification-blocked" in node.eligibility.blockers
        or "missing-edge-evidence" in node.eligibility.blockers
    ]
    ledger = AttentionBudgetLedger(
        attention_budget=attention_budget,
        occupied=occupied,
        diagnostic_reserve_required=reserve_required,
        diagnostic_reserve_available=reserve_available,
        reserve_preserved=not unknown_item_ids and reserve_available >= reserve_required,
        measurement_state="known" if not unknown_item_ids else "unknown",
        unknown_item_ids=sorted(unknown_item_ids),
    )
    pressure = VerificationQueuePressure(
        backlog_count=len(candidate_nodes) + len(graph.missing_edge_evidence),
        stale_packet_count=len(stale_nodes),
        unsafe_packet_count=len(unsafe_nodes),
        candidate_only_count=len(candidate_nodes),
        pressure=(len(candidate_nodes) + len(graph.missing_edge_evidence))
        / max(1, len(graph.nodes)),
    )
    return QueueOccupationReport(
        graph_id=graph.graph_id,
        attention_budget_ledger=ledger,
        verification_queue_pressure=pressure,
        low_value_packet_ids=[node.node_id for node in candidate_nodes],
        repeated_candidate_only_packets=repeated,
        blocked_high_value_packets=blocked_high_value,
        rollback_unavailable_decisions=[
            node.node_id
            for node in graph.nodes
            if not node.eligibility.rollback_available_or_not_required
        ],
        queue_costs=sorted(measured_costs, key=lambda item: item.packet_id),
        accepted=not unknown_item_ids,
        settled=False,
        reasons=[
            "queue occupation report is diagnostic only",
            "raw candidate volume does not improve phase metrics",
            *(
                ["queue item costs are unknown; occupied capacity and reserve are not certified"]
                if unknown_item_ids
                else []
            ),
        ],
    )


def diagnose_salience_obstruction(graph: EffectivePacketGraph) -> SalienceObstructionDiagnosis:
    """Find nodes blocked by salience, queue, stale, or unsafe pressure."""

    obstruction: dict[str, list[str]] = {}
    for node in graph.nodes:
        reasons = [
            blocker
            for blocker in node.eligibility.blockers
            if blocker
            in {
                "salience-obstruction",
                "candidate-only",
                "raw-external-volume",
                "stale",
                "authority-invalid",
            }
        ]
        if reasons:
            obstruction[node.node_id] = sorted(set(reasons))
    return SalienceObstructionDiagnosis(
        graph_id=graph.graph_id,
        obstructed_packet_ids=sorted(obstruction),
        obstruction_reasons=dict(sorted(obstruction.items())),
        obstruction_load=len(obstruction) / max(1, len(graph.nodes)),
        accepted=bool(obstruction),
        settled=False,
        reasons=["salience obstruction diagnosis does not execute or delete queue items"],
    )


def build_queue_rebalance_plan(graph: EffectivePacketGraph) -> QueueRebalancePlan:
    """Recommend reversible queue actions without applying them."""

    actions: dict[str, str] = {}
    quarantine = build_quarantine_decisions(graph)
    quarantine_ids = {decision.packet_id for decision in quarantine}
    for node in graph.nodes:
        if node.node_id in quarantine_ids:
            actions[node.node_id] = "quarantine"
        elif "verification-blocked" in node.eligibility.blockers:
            actions[node.node_id] = "route verifier"
        elif "salience-obstruction" in node.eligibility.blockers:
            actions[node.node_id] = "rebalance"
        elif node.contribution.positive_contribution:
            actions[node.node_id] = "accept"
        elif node.contribution.candidate_only:
            actions[node.node_id] = "inspect"
        else:
            actions[node.node_id] = "preserve residual"
    return QueueRebalancePlan(
        graph_id=graph.graph_id,
        recommended_actions=dict(sorted(actions.items())),
        quarantine_decisions=quarantine,
        executes_actions=False,
        deletes_packets=False,
        accepted=bool(actions),
        settled=False,
        reasons=[
            "rebalance plan is recommendation-only",
            "quarantine decisions are report objects unless an operator applies them",
        ],
    )


def build_quarantine_decisions(graph: EffectivePacketGraph) -> list[PacketQuarantineDecision]:
    """Build reversible quarantine decisions for unsafe graph nodes."""

    decisions: list[PacketQuarantineDecision] = []
    for node in graph.nodes:
        reasons = []
        if not node.eligibility.hash_valid:
            reasons.append("hash-invalid")
        if not node.eligibility.authority_valid:
            reasons.append("authority-invalid")
        if not node.eligibility.not_stale:
            reasons.append("stale")
        if node.source_kind in {"raw-external", "general-intake"}:
            reasons.append("raw-external-volume")
        if reasons:
            decisions.append(
                PacketQuarantineDecision(
                    decision_id=f"quarantine:{node.node_id}",
                    packet_id=node.node_id,
                    decision="quarantine",
                    reasons=sorted(set(reasons)),
                    reversible=True,
                    applied=False,
                    deletes_packet=False,
                    settled=False,
                )
            )
    return sorted(decisions, key=lambda item: item.packet_id)


def check_diagnostic_reserve(
    graph: EffectivePacketGraph,
    *,
    attention_budget: float = 1.0,
    reserve_fraction: float = 0.1,
    item_costs: Mapping[str, QueueItemCost] | None = None,
) -> DiagnosticReserveReport:
    """Check whether diagnostic reserve remains available."""

    occupation = diagnose_queue_occupation(
        graph,
        attention_budget=attention_budget,
        reserve_fraction=reserve_fraction,
        item_costs=item_costs,
    )
    ledger = occupation.attention_budget_ledger
    deficit = max(0.0, ledger.diagnostic_reserve_required - ledger.diagnostic_reserve_available)
    measured = ledger.measurement_state == "known"
    return DiagnosticReserveReport(
        graph_id=graph.graph_id,
        attention_budget_ledger=ledger,
        reserve_deficit=deficit,
        accepted=measured and deficit <= 0.0,
        settled=False,
        reasons=[
            "diagnostic reserve is checked without scheduling or executing work",
            *([] if deficit <= 0 else ["diagnostic reserve is below required threshold"]),
            *(
                []
                if measured
                else ["diagnostic reserve is unknown because queue costs are missing"]
            ),
        ],
    )


def build_salience_sovereignty_certificate(
    plan: QueueRebalancePlan,
) -> ReversibleSalienceSovereigntyCertificate:
    """Build a fail-closed reversible salience certificate from a plan."""

    rollback_available = all(decision.reversible for decision in plan.quarantine_decisions)
    status = "candidate" if rollback_available and plan.quarantine_decisions else "abstain"
    return ReversibleSalienceSovereigntyCertificate(
        graph_id=plan.graph_id,
        rebalance_plan_id=plan.plan_id,
        reversible=rollback_available,
        rollback_available=rollback_available,
        grants_execution_authority=False,
        certificate_status=status,
        settled=False,
        reasons=[
            "certificate does not apply queue mutations",
            "rollback availability is diagnostic until operator-supplied evidence is checked",
        ],
    )


def _repeated_candidate_nodes(nodes: Sequence[object]) -> list[str]:
    digests = Counter(getattr(node, "content_digest", "") for node in nodes)
    return sorted(
        getattr(node, "node_id", "")
        for node in nodes
        if digests[getattr(node, "content_digest", "")] > 1
    )


def _queue_cost_known(cost: QueueItemCost | None) -> bool:
    if cost is None or not cost.validity_domain or not cost.evidence_refs:
        return False
    values = (cost.attention_cost, cost.verification_cost, cost.age_cost, cost.hazard_cost)
    return all(value is not None and isfinite(value) and value >= 0.0 for value in values)
