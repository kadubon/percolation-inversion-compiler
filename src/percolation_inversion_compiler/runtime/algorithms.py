"""Deterministic ECPT active runtime algorithms."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from percolation_inversion_compiler.core import (
    AdapterRouteSpec,
    VerifierResolution,
    binding_for_route,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology import (
    BottleneckIntervention,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitnessCertificate,
    PacketIngestionReport,
    PacketPromotionPolicy,
    PacketPromotionReport,
    PacketRejection,
    PacketSourceKind,
    VerifiedCapabilityPacket,
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_registry,
    build_psi_dashboard,
    edge_certificate_from_witness,
    infer_live_kind,
    ingest_agent_output,
    ingest_live_source,
    ingest_local_file,
)
from percolation_inversion_compiler.ecpt import (
    PhaseControlAction,
    PhaseControlPlan,
    PhaseControlRunReport,
    build_phase_control_plan,
    reachable_mass,
)
from percolation_inversion_compiler.runtime.records import (
    AccelerationCertificate,
    ActionCommit,
    ActionCommitPolicy,
    AgentRuntimeConfig,
    AgentTask,
    EvidenceResolutionBatch,
    PhaseAccelerationScore,
    RouteExecutionRequest,
    RuntimeActionResult,
    RuntimeComparisonReport,
    RuntimeEvent,
    RuntimeEventLog,
    RuntimeHealthReport,
    RuntimeRunReport,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)
from percolation_inversion_compiler.sqot import (
    DiagnosticReservePolicy,
    QuarantineLedger,
    SalienceQueueRecord,
    build_salience_schedule,
)


def build_runtime_step(
    state: RuntimeState,
    step_input: RuntimeStepInput,
    config: AgentRuntimeConfig | None = None,
) -> RuntimeStepReport:
    """Run one finite active runtime step.

    The step composes packet ingestion, edge-witness construction, Psi dashboard
    evaluation, bottleneck inversion, ECPT phase planning, SQOT scheduling, and
    route-request emission.  It is intentionally fail-closed: planning alone does
    not set ``settled``.
    """

    active_config = config or AgentRuntimeConfig()
    evidence_batch = resolve_step_evidence(step_input, profile=active_config.profile)
    ingestion_reports = _ingest_step_sources(step_input, active_config)
    packets, residual, reasons = _merge_packets(state, step_input, ingestion_reports)
    residual = residual.combine(evidence_batch.residual_ledger)
    edges = build_edge_witnesses(packets)
    edge_certificates = [
        *[edge_certificate_from_witness(edge) for edge in edges],
        *step_input.edge_certificates,
    ]
    promotion_report = promote_runtime_packets(
        packets,
        evidence_batch.resolutions,
        edge_certificates,
        PacketPromotionPolicy(),
        report_id=f"packet-promotion:{state.state_id}:{step_input.input_id}",
    )
    registry = build_packet_registry(
        packets,
        edges,
        registry_id=f"runtime-registry:{state.state_id}:{step_input.input_id}",
    )
    residual = residual.combine(registry.residual_ledger)
    threshold = dict(state.psi_threshold)
    threshold.update(active_config.psi_threshold)
    dashboard = build_psi_dashboard(registry, threshold=threshold or None, target_tags=["phase"])
    bottleneck = build_bottleneck_plan(registry, dashboard, profile=active_config.profile)
    phase_report = _build_phase_report(state, active_config)
    residual = residual.combine(dashboard.residual_ledger)
    residual = residual.combine(bottleneck.residual_ledger)
    residual = residual.combine(phase_report.plan.residual_ledger)

    route_requests = _route_requests(
        _routes_from_runtime_outputs(phase_report, bottleneck, active_config),
        priority_score=1.0,
    )
    tasks = _agent_tasks(
        phase_actions=phase_report.plan.selected_actions,
        bottleneck_interventions=bottleneck.interventions,
        route_specs={spec.route_id: spec for spec in list_adapter_route_specs()},
        max_tasks=active_config.max_tasks,
        minimum_task_score=active_config.minimum_task_score,
    )
    schedule = build_salience_schedule(
        _salience_records(tasks, registry),
        attention_budget=active_config.attention_budget,
        diagnostic_reserve=DiagnosticReservePolicy(minimum_reserve=0.0, reserve_fraction=0.1),
        risk_budget=active_config.risk_budget,
        profile=active_config.profile,
    )
    residual = residual.combine(_schedule_residual(schedule))
    residual = residual.combine(promotion_report.residual_ledger)
    score = phase_acceleration_score(
        score_id=f"phase-acceleration:{state.state_id}:{step_input.input_id}",
        phase_report=phase_report,
        bottleneck_plan=bottleneck,
        registry=registry,
        route_requests=route_requests,
        schedule_residual=schedule.residual_debt_growth,
        prior_residual_debt=state.residual_ledger.burden_sum(),
    )
    commits = [
        _action_commit(action, active_config.action_commit_policy)
        for action in phase_report.plan.selected_actions
    ]
    route_residuals = {
        obligation
        for request in route_requests
        for obligation in request.residual_external_obligations
    }
    missing_obligations = sorted(
        set(phase_report.plan.missing_obligations)
        | route_residuals
        | {obligation for task in tasks for obligation in task.residual_coordinates}
    )
    if step_input.live_sources and not _live_enabled(step_input, active_config):
        reasons.append(
            "live connector sources were diagnostic because runtime live ingestion is disabled"
        )
    if schedule.quarantine_ledger.quarantined_items:
        reasons.append("SQOT quarantined one or more runtime packets or tasks")
    if evidence_batch.unresolved_envelope_refs:
        reasons.append("one or more evidence envelope refs were unresolved")
    accepted = bool(tasks)
    finite_checks_passed = bool(
        phase_report.plan.accepted or bottleneck.accepted or schedule.accepted or registry.packets
    )
    operationally_usable = (
        accepted
        and bool(finite_checks_passed)
        and schedule.accepted
        and not missing_obligations
        and not schedule.quarantine_ledger.quarantined_items
        and active_config.action_commit_policy != ActionCommitPolicy.RECOMMEND_ONLY
    )
    event_log_delta = RuntimeEventLog(
        events=[
            _runtime_event(
                event_id=f"event:{state.state_id}:{state.step_index}:{step_input.input_id}:step",
                event_type="runtime-step",
                step_index=state.step_index,
                payload_ref=f"runtime-step:{step_input.input_id}",
                payload={
                    "input_id": step_input.input_id,
                    "packet_ids": [packet.packet_id for packet in packets],
                    "resolution_ids": [
                        resolution.resolution_id for resolution in evidence_batch.resolutions
                    ],
                    "verified_packet_ids": [
                        packet.packet_id for packet in promotion_report.verified_packets
                    ],
                },
                residual_delta=residual,
            )
        ]
    )
    event_log_delta = _event_log_with_hash(event_log_delta.events)
    return RuntimeStepReport(
        report_id=f"runtime-step:{state.state_id}:{state.step_index}:{step_input.input_id}",
        state_id=state.state_id,
        input_id=step_input.input_id,
        step_index=state.step_index,
        accepted=accepted,
        finite_checks_passed=finite_checks_passed,
        operationally_usable=operationally_usable,
        settled=False,
        status=ClaimStatus.PROVISIONAL if operationally_usable else ClaimStatus.DIAGNOSTIC,
        ingestion_reports=ingestion_reports,
        registry=registry,
        psi=dashboard,
        bottleneck_plan=bottleneck,
        phase_run_report=phase_report,
        salience_schedule=schedule,
        phase_acceleration_score=score,
        evidence_resolution_batch=evidence_batch,
        promotion_report=promotion_report,
        event_log_delta=event_log_delta,
        verified_packet_count=len(state.verified_packets) + len(promotion_report.verified_packets),
        acceleration_certificate_eligible=bool(
            promotion_report.verified_packets and score.total_score > 0.0
        ),
        agent_tasks=tasks,
        action_commits=commits,
        route_execution_requests=route_requests,
        missing_obligations=missing_obligations,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
        allow_live_connectors=_live_enabled(step_input, active_config),
    )


def run_runtime_loop(
    state: RuntimeState,
    inputs: Sequence[RuntimeStepInput],
    config: AgentRuntimeConfig | None = None,
    *,
    max_steps: int | None = None,
) -> list[RuntimeStepReport]:
    """Run multiple deterministic runtime steps while preserving residual ledgers."""

    active_config = config or AgentRuntimeConfig()
    reports: list[RuntimeStepReport] = []
    current = state
    for step_input in list(inputs)[: max_steps or len(inputs)]:
        report = build_runtime_step(current, step_input, active_config)
        reports.append(report)
        current = loop_state_after_report(current, report)
    return reports


def resolve_step_evidence(
    step_input: RuntimeStepInput,
    route_catalog: Mapping[str, AdapterRouteSpec] | None = None,
    profile: str = "development",
) -> EvidenceResolutionBatch:
    """Resolve inline verifier envelopes and preserve unresolved refs as debt."""

    source_specs = (
        list(route_catalog.values()) if route_catalog is not None else list_adapter_route_specs()
    )
    specs = {catalog_spec.route_id: catalog_spec for catalog_spec in source_specs}
    for catalog_spec in source_specs:
        specs[catalog_spec.verifier_route] = catalog_spec
    resolutions: list[VerifierResolution] = []
    residual = Ledger()
    rejected: list[str] = []
    accepted: list[str] = []
    unresolved_refs: list[str] = []
    for envelope in sorted(step_input.evidence_envelopes, key=lambda item: item.envelope_id):
        route_spec = specs.get(envelope.route_id)
        if route_spec is None:
            residual = residual.add_coordinate(
                f"runtime-evidence:{envelope.envelope_id}:unknown-route",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            rejected.extend(envelope.obligation_ids)
            continue
        resolution = resolve_adapter_route(route_spec, envelope, profile=profile)
        resolutions.append(resolution)
        residual = residual.combine(resolution.residual_ledger)
        accepted.extend(resolution.accepted_obligation_ids)
        rejected.extend(resolution.rejected_obligation_ids)
    for ref in sorted(step_input.evidence_envelope_refs):
        unresolved_refs.append(Path(ref).name)
        residual = residual.add_coordinate(
            f"runtime-evidence-ref:{Path(ref).name}:unresolved",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    finite = bool(resolutions) and all(resolution.accepted for resolution in resolutions)
    return EvidenceResolutionBatch(
        batch_id=f"evidence-resolution:{step_input.input_id}",
        envelope_refs=[
            *sorted(step_input.evidence_envelope_refs),
            *[envelope.envelope_id for envelope in step_input.evidence_envelopes],
        ],
        resolutions=sorted(resolutions, key=lambda item: item.resolution_id),
        accepted_obligations=sorted(set(accepted)),
        rejected_obligations=sorted(set(rejected)),
        unresolved_envelope_refs=unresolved_refs,
        residual_ledger=residual,
        accepted=finite and not unresolved_refs,
        finite_checks_passed=finite,
        operationally_usable=finite and not unresolved_refs,
        settled=False,
    )


def promote_packet_candidate(
    candidate: CapabilityPacketCandidate,
    resolutions: Sequence[VerifierResolution],
    edge_certificates: Sequence[EdgeWitnessCertificate],
    policy: PacketPromotionPolicy | None = None,
) -> VerifiedCapabilityPacket | PacketRejection:
    """Promote one packet candidate to finite-scope reusable packet capital."""

    active_policy = policy or PacketPromotionPolicy()
    residual = Ledger()
    reasons: list[str] = []
    if candidate.expires_at == "expired":
        reasons.append("packet candidate is expired")
    if not candidate.evidence_hash_valid:
        reasons.append("packet evidence hash is invalid")
    if not candidate.route_safe:
        reasons.append("packet verifier route is unsafe")
    if candidate.authority_required and not candidate.authority_granted:
        reasons.append("packet authority is not granted")
    if active_policy.require_rollback_available and not candidate.rollback_available:
        reasons.append("packet rollback receipt is unavailable")
    if active_policy.require_receiver_compatibility and not candidate.receiver_family:
        reasons.append("packet receiver family is empty")
    if candidate.evidence_refs and not any(
        ref.endswith(candidate.content_sha256) or candidate.content_sha256 in ref
        for ref in candidate.evidence_refs
    ):
        reasons.append("packet evidence refs do not bind content sha256")
    resolution_by_route = {
        key: resolution
        for resolution in resolutions
        for key in {resolution.route_id, resolution.route_id.split(".")[-1]}
    }
    matched_resolutions = [
        resolution_by_route[route]
        for route in candidate.verifier_routes
        if route in resolution_by_route
    ]
    if active_policy.require_route_resolution and candidate.verifier_routes:
        missing_routes = sorted(set(candidate.verifier_routes) - set(resolution_by_route))
        if missing_routes:
            reasons.append("packet verifier route resolution is missing")
            for route in missing_routes:
                residual = residual.add_coordinate(
                    f"packet-promotion:{candidate.packet_id}:missing-route:{route}",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
    rejected_resolutions = [
        resolution for resolution in matched_resolutions if not resolution.accepted
    ]
    if rejected_resolutions:
        reasons.append("packet verifier route resolution is rejected")
    accepted_edge_ids: list[str] = []
    for certificate in sorted(edge_certificates, key=lambda item: item.certificate_id):
        if candidate.packet_id != certificate.target_packet_id:
            continue
        if certificate.confidence_lower_bound < active_policy.minimum_confidence_lower_bound:
            residual = residual.add_coordinate(
                f"packet-promotion:{candidate.packet_id}:low-edge-confidence",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            continue
        if certificate.accepted:
            accepted_edge_ids.append(certificate.edge_id)
            residual = residual.combine(certificate.residual_ledger)
    if active_policy.require_edge_certificate and not accepted_edge_ids:
        reasons.append("packet has no accepted edge certificate")
    residual_external = sorted(
        {
            obligation
            for resolution in matched_resolutions
            for obligation in resolution.residual_external_obligations
        }
    )
    if residual_external and not active_policy.allow_residual_external_obligations:
        reasons.append("packet has unresolved external domain obligations")
    for obligation in residual_external:
        residual = residual.add_coordinate(
            f"packet-promotion:{candidate.packet_id}:external:{obligation}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    if reasons:
        return PacketRejection(
            packet_id=f"rejected:{candidate.packet_id}",
            source_candidate_id=candidate.packet_id,
            reasons=sorted(set(reasons)),
            residual_ledger=residual,
        )
    settlement_scope = sorted(
        {scope for resolution in matched_resolutions for scope in resolution.settled_scope}
    )
    liquidity = max(
        0.0,
        candidate.expected_downstream_gain
        - candidate.verification_cost
        - candidate.residual_charge
        - candidate.hazard_charge
        - residual.burden_sum(),
    )
    return VerifiedCapabilityPacket(
        packet_id=f"verified:{candidate.packet_id}",
        source_candidate_id=candidate.packet_id,
        verification_resolution_ids=sorted(
            resolution.resolution_id for resolution in matched_resolutions
        ),
        accepted_edge_witness_ids=sorted(accepted_edge_ids),
        receiver_family=sorted(candidate.receiver_family),
        liquidity_score=liquidity,
        execution_available=bool(candidate.rollback_available and candidate.route_safe),
        settlement_scope=settlement_scope,
        residual_external_obligations=residual_external,
        residual_ledger=residual,
        expires_at=candidate.expires_at,
        rollback_receipt="candidate-rollback-available" if candidate.rollback_available else None,
        operationally_usable=liquidity > 0.0,
        settled=False,
    )


def promote_runtime_packets(
    packets: Sequence[CapabilityPacketCandidate],
    resolutions: Sequence[VerifierResolution],
    edge_certificates: Sequence[EdgeWitnessCertificate],
    policy: PacketPromotionPolicy | None = None,
    *,
    report_id: str = "packet-promotion:runtime",
) -> PacketPromotionReport:
    """Promote a deterministic batch of runtime packet candidates."""

    verified: list[VerifiedCapabilityPacket] = []
    rejected: list[PacketRejection] = []
    residual = Ledger()
    for packet in sorted(packets, key=lambda item: item.packet_id):
        result = promote_packet_candidate(packet, resolutions, edge_certificates, policy)
        residual = residual.combine(result.residual_ledger)
        if isinstance(result, VerifiedCapabilityPacket):
            verified.append(result)
        else:
            rejected.append(result)
    return PacketPromotionReport(
        report_id=report_id,
        accepted=bool(verified),
        verified_packets=verified,
        rejected_packets=rejected,
        residual_ledger=residual,
    )


def runtime_health(
    state: RuntimeState,
    config: AgentRuntimeConfig | None = None,
) -> RuntimeHealthReport:
    """Return a finite runtime health report without performing agent actions."""

    active_config = config or AgentRuntimeConfig()
    dashboard = build_psi_dashboard(
        state.packet_registry,
        threshold=active_config.psi_threshold or state.psi_threshold or None,
    )
    routes = sorted(
        {route for packet in state.packet_registry.packets for route in packet.verifier_routes}
        | set(state.phase_state.route_ids)
        | set(active_config.required_routes)
    )
    missing = [
        route
        for route in routes
        if route not in {spec.route_id for spec in list_adapter_route_specs()}
        and route not in {spec.verifier_route for spec in list_adapter_route_specs()}
    ]
    checks = {
        "live_connectors": "enabled" if active_config.allow_live_connectors else "disabled",
        "packet_registry": "present" if state.packet_registry.packets else "empty",
        "residual_ledger": "nonempty" if state.residual_ledger.coordinates else "empty",
        "required_routes": "complete" if not missing else "missing",
    }
    accepted = not missing and bool(state.phase_actions or state.packet_registry.packets)
    return RuntimeHealthReport(
        report_id=f"runtime-health:{state.state_id}:{active_config.profile}",
        state_id=state.state_id,
        profile=active_config.profile,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and active_config.profile != "production",
        settled=False,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        packet_count=len(state.packet_registry.packets),
        edge_count=len(state.packet_registry.edges),
        route_count=len(routes),
        residual_debt=state.residual_ledger.burden_sum()
        + state.packet_registry.residual_ledger.burden_sum(),
        psi_components=dashboard.components,
        missing_obligations=missing,
        checks=checks,
    )


def phase_acceleration_score(
    *,
    score_id: str,
    phase_report: PhaseControlRunReport,
    bottleneck_plan: object,
    registry: CapabilityPacketRegistry,
    route_requests: Sequence[RouteExecutionRequest],
    schedule_residual: float = 0.0,
    prior_residual_debt: float = 0.0,
) -> PhaseAccelerationScore:
    """Compute a finite ECPT ASI-proxy acceleration score."""

    interventions = getattr(bottleneck_plan, "interventions", [])
    before = getattr(bottleneck_plan, "before_psi", {})
    after = getattr(bottleneck_plan, "after_psi_lower_bound", {})
    finite_proxy_gain = phase_report.plan.finite_proxy_gain_total + sum(
        max(0.0, item.expected_gain) for item in interventions
    )
    psi_distance_reduction = sum(
        max(0.0, float(after.get(key, 0.0)) - float(before.get(key, 0.0)))
        for key in sorted(set(before) | set(after))
    )
    throughput = max(
        0.0,
        (registry.residual_ledger.benefit_sum() + len(registry.edges) + 1.0)
        / (len(route_requests) + registry.residual_ledger.burden_sum() + 1.0),
    )
    residual_debt = (
        registry.residual_ledger.burden_sum()
        + phase_report.plan.residual_ledger.burden_sum()
        + float(schedule_residual)
        + max(0.0, prior_residual_debt)
    )
    risk_charge = sum(max(0.0, candidate.risk_charge) for candidate in phase_report.plan.candidates)
    stale_charge = _stale_ratio(registry)
    false_liquidity_charge = _false_liquidity_rate(registry)
    missing_route_charge = 0.25 * float(
        sum(1 for request in route_requests if request.residual_external_obligations)
        + len(phase_report.plan.missing_obligations)
    )
    total = (
        finite_proxy_gain
        + psi_distance_reduction
        + throughput
        - residual_debt
        - risk_charge
        - stale_charge
        - false_liquidity_charge
        - missing_route_charge
    )
    components = {
        "finite_proxy_gain": finite_proxy_gain,
        "missing_route_charge": missing_route_charge,
        "psi_distance_reduction": psi_distance_reduction,
        "residual_debt_charge": residual_debt,
        "risk_charge": risk_charge,
        "stale_packet_charge": stale_charge,
        "verification_throughput_score": throughput,
    }
    return PhaseAccelerationScore(
        score_id=score_id,
        total_score=total,
        finite_proxy_gain=finite_proxy_gain,
        psi_distance_reduction=psi_distance_reduction,
        verification_throughput_score=throughput,
        residual_debt_charge=residual_debt,
        risk_charge=risk_charge,
        stale_packet_charge=stale_charge,
        false_liquidity_charge=false_liquidity_charge,
        missing_route_charge=missing_route_charge,
        components=dict(sorted(components.items())),
    )


def _ingest_step_sources(
    step_input: RuntimeStepInput,
    config: AgentRuntimeConfig,
) -> list[PacketIngestionReport]:
    reports: list[PacketIngestionReport] = []
    if step_input.agent_output:
        reports.append(ingest_agent_output(step_input.agent_output, output_id=step_input.input_id))
    for source in step_input.local_sources:
        reports.append(_ingest_local_source(Path(source)))
    for source in step_input.live_sources:
        if not _live_enabled(step_input, config):
            reports.append(
                _diagnostic_ingestion(
                    PacketSourceKind.AUTO,
                    source,
                    "live connector source requires allow_live_connectors=true in input and config",
                )
            )
            continue
        reports.append(ingest_live_source(source, kind=infer_live_kind(source)))
    return reports


def _live_enabled(step_input: RuntimeStepInput, config: AgentRuntimeConfig) -> bool:
    return config.allow_live_connectors and step_input.allow_live_connectors


def _ingest_local_source(source: Path) -> PacketIngestionReport:
    if not source.exists() or not source.is_file():
        return _diagnostic_ingestion(
            PacketSourceKind.LOCAL,
            source.name,
            "local packet source does not exist or is not a file",
        )
    return ingest_local_file(source)


def _diagnostic_ingestion(
    source_kind: PacketSourceKind,
    source_ref: str,
    reason: str,
) -> PacketIngestionReport:
    residual = Ledger().add_coordinate(
        f"runtime-ingest:{source_kind.value}:{Path(source_ref).name}:diagnostic",
        1.0,
        kind=CoordinateKind.RESIDUAL,
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:diagnostic:{source_kind.value}",
        accepted=False,
        source_kind=source_kind,
        rejected_sources=[Path(source_ref).name],
        reasons=[reason],
        residual_ledger=residual,
    )


def _merge_packets(
    state: RuntimeState,
    step_input: RuntimeStepInput,
    reports: Sequence[PacketIngestionReport],
) -> tuple[list[CapabilityPacketCandidate], Ledger, list[str]]:
    packets: dict[str, CapabilityPacketCandidate] = {}
    residual = state.residual_ledger.combine(state.packet_registry.residual_ledger)
    reasons: list[str] = []
    for packet in [*state.packet_registry.packets, *step_input.packets]:
        packets.setdefault(packet.packet_id, packet)
    for report in reports:
        residual = residual.combine(report.residual_ledger)
        for packet in report.packets:
            if packet.packet_id in packets:
                residual = residual.add_coordinate(
                    f"runtime-packet:{packet.packet_id}:duplicate",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
                reasons.append(f"duplicate packet id preserved first packet: {packet.packet_id}")
                continue
            packets[packet.packet_id] = packet
    return sorted(packets.values(), key=lambda item: item.packet_id), residual, reasons


def _build_phase_report(
    state: RuntimeState,
    config: AgentRuntimeConfig,
) -> PhaseControlRunReport:
    if state.phase_actions:
        return build_phase_control_plan(
            state.phase_state,
            state.phase_objective,
            state.phase_actions,
            profile=config.profile,
        )
    plan = PhaseControlPlan(
        plan_id=f"phase-control-plan:{state.state_id}:empty",
        objective_id=state.phase_objective.objective_id,
        profile=config.profile,
        accepted=False,
        status=ClaimStatus.DIAGNOSTIC,
        partial=True,
        reasons=["runtime state has no phase-control actions"],
        missing_obligations=["phase-control-action-catalog"],
    )
    return PhaseControlRunReport(
        report_id=f"phase-control-run:{state.state_id}:empty",
        state_id=state.phase_state.state_id,
        target_id=state.phase_objective.target.target_id,
        plan=plan,
        baseline_reachable_mass=dict(sorted(reachable_mass(state.phase_state.graph).items())),
        controlled_reachable_mass=dict(sorted(reachable_mass(state.phase_state.graph).items())),
    )


def _routes_from_runtime_outputs(
    phase_report: PhaseControlRunReport,
    bottleneck_plan: object,
    config: AgentRuntimeConfig,
) -> list[str]:
    routes = set(config.required_routes)
    routes.update(phase_report.plan.required_evidence_routes)
    for action in phase_report.plan.selected_actions:
        routes.update(action.verifier_routes)
    for intervention in getattr(bottleneck_plan, "interventions", []):
        routes.update(intervention.required_routes)
    return sorted(routes)


def _route_requests(
    route_ids: Sequence[str],
    *,
    priority_score: float,
) -> list[RouteExecutionRequest]:
    by_key: dict[str, AdapterRouteSpec] = {}
    for route_spec in list_adapter_route_specs():
        by_key[route_spec.route_id] = route_spec
        by_key[route_spec.verifier_route] = route_spec
    requests: list[RouteExecutionRequest] = []
    for route in sorted(set(route_ids)):
        spec = by_key.get(route)
        if spec is None:
            requests.append(
                RouteExecutionRequest(
                    request_id=f"route-request:unknown:{route}",
                    route_id=route,
                    verifier_route=route,
                    obligation_category="unknown-route",
                    safe_default="diagnostic-with-unknown-route",
                    residual_policy="preserve-unknown-route-obligation",
                    residual_external_obligations=["unknown-route-binding"],
                    priority_score=priority_score,
                )
            )
            continue
        binding = binding_for_route(spec.route_id)
        requests.append(
            RouteExecutionRequest(
                request_id=f"route-request:{spec.route_id}",
                route_id=spec.route_id,
                verifier_route=spec.verifier_route,
                obligation_category=spec.obligation_category,
                required_evidence_kind=spec.required_evidence_kind,
                safe_default=spec.safe_default,
                residual_policy=spec.residual_policy,
                settlement_scope=[] if binding is None else binding.settlement_scope,
                residual_external_obligations=(
                    [] if binding is None else binding.residual_external_obligation_refs
                ),
                priority_score=priority_score,
                status=ClaimStatus.DIAGNOSTIC,
            )
        )
    return requests


def _agent_tasks(
    *,
    phase_actions: Sequence[PhaseControlAction],
    bottleneck_interventions: Sequence[BottleneckIntervention],
    route_specs: Mapping[str, AdapterRouteSpec],
    max_tasks: int,
    minimum_task_score: float,
) -> list[AgentTask]:
    tasks: list[AgentTask] = []
    for intervention in bottleneck_interventions:
        if intervention.score < minimum_task_score:
            continue
        tasks.append(
            AgentTask(
                task_id=f"task:{intervention.intervention_id}",
                task_type="bottleneck-intervention",
                priority_score=intervention.score,
                target_component=intervention.target_component,
                action_kind=intervention.action_kind,
                expected_proxy_gain=intervention.expected_gain,
                required_routes=intervention.required_routes,
                required_evidence_kind=_evidence_kinds(intervention.required_routes, route_specs),
                residual_coordinates=sorted(intervention.residual_ledger.coordinates),
                rollback_condition=intervention.rollback_condition,
                operationally_usable=intervention.score > 0.0,
                settled=False,
                reasons=[] if intervention.score > 0.0 else ["nonpositive intervention score"],
            )
        )
    for action in phase_actions:
        routes = sorted(action.verifier_routes)
        score = (
            action.activation_delta
            - action.burden_delta
            - action.residual_charge
            - action.risk_charge
        )
        if score < minimum_task_score:
            continue
        tasks.append(
            AgentTask(
                task_id=f"task:phase-action:{action.action_id}",
                task_type="phase-control-action",
                priority_score=score,
                target_component=action.target_node,
                action_kind="execute-phase-control-action",
                action_id=action.action_id,
                expected_proxy_gain=max(0.0, action.activation_delta),
                required_routes=routes,
                required_evidence_kind=_evidence_kinds(routes, route_specs),
                residual_coordinates=sorted(action.required_obligations),
                rollback_condition="verifier-resolution-missing-or-negative-proxy-gain",
                operationally_usable=score > 0.0,
                settled=False,
                reasons=[] if score > 0.0 else ["nonpositive phase-action score"],
            )
        )
    return sorted(tasks, key=lambda item: (-item.priority_score, item.task_id))[: max(0, max_tasks)]


def _evidence_kinds(routes: Sequence[str], specs: Mapping[str, AdapterRouteSpec]) -> list[str]:
    by_key: dict[str, AdapterRouteSpec] = {}
    for spec in specs.values():
        by_key[spec.route_id] = spec
        by_key[spec.verifier_route] = spec
    kinds: set[str] = set()
    for route in routes:
        route_spec = by_key.get(route)
        if route_spec is not None:
            kinds.update(route_spec.required_evidence_kind)
    return sorted(kinds)


def _salience_records(
    tasks: Sequence[AgentTask],
    registry: CapabilityPacketRegistry,
) -> list[SalienceQueueRecord]:
    records: list[SalienceQueueRecord] = []
    for task in tasks:
        records.append(
            SalienceQueueRecord(
                record_id=task.task_id,
                item_type="verifier-task" if task.required_routes else "agent-task",
                salience_class=task.task_type,
                expected_downstream_gain=task.expected_proxy_gain,
                residual_reduction=max(0.0, task.priority_score),
                verification_cost=max(0.01, len(task.required_evidence_kind) * 0.1),
                freshness=1.0,
                hazard_charge=0.0 if task.operationally_usable else 0.2,
                obligation_ids=task.residual_coordinates,
                verifier_routes=task.required_routes,
            )
        )
    for packet in registry.packets:
        records.append(
            SalienceQueueRecord(
                record_id=f"queue:{packet.packet_id}",
                item_type="packet",
                salience_class=packet.salience_class,
                expected_downstream_gain=packet.expected_downstream_gain,
                residual_reduction=max(0.0, 1.0 - packet.residual_charge),
                verification_cost=packet.verification_cost,
                freshness=packet.freshness,
                hazard_charge=packet.hazard_charge,
                authority_required=packet.authority_required,
                authority_granted=packet.authority_granted,
                stale=packet.expires_at == "expired",
                evidence_hash_valid=packet.evidence_hash_valid,
                route_safe=packet.route_safe,
                rollback_available=packet.rollback_available,
                obligation_ids=packet.evidence_refs,
                verifier_routes=packet.verifier_routes,
            )
        )
    return records


def _schedule_residual(schedule: object) -> Ledger:
    residual = Ledger()
    for decision in getattr(schedule, "decisions", []):
        residual = residual.combine(decision.residual_ledger)
    return residual


def _action_commit(action: PhaseControlAction, policy: ActionCommitPolicy) -> ActionCommit:
    finite_scope_usable = action.activation_delta > 0 and action.risk_charge >= 0
    reasons: list[str] = []
    if policy == ActionCommitPolicy.RECOMMEND_ONLY:
        reasons.append("policy is recommend_only")
    if policy == ActionCommitPolicy.REQUIRE_VERIFIER_RESOLUTION:
        reasons.append("verifier resolution required before action commit")
    committed = policy == ActionCommitPolicy.ALLOW_FINITE_SCOPE_COMMIT and finite_scope_usable
    return ActionCommit(
        action_id=action.action_id,
        policy=policy,
        recommended=True,
        committed=committed,
        finite_scope_usable=finite_scope_usable,
        verifier_resolution_required=policy == ActionCommitPolicy.REQUIRE_VERIFIER_RESOLUTION,
        operationally_usable=committed,
        settled=False,
        reasons=reasons,
    )


def _stale_ratio(registry: CapabilityPacketRegistry) -> float:
    if not registry.packets:
        return 0.0
    return sum(1 for packet in registry.packets if packet.expires_at == "expired") / len(
        registry.packets
    )


def _false_liquidity_rate(registry: CapabilityPacketRegistry) -> float:
    if not registry.packets:
        return 0.0
    false = sum(
        1
        for packet in registry.packets
        if packet.expected_downstream_gain <= 0.0
        or packet.verification_cost > packet.expected_downstream_gain
    )
    return false / len(registry.packets)


def loop_state_after_report(state: RuntimeState, report: RuntimeStepReport) -> RuntimeState:
    """Return the next persistent state after a runtime report."""

    verified = _merge_verified_packets(
        state.verified_packets,
        report.promotion_report.verified_packets,
    )
    quarantine = _merge_quarantine_ledgers(
        state.quarantine_ledger,
        report.salience_schedule.quarantine_ledger,
    )
    event_log = _event_log_with_hash([*state.event_log.events, *report.event_log_delta.events])
    return state.model_copy(
        update={
            "packet_registry": report.registry,
            "residual_ledger": report.residual_ledger,
            "step_index": state.step_index + 1,
            "runtime_memory": [*state.runtime_memory, report.report_id],
            "event_log": event_log,
            "verified_packets": verified,
            "quarantine_ledger": quarantine,
        }
    )


def collect_missing_routes(
    route_ids: Iterable[str],
) -> list[str]:
    """Return unknown route ids for diagnostics and tests."""

    known = {
        key for spec in list_adapter_route_specs() for key in (spec.route_id, spec.verifier_route)
    }
    return sorted(set(route_ids) - known)


def apply_action_results(
    state: RuntimeState,
    report: RuntimeStepReport,
    results: Sequence[RuntimeActionResult],
) -> RuntimeState:
    """Apply agent task results without creating a new status-promotion path."""

    packets = {packet.packet_id: packet for packet in report.registry.packets}
    residual = report.residual_ledger
    events = list(state.event_log.events)
    reasons: list[str] = []
    for result in sorted(results, key=lambda item: item.result_id):
        residual = residual.combine(result.residual_ledger)
        for packet in result.output_packets:
            packets.setdefault(packet.packet_id, packet)
        if result.verifier_resolution is not None:
            residual = residual.combine(result.verifier_resolution.residual_ledger)
        if not result.executed:
            reasons.append(f"result {result.result_id} was not executed")
            residual = residual.add_coordinate(
                f"runtime-result:{result.result_id}:not-executed",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        events.append(
            _runtime_event(
                event_id=f"event:{state.state_id}:{report.step_index}:{result.result_id}",
                event_type="runtime-action-result",
                step_index=report.step_index,
                payload_ref=result.output_ref or result.result_id,
                payload=result.model_dump(mode="json"),
                residual_delta=result.residual_ledger,
            )
        )
    edges = build_edge_witnesses(list(packets.values()))
    registry = build_packet_registry(
        list(packets.values()),
        edges,
        registry_id=f"{report.registry.registry_id}:applied",
    )
    return state.model_copy(
        update={
            "packet_registry": registry,
            "residual_ledger": residual.combine(registry.residual_ledger),
            "step_index": max(state.step_index, report.step_index + 1),
            "runtime_memory": [
                *state.runtime_memory,
                report.report_id,
                *[result.result_id for result in results],
            ],
            "event_log": _event_log_with_hash(events),
            "quarantine_ledger": _merge_quarantine_ledgers(
                state.quarantine_ledger,
                report.salience_schedule.quarantine_ledger,
            ),
        }
    )


def build_runtime_run_report(
    initial_state: RuntimeState,
    reports: Sequence[RuntimeStepReport],
    *,
    run_id: str | None = None,
    threshold: Mapping[str, float] | None = None,
) -> RuntimeRunReport:
    """Summarize a runtime trajectory for finite baseline comparison."""

    cumulative = initial_state.residual_ledger
    psi = [report.psi for report in reports]
    scores = [report.phase_acceleration_score for report in reports]
    for report in reports:
        cumulative = cumulative.combine(report.residual_ledger)
    crossing = _threshold_crossing_step(psi, threshold)
    accepted = bool(reports) and all(report.finite_checks_passed for report in reports)
    return RuntimeRunReport(
        run_id=run_id or f"runtime-run:{initial_state.state_id}:{len(reports)}",
        initial_state_id=initial_state.state_id,
        reports=list(reports),
        psi_trajectory=psi,
        score_trajectory=scores,
        cumulative_residual_ledger=cumulative,
        threshold_crossing_step=crossing,
        resource_units=float(len(reports)),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and any(report.agent_tasks for report in reports),
        settled=False,
    )


def certify_runtime_acceleration(
    baseline: RuntimeRunReport,
    candidate: RuntimeRunReport,
    threshold: Mapping[str, float] | None = None,
) -> AccelerationCertificate:
    """Build a finite ASI-proxy acceleration certificate against a baseline."""

    active_threshold = dict(threshold or {})
    resource_matched = abs(baseline.resource_units - candidate.resource_units) <= 0.0
    tau_baseline = (
        None
        if baseline.threshold_crossing_step is None
        else float(baseline.threshold_crossing_step)
    )
    tau_candidate = (
        None
        if candidate.threshold_crossing_step is None
        else float(candidate.threshold_crossing_step)
    )
    hitting_gain = 0.0
    if tau_baseline is not None and tau_candidate is not None:
        hitting_gain = max(0.0, tau_baseline - tau_candidate)
    psi_gain = max(0.0, _final_psi_mass(candidate) - _final_psi_mass(baseline))
    score_gain = max(0.0, _final_score(candidate) - _final_score(baseline))
    residual_gain = baseline.cumulative_residual_ledger.burden_sum() - (
        candidate.cumulative_residual_ledger.burden_sum()
    )
    salience_non_obstructed = all(
        not report.salience_schedule.quarantine_ledger.quarantined_items
        for report in candidate.reports
    )
    false_liquidity_bounded = all(
        report.psi.throughput.false_liquidity_rate <= 0.25 for report in candidate.reports
    )
    verification_backlog_bounded = all(
        report.psi.throughput.unresolved_obligation_backlog
        <= max(1, len(report.route_execution_requests) + len(report.registry.packets))
        for report in candidate.reports
    )
    residual_external = sorted(
        {
            obligation
            for report in candidate.reports
            for request in report.route_execution_requests
            for obligation in request.residual_external_obligations
        }
    )
    reasons: list[str] = []
    if not resource_matched:
        reasons.append("runtime runs are not resource matched")
    if score_gain <= 0.0 and psi_gain <= 0.0 and hitting_gain <= 0.0:
        reasons.append("candidate has no positive finite acceleration lower bound")
    if not salience_non_obstructed:
        reasons.append("candidate run is obstructed by SQOT quarantine")
    if not false_liquidity_bounded:
        reasons.append("candidate false-liquidity rate exceeds bound")
    if not verification_backlog_bounded:
        reasons.append("candidate verifier backlog exceeds bound")
    if residual_gain < 0.0:
        reasons.append("candidate residual debt exceeds baseline")
    accepted = not reasons
    residual = candidate.cumulative_residual_ledger
    for obligation in residual_external:
        residual = residual.add_coordinate(
            f"acceleration-certificate:{candidate.run_id}:external:{obligation}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    return AccelerationCertificate(
        certificate_id=f"acceleration-certificate:{baseline.run_id}:{candidate.run_id}",
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        threshold=dict(sorted(active_threshold.items())),
        tau_baseline=tau_baseline,
        tau_candidate=tau_candidate,
        hitting_time_gain_lower_bound=hitting_gain,
        psi_distance_reduction_lower_bound=psi_gain,
        score_gain_lower_bound=score_gain,
        resource_matched=resource_matched,
        salience_non_obstructed=salience_non_obstructed,
        false_liquidity_bounded=false_liquidity_bounded,
        verification_backlog_bounded=verification_backlog_bounded,
        residual_external_obligations=residual_external,
        residual_ledger=residual,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )


def compare_runtime_runs(
    baseline: RuntimeRunReport,
    candidate: RuntimeRunReport,
    threshold: Mapping[str, float] | None = None,
) -> RuntimeComparisonReport:
    """Compare baseline and candidate runtime trajectories."""

    certificate = certify_runtime_acceleration(baseline, candidate, threshold)
    return RuntimeComparisonReport(
        comparison_id=f"runtime-comparison:{baseline.run_id}:{candidate.run_id}",
        baseline=baseline,
        candidate=candidate,
        resource_matched=certificate.resource_matched,
        acceleration_certificate=certificate,
        accepted=certificate.accepted,
        finite_checks_passed=certificate.finite_checks_passed,
        operationally_usable=certificate.operationally_usable,
        settled=False,
    )


def _runtime_event(
    *,
    event_id: str,
    event_type: str,
    step_index: int,
    payload_ref: str,
    payload: Mapping[str, object],
    residual_delta: Ledger,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        event_type=event_type,
        step_index=step_index,
        payload_ref=Path(payload_ref).name,
        payload_sha256=_stable_digest(payload),
        residual_delta=residual_delta,
    )


def _event_log_with_hash(events: Sequence[RuntimeEvent]) -> RuntimeEventLog:
    sorted_events = sorted(events, key=lambda item: item.event_id)
    digest = _stable_digest([event.model_dump(mode="json") for event in sorted_events])
    return RuntimeEventLog(events=sorted_events, aggregate_sha256=digest)


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _merge_verified_packets(
    existing: Sequence[VerifiedCapabilityPacket],
    new_packets: Sequence[VerifiedCapabilityPacket],
) -> list[VerifiedCapabilityPacket]:
    packets = {packet.packet_id: packet for packet in existing}
    for packet in new_packets:
        packets.setdefault(packet.packet_id, packet)
    return sorted(packets.values(), key=lambda item: item.packet_id)


def _merge_quarantine_ledgers(left: QuarantineLedger, right: QuarantineLedger) -> QuarantineLedger:
    reasons = dict(left.reasons)
    for key, value in right.reasons.items():
        reasons[key] = sorted(set(reasons.get(key, []) + value))
    return QuarantineLedger(
        quarantined_items=sorted(set(left.quarantined_items + right.quarantined_items)),
        rollback_items=sorted(set(left.rollback_items + right.rollback_items)),
        reasons=dict(sorted(reasons.items())),
    )


def _threshold_crossing_step(
    psi_trajectory: Sequence[object],
    threshold: Mapping[str, float] | None,
) -> int | None:
    active_threshold = dict(threshold or {})
    for index, psi in enumerate(psi_trajectory):
        components = getattr(psi, "components", {})
        psi_threshold = active_threshold or getattr(psi, "threshold", {})
        if psi_threshold and all(
            float(components.get(key, 0.0)) >= float(value) for key, value in psi_threshold.items()
        ):
            return index
    return None


def _final_psi_mass(run: RuntimeRunReport) -> float:
    if not run.psi_trajectory:
        return 0.0
    return sum(max(0.0, value) for value in run.psi_trajectory[-1].components.values())


def _final_score(run: RuntimeRunReport) -> float:
    if not run.score_trajectory:
        return 0.0
    return run.score_trajectory[-1].total_score
