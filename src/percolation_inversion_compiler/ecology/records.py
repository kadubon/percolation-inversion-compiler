"""Capability packet ecology records for ECPT active runtimes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus


class PacketSourceKind(StrEnum):
    LOCAL = "local"
    GITHUB = "github"
    ZENODO = "zenodo"
    ARXIV = "arxiv"
    AGENT_OUTPUT = "agent-output"
    AUTO = "auto"


class CapabilityPacketCandidate(BaseModel):
    """An observable artifact that may become an ECPT capability packet."""

    packet_id: str
    source_kind: PacketSourceKind = PacketSourceKind.LOCAL
    source_ref: str
    content_sha256: str
    claim: str
    reuse_context: str = "general"
    receiver_family: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    expected_downstream_gain: float = 0.0
    verification_cost: float = 0.0
    residual_charge: float = 0.0
    salience_class: str = "default"
    freshness: float = 1.0
    expires_at: str | None = None
    verifier_routes: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    authority_required: bool = False
    authority_granted: bool = True
    route_safe: bool = True
    evidence_hash_valid: bool = True
    rollback_available: bool = True
    hazard_charge: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL


class EdgeWitness(BaseModel):
    """Finite witness that one or more packets support another packet or receiver."""

    edge_id: str
    source_packet_ids: list[str]
    target_packet_id: str
    edge_type: str = "semantic-dependency"
    confidence: float = 0.0
    residual: float = 0.0
    expires_at: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    accepted: bool = False


class EdgeWitnessCertificate(BaseModel):
    """Auditable finite certificate for a packet ecology edge."""

    certificate_id: str
    edge_id: str
    relation_type: str = "semantic-dependency"
    source_packet_ids: list[str] = Field(default_factory=list)
    target_packet_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    verifier_resolution_id: str | None = None
    confidence_lower_bound: float = 0.0
    false_edge_residual: float = 1.0
    expires_at: str | None = None
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


class VerifiedCapabilityPacket(BaseModel):
    """Finite-scope reusable packet capital after verifier and edge checks."""

    packet_id: str
    source_candidate_id: str
    verification_resolution_ids: list[str] = Field(default_factory=list)
    accepted_edge_witness_ids: list[str] = Field(default_factory=list)
    validity_domain: str = "protocol-relative-finite"
    receiver_family: list[str] = Field(default_factory=list)
    liquidity_score: float = 0.0
    execution_available: bool = False
    settlement_scope: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    expires_at: str | None = None
    rollback_receipt: str | None = None
    operationally_usable: bool = False
    settled: bool = False


class PacketPromotionPolicy(BaseModel):
    """Fail-closed policy for candidate-to-verified packet promotion."""

    require_route_resolution: bool = True
    require_receiver_compatibility: bool = True
    require_edge_certificate: bool = False
    require_rollback_available: bool = True
    allow_residual_external_obligations: bool = True
    minimum_confidence_lower_bound: float = 0.2


class PacketRejection(BaseModel):
    """Machine-readable packet promotion rejection."""

    packet_id: str
    source_candidate_id: str
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC


class PacketPromotionReport(BaseModel):
    """Batch packet promotion output for runtime steps."""

    report_id: str
    accepted: bool = False
    verified_packets: list[VerifiedCapabilityPacket] = Field(default_factory=list)
    rejected_packets: list[PacketRejection] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "packet promotion is finite-scope and protocol-relative",
            "verified packets do not settle residual external obligations",
            "hash, route, authority, expiry, rollback, and edge checks fail closed",
        ]
    )


class CapabilityPacketRegistry(BaseModel):
    """Deterministic packet registry for an ECPT packet ecology run."""

    registry_id: str
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    edges: list[EdgeWitness] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


class CapabilityBasinContract(BaseModel):
    """Finite target basin contract beyond tag-hit proxies."""

    basin_id: str
    receiver_family: list[str] = Field(default_factory=list)
    target_basis: list[str] = Field(default_factory=list)
    required_packet_types: list[str] = Field(default_factory=list)
    required_edge_types: list[str] = Field(default_factory=list)
    required_verifier_routes: list[str] = Field(default_factory=list)
    max_path_cost: float = 1.0
    validity_domain: str = "protocol-relative-finite"


class BasinReachabilityReport(BaseModel):
    """Finite basin reachability report for ECPT target contracts."""

    report_id: str
    basin_id: str
    accepted: bool = False
    reachable_packet_ids: list[str] = Field(default_factory=list)
    accepted_edge_ids: list[str] = Field(default_factory=list)
    missing_packet_types: list[str] = Field(default_factory=list)
    missing_edge_types: list[str] = Field(default_factory=list)
    missing_verifier_routes: list[str] = Field(default_factory=list)
    receiver_compatible: bool = False
    path_cost_lower_bound: float = 0.0
    residual_ledger: Ledger = Field(default_factory=Ledger)
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketIngestionReport(BaseModel):
    """Packet ingestion result for local, live, or agent-output sources."""

    report_id: str
    accepted: bool
    source_kind: PacketSourceKind
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


class VerificationThroughputReport(BaseModel):
    """Finite throughput dashboard for verifier queue health."""

    packet_inflow: int = 0
    accepted_packets: int = 0
    rejected_packets: int = 0
    abstained_packets: int = 0
    unresolved_obligation_backlog: int = 0
    verifier_latency_proxy: float = 0.0
    evidence_hash_mismatch_rate: float = 0.0
    stale_packet_ratio: float = 0.0
    false_liquidity_rate: float = 0.0
    residual_debt_growth: float = 0.0
    low_contribution_queue_occupation: float = 0.0


class PsiDashboard(BaseModel):
    """ECPT ASI-proxy phase bundle dashboard."""

    dashboard_id: str
    components: dict[str, float]
    threshold: dict[str, float]
    distance_to_threshold: dict[str, float]
    limiting_components: list[str] = Field(default_factory=list)
    throughput: VerificationThroughputReport = Field(default_factory=VerificationThroughputReport)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "Psi components are protocol-relative finite proxies",
            "dashboard output does not prove unobserved ASI or physical outcomes",
            "residual obligations remain explicit until verifier routes discharge them",
        ]
    )


class BottleneckIntervention(BaseModel):
    """One ranked bottleneck-inversion intervention."""

    intervention_id: str
    target_component: str
    action_kind: str
    expected_gain: float = 0.0
    verification_cost: float = 0.0
    risk_charge: float = 0.0
    rollback_condition: str = "no-positive-finite-gain"
    post_intervention_horizon: int = 1
    required_routes: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    score: float = 0.0


class BottleneckInversionPlan(BaseModel):
    """Ranked plan for improving limiting ECPT proxy components."""

    plan_id: str
    accepted: bool = False
    interventions: list[BottleneckIntervention] = Field(default_factory=list)
    limiting_components: list[str] = Field(default_factory=list)
    before_psi: dict[str, float] = Field(default_factory=dict)
    after_psi_lower_bound: dict[str, float] = Field(default_factory=dict)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    settled: bool = False


class ClosedLoopAgentIteration(BaseModel):
    """One closed-loop packet ecology iteration around an agent output."""

    iteration_id: str
    ingestion: PacketIngestionReport
    registry: CapabilityPacketRegistry
    psi: PsiDashboard
    plan: BottleneckInversionPlan
    next_agent_tasks: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "agent output is treated as packet evidence candidate, not proof",
            "planner output preserves residual and hazard ledgers",
            "closed-loop iteration is deterministic for identical inputs",
        ]
    )
