"""Phase Ecology Lab records for v0.5.0 windowed packet ecology diagnostics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PhaseLabStoreManifest(BaseModel):
    """Local Phase Lab store metadata."""

    store_id: str = "phase-lab-store"
    schema_version: str = "phase-lab-store-v1"
    store_path: str = ""
    database_path: str = ""
    event_count: int = 0
    window_count: int = 0
    latest_window_id: str | None = None
    accepted: bool = True
    settled: bool = False
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "phase lab stores local report data only",
            "phase lab never executes report or packet content",
            "phase lab diagnostics do not settle claims",
        ]
    )
    reasons: list[str] = Field(default_factory=list)


class PhaseLabEvent(BaseModel):
    """One inert report or packet stored by the Phase Lab."""

    event_id: str
    window_id: str
    source_kind: str = "unknown-report"
    schema_hint: str = "unknown"
    content_digest: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_path: str | None = None
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    candidate_only: bool = True
    positive_contribution_allowed: bool = False
    residual_summary: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    candidate_only_reasons: list[str] = Field(default_factory=list)
    settled_blockers: list[str] = Field(default_factory=list)
    safety_boundary: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class PhaseLabWindowIndex(BaseModel):
    """Index entry for one deterministic ingest window."""

    window_id: str
    sequence: int
    event_ids: list[str] = Field(default_factory=list)
    event_count: int = 0
    accepted_event_count: int = 0
    candidate_only_event_count: int = 0
    positive_contribution_event_count: int = 0
    settled_event_count: int = 0
    residual_debt: float = 0.0
    missing_obligation_count: int = 0
    accepted: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseLabIngestReport(BaseModel):
    """Report emitted after ingesting inert files into a Phase Lab store."""

    report_id: str
    store_manifest: PhaseLabStoreManifest
    window: PhaseLabWindowIndex
    ingested_events: list[PhaseLabEvent] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    content_treated_as_data: bool = True
    executed_command_count: int = 0
    accepted: bool = False
    workflow_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseLabExportManifest(BaseModel):
    """Manifest for a deterministic local Phase Lab export."""

    export_id: str = "phase-lab-export"
    store_manifest: PhaseLabStoreManifest
    output_dir: str = ""
    files: list[str] = Field(default_factory=list)
    absolute_paths_sanitized: bool = True
    accepted: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketContributionStatus(BaseModel):
    """Portable contribution status for one graph object."""

    status: str = "diagnostic"
    positive_contribution: bool = False
    candidate_only: bool = True
    non_contributing_reason: str = "candidate-only data does not improve phase metrics"
    settled: bool = False


class EffectivePacketEligibility(BaseModel):
    """Eligibility checks for positive phase contribution."""

    accepted_or_certificate_admissible: bool = False
    retrievable: bool = False
    not_salience_blocked: bool = False
    not_verification_blocked: bool = False
    not_stale: bool = False
    hash_valid: bool = False
    authority_valid: bool = False
    rollback_available_or_not_required: bool = False
    within_validity_domain: bool = False
    residuals_preserved: bool = False
    not_registry_metadata_only: bool = False
    not_raw_external_volume: bool = False
    agent_text_not_treated_as_evidence: bool = False
    eligible: bool = False
    blockers: list[str] = Field(default_factory=list)


class EffectivePacketNode(BaseModel):
    """One node in the effective packet graph."""

    node_id: str
    source_event_id: str = ""
    source_kind: str = "unknown-report"
    schema_hint: str = "unknown"
    content_digest: str = ""
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    eligibility: EffectivePacketEligibility = Field(default_factory=EffectivePacketEligibility)
    contribution: PacketContributionStatus = Field(default_factory=PacketContributionStatus)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SemanticEdgeEvidence(BaseModel):
    """Evidence summary for one effective graph edge."""

    evidence_refs: list[str] = Field(default_factory=list)
    edge_certificate_refs: list[str] = Field(default_factory=list)
    verifier_resolution_refs: list[str] = Field(default_factory=list)
    evidence_supported: bool = False
    missing_evidence: list[str] = Field(default_factory=list)


class EffectivePacketEdge(BaseModel):
    """One edge in the effective packet graph."""

    edge_id: str
    source_node_ids: list[str] = Field(default_factory=list)
    target_node_id: str
    relation_type: str = "semantic-dependency"
    evidence: SemanticEdgeEvidence = Field(default_factory=SemanticEdgeEvidence)
    accepted: bool = False
    settled: bool = False
    contribution: PacketContributionStatus = Field(default_factory=PacketContributionStatus)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class EffectiveGraphResidualSummary(BaseModel):
    """Residual summary carried by an effective graph."""

    residual_summary: dict[str, float] = Field(default_factory=dict)
    residual_debt: float = 0.0
    missing_obligation_count: int = 0
    settled_blockers: list[str] = Field(default_factory=list)
    candidate_only_reasons: list[str] = Field(default_factory=list)


class EffectivePacketGraph(BaseModel):
    """Protocol-relative graph of accepted and diagnostic packet structures."""

    graph_id: str = "effective-packet-graph"
    source_window_id: str = "adhoc"
    nodes: list[EffectivePacketNode] = Field(default_factory=list)
    edges: list[EffectivePacketEdge] = Field(default_factory=list)
    node_count_by_status: dict[str, int] = Field(default_factory=dict)
    edge_count_by_relation: dict[str, int] = Field(default_factory=dict)
    accepted_packet_capital: int = 0
    candidate_only_packets: int = 0
    rejected_or_quarantined_packets: int = 0
    missing_edge_evidence: list[str] = Field(default_factory=list)
    stale_or_unsafe_packets: list[str] = Field(default_factory=list)
    semantic_edge_witnesses: list[SemanticEdgeEvidence] = Field(default_factory=list)
    non_contributing_volume: int = 0
    residual_summary: EffectiveGraphResidualSummary = Field(
        default_factory=EffectiveGraphResidualSummary
    )
    graph_safety_boundary: list[str] = Field(
        default_factory=lambda: [
            "raw packet volume is diagnostic only",
            "candidate-only nodes do not improve positive phase components",
            "graph construction does not execute packet content",
            "graph construction does not settle claims",
        ]
    )
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class EffectivePacketGraphBuildReport(BaseModel):
    """Build report for an effective packet graph."""

    report_id: str = "effective-packet-graph-build"
    graph: EffectivePacketGraph
    input_event_count: int = 0
    positive_contribution_count: int = 0
    diagnostic_only_count: int = 0
    raw_volume_positive_contribution: int = 0
    accepted: bool = False
    workflow_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseWindow(BaseModel):
    """A finite Phase Lab observation window."""

    window_id: str
    sequence: int = 0
    event_count: int = 0
    event_ids: list[str] = Field(default_factory=list)


class PhaseComponentObservation(BaseModel):
    """One phase component value and threshold distance."""

    component: str
    value: float = 0.0
    threshold: float = 0.0
    distance: float = 0.0
    positive_contribution_source: str = "effective-graph-only"
    diagnostic_only: bool = True


class VerificationThroughputWindow(BaseModel):
    accepted_count: int = 0
    backlog_count: int = 0
    throughput_ratio: float = 0.0


class FalseLiquidityLoad(BaseModel):
    candidate_count: int = 0
    certified_count: int = 0
    load: float = 0.0


class WasteLoad(BaseModel):
    non_contributing_volume: int = 0
    total_volume: int = 0
    load: float = 0.0


class SalienceObstructionLoad(BaseModel):
    blocked_count: int = 0
    total_count: int = 0
    load: float = 0.0


class BasinReachabilityProxy(BaseModel):
    execution_available_path_count: int = 0
    effective_node_count: int = 0
    reachability_proxy: float = 0.0


class PhaseWindowObservation(BaseModel):
    """Windowed observation over Phase Lab events and an effective graph."""

    observation_id: str = "phase-window-observation"
    window: PhaseWindow
    packet_candidate_count: int = 0
    accepted_packet_count: int = 0
    workflow_usable_packet_count: int = 0
    settled_packet_count: int = 0
    candidate_only_packet_count: int = 0
    effective_node_count: int = 0
    effective_edge_count: int = 0
    execution_available_path_count: int = 0
    closure_witness_count: int = 0
    autocatalytic_closure_score: float = 0.0
    verification_throughput: VerificationThroughputWindow = Field(
        default_factory=VerificationThroughputWindow
    )
    residual_debt: float = 0.0
    missing_obligation_count: int = 0
    false_liquidity_load: FalseLiquidityLoad = Field(default_factory=FalseLiquidityLoad)
    waste_load: WasteLoad = Field(default_factory=WasteLoad)
    salience_obstruction_load: SalienceObstructionLoad = Field(
        default_factory=SalienceObstructionLoad
    )
    basin_reachability_proxy: BasinReachabilityProxy = Field(default_factory=BasinReachabilityProxy)
    alt_liquidity_candidate_count: int = 0
    alt_certified_capital_count: int = 0
    phase_gap_vector: dict[str, float] = Field(default_factory=dict)
    bottleneck_count_by_type: dict[str, int] = Field(default_factory=dict)
    threshold_distance: float = 0.0
    components: list[PhaseComponentObservation] = Field(default_factory=list)
    protocol_relative_only: bool = True
    proves_real_asi: bool = False
    proves_physical_or_oracle_truth: bool = False
    raw_external_volume_diagnostic_only: bool = True
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseWindowComparison(BaseModel):
    """Comparison between two Phase Lab windows."""

    comparison_id: str = "phase-window-comparison"
    baseline_window_id: str
    candidate_window_id: str
    metric_delta: dict[str, float] = Field(default_factory=dict)
    positive_progress_components: list[str] = Field(default_factory=list)
    diagnostic_only_components: list[str] = Field(default_factory=list)
    accepted: bool = False
    workflow_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseThresholdStatus(BaseModel):
    """Legacy-compatible threshold status alias used by phase observations."""

    threshold_id: str = "phase-threshold"
    passed: bool = False
    abstain: bool = True
    rejected: bool = False
    component_status: dict[str, bool] = Field(default_factory=dict)
    threshold_distance: float = 0.0
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ASIProxyThresholdSpec(BaseModel):
    """Protocol-relative finite threshold specification for ASI-proxy diagnostics."""

    threshold_id: str = "asi-proxy-development"
    minimum_accepted_packet_count: int = 1
    minimum_effective_edge_count: int = 1
    minimum_execution_available_path_density: float = 0.1
    minimum_closure_witness_count: int = 1
    maximum_residual_debt: float = 0.0
    maximum_false_liquidity_load: float = 0.5
    maximum_salience_obstruction: float = 0.5
    minimum_verification_throughput: float = 0.1
    minimum_alt_to_ecpt_lift_count: int = 0
    required_identity_mode: str = "declared"
    required_rollback_availability: bool = True
    required_authority_status: str = "explicit-scope-bounded"


class ASIProxyThresholdStatus(BaseModel):
    """Threshold status over one protocol-relative phase observation."""

    status_id: str = "asi-proxy-threshold-status"
    threshold: ASIProxyThresholdSpec
    observation: PhaseWindowObservation
    certificate_status: str = "abstain"
    component_status: dict[str, bool] = Field(default_factory=dict)
    failed_components: list[str] = Field(default_factory=list)
    abstention_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    threshold_distance: float = 0.0
    protocol_relative_only: bool = True
    proves_real_asi: bool = False
    settled: bool = False
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseCertificateDefect(BaseModel):
    defect_id: str
    component: str
    defect_type: str
    required_remediation: str
    residual_preserved: bool = True


class CollectivePhaseAbstentionReport(BaseModel):
    report_id: str = "collective-phase-abstention"
    threshold_status: ASIProxyThresholdStatus
    defects: list[PhaseCertificateDefect] = Field(default_factory=list)
    protocol_relative_only: bool = True
    proves_real_asi: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class CollectivePhaseCertificateCandidate(BaseModel):
    certificate_id: str = "collective-phase-certificate-candidate"
    certificate_status: str = "abstain"
    threshold_status: ASIProxyThresholdStatus
    graph_id: str = ""
    observation_id: str = ""
    finite_requirements_passed: bool = False
    abstention_report: CollectivePhaseAbstentionReport | None = None
    defects: list[PhaseCertificateDefect] = Field(default_factory=list)
    protocol_relative_only: bool = True
    proves_real_asi: bool = False
    proves_physical_or_oracle_truth: bool = False
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AutocatalyticClosureWitness(BaseModel):
    """Evidence-supported diagnostic closure witness over effective packet edges."""

    witness_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    witness_kind: str = "autocatalytic-closure"
    evidence_supported: bool = False
    productive: bool = False
    execution_available: bool = False
    accepted: bool = False
    protocol_relative_only: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ProductiveClosureWitness(BaseModel):
    witness_id: str
    packet_ids: list[str] = Field(default_factory=list)
    productive_edge_ids: list[str] = Field(default_factory=list)
    productivity_lower_bound: float = 0.0
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ExecutableClosureWitness(BaseModel):
    witness_id: str
    closure_witness_id: str
    execution_path_ids: list[str] = Field(default_factory=list)
    execution_available: bool = False
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ClosureSupportHyperpath(BaseModel):
    hyperpath_id: str
    source_packet_ids: list[str] = Field(default_factory=list)
    target_packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    accepted: bool = False
    settled: bool = False


class ClosureDefect(BaseModel):
    defect_id: str
    packet_or_edge_id: str
    defect_type: str
    residual_preserved: bool = True


class ClosureAbstentionReason(BaseModel):
    reason_id: str
    reason: str
    missing_evidence_refs: list[str] = Field(default_factory=list)


class ClosureCertificateCandidate(BaseModel):
    certificate_id: str = "closure-certificate-candidate"
    certificate_status: str = "abstain"
    witness_ids: list[str] = Field(default_factory=list)
    defects: list[ClosureDefect] = Field(default_factory=list)
    abstention_reasons: list[ClosureAbstentionReason] = Field(default_factory=list)
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AutocatalyticClosureReport(BaseModel):
    report_id: str = "autocatalytic-closure-report"
    graph_id: str
    closure_witnesses: list[AutocatalyticClosureWitness] = Field(default_factory=list)
    productive_witnesses: list[ProductiveClosureWitness] = Field(default_factory=list)
    executable_witnesses: list[ExecutableClosureWitness] = Field(default_factory=list)
    support_hyperpaths: list[ClosureSupportHyperpath] = Field(default_factory=list)
    defects: list[ClosureDefect] = Field(default_factory=list)
    certificate_candidate: ClosureCertificateCandidate
    closure_score: float = 0.0
    accepted: bool = False
    workflow_usable: bool = True
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ReceiverContextSupport(BaseModel):
    receiver_context_id: str = "receiver-context:default"
    present: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class ActionBoundaryRequirement(BaseModel):
    requirement_id: str
    requirement_type: str
    satisfied: bool = False
    residual: str = ""


class ExecutionAuthorityStatus(BaseModel):
    authority_status: str = "not-granted"
    explicit_scope_bounded: bool = False
    grants_execution: bool = False
    reasons: list[str] = Field(default_factory=list)


class ExecutionPathWitness(BaseModel):
    witness_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ExecutionPathDefect(BaseModel):
    defect_id: str
    path_id: str
    defect_type: str
    residual_preserved: bool = True


class ExecutionAvailableHyperpath(BaseModel):
    path_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    witness: ExecutionPathWitness
    receiver_context: ReceiverContextSupport = Field(default_factory=ReceiverContextSupport)
    action_boundary_requirements: list[ActionBoundaryRequirement] = Field(default_factory=list)
    authority_status: ExecutionAuthorityStatus = Field(default_factory=ExecutionAuthorityStatus)
    accepted: bool = False
    candidate_only: bool = True
    blocked: bool = True
    not_executed: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ExecutablePathDensityReport(BaseModel):
    report_id: str = "execution-available-path-density"
    graph_id: str
    paths: list[ExecutionAvailableHyperpath] = Field(default_factory=list)
    path_count: int = 0
    path_density: float = 0.0
    accepted_path_count: int = 0
    candidate_only_path_count: int = 0
    blocked_path_count: int = 0
    blocker_reason_by_path: dict[str, list[str]] = Field(default_factory=dict)
    authority_requirements: list[str] = Field(default_factory=list)
    rollback_requirements: list[str] = Field(default_factory=list)
    residual_carry_forward: list[str] = Field(default_factory=list)
    executed_path_count: int = 0
    accepted: bool = False
    workflow_usable: bool = True
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
