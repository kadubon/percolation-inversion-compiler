"""Deterministic ECPT active runtime algorithms."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from percolation_inversion_compiler.core import (
    AdapterRouteSpec,
    VerifierEvidenceEnvelope,
    VerifierResolution,
    binding_for_route,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology import (
    BottleneckIntervention,
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitness,
    EdgeWitnessCertificate,
    PacketIngestionReport,
    PacketPromotionPolicy,
    PacketPromotionReport,
    PacketRejection,
    PacketSourceKind,
    VerifiedCapabilityPacket,
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_capital_lineage,
    build_packet_registry,
    build_psi_dashboard,
    check_no_hidden_capability_injection,
    edge_certificate_from_witness,
    edge_relation_verifier_spec,
    find_autocatalytic_closures,
    find_execution_available_paths,
    infer_live_kind,
    ingest_agent_output,
    ingest_live_source,
    ingest_local_file,
    verify_edge_relation,
)
from percolation_inversion_compiler.ecpt import (
    PhaseControlAction,
    PhaseControlPlan,
    PhaseControlRunReport,
    build_phase_control_plan,
    reachable_mass,
)
from percolation_inversion_compiler.identity import (
    IdentityContributionStatus,
    SybilResistancePolicy,
    check_sybil_resistance,
    identity_contribution_status_for_packet,
    normalize_identity_profile,
    sybil_policy_for_profile,
)
from percolation_inversion_compiler.runtime.records import (
    AccelerationCertificate,
    AccelerationExperimentSuite,
    ActionCommit,
    ActionCommitPolicy,
    AgentPopulationState,
    AgentRuntimeConfig,
    AgentTask,
    CollectivePhaseCertificate,
    EvidenceResolutionBatch,
    FixedPopulationLedger,
    PhaseAccelerationScore,
    PopulationRuntimeStepReport,
    ResourceEnvelope,
    ResourceMatchedBaselineConfig,
    RouteExecutionBatch,
    RouteExecutionRequest,
    RuntimeActionResult,
    RuntimeComparisonReport,
    RuntimeEvent,
    RuntimeEventLog,
    RuntimeExecutionReport,
    RuntimeExecutorPolicy,
    RuntimeHealthReport,
    RuntimeIdentityContext,
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


class FileEvidenceEnvelopeStore:
    """Sandboxed content-addressed verifier-envelope store."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def load(self, ref: str, *, profile: str = "development") -> VerifierEvidenceEnvelope | None:
        path = self._path_for_ref(ref)
        if path is None or not path.exists() or not path.is_file():
            return None
        digest = _file_sha256(path)
        if ref.startswith("sha256:") and digest != ref.removeprefix("sha256:").lower():
            return None
        if profile == "production" and not ref.startswith("sha256:"):
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            envelope = VerifierEvidenceEnvelope.model_validate(payload)
        except ValueError:
            return None
        if profile == "production" and not envelope.evidence_artifacts:
            return None
        return envelope

    def _path_for_ref(self, ref: str) -> Path | None:
        if ref.startswith("sha256:"):
            digest = ref.removeprefix("sha256:").lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                return None
            path = self.root / f"{digest}.json"
        else:
            raw = Path(ref)
            if raw.is_absolute() or ".." in raw.parts:
                return None
            path = self.root / raw
        resolved = path.resolve()
        if self.root not in resolved.parents and resolved != self.root:
            return None
        return resolved


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
    registry = build_packet_registry(
        packets,
        edges,
        registry_id=f"runtime-registry:{state.state_id}:{step_input.input_id}",
    )
    edge_relation_reports = [
        verify_edge_relation(
            registry,
            certificate,
            edge_relation_verifier_spec(certificate.relation_type),
        )
        for certificate in edge_certificates
    ]
    semantic_edge_certificates = [
        certificate if report.accepted else certificate.model_copy(update={"accepted": False})
        for certificate, report in zip(edge_certificates, edge_relation_reports, strict=True)
    ]
    for report in edge_relation_reports:
        residual = residual.combine(report.residual_ledger)
    route_inventory = _merge_verifier_resolutions(
        state.verifier_resolution_inventory,
        evidence_batch.resolutions,
    )
    identity_profile = active_config.identity_profile or active_config.profile
    promotion_policy = PacketPromotionPolicy.for_profile(identity_profile)
    if packets and promotion_policy.require_issuer_in_population and not state.accepted_agent_ids:
        residual = residual.add_coordinate(
            f"runtime-identity:{state.state_id}:missing-accepted-agent-context",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("accepted agent identity context is missing for packet promotion")
    if (
        packets
        and promotion_policy.require_issuer_in_population
        and not state.accepted_public_key_ids
    ):
        residual = residual.add_coordinate(
            f"runtime-identity:{state.state_id}:missing-accepted-public-key-context",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
        reasons.append("accepted public key identity context is missing for packet promotion")
    promotion_report = promote_runtime_packets(
        packets,
        route_inventory,
        semantic_edge_certificates,
        promotion_policy,
        report_id=f"packet-promotion:{state.state_id}:{step_input.input_id}",
        accepted_agent_ids=state.accepted_agent_ids,
        accepted_public_key_ids=state.accepted_public_key_ids,
        identity_profile=identity_profile,
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
        edge_relation_reports=edge_relation_reports,
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
    envelope_store: FileEvidenceEnvelopeStore | None = None,
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
    loaded_envelopes, loaded_residual, unresolved_refs = load_evidence_refs(
        step_input,
        envelope_store,
        profile=profile,
    )
    residual = residual.combine(loaded_residual)
    envelopes = [*step_input.evidence_envelopes, *loaded_envelopes]
    for envelope in sorted(envelopes, key=lambda item: item.envelope_id):
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
    finite = bool(resolutions) and all(resolution.accepted for resolution in resolutions)
    return EvidenceResolutionBatch(
        batch_id=f"evidence-resolution:{step_input.input_id}",
        envelope_refs=[
            *sorted(step_input.evidence_envelope_refs),
            *[envelope.envelope_id for envelope in envelopes],
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


def load_evidence_refs(
    step_input: RuntimeStepInput,
    envelope_store: FileEvidenceEnvelopeStore | None,
    *,
    profile: str = "development",
) -> tuple[list[VerifierEvidenceEnvelope], Ledger, list[str]]:
    """Load content-addressed evidence refs without trusting unresolved metadata."""

    residual = Ledger()
    loaded: list[VerifierEvidenceEnvelope] = []
    unresolved: list[str] = []
    for ref in sorted(step_input.evidence_envelope_refs):
        envelope = envelope_store.load(ref, profile=profile) if envelope_store is not None else None
        if envelope is None:
            unresolved.append(Path(ref).name if not ref.startswith("sha256:") else ref)
            residual = residual.add_coordinate(
                f"runtime-evidence-ref:{Path(ref).name}:unresolved",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            continue
        loaded.append(envelope)
    return loaded, residual, unresolved


def promote_packet_candidate(
    candidate: CapabilityPacketCandidate,
    resolutions: Sequence[VerifierResolution],
    edge_certificates: Sequence[EdgeWitnessCertificate],
    policy: PacketPromotionPolicy | None = None,
    *,
    accepted_agent_ids: Sequence[str] | None = None,
    accepted_public_key_ids: Sequence[str] | None = None,
    identity_profile: str = "development",
) -> VerifiedCapabilityPacket | PacketRejection:
    """Promote one packet candidate to finite-scope reusable packet capital."""

    active_policy = policy or PacketPromotionPolicy()
    residual = Ledger()
    reasons: list[str] = []
    contribution_status = identity_contribution_status_for_packet(
        candidate,
        None,
        identity_profile,
    )
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
    if active_policy.require_agent_identity_attestation:
        missing_identity_fields = [
            field_name
            for field_name, value in {
                "issuer_agent_id": candidate.issuer_agent_id,
                "issuer_public_key_id": candidate.issuer_public_key_id,
                "issuer_attestation_id": candidate.issuer_attestation_id,
                "issuer_signature_ref": candidate.issuer_signature_ref,
            }.items()
            if not value
        ]
        if missing_identity_fields:
            reasons.append("packet issuer identity attestation is missing")
            for field_name in missing_identity_fields:
                residual = residual.add_coordinate(
                    f"packet-promotion:{candidate.packet_id}:missing-{field_name}",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
    if active_policy.require_issuer_in_population:
        if accepted_agent_ids is None:
            reasons.append("accepted agent identity context is missing")
            residual = residual.add_coordinate(
                f"packet-promotion:{candidate.packet_id}:missing-accepted-agent-context",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        elif candidate.issuer_agent_id not in set(accepted_agent_ids):
            reasons.append("packet issuer is outside accepted population")
            residual = residual.add_coordinate(
                f"packet-promotion:{candidate.packet_id}:issuer-outside-population",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        if accepted_public_key_ids is None:
            reasons.append("accepted public key identity context is missing")
            residual = residual.add_coordinate(
                f"packet-promotion:{candidate.packet_id}:missing-accepted-public-key-context",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
        elif candidate.issuer_public_key_id not in set(accepted_public_key_ids):
            reasons.append("packet issuer public key is outside accepted population")
            residual = residual.add_coordinate(
                f"packet-promotion:{candidate.packet_id}:issuer-key-outside-population",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
    if (
        candidate.issuer_agent_id in set(accepted_agent_ids or [])
        and candidate.issuer_public_key_id in set(accepted_public_key_ids or [])
        and candidate.issuer_attestation_id
        and candidate.issuer_signature_ref
    ):
        contribution_status = IdentityContributionStatus.VERIFIED
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
            identity_contribution_status=contribution_status,
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
        issuer_agent_id=candidate.issuer_agent_id,
        issuer_public_key_id=candidate.issuer_public_key_id,
        issuer_attestation_id=candidate.issuer_attestation_id,
        identity_contribution_status=contribution_status,
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
    accepted_agent_ids: Sequence[str] | None = None,
    accepted_public_key_ids: Sequence[str] | None = None,
    identity_profile: str = "development",
) -> PacketPromotionReport:
    """Promote a deterministic batch of runtime packet candidates."""

    verified: list[VerifiedCapabilityPacket] = []
    rejected: list[PacketRejection] = []
    residual = Ledger()
    for packet in sorted(packets, key=lambda item: item.packet_id):
        result = promote_packet_candidate(
            packet,
            resolutions,
            edge_certificates,
            policy,
            accepted_agent_ids=accepted_agent_ids,
            accepted_public_key_ids=accepted_public_key_ids,
            identity_profile=identity_profile,
        )
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
        identity_contribution_summary=_identity_contribution_summary([*verified, *rejected]),
        residual_ledger=residual,
    )


def _identity_contribution_summary(
    packets: Sequence[object],
) -> dict[str, int]:
    summary = {status.value: 0 for status in IdentityContributionStatus}
    for packet in packets:
        status = getattr(packet, "identity_contribution_status", None)
        if isinstance(status, IdentityContributionStatus):
            summary[status.value] += 1
        elif isinstance(status, str) and status in summary:
            summary[status] += 1
    return dict(sorted((key, value) for key, value in summary.items() if value))


def runtime_health(
    state: RuntimeState,
    config: AgentRuntimeConfig | None = None,
) -> RuntimeHealthReport:
    """Return a finite runtime health report without performing agent actions."""

    active_config = config or AgentRuntimeConfig()
    identity_profile = active_config.identity_profile or active_config.profile
    normalized_identity_profile = normalize_identity_profile(identity_profile)
    promotion_policy = PacketPromotionPolicy.for_profile(identity_profile)
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
        "accepted_agent_context": "present" if state.accepted_agent_ids else "missing",
        "accepted_public_key_context": "present" if state.accepted_public_key_ids else "missing",
        "identity_mode": state.identity_mode,
        "live_connectors": "enabled" if active_config.allow_live_connectors else "disabled",
        "packet_registry": "present" if state.packet_registry.packets else "empty",
        "residual_ledger": "nonempty" if state.residual_ledger.coordinates else "empty",
        "required_routes": "complete" if not missing else "missing",
    }
    identity_required = _profile_requires_identity(identity_profile)
    production_identity_ready = not identity_required or (
        bool(state.accepted_agent_ids) and bool(state.accepted_public_key_ids)
    )
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
        identity_mode=state.identity_mode,
        accepted_agent_context_present=bool(state.accepted_agent_ids),
        accepted_public_key_context_present=bool(state.accepted_public_key_ids),
        cryptographic_identity_required=identity_required,
        sybil_policy_profile=normalized_identity_profile.value,
        can_promote_unsigned_packets=not promotion_policy.require_agent_identity_attestation,
        production_identity_ready=production_identity_ready,
        identity_contribution_summary=_identity_contribution_summary(state.packet_registry.packets),
        checks=checks,
    )


def derive_runtime_identity_context(
    population: AgentPopulationState,
    profile: str = "development",
) -> RuntimeIdentityContext:
    """Derive accepted runtime identity context from a population state."""

    policy = _population_sybil_policy(population, profile)
    ledger = check_sybil_resistance(
        population.population_id,
        population.cryptographic_identities,
        policy,
        [attestation.attestation_id for attestation in population.identity_attestations],
    )
    normalized_profile = normalize_identity_profile(profile)
    return RuntimeIdentityContext(
        context_id=f"runtime-identity-context:{population.population_id}:{normalized_profile.value}",
        identity_profile=normalized_profile,
        accepted_agent_ids=ledger.accepted_agent_ids,
        accepted_public_key_ids=ledger.accepted_public_key_ids,
        sybil_ledger=ledger,
        accepted=ledger.accepted,
        reasons=ledger.reasons,
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
    inventory = _merge_verifier_resolutions(
        state.verifier_resolution_inventory,
        report.evidence_resolution_batch.resolutions,
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
            "verifier_resolution_inventory": inventory,
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
    inventory = list(state.verifier_resolution_inventory)
    execution_refs = list(state.execution_report_refs)
    for result in sorted(results, key=lambda item: item.result_id):
        residual = residual.combine(result.residual_ledger)
        for packet in result.output_packets:
            packets.setdefault(packet.packet_id, packet)
        if result.verifier_resolution is not None:
            residual = residual.combine(result.verifier_resolution.residual_ledger)
            inventory = _merge_verifier_resolutions(inventory, [result.verifier_resolution])
        if not result.executed:
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
        execution_refs.append(result.result_id)
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
            "verifier_resolution_inventory": inventory,
            "execution_report_refs": sorted(set(execution_refs)),
        }
    )


def apply_route_execution_batch(
    state: RuntimeState,
    report: RuntimeStepReport,
    batch: RouteExecutionBatch,
) -> RuntimeState:
    """Persist route execution resolutions for later finite packet promotion."""

    residual = state.residual_ledger.combine(batch.residual_ledger)
    inventory = _merge_verifier_resolutions(state.verifier_resolution_inventory, batch.resolutions)
    event = _runtime_event(
        event_id=f"event:{state.state_id}:{report.step_index}:{batch.batch_id}",
        event_type="route-execution-batch",
        step_index=report.step_index,
        payload_ref=batch.batch_id,
        payload=batch.model_dump(mode="json"),
        residual_delta=batch.residual_ledger,
    )
    return state.model_copy(
        update={
            "residual_ledger": residual,
            "event_log": _event_log_with_hash([*state.event_log.events, event]),
            "verifier_resolution_inventory": inventory,
            "route_batch_refs": sorted(set([*state.route_batch_refs, batch.batch_id])),
            "runtime_memory": sorted(set([*state.runtime_memory, batch.batch_id])),
        }
    )


def build_runtime_run_report(
    initial_state: RuntimeState,
    reports: Sequence[RuntimeStepReport],
    *,
    run_id: str | None = None,
    threshold: Mapping[str, float] | None = None,
    resource_envelope: ResourceEnvelope | None = None,
    baseline_config: ResourceMatchedBaselineConfig | None = None,
) -> RuntimeRunReport:
    """Summarize a runtime trajectory for finite baseline comparison."""

    cumulative = initial_state.residual_ledger
    psi = [report.psi for report in reports]
    scores = [report.phase_acceleration_score for report in reports]
    for report in reports:
        cumulative = cumulative.combine(report.residual_ledger)
    crossing = _threshold_crossing_step(psi, threshold)
    accepted = bool(reports) and all(report.finite_checks_passed for report in reports)
    envelope = resource_envelope or _resource_envelope_from_reports(reports)
    return RuntimeRunReport(
        run_id=run_id or f"runtime-run:{initial_state.state_id}:{len(reports)}",
        initial_state_id=initial_state.state_id,
        reports=list(reports),
        psi_trajectory=psi,
        score_trajectory=scores,
        cumulative_residual_ledger=cumulative,
        threshold_crossing_step=crossing,
        resource_units=float(envelope.verifier_calls + envelope.network_calls + len(reports)),
        resource_envelope=envelope,
        baseline_config=baseline_config,
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
    resource_envelope_matched = _resource_envelopes_match(
        baseline.resource_envelope,
        candidate.resource_envelope,
        tolerance=_baseline_tolerance(baseline, candidate),
    )
    resource_matched = (
        abs(baseline.resource_units - candidate.resource_units) <= 0.0
        and resource_envelope_matched
        and _baseline_configs_match(baseline, candidate)
    )
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
        resource_envelope_matched=resource_envelope_matched,
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


def build_acceleration_experiment_suite(
    suite_id: str,
    comparisons: Sequence[RuntimeComparisonReport],
    *,
    negative_control_passed: bool = True,
) -> AccelerationExperimentSuite:
    """Aggregate repeated finite acceleration comparisons."""

    residual = Ledger()
    gains = []
    reasons: list[str] = []
    for comparison in comparisons:
        residual = residual.combine(comparison.acceleration_certificate.residual_ledger)
        gains.append(comparison.acceleration_certificate.score_gain_lower_bound)
        reasons.extend(comparison.acceleration_certificate.reasons)
    lower_bound = min(gains) if gains else 0.0
    accepted = bool(comparisons) and negative_control_passed and lower_bound > 0.0 and not reasons
    if not negative_control_passed:
        reasons.append("negative control failed")
    return AccelerationExperimentSuite(
        suite_id=suite_id,
        paired_comparisons=sorted(comparisons, key=lambda item: item.comparison_id),
        lower_confidence_bound=lower_bound,
        negative_control_passed=negative_control_passed,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def execute_runtime_task(
    task: AgentTask,
    state: RuntimeState,
    policy: RuntimeExecutorPolicy | None = None,
    store: object | None = None,
) -> RuntimeExecutionReport:
    """Execute one allowlisted runtime task without arbitrary shell execution."""

    active_policy = policy or RuntimeExecutorPolicy()
    task_kind = task.task_type or task.action_kind
    residual = Ledger()
    reasons: list[str] = []
    if task_kind not in active_policy.allowed_task_types:
        reasons.append("runtime task type is not allowlisted")
    if active_policy.require_authority_grant and task.metadata.get("authority_granted") != "true":
        reasons.append("runtime task lacks authority grant")
    if active_policy.require_rollback_receipt and not (
        task.metadata.get("rollback_receipt") or task.rollback_condition
    ):
        reasons.append("runtime task lacks rollback receipt")
    if task.required_routes and active_policy.allowed_route_ids:
        disallowed = sorted(set(task.required_routes) - set(active_policy.allowed_route_ids))
        if disallowed:
            reasons.append("runtime task requires routes outside executor policy")
    if reasons:
        residual = residual.add_coordinate(
            f"runtime-executor:{task.task_id}:rejected",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons
    action_result = RuntimeActionResult(
        result_id=f"runtime-execution-result:{task.task_id}",
        task_id=task.task_id,
        action_id=task.action_id,
        executed=accepted,
        observed_delta={"expected_proxy_gain": task.expected_proxy_gain} if accepted else {},
        residual_ledger=residual,
        rollback_available=bool(task.rollback_condition),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )
    if accepted and store is not None and hasattr(store, "append_event"):
        event = _runtime_event(
            event_id=f"event:{state.state_id}:{state.step_index}:{task.task_id}:execute",
            event_type="runtime-task-executed",
            step_index=state.step_index,
            payload_ref=task.task_id,
            payload=action_result.model_dump(mode="json"),
            residual_delta=residual,
        )
        store.append_event(event)
    return RuntimeExecutionReport(
        report_id=f"runtime-execution:{task.task_id}",
        task_id=task.task_id,
        task_type=task_kind,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        action_result=action_result,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def execute_route_batch(
    requests: Sequence[RouteExecutionRequest],
    evidence_store: FileEvidenceEnvelopeStore | None = None,
    policy: RuntimeExecutorPolicy | None = None,
    *,
    profile: str = "development",
) -> RouteExecutionBatch:
    """Execute route requests using evidence envelopes from a sandboxed store."""

    active_policy = policy or RuntimeExecutorPolicy(profile=profile)
    route_specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
    route_specs.update({spec.verifier_route: spec for spec in list_adapter_route_specs()})
    reports: list[RuntimeExecutionReport] = []
    resolutions: list[VerifierResolution] = []
    residual = Ledger()
    reasons: list[str] = []
    for request in sorted(requests, key=lambda item: item.request_id):
        route_id = request.route_id
        if active_policy.allowed_route_ids and route_id not in active_policy.allowed_route_ids:
            report_residual = Ledger().add_coordinate(
                f"route-execution:{request.request_id}:disallowed-route",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            reports.append(
                RuntimeExecutionReport(
                    report_id=f"route-execution:{request.request_id}",
                    task_id=request.request_id,
                    task_type="route-execution",
                    residual_ledger=report_residual,
                    reasons=["route is outside executor policy"],
                )
            )
            residual = residual.combine(report_residual)
            reasons.append("one or more routes are outside executor policy")
            continue
        spec = route_specs.get(route_id) or route_specs.get(request.verifier_route)
        envelope = (
            evidence_store.load(f"{request.request_id}.json", profile=profile)
            if evidence_store is not None
            else None
        )
        if spec is None or envelope is None:
            report_residual = Ledger().add_coordinate(
                f"route-execution:{request.request_id}:missing-evidence-or-route",
                1.0,
                kind=CoordinateKind.RESIDUAL,
            )
            reports.append(
                RuntimeExecutionReport(
                    report_id=f"route-execution:{request.request_id}",
                    task_id=request.request_id,
                    task_type="route-execution",
                    residual_ledger=report_residual,
                    reasons=["route spec or evidence envelope is missing"],
                )
            )
            residual = residual.combine(report_residual)
            reasons.append("one or more route requests lacked evidence or route specs")
            continue
        resolution = resolve_adapter_route(spec, envelope, profile=profile)
        resolutions.append(resolution)
        residual = residual.combine(resolution.residual_ledger)
        accepted = resolution.accepted
        reports.append(
            RuntimeExecutionReport(
                report_id=f"route-execution:{request.request_id}",
                task_id=request.request_id,
                task_type="route-execution",
                accepted=accepted,
                finite_checks_passed=accepted,
                operationally_usable=resolution.operationally_usable,
                settled=resolution.settled,
                residual_ledger=resolution.residual_ledger,
                reasons=resolution.reasons,
            )
        )
    accepted = bool(reports) and all(report.accepted for report in reports)
    return RouteExecutionBatch(
        batch_id="route-execution-batch",
        reports=reports,
        resolutions=sorted(resolutions, key=lambda item: item.resolution_id),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and any(report.operationally_usable for report in reports),
        settled=False,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def run_agent_loop_with_store(
    state: RuntimeState,
    inputs: Sequence[RuntimeStepInput],
    executor_policy: RuntimeExecutorPolicy,
    store: object | None,
    *,
    max_steps: int | None = None,
) -> list[RuntimeStepReport]:
    """Run runtime loop, execute allowlisted tasks, and persist state snapshots."""

    reports: list[RuntimeStepReport] = []
    current = state
    for step_input in list(inputs)[: max_steps or len(inputs)]:
        report = build_runtime_step(
            current,
            step_input,
            AgentRuntimeConfig(profile=executor_policy.profile),
        )
        reports.append(report)
        if store is not None and hasattr(store, "append_state"):
            store.append_state(current)
        next_state = loop_state_after_report(current, report)
        route_batch = execute_route_batch(
            report.route_execution_requests,
            None,
            executor_policy,
            profile=executor_policy.profile,
        )
        if route_batch.reports:
            next_state = apply_route_execution_batch(next_state, report, route_batch)
            if store is not None and hasattr(store, "append_route_batch"):
                store.append_route_batch(route_batch)
        action_results: list[RuntimeActionResult] = []
        for task in report.agent_tasks[: executor_policy.max_tasks]:
            execution = execute_runtime_task(task, current, executor_policy, store=store)
            if execution.action_result is not None:
                action_results.append(execution.action_result)
            if store is not None and hasattr(store, "append_execution_report"):
                store.append_execution_report(execution)
        if action_results:
            next_state = apply_action_results(next_state, report, action_results)
        current = next_state
    if store is not None and hasattr(store, "append_state"):
        store.append_state(current)
    return reports


def check_fixed_population_ledger(ledger: FixedPopulationLedger) -> FixedPopulationLedger:
    """Check fixed population and no-self-rewrite invariants."""

    residual = ledger.residual_ledger
    reasons = list(ledger.reasons)
    before = {agent.agent_id: agent for agent in ledger.before_agents}
    after = {agent.agent_id: agent for agent in ledger.after_agents}
    if sorted(before) != sorted(after):
        reasons.append("agent population changed across observation window")
    for agent_id, before_agent in before.items():
        after_agent = after.get(agent_id)
        if after_agent is None:
            continue
        if before_agent.policy_digest != after_agent.policy_digest:
            reasons.append("agent policy digest changed")
        if before_agent.model_digest != after_agent.model_digest:
            reasons.append("agent model digest changed")
        if before_agent.self_rewrite_allowed or after_agent.self_rewrite_allowed:
            reasons.append("self-rewrite is allowed by agent policy")
        if before_agent.weight_update_allowed or after_agent.weight_update_allowed:
            reasons.append("weight update is allowed by agent policy")
    if not ledger.no_self_rewrite:
        reasons.append("ledger does not assert no self-rewrite")
    if not ledger.no_weight_update:
        reasons.append("ledger does not assert no weight update")
    if not ledger.fixed_population:
        reasons.append("ledger does not assert fixed population")
    if not ledger.policy_digests_unchanged:
        reasons.append("ledger does not assert unchanged policy digests")
    if reasons:
        residual = residual.add_coordinate(
            f"fixed-population:{ledger.ledger_id}:diagnostic",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons and bool(before)
    return ledger.model_copy(
        update={
            "residual_ledger": residual,
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "reasons": sorted(set(reasons)),
        }
    )


def build_population_runtime_step(
    population: AgentPopulationState,
    inputs: Sequence[RuntimeStepInput],
    config: AgentRuntimeConfig | None = None,
) -> PopulationRuntimeStepReport:
    """Run one deterministic step over a fixed population of runtime states."""

    active_config = config or AgentRuntimeConfig()
    identity_profile = active_config.identity_profile or active_config.profile
    ledger = check_fixed_population_ledger(population.fixed_population_ledger)
    sybil_policy = _population_sybil_policy(population, identity_profile)
    sybil = (
        check_sybil_resistance(
            population.population_id,
            population.cryptographic_identities,
            sybil_policy,
            [attestation.attestation_id for attestation in population.identity_attestations],
        )
        if _profile_requires_identity(identity_profile) or population.cryptographic_identities
        else None
    )
    reports: list[RuntimeStepReport] = []
    next_states: list[RuntimeState] = []
    residual = population.residual_ledger.combine(ledger.residual_ledger)
    if sybil is not None:
        residual = residual.combine(sybil.residual_ledger)
    runtime_states = sorted(population.runtime_states, key=lambda item: item.state_id)
    step_inputs = list(inputs)
    for index, runtime_state in enumerate(runtime_states):
        step_input = (
            step_inputs[index]
            if index < len(step_inputs)
            else RuntimeStepInput(input_id=f"population-empty-input:{runtime_state.state_id}")
        )
        runtime_state_with_identity = runtime_state.model_copy(
            update={
                "accepted_agent_ids": [] if sybil is None else sybil.accepted_agent_ids,
                "accepted_public_key_ids": [] if sybil is None else sybil.accepted_public_key_ids,
                "identity_mode": "cryptographic" if sybil is not None else "declared",
            }
        )
        report = build_runtime_step(runtime_state_with_identity, step_input, active_config)
        reports.append(report)
        residual = residual.combine(report.residual_ledger)
        next_states.append(loop_state_after_report(runtime_state, report))
    merged_registry = _merge_population_registries(reports, population.population_id)
    hidden = check_no_hidden_capability_injection(
        merged_registry,
        population.protocol_frame,
        runtime_events=[
            event.model_dump(mode="json")
            for report in reports
            for event in report.event_log_delta.events
        ],
        accepted_agent_ids=[] if sybil is None else sybil.accepted_agent_ids,
        trusted_public_key_ids=[] if sybil is None else sybil.accepted_public_key_ids,
        profile=identity_profile,
    )
    residual = residual.combine(hidden.residual_ledger)
    aggregate_psi = build_psi_dashboard(
        merged_registry,
        threshold=active_config.psi_threshold or None,
        closure_witnesses=find_autocatalytic_closures(merged_registry),
    )
    next_population = population.model_copy(
        update={
            "runtime_states": next_states,
            "fixed_population_ledger": ledger,
            "sybil_resistance_policy": sybil_policy,
            "sybil_resistance_ledger": sybil,
            "residual_ledger": residual,
            "step_index": population.step_index + 1,
        }
    )
    sybil_required = _profile_requires_identity(identity_profile)
    sybil_accepted = sybil.accepted if sybil is not None else not sybil_required
    accepted = (
        ledger.accepted
        and hidden.accepted
        and sybil_accepted
        and all(report.accepted for report in reports)
    )
    reasons = [*ledger.reasons, *hidden.reasons]
    if sybil_required and sybil is None:
        reasons.append("production population step requires cryptographic identities")
    if sybil is not None:
        reasons.extend(sybil.reasons)
    for report in reports:
        reasons.extend(report.reasons)
    return PopulationRuntimeStepReport(
        report_id=f"population-step:{population.population_id}:{population.step_index}",
        population_id=population.population_id,
        step_index=population.step_index,
        agent_reports=reports,
        fixed_population_ledger=ledger,
        hidden_injection_report=hidden,
        sybil_resistance_ledger=sybil,
        aggregate_psi=aggregate_psi,
        next_population=next_population,
        residual_ledger=residual,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and any(report.operationally_usable for report in reports),
        settled=False,
        reasons=sorted(set(reasons)),
    )


def certify_collective_phase(
    population: AgentPopulationState,
    state: RuntimeState,
    basin: CapabilityBasinContract,
    baseline: RuntimeRunReport,
    threshold: Mapping[str, float] | None = None,
    *,
    profile: str = "development",
) -> CollectivePhaseCertificate:
    """Build an ECPT collective packet-phase certificate."""

    identity_profile = profile
    active_threshold = dict(threshold or state.psi_threshold or {})
    fixed = check_fixed_population_ledger(population.fixed_population_ledger)
    sybil_policy = _population_sybil_policy(population, identity_profile)
    sybil = (
        check_sybil_resistance(
            population.population_id,
            population.cryptographic_identities,
            sybil_policy,
            [attestation.attestation_id for attestation in population.identity_attestations],
        )
        if _profile_requires_identity(identity_profile) or population.cryptographic_identities
        else None
    )
    hidden = check_no_hidden_capability_injection(
        state.packet_registry,
        population.protocol_frame,
        accepted_agent_ids=[] if sybil is None else sybil.accepted_agent_ids,
        trusted_public_key_ids=[] if sybil is None else sybil.accepted_public_key_ids,
        profile=identity_profile,
    )
    closures = find_autocatalytic_closures(state.packet_registry, basin)
    paths = find_execution_available_paths(
        state.packet_registry,
        basin,
        constraint_frame=state.phase_state.constraint_frame.model_dump(mode="json"),
    )
    psi = build_psi_dashboard(
        state.packet_registry,
        threshold=active_threshold or None,
        closure_witnesses=closures,
        execution_paths=paths,
        basin=basin,
    )
    threshold_crossed = bool(active_threshold) and all(
        psi.components.get(key, 0.0) >= value for key, value in active_threshold.items()
    )
    false_liquidity_bounded = psi.throughput.false_liquidity_rate <= 0.25
    verification_backlog_bounded = psi.throughput.unresolved_obligation_backlog <= max(
        1,
        len(state.packet_registry.packets) + len(state.verifier_resolution_inventory),
    )
    sqot_reserve_live = psi.components.get("QS", 0.0) >= active_threshold.get("QS", 0.5)
    hazard_non_rejecting = psi.components.get("HZ", 0.0) >= active_threshold.get("HZ", 0.5)
    resource_matched = baseline.resource_envelope.verifier_calls >= 0 and baseline.run_id != ""
    lineage = [
        build_packet_capital_lineage(
            packet,
            edge_certificate_ids=packet.accepted_edge_witness_ids,
            verifier_resolution_ids=packet.verification_resolution_ids,
            protocol_frame_sha256=population.protocol_frame.sha256 or None,
        )
        for packet in state.verified_packets
    ]
    residual_external = sorted(
        {
            obligation
            for packet in state.verified_packets
            for obligation in packet.residual_external_obligations
        }
    )
    residual = state.residual_ledger.combine(psi.residual_ledger)
    residual = residual.combine(fixed.residual_ledger).combine(hidden.residual_ledger)
    if sybil is not None:
        residual = residual.combine(sybil.residual_ledger)
    for closure in closures:
        residual = residual.combine(closure.residual_ledger)
    for path in paths:
        residual = residual.combine(path.residual_ledger)
    reasons: list[str] = []
    if not fixed.accepted:
        reasons.append("fixed population/no-self-rewrite ledger rejected")
    if not hidden.accepted:
        reasons.append("hidden capability injection check rejected")
    if _profile_requires_identity(identity_profile) and sybil is None:
        reasons.append("production collective certificate requires cryptographic identities")
    if sybil is not None and not sybil.accepted:
        if _profile_requires_identity(identity_profile):
            reasons.append("Sybil-resistance ledger rejected under selected profile")
        else:
            reasons.append("identity trust profile is diagnostic only")
    contribution_summary = _identity_contribution_summary(
        [
            packet.model_copy(
                update={
                    "identity_contribution_status": identity_contribution_status_for_packet(
                        packet,
                        sybil,
                        identity_profile,
                    )
                }
            )
            for packet in state.packet_registry.packets
        ]
    )
    if not any(witness.accepted for witness in closures):
        reasons.append("no accepted autocatalytic closure witness")
    if not any(path.accepted for path in paths):
        reasons.append("no accepted execution-available path certificate")
    if not threshold_crossed:
        reasons.append("Psi threshold is not crossed")
    if not resource_matched:
        reasons.append("resource-matched baseline is unavailable")
    if not false_liquidity_bounded:
        reasons.append("false liquidity exceeds collective certificate bound")
    if not verification_backlog_bounded:
        reasons.append("verification backlog exceeds collective certificate bound")
    if not sqot_reserve_live:
        reasons.append("SQOT diagnostic reserve is not live")
    if not hazard_non_rejecting:
        reasons.append("hazard/authority checks are rejecting")
    accepted = not reasons
    return CollectivePhaseCertificate(
        certificate_id=f"collective-phase:{population.population_id}:{state.state_id}:{basin.basin_id}",
        population_id=population.population_id,
        state_id=state.state_id,
        basin_id=basin.basin_id,
        protocol_frame=population.protocol_frame,
        fixed_population_ledger=fixed,
        hidden_injection_report=hidden,
        sybil_resistance_ledger=sybil,
        identity_attestation_refs=sorted(
            attestation.attestation_id for attestation in population.identity_attestations
        ),
        minimum_identity_strength=sybil_policy.minimum_identity_strength.value,
        identity_profile=normalize_identity_profile(identity_profile).value,
        identity_contribution_summary=contribution_summary,
        closure_witnesses=closures,
        execution_available_paths=paths,
        packet_lineage=lineage,
        psi=psi,
        threshold=dict(sorted(active_threshold.items())),
        threshold_crossed=threshold_crossed,
        resource_matched_baseline=resource_matched,
        false_liquidity_bounded=false_liquidity_bounded,
        verification_backlog_bounded=verification_backlog_bounded,
        sqot_reserve_live=sqot_reserve_live,
        hazard_authority_non_rejecting=hazard_non_rejecting,
        residual_external_obligations=residual_external,
        residual_ledger=residual,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
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


def _profile_requires_identity(profile: str) -> bool:
    return normalize_identity_profile(profile).value in {
        "controlled",
        "federated",
        "production",
        "adversarial",
    }


def _population_sybil_policy(
    population: AgentPopulationState,
    profile: str,
) -> SybilResistancePolicy:
    if population.sybil_resistance_policy.policy_id != "default-sybil-policy":
        return population.sybil_resistance_policy
    return sybil_policy_for_profile(profile)


def _event_log_with_hash(events: Sequence[RuntimeEvent]) -> RuntimeEventLog:
    sorted_events = sorted(events, key=lambda item: item.event_id)
    digest = _stable_digest([event.model_dump(mode="json") for event in sorted_events])
    return RuntimeEventLog(events=sorted_events, aggregate_sha256=digest)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _resource_envelope_from_reports(reports: Sequence[RuntimeStepReport]) -> ResourceEnvelope:
    return ResourceEnvelope(
        wall_time_seconds=float(len(reports)),
        token_budget=sum(len(report.agent_tasks) for report in reports),
        verifier_calls=sum(len(report.evidence_resolution_batch.resolutions) for report in reports),
        network_calls=sum(1 for report in reports if report.allow_live_connectors),
        compute_cost=float(len(reports)),
        human_review_budget=0.0,
        risk_budget=sum(
            report.phase_acceleration_score.risk_charge
            + report.phase_acceleration_score.false_liquidity_charge
            for report in reports
        ),
    )


def _baseline_tolerance(baseline: RuntimeRunReport, candidate: RuntimeRunReport) -> float:
    values = [
        config.tolerance
        for config in [baseline.baseline_config, candidate.baseline_config]
        if config is not None
    ]
    return max(values, default=0.0)


def _baseline_configs_match(baseline: RuntimeRunReport, candidate: RuntimeRunReport) -> bool:
    left = baseline.baseline_config
    right = candidate.baseline_config
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return (
        left.observation_protocol_id == right.observation_protocol_id
        and left.constraint_frame_id == right.constraint_frame_id
        and sorted(left.receiver_family) == sorted(right.receiver_family)
        and left.validity_domain == right.validity_domain
    )


def _resource_envelopes_match(
    baseline: ResourceEnvelope,
    candidate: ResourceEnvelope,
    *,
    tolerance: float = 0.0,
) -> bool:
    for field in ResourceEnvelope.model_fields:
        left = float(getattr(baseline, field))
        right = float(getattr(candidate, field))
        if abs(left - right) > tolerance:
            return False
    return True


def _merge_verified_packets(
    existing: Sequence[VerifiedCapabilityPacket],
    new_packets: Sequence[VerifiedCapabilityPacket],
) -> list[VerifiedCapabilityPacket]:
    packets = {packet.packet_id: packet for packet in existing}
    for packet in new_packets:
        packets.setdefault(packet.packet_id, packet)
    return sorted(packets.values(), key=lambda item: item.packet_id)


def _merge_verifier_resolutions(
    existing: Sequence[VerifierResolution],
    new_resolutions: Sequence[VerifierResolution],
) -> list[VerifierResolution]:
    resolutions = {resolution.resolution_id: resolution for resolution in existing}
    for resolution in new_resolutions:
        resolutions.setdefault(resolution.resolution_id, resolution)
    return sorted(resolutions.values(), key=lambda item: item.resolution_id)


def _merge_population_registries(
    reports: Sequence[RuntimeStepReport],
    population_id: str,
) -> CapabilityPacketRegistry:
    packets: dict[str, CapabilityPacketCandidate] = {}
    edges: dict[str, EdgeWitness] = {}
    residual = Ledger()
    for report in reports:
        residual = residual.combine(report.registry.residual_ledger)
        for packet in report.registry.packets:
            packets.setdefault(packet.packet_id, packet)
        for edge in report.registry.edges:
            edges.setdefault(edge.edge_id, edge)
    return build_packet_registry(
        sorted(packets.values(), key=lambda item: item.packet_id),
        sorted(edges.values(), key=lambda item: item.edge_id),
        registry_id=f"population-registry:{population_id}",
    ).model_copy(update={"residual_ledger": residual})


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
