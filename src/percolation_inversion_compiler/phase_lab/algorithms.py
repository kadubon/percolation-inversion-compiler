"""Deterministic Phase Ecology Lab algorithms."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

from percolation_inversion_compiler.phase_lab.records import (
    ActionBoundaryRequirement,
    ASIProxyThresholdSpec,
    ASIProxyThresholdStatus,
    AutocatalyticClosureReport,
    AutocatalyticClosureWitness,
    BasinReachabilityProxy,
    ClosureAbstentionReason,
    ClosureCertificateCandidate,
    ClosureDefect,
    ClosureSupportHyperpath,
    CollectivePhaseAbstentionReport,
    CollectivePhaseCertificateCandidate,
    EffectiveGraphResidualSummary,
    EffectivePacketEdge,
    EffectivePacketEligibility,
    EffectivePacketGraph,
    EffectivePacketGraphBuildReport,
    EffectivePacketNode,
    ExecutableClosureWitness,
    ExecutablePathDensityReport,
    ExecutionAuthorityStatus,
    ExecutionAvailableHyperpath,
    ExecutionPathDefect,
    ExecutionPathWitness,
    FalseLiquidityLoad,
    PacketContributionStatus,
    PhaseCertificateDefect,
    PhaseComponentObservation,
    PhaseLabEvent,
    PhaseLabWindowIndex,
    PhaseThresholdStatus,
    PhaseWindow,
    PhaseWindowComparison,
    PhaseWindowObservation,
    ProductiveClosureWitness,
    ReceiverContextSupport,
    SalienceObstructionLoad,
    SemanticEdgeEvidence,
    VerificationThroughputWindow,
    WasteLoad,
)

SAFETY_BOUNDARY = [
    "protocol-relative only",
    "does not prove real ASI",
    "does not prove physical or oracle truth",
    "does not execute command text or safe_commands",
    "raw packet volume is diagnostic only",
]


def stable_json_digest(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def event_from_payload(
    payload: dict[str, Any],
    *,
    window_id: str,
    sequence: int,
    source_path: str | None = None,
    source_kind_override: str | None = None,
) -> PhaseLabEvent:
    """Normalize one arbitrary PIC report or packet envelope as inert event data."""

    digest = stable_json_digest(payload)
    schema_hint = infer_schema_hint(payload)
    source_kind = source_kind_override or infer_source_kind(payload, schema_hint)
    accepted = bool(payload.get("accepted", False))
    workflow_usable = bool(payload.get("workflow_usable", False))
    operationally_usable = bool(payload.get("operationally_usable", False))
    settled = bool(payload.get("settled", False))
    missing = _string_list(payload.get("missing_obligations")) + _string_list(
        payload.get("unresolved_obligations")
    )
    candidate_reasons = _string_list(payload.get("candidate_only_reasons"))
    settled_blockers = _string_list(payload.get("settled_blockers"))
    residual_summary = _extract_residual_summary(payload)
    candidate_only = (
        bool(payload.get("candidate_only", False))
        or bool(candidate_reasons)
        or source_kind in {"packet-exchange", "general-intake", "phase-dashboard"}
        or not accepted
    )
    unsafe_reasons = _unsafe_reasons(payload, missing, candidate_reasons, settled_blockers)
    positive = bool(
        accepted
        and not candidate_only
        and not unsafe_reasons
        and _has_retrievable_identity(payload, digest)
    )
    return PhaseLabEvent(
        event_id=f"phase-lab-event:{sequence}:{digest[:12]}",
        window_id=window_id,
        source_kind=source_kind,
        schema_hint=schema_hint,
        content_digest=digest,
        payload=payload,
        source_path=_sanitize_source_path(source_path),
        accepted=accepted,
        workflow_usable=workflow_usable,
        operationally_usable=operationally_usable,
        settled=False,
        candidate_only=candidate_only,
        positive_contribution_allowed=positive,
        residual_summary=residual_summary,
        missing_obligations=sorted(set(missing)),
        candidate_only_reasons=sorted(set(candidate_reasons)),
        settled_blockers=sorted(
            set(settled_blockers + ([] if not settled else ["source-settled-ignored"]))
        ),
        safety_boundary=SAFETY_BOUNDARY,
        reasons=[
            "event content is stored as inert data",
            *unsafe_reasons,
            *(["candidate-only event cannot improve phase metrics"] if candidate_only else []),
        ],
    )


def build_window_index(
    window_id: str,
    sequence: int,
    events: list[PhaseLabEvent],
) -> PhaseLabWindowIndex:
    residual_debt = sum(sum(event.residual_summary.values()) for event in events)
    return PhaseLabWindowIndex(
        window_id=window_id,
        sequence=sequence,
        event_ids=[event.event_id for event in events],
        event_count=len(events),
        accepted_event_count=sum(1 for event in events if event.accepted),
        candidate_only_event_count=sum(1 for event in events if event.candidate_only),
        positive_contribution_event_count=sum(
            1 for event in events if event.positive_contribution_allowed
        ),
        settled_event_count=0,
        residual_debt=residual_debt,
        missing_obligation_count=sum(len(event.missing_obligations) for event in events),
        accepted=True,
        settled=False,
        reasons=["window index preserves event residuals without settling claims"],
    )


def build_effective_packet_graph(
    events: list[PhaseLabEvent] | list[dict[str, Any]],
    *,
    graph_id: str = "effective-packet-graph",
    source_window_id: str = "adhoc",
) -> EffectivePacketGraphBuildReport:
    """Build an effective graph while keeping non-contributing volume explicit."""

    normalized: list[PhaseLabEvent] = []
    for index, event in enumerate(events):
        if isinstance(event, PhaseLabEvent):
            normalized.append(event)
            continue
        normalized.append(
            event_from_payload(
                cast(dict[str, Any], event),
                window_id=source_window_id,
                sequence=index,
            )
        )
    nodes = [_node_from_event(event) for event in normalized]
    edges = _edges_from_nodes_and_payloads(nodes, normalized)
    node_status = Counter(node.contribution.status for node in nodes)
    edge_relations = Counter(edge.relation_type for edge in edges)
    residual_summary = _merge_residuals([node.residual_summary for node in nodes])
    missing_edge_evidence = [
        edge.edge_id for edge in edges if edge.accepted and not edge.evidence.evidence_supported
    ]
    graph = EffectivePacketGraph(
        graph_id=graph_id,
        source_window_id=source_window_id,
        nodes=nodes,
        edges=edges,
        node_count_by_status=dict(sorted(node_status.items())),
        edge_count_by_relation=dict(sorted(edge_relations.items())),
        accepted_packet_capital=sum(1 for node in nodes if node.contribution.positive_contribution),
        candidate_only_packets=sum(1 for node in nodes if node.contribution.candidate_only),
        rejected_or_quarantined_packets=sum(
            1 for node in nodes if node.contribution.status in {"rejected", "quarantined"}
        ),
        missing_edge_evidence=missing_edge_evidence,
        stale_or_unsafe_packets=[
            node.node_id
            for node in nodes
            if not node.eligibility.not_stale or not node.eligibility.authority_valid
        ],
        semantic_edge_witnesses=[
            edge.evidence for edge in edges if edge.evidence.evidence_supported
        ],
        non_contributing_volume=sum(
            1 for node in nodes if not node.contribution.positive_contribution
        ),
        residual_summary=EffectiveGraphResidualSummary(
            residual_summary=residual_summary,
            residual_debt=sum(residual_summary.values()),
            missing_obligation_count=sum(len(node.missing_obligations) for node in nodes),
            settled_blockers=sorted(
                {
                    blocker
                    for event in normalized
                    for blocker in [*event.settled_blockers, *event.missing_obligations]
                }
            ),
            candidate_only_reasons=sorted(
                {reason for event in normalized for reason in event.candidate_only_reasons}
            ),
        ),
        accepted=bool(nodes),
        workflow_usable=True,
        operationally_usable=any(node.contribution.positive_contribution for node in nodes),
        settled=False,
        reasons=[
            "effective graph separates positive contribution from diagnostic volume",
            "raw packet count does not increase positive phase metrics",
        ],
    )
    return EffectivePacketGraphBuildReport(
        graph=graph,
        input_event_count=len(normalized),
        positive_contribution_count=graph.accepted_packet_capital,
        diagnostic_only_count=graph.non_contributing_volume,
        raw_volume_positive_contribution=0,
        accepted=bool(nodes),
        workflow_usable=True,
        settled=False,
        reasons=["graph build is diagnostic and non-executing"],
    )


def observe_phase_window(
    window: PhaseLabWindowIndex,
    events: list[PhaseLabEvent],
    graph: EffectivePacketGraph,
) -> PhaseWindowObservation:
    """Build a window observation from Phase Lab events and an effective graph."""

    effective_nodes = graph.accepted_packet_capital
    effective_edges = sum(1 for edge in graph.edges if edge.contribution.positive_contribution)
    closure_count = _supported_cycle_count(graph)
    execution_count = _execution_path_count(graph)
    total = max(1, len(events))
    accepted_count = sum(1 for event in events if event.accepted)
    missing_count = sum(len(event.missing_obligations) for event in events)
    residual_debt = graph.residual_summary.residual_debt
    non_contributing = graph.non_contributing_volume
    false_liquidity_candidates = sum(
        1
        for event in events
        if "alt" in event.source_kind.lower() and not event.positive_contribution_allowed
    )
    false_liquidity_certified = sum(
        1
        for event in events
        if "alt" in event.source_kind.lower() and event.positive_contribution_allowed
    )
    obstruction_count = sum(
        1
        for node in graph.nodes
        if "salience" in " ".join([*node.eligibility.blockers, *node.reasons]).lower()
    )
    components = [
        PhaseComponentObservation(
            component="accepted_packet_count",
            value=float(accepted_count),
            distance=0.0,
            diagnostic_only=False,
        ),
        PhaseComponentObservation(
            component="effective_node_count",
            value=float(effective_nodes),
            distance=0.0,
            diagnostic_only=False,
        ),
        PhaseComponentObservation(
            component="effective_edge_count",
            value=float(effective_edges),
            distance=0.0,
            diagnostic_only=False,
        ),
        PhaseComponentObservation(
            component="raw_volume",
            value=float(len(events)),
            distance=0.0,
            diagnostic_only=True,
        ),
    ]
    return PhaseWindowObservation(
        window=PhaseWindow(
            window_id=window.window_id,
            sequence=window.sequence,
            event_count=window.event_count,
            event_ids=window.event_ids,
        ),
        packet_candidate_count=len(events),
        accepted_packet_count=accepted_count,
        workflow_usable_packet_count=sum(1 for event in events if event.workflow_usable),
        settled_packet_count=0,
        candidate_only_packet_count=sum(1 for event in events if event.candidate_only),
        effective_node_count=effective_nodes,
        effective_edge_count=effective_edges,
        execution_available_path_count=execution_count,
        closure_witness_count=closure_count,
        autocatalytic_closure_score=0.0 if not effective_nodes else closure_count / effective_nodes,
        verification_throughput=VerificationThroughputWindow(
            accepted_count=accepted_count,
            backlog_count=missing_count,
            throughput_ratio=accepted_count / total,
        ),
        residual_debt=residual_debt,
        missing_obligation_count=missing_count,
        false_liquidity_load=FalseLiquidityLoad(
            candidate_count=false_liquidity_candidates,
            certified_count=false_liquidity_certified,
            load=false_liquidity_candidates / total,
        ),
        waste_load=WasteLoad(
            non_contributing_volume=non_contributing,
            total_volume=len(events),
            load=non_contributing / total,
        ),
        salience_obstruction_load=SalienceObstructionLoad(
            blocked_count=obstruction_count,
            total_count=len(graph.nodes),
            load=obstruction_count / max(1, len(graph.nodes)),
        ),
        basin_reachability_proxy=BasinReachabilityProxy(
            execution_available_path_count=execution_count,
            effective_node_count=effective_nodes,
            reachability_proxy=execution_count / max(1, effective_nodes),
        ),
        alt_liquidity_candidate_count=false_liquidity_candidates,
        alt_certified_capital_count=false_liquidity_certified,
        phase_gap_vector={
            "effective_nodes": float(max(0, 1 - effective_nodes)),
            "effective_edges": float(max(0, 1 - effective_edges)),
            "closure": float(max(0, 1 - closure_count)),
            "execution_paths": float(max(0, 1 - execution_count)),
        },
        bottleneck_count_by_type=_bottleneck_counts(graph),
        threshold_distance=float(
            max(0, 1 - effective_nodes)
            + max(0, 1 - effective_edges)
            + max(0, 1 - closure_count)
            + max(0, 1 - execution_count)
        ),
        components=components,
        accepted=bool(events),
        workflow_usable=True,
        operationally_usable=effective_nodes > 0,
        settled=False,
        reasons=[
            "window observation is protocol-relative only",
            "raw external volume is diagnostic only",
        ],
    )


def compare_phase_windows(
    baseline: PhaseWindowObservation,
    candidate: PhaseWindowObservation,
) -> PhaseWindowComparison:
    metrics = {
        "effective_node_count": float(
            candidate.effective_node_count - baseline.effective_node_count
        ),
        "effective_edge_count": float(
            candidate.effective_edge_count - baseline.effective_edge_count
        ),
        "execution_available_path_count": float(
            candidate.execution_available_path_count - baseline.execution_available_path_count
        ),
        "closure_witness_count": float(
            candidate.closure_witness_count - baseline.closure_witness_count
        ),
        "residual_debt": float(candidate.residual_debt - baseline.residual_debt),
    }
    positive = [key for key, value in metrics.items() if key != "residual_debt" and value > 0]
    return PhaseWindowComparison(
        baseline_window_id=baseline.window.window_id,
        candidate_window_id=candidate.window.window_id,
        metric_delta=metrics,
        positive_progress_components=positive,
        diagnostic_only_components=["packet_candidate_count", "raw_volume"],
        accepted=True,
        workflow_usable=True,
        settled=False,
        reasons=["comparison preserves protocol-relative diagnostic status"],
    )


def detect_autocatalytic_closure(graph: EffectivePacketGraph) -> AutocatalyticClosureReport:
    supported_edges = [
        edge
        for edge in graph.edges
        if edge.contribution.positive_contribution and edge.evidence.evidence_supported
    ]
    witness_ids: list[str] = []
    closure_witnesses: list[AutocatalyticClosureWitness] = []
    support_hyperpaths: list[ClosureSupportHyperpath] = []
    productive: list[ProductiveClosureWitness] = []
    executable: list[ExecutableClosureWitness] = []
    defects: list[ClosureDefect] = []
    for edge in supported_edges:
        if edge.target_node_id in edge.source_node_ids:
            witness_id = f"closure-witness:{edge.edge_id}"
            witness_ids.append(witness_id)
            closure_witnesses.append(
                AutocatalyticClosureWitness(
                    witness_id=witness_id,
                    packet_ids=sorted(set([*edge.source_node_ids, edge.target_node_id])),
                    edge_ids=[edge.edge_id],
                    evidence_supported=True,
                    productive=True,
                    accepted=True,
                    settled=False,
                    reasons=[
                        "witness is evidence-supported within the effective graph",
                        "witness remains diagnostic until finite threshold checks pass",
                    ],
                )
            )
            support_hyperpaths.append(
                ClosureSupportHyperpath(
                    hyperpath_id=f"closure-hyperpath:{edge.edge_id}",
                    source_packet_ids=edge.source_node_ids,
                    target_packet_ids=[edge.target_node_id],
                    edge_ids=[edge.edge_id],
                    accepted=True,
                )
            )
            productive.append(
                ProductiveClosureWitness(
                    witness_id=f"productive:{edge.edge_id}",
                    packet_ids=sorted(set([*edge.source_node_ids, edge.target_node_id])),
                    productive_edge_ids=[edge.edge_id],
                    productivity_lower_bound=0.1,
                    accepted=True,
                    reasons=["self-supporting evidence edge is productive in declared scope"],
                )
            )
    for edge in graph.edges:
        if edge.accepted and not edge.evidence.evidence_supported:
            defects.append(
                ClosureDefect(
                    defect_id=f"closure-defect:{edge.edge_id}",
                    packet_or_edge_id=edge.edge_id,
                    defect_type="missing-edge-evidence",
                )
            )
    status = "candidate" if witness_ids and not defects else "abstain"
    abstentions = (
        []
        if witness_ids
        else [
            ClosureAbstentionReason(
                reason_id="closure-abstain:no-evidence-supported-cycle",
                reason="closure requires evidence-supported accepted edges",
            )
        ]
    )
    candidate = ClosureCertificateCandidate(
        certificate_status=status,
        witness_ids=witness_ids,
        defects=defects,
        abstention_reasons=abstentions,
        accepted=status == "candidate",
        reasons=[
            "closure candidate is not automatically settled",
            "candidate-only cycles do not count",
        ],
    )
    return AutocatalyticClosureReport(
        graph_id=graph.graph_id,
        closure_witnesses=closure_witnesses,
        productive_witnesses=productive,
        executable_witnesses=executable,
        support_hyperpaths=support_hyperpaths,
        defects=defects,
        certificate_candidate=candidate,
        closure_score=0.0 if not graph.nodes else len(witness_ids) / len(graph.nodes),
        accepted=status == "candidate",
        operationally_usable=status == "candidate",
        settled=False,
        reasons=["closure detection does not execute or settle paths"],
    )


def detect_execution_available_paths(graph: EffectivePacketGraph) -> ExecutablePathDensityReport:
    paths: list[ExecutionAvailableHyperpath] = []
    defects: list[ExecutionPathDefect] = []
    for edge in graph.edges:
        source_nodes = [node for node in graph.nodes if node.node_id in edge.source_node_ids]
        target_nodes = [node for node in graph.nodes if node.node_id == edge.target_node_id]
        nodes = [*source_nodes, *target_nodes]
        accepted = bool(nodes) and all(node.contribution.positive_contribution for node in nodes)
        evidence_ok = edge.evidence.evidence_supported and edge.contribution.positive_contribution
        authority_ok = all(node.eligibility.authority_valid for node in nodes)
        rollback_ok = all(node.eligibility.rollback_available_or_not_required for node in nodes)
        receiver_ok = bool(target_nodes)
        reasons: list[str] = []
        if not accepted:
            reasons.append("required packets are not all accepted positive contributors")
        if not evidence_ok:
            reasons.append("required edges are not evidence-supported")
        if not authority_ok:
            reasons.append("authority is not explicit and scope-bounded")
        if not rollback_ok:
            reasons.append("rollback or safe abort support is missing")
        if not receiver_ok:
            reasons.append("receiver context is missing")
        path_accepted = accepted and evidence_ok and authority_ok and rollback_ok and receiver_ok
        path = ExecutionAvailableHyperpath(
            path_id=f"execution-path:{edge.edge_id}",
            packet_ids=sorted({node.node_id for node in nodes}),
            edge_ids=[edge.edge_id],
            witness=ExecutionPathWitness(
                witness_id=f"execution-witness:{edge.edge_id}",
                packet_ids=sorted({node.node_id for node in nodes}),
                edge_ids=[edge.edge_id],
                accepted=path_accepted,
                reasons=reasons,
            ),
            receiver_context=ReceiverContextSupport(
                receiver_context_id=f"receiver:{edge.target_node_id}",
                present=receiver_ok,
                evidence_refs=edge.evidence.evidence_refs,
            ),
            action_boundary_requirements=[
                ActionBoundaryRequirement(
                    requirement_id=f"authority:{edge.edge_id}",
                    requirement_type="authority",
                    satisfied=authority_ok,
                    residual="" if authority_ok else "authority evidence required",
                ),
                ActionBoundaryRequirement(
                    requirement_id=f"rollback:{edge.edge_id}",
                    requirement_type="rollback",
                    satisfied=rollback_ok,
                    residual="" if rollback_ok else "rollback evidence required",
                ),
            ],
            authority_status=ExecutionAuthorityStatus(
                authority_status="explicit-scope-bounded" if authority_ok else "not-granted",
                explicit_scope_bounded=authority_ok,
                grants_execution=False,
                reasons=["execution path report never grants execution authority"],
            ),
            accepted=path_accepted,
            candidate_only=not path_accepted,
            blocked=not path_accepted,
            not_executed=True,
            reasons=reasons or ["execution path is available as a finite diagnostic witness"],
        )
        paths.append(path)
        if not path_accepted:
            defects.append(
                ExecutionPathDefect(
                    defect_id=f"execution-defect:{edge.edge_id}",
                    path_id=path.path_id,
                    defect_type="; ".join(reasons) if reasons else "blocked",
                )
            )
    accepted_count = sum(1 for path in paths if path.accepted)
    return ExecutablePathDensityReport(
        graph_id=graph.graph_id,
        paths=paths,
        path_count=len(paths),
        path_density=accepted_count / max(1, len(graph.nodes)),
        accepted_path_count=accepted_count,
        candidate_only_path_count=sum(1 for path in paths if path.candidate_only),
        blocked_path_count=sum(1 for path in paths if path.blocked),
        blocker_reason_by_path={path.path_id: path.reasons for path in paths if path.blocked},
        authority_requirements=sorted(
            requirement.requirement_id
            for path in paths
            for requirement in path.action_boundary_requirements
            if requirement.requirement_type == "authority"
        ),
        rollback_requirements=sorted(
            requirement.requirement_id
            for path in paths
            for requirement in path.action_boundary_requirements
            if requirement.requirement_type == "rollback"
        ),
        residual_carry_forward=sorted({reason for path in paths for reason in path.reasons}),
        executed_path_count=0,
        accepted=bool(paths),
        operationally_usable=accepted_count > 0,
        settled=False,
        reasons=["execution-available path detection never executes paths"],
    )


def build_threshold_status(
    observation: PhaseWindowObservation,
    threshold: ASIProxyThresholdSpec,
) -> ASIProxyThresholdStatus:
    path_density = observation.basin_reachability_proxy.reachability_proxy
    component_status = {
        "minimum_accepted_packet_count": (
            observation.accepted_packet_count >= threshold.minimum_accepted_packet_count
        ),
        "minimum_effective_edge_count": (
            observation.effective_edge_count >= threshold.minimum_effective_edge_count
        ),
        "minimum_execution_available_path_density": (
            path_density >= threshold.minimum_execution_available_path_density
        ),
        "minimum_closure_witness_count": (
            observation.closure_witness_count >= threshold.minimum_closure_witness_count
        ),
        "maximum_residual_debt": observation.residual_debt <= threshold.maximum_residual_debt,
        "maximum_false_liquidity_load": (
            observation.false_liquidity_load.load <= threshold.maximum_false_liquidity_load
        ),
        "maximum_salience_obstruction": (
            observation.salience_obstruction_load.load <= threshold.maximum_salience_obstruction
        ),
        "minimum_verification_throughput": (
            observation.verification_throughput.throughput_ratio
            >= threshold.minimum_verification_throughput
        ),
        "minimum_alt_to_ecpt_lift_count": (
            observation.alt_certified_capital_count >= threshold.minimum_alt_to_ecpt_lift_count
        ),
    }
    failed = sorted(key for key, value in component_status.items() if not value)
    status = "candidate" if not failed else "abstain"
    distance = _threshold_distance(observation, threshold, component_status)
    return ASIProxyThresholdStatus(
        threshold=threshold,
        observation=observation,
        certificate_status=status,
        component_status=component_status,
        failed_components=failed,
        abstention_reasons=[
            f"missing finite threshold component: {component}" for component in failed
        ],
        threshold_distance=distance,
        accepted=status == "candidate",
        settled=False,
        reasons=[
            "threshold status is protocol-relative only",
            "threshold status does not prove real ASI",
        ],
    )


def build_phase_threshold_status(
    observation: PhaseWindowObservation,
    threshold: ASIProxyThresholdSpec,
) -> PhaseThresholdStatus:
    status = build_threshold_status(observation, threshold)
    return PhaseThresholdStatus(
        threshold_id=threshold.threshold_id,
        passed=status.certificate_status == "candidate",
        abstain=status.certificate_status == "abstain",
        rejected=status.certificate_status == "reject",
        component_status=status.component_status,
        threshold_distance=status.threshold_distance,
        settled=False,
        reasons=status.reasons + status.abstention_reasons,
    )


def build_collective_phase_certificate_candidate(
    threshold_status: ASIProxyThresholdStatus,
    graph: EffectivePacketGraph,
) -> CollectivePhaseCertificateCandidate:
    defects = [
        PhaseCertificateDefect(
            defect_id=f"phase-defect:{component}",
            component=component,
            defect_type="threshold-component-missing",
            required_remediation=f"provide finite evidence for {component}",
        )
        for component in threshold_status.failed_components
    ]
    status = threshold_status.certificate_status
    abstention = None
    if status != "candidate":
        abstention = CollectivePhaseAbstentionReport(
            threshold_status=threshold_status,
            defects=defects,
            reasons=["certificate abstains when finite evidence is missing"],
        )
    return CollectivePhaseCertificateCandidate(
        certificate_status=status,
        threshold_status=threshold_status,
        graph_id=graph.graph_id,
        observation_id=threshold_status.observation.observation_id,
        finite_requirements_passed=status == "candidate",
        abstention_report=abstention,
        defects=defects,
        accepted=status == "candidate",
        workflow_usable=True,
        operationally_usable=status == "candidate",
        settled=False,
        reasons=[
            "certificate candidate is protocol-relative only",
            "certificate candidate does not prove real ASI",
            "certificate candidate does not settle diagnostic reports",
        ],
    )


def infer_schema_hint(payload: dict[str, Any]) -> str:
    if "packet_id" in payload and "content_digest" in payload and "content" in payload:
        return "PacketExchangeEnvelope"
    if "report_id" in payload and "registry" in payload and "phase_acceleration_score" in payload:
        return "RuntimeStepReport"
    if "dashboard_id" in payload and "packet_candidate_count" in payload:
        return "PhaseDashboardReport"
    if "plan_id" in payload and "phase_gap_vector" in payload:
        return "PhaseAccelerationPlan"
    if "accepted" in payload and "workflow_usable" in payload and "residual_summary" in payload:
        return "AgentCheckReport"
    if "decision_id" in payload and "packet_id" in payload:
        return "ALTAdmissionDecision"
    if "report_id" in payload and "packets" in payload and "provenance" in payload:
        return "GeneralIntakeReport"
    if "message_id" in payload and "sender_agent_id" in payload:
        return "AgentMessageEnvelope"
    if "graph_id" in payload and "nodes" in payload and "edges" in payload:
        return "EffectivePacketGraph"
    return str(payload.get("schema", payload.get("schema_hint", "UnknownPICReport")))


def infer_source_kind(payload: dict[str, Any], schema_hint: str) -> str:
    explicit = payload.get("source_kind")
    if isinstance(explicit, str):
        return explicit
    mapping = {
        "PacketExchangeEnvelope": "packet-exchange",
        "RuntimeStepReport": "runtime-step-report",
        "PhaseDashboardReport": "phase-dashboard",
        "PhaseAccelerationPlan": "phase-plan",
        "AgentCheckReport": "agent-check",
        "ALTAdmissionDecision": "alt-admission",
        "GeneralIntakeReport": "general-intake",
        "AgentMessageEnvelope": "agent-message",
        "EffectivePacketGraph": "effective-graph",
    }
    return mapping.get(schema_hint, "unknown-report")


def _node_from_event(event: PhaseLabEvent) -> EffectivePacketNode:
    blockers = _eligibility_blockers(event)
    eligible = not blockers and event.positive_contribution_allowed
    eligibility = EffectivePacketEligibility(
        accepted_or_certificate_admissible=event.accepted,
        retrievable=bool(event.content_digest),
        not_salience_blocked="salience-obstruction" not in blockers,
        not_verification_blocked="verification-blocked" not in blockers,
        not_stale="stale" not in blockers,
        hash_valid="hash-invalid" not in blockers,
        authority_valid="authority-invalid" not in blockers,
        rollback_available_or_not_required="rollback-missing" not in blockers,
        within_validity_domain="validity-domain-missing" not in blockers,
        residuals_preserved=True,
        not_registry_metadata_only=event.source_kind != "registry-metadata",
        not_raw_external_volume=event.source_kind not in {"general-intake", "raw-external"},
        agent_text_not_treated_as_evidence=event.source_kind != "agent-text-only",
        eligible=eligible,
        blockers=blockers,
    )
    status = (
        "accepted" if eligible else ("candidate-only" if event.candidate_only else "diagnostic")
    )
    contribution = PacketContributionStatus(
        status=status,
        positive_contribution=eligible,
        candidate_only=not eligible,
        non_contributing_reason=(
            "" if eligible else "eligibility blockers prevent positive contribution"
        ),
    )
    return EffectivePacketNode(
        node_id=f"node:{event.content_digest[:12]}",
        source_event_id=event.event_id,
        source_kind=event.source_kind,
        schema_hint=event.schema_hint,
        content_digest=event.content_digest,
        accepted=event.accepted,
        workflow_usable=event.workflow_usable,
        operationally_usable=event.operationally_usable,
        eligibility=eligibility,
        contribution=contribution,
        residual_summary=event.residual_summary,
        missing_obligations=event.missing_obligations,
        reasons=event.reasons,
    )


def _edges_from_nodes_and_payloads(
    nodes: list[EffectivePacketNode],
    events: list[PhaseLabEvent],
) -> list[EffectivePacketEdge]:
    by_event = {event.event_id: node for event, node in zip(events, nodes, strict=True)}
    edges: list[EffectivePacketEdge] = []
    for event in events:
        node = by_event[event.event_id]
        explicit_edges = _extract_explicit_edges(event.payload)
        for index, edge_data in enumerate(explicit_edges):
            raw_source_ids = [
                _node_id_for_packet_ref(ref, nodes)
                for ref in _string_list(edge_data.get("source_packet_ids"))
            ]
            source_ids = [item for item in raw_source_ids if item is not None]
            target = (
                _node_id_for_packet_ref(str(edge_data.get("target_packet_id", "")), nodes)
                or node.node_id
            )
            evidence_refs = _string_list(edge_data.get("evidence_refs"))
            accepted = bool(edge_data.get("accepted", event.accepted))
            evidence_supported = accepted and bool(evidence_refs)
            relation = str(
                edge_data.get(
                    "edge_type",
                    edge_data.get("relation_type", "semantic-dependency"),
                )
            )
            edge_id = str(edge_data.get("edge_id", f"edge:{node.node_id}:{index}"))
            positive = (
                accepted
                and evidence_supported
                and all(_node_positive(source, nodes) for source in source_ids)
                and _node_positive(target, nodes)
            )
            edges.append(
                EffectivePacketEdge(
                    edge_id=edge_id,
                    source_node_ids=source_ids or [node.node_id],
                    target_node_id=target,
                    relation_type=relation,
                    evidence=SemanticEdgeEvidence(
                        evidence_refs=evidence_refs,
                        edge_certificate_refs=_string_list(edge_data.get("edge_certificate_refs")),
                        verifier_resolution_refs=_string_list(
                            edge_data.get("verifier_resolution_refs")
                        ),
                        evidence_supported=evidence_supported,
                        missing_evidence=(
                            [] if evidence_supported else ["edge evidence refs required"]
                        ),
                    ),
                    accepted=accepted,
                    contribution=PacketContributionStatus(
                        status="accepted" if positive else "diagnostic",
                        positive_contribution=positive,
                        candidate_only=not positive,
                        non_contributing_reason=(
                            "" if positive else "edge lacks accepted evidence support"
                        ),
                    ),
                    residual_summary=event.residual_summary,
                    reasons=["edge extracted from inert report data"],
                )
            )
    return edges


def _extract_explicit_edges(payload: dict[str, Any]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for key in ("edges", "edge_witnesses", "edge_certificates"):
        value = payload.get(key)
        if isinstance(value, list):
            edges.extend(item for item in value if isinstance(item, dict))
    registry = payload.get("registry")
    if isinstance(registry, dict):
        for key in ("edges", "edge_witnesses", "edge_certificates"):
            value = registry.get(key)
            if isinstance(value, list):
                edges.extend(item for item in value if isinstance(item, dict))
    content = payload.get("content")
    if isinstance(content, dict):
        edges.extend(_extract_explicit_edges(content))
    return edges


def _node_id_for_packet_ref(ref: str, nodes: list[EffectivePacketNode]) -> str | None:
    if not ref:
        return None
    for node in nodes:
        if ref in {
            node.node_id,
            node.content_digest,
            node.content_digest[:12],
            node.source_event_id,
        }:
            return node.node_id
        if ref in json.dumps(node.model_dump(mode="json"), sort_keys=True):
            return node.node_id
    return None


def _node_positive(node_id: str, nodes: list[EffectivePacketNode]) -> bool:
    return any(
        node.node_id == node_id and node.contribution.positive_contribution for node in nodes
    )


def _eligibility_blockers(event: PhaseLabEvent) -> list[str]:
    joined = " ".join(
        [
            event.source_kind,
            *event.missing_obligations,
            *event.candidate_only_reasons,
            *event.settled_blockers,
            *event.reasons,
        ]
    ).lower()
    blockers: list[str] = []
    markers = {
        "salience-obstruction": ("salience", "queue occupation"),
        "verification-blocked": ("missing evidence", "missing verifier", "verification"),
        "stale": ("stale", "expired"),
        "hash-invalid": ("hash-invalid", "digest mismatch"),
        "authority-invalid": ("authority-invalid", "missing authority"),
        "rollback-missing": ("rollback", "safe abort"),
        "validity-domain-missing": ("validity domain",),
    }
    for blocker, needles in markers.items():
        if any(needle in joined for needle in needles):
            blockers.append(blocker)
    if event.candidate_only:
        blockers.append("candidate-only")
    if event.source_kind in {"general-intake", "raw-external"}:
        blockers.append("raw-external-volume")
    return sorted(set(blockers))


def _unsafe_reasons(
    payload: dict[str, Any],
    missing: list[str],
    candidate_reasons: list[str],
    settled_blockers: list[str],
) -> list[str]:
    text = json.dumps(payload, sort_keys=True, default=str).lower()
    reasons = []
    if any(
        marker in text for marker in ("rm -rf", "powershell", "cmd.exe", "bash ", "pip install")
    ):
        reasons.append("embedded command-like text remains inert")
    if missing:
        reasons.append("missing obligations remain visible")
    if candidate_reasons:
        reasons.append("candidate-only reasons remain visible")
    if settled_blockers:
        reasons.append("settlement blockers remain visible")
    return reasons


def _has_retrievable_identity(payload: dict[str, Any], digest: str) -> bool:
    return bool(
        digest
        or payload.get("packet_id")
        or payload.get("report_id")
        or payload.get("dashboard_id")
        or payload.get("plan_id")
    )


def _extract_residual_summary(payload: dict[str, Any]) -> dict[str, float]:
    for key in ("residual_summary", "residual_ledger_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            return _numeric_dict(value)
    ledger = payload.get("residual_ledger")
    if isinstance(ledger, dict):
        coordinates = ledger.get("coordinates")
        if isinstance(coordinates, dict):
            summary: dict[str, float] = {}
            for coordinate in coordinates.values():
                if isinstance(coordinate, dict):
                    kind = str(coordinate.get("kind", "residual"))
                    value = _as_float(coordinate.get("value"))
                    summary[kind] = summary.get(kind, 0.0) + value
            return dict(sorted(summary.items()))
    return {}


def _merge_residuals(items: list[dict[str, float]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for item in items:
        for key, value in item.items():
            merged[key] = merged.get(key, 0.0) + float(value)
    return dict(sorted(merged.items()))


def _numeric_dict(value: dict[Any, Any]) -> dict[str, float]:
    return dict(sorted((str(key), _as_float(item)) for key, item in value.items()))


def _as_float(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return 0.0


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, set | tuple):
        return [str(item) for item in value]
    return [str(value)]


def _sanitize_source_path(path: str | None) -> str | None:
    if path is None:
        return None
    parsed = Path(path)
    return parsed.name


def _supported_cycle_count(graph: EffectivePacketGraph) -> int:
    count = 0
    for edge in graph.edges:
        if (
            edge.contribution.positive_contribution
            and edge.evidence.evidence_supported
            and edge.target_node_id in edge.source_node_ids
        ):
            count += 1
    return count


def _execution_path_count(graph: EffectivePacketGraph) -> int:
    return sum(
        1
        for edge in graph.edges
        if edge.contribution.positive_contribution and edge.evidence.evidence_supported
    )


def _bottleneck_counts(graph: EffectivePacketGraph) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for node in graph.nodes:
        for blocker in node.eligibility.blockers:
            counts[blocker] += 1
    for edge in graph.edges:
        if not edge.evidence.evidence_supported:
            counts["missing-edge-evidence"] += 1
    return dict(sorted(counts.items()))


def _threshold_distance(
    observation: PhaseWindowObservation,
    threshold: ASIProxyThresholdSpec,
    component_status: dict[str, bool],
) -> float:
    distances = {
        "minimum_accepted_packet_count": max(
            0.0,
            threshold.minimum_accepted_packet_count - observation.accepted_packet_count,
        ),
        "minimum_effective_edge_count": max(
            0.0,
            threshold.minimum_effective_edge_count - observation.effective_edge_count,
        ),
        "minimum_execution_available_path_density": max(
            0.0,
            threshold.minimum_execution_available_path_density
            - observation.basin_reachability_proxy.reachability_proxy,
        ),
        "minimum_closure_witness_count": max(
            0.0,
            threshold.minimum_closure_witness_count - observation.closure_witness_count,
        ),
        "maximum_residual_debt": max(
            0.0,
            observation.residual_debt - threshold.maximum_residual_debt,
        ),
        "maximum_false_liquidity_load": max(
            0.0,
            observation.false_liquidity_load.load - threshold.maximum_false_liquidity_load,
        ),
        "maximum_salience_obstruction": max(
            0.0,
            observation.salience_obstruction_load.load - threshold.maximum_salience_obstruction,
        ),
        "minimum_verification_throughput": max(
            0.0,
            threshold.minimum_verification_throughput
            - observation.verification_throughput.throughput_ratio,
        ),
        "minimum_alt_to_ecpt_lift_count": max(
            0.0,
            threshold.minimum_alt_to_ecpt_lift_count - observation.alt_certified_capital_count,
        ),
    }
    return sum(distances[key] for key, passed in component_status.items() if not passed)
