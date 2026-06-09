"""Capability packet ecology records for ECPT active runtimes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.identity.records import IdentityContributionStatus


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
    issuer_agent_id: str | None = None
    issuer_public_key_id: str | None = None
    issuer_attestation_id: str | None = None
    issuer_signature_ref: str | None = None
    identity_contribution_status: IdentityContributionStatus = (
        IdentityContributionStatus.PROVISIONAL
    )
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
    relation_evidence: dict[str, str] = Field(default_factory=dict)


class EdgeRelationVerifierSpec(BaseModel):
    """Portable verifier policy for one packet-edge relation type."""

    relation_type: str
    required_evidence_markers: list[str] = Field(default_factory=list)
    required_relation_evidence_keys: list[str] = Field(default_factory=list)
    required_source_tags: list[str] = Field(default_factory=list)
    required_target_tags: list[str] = Field(default_factory=list)
    require_verifier_resolution: bool = False
    require_receiver_overlap: bool = False
    minimum_confidence_lower_bound: float = 0.2
    residual_policy: str = "charge-false-edge-until-relation-evidence-is-accepted"


class EdgeRelationVerificationReport(BaseModel):
    """Semantic finite check for an edge certificate relation."""

    report_id: str
    certificate_id: str
    relation_type: str
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    matched_evidence_refs: list[str] = Field(default_factory=list)
    missing_evidence_markers: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class AcceptedPacketPath(BaseModel):
    """Accepted packet path witness into a finite ECPT basin."""

    path_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    route_ids: list[str] = Field(default_factory=list)
    cost: float = 0.0
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class ProtocolFrameDigest(BaseModel):
    """Finite digest of the declared ECPT protocol frame.

    The digest fixes the observation window, validity domain, allowed packet
    sources, and route catalog used by hidden-capability-injection checks.  It
    is a protocol identity record, not a proof of physical outcomes.
    """

    protocol_id: str
    observation_window_id: str = "default-observation-window"
    constraint_frame_id: str = "default-constraint-frame"
    validity_domain: str = "protocol-relative-finite"
    allowed_source_kinds: list[str] = Field(default_factory=list)
    allowed_route_ids: list[str] = Field(default_factory=list)
    allowed_packet_ids: list[str] = Field(default_factory=list)
    allowed_evidence_prefixes: list[str] = Field(default_factory=lambda: ["sha256:"])
    route_catalog_digest: str = ""
    sha256: str = ""
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class AutocatalyticClosureWitness(BaseModel):
    """Accepted finite closure witness for ECPT collective packet regeneration."""

    witness_id: str
    closure_packet_ids: list[str] = Field(default_factory=list)
    internal_edge_ids: list[str] = Field(default_factory=list)
    regeneration_edge_ids: list[str] = Field(default_factory=list)
    productive_packet_ids: list[str] = Field(default_factory=list)
    external_seed_packet_ids: list[str] = Field(default_factory=list)
    closure_strength: float = 0.0
    productivity_lower_bound: float = 0.0
    false_liquidity_rate: float = 0.0
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ExecutionAvailablePathCertificate(BaseModel):
    """Finite certificate that a path is execution-available but not executed."""

    certificate_id: str
    path_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    route_ids: list[str] = Field(default_factory=list)
    not_executed: bool = True
    execution_gates: list[str] = Field(default_factory=list)
    authority_granted: bool = True
    rollback_available: bool = True
    receiver_context: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    constraint_frame_id: str = "default-constraint-frame"
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketCapitalLineage(BaseModel):
    """Lineage record for finite verified packet capital."""

    lineage_id: str
    packet_id: str
    source_candidate_id: str | None = None
    parent_packet_ids: list[str] = Field(default_factory=list)
    edge_certificate_ids: list[str] = Field(default_factory=list)
    verifier_resolution_ids: list[str] = Field(default_factory=list)
    runtime_event_ids: list[str] = Field(default_factory=list)
    protocol_frame_sha256: str | None = None
    residual_external_obligations: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class HiddenCapabilityInjectionReport(BaseModel):
    """Fail-closed check for packets, edges, evidence, or events outside protocol."""

    report_id: str
    protocol_id: str
    checked_packet_ids: list[str] = Field(default_factory=list)
    rejected_packet_ids: list[str] = Field(default_factory=list)
    rejected_edge_ids: list[str] = Field(default_factory=list)
    rejected_event_ids: list[str] = Field(default_factory=list)
    rejected_evidence_refs: list[str] = Field(default_factory=list)
    rejected_agent_ids: list[str] = Field(default_factory=list)
    unsigned_packet_ids: list[str] = Field(default_factory=list)
    allowed_source_kinds: list[str] = Field(default_factory=list)
    allowed_route_ids: list[str] = Field(default_factory=list)
    allowed_packet_ids: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


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
    issuer_agent_id: str | None = None
    issuer_public_key_id: str | None = None
    issuer_attestation_id: str | None = None
    identity_contribution_status: IdentityContributionStatus = IdentityContributionStatus.VERIFIED
    operationally_usable: bool = False
    settled: bool = False


class PacketPromotionPolicy(BaseModel):
    """Fail-closed policy for candidate-to-verified packet promotion."""

    require_route_resolution: bool = True
    require_receiver_compatibility: bool = True
    require_edge_certificate: bool = False
    require_rollback_available: bool = True
    require_agent_identity_attestation: bool = False
    require_issuer_in_population: bool = False
    allow_residual_external_obligations: bool = True
    minimum_confidence_lower_bound: float = 0.2

    @classmethod
    def for_profile(cls, profile: str) -> PacketPromotionPolicy:
        """Return the packet-promotion policy for an execution profile."""

        normalized = profile.lower()
        if normalized in {"production", "adversarial"}:
            return cls(
                require_route_resolution=True,
                require_receiver_compatibility=True,
                require_edge_certificate=True,
                require_rollback_available=True,
                require_agent_identity_attestation=True,
                require_issuer_in_population=True,
                allow_residual_external_obligations=False,
                minimum_confidence_lower_bound=0.5,
            )
        if normalized in {"controlled", "federated"}:
            return cls(
                require_route_resolution=True,
                require_receiver_compatibility=True,
                require_edge_certificate=True,
                require_rollback_available=True,
                require_agent_identity_attestation=True,
                require_issuer_in_population=True,
                allow_residual_external_obligations=True,
                minimum_confidence_lower_bound=0.4,
            )
        if normalized == "research":
            return cls(
                require_route_resolution=True,
                require_receiver_compatibility=True,
                require_edge_certificate=True,
                require_rollback_available=True,
                require_agent_identity_attestation=True,
                require_issuer_in_population=False,
                allow_residual_external_obligations=True,
                minimum_confidence_lower_bound=0.35,
            )
        return cls()


class PacketRejection(BaseModel):
    """Machine-readable packet promotion rejection."""

    packet_id: str
    source_candidate_id: str
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    identity_contribution_status: IdentityContributionStatus = IdentityContributionStatus.REJECTED
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC


class PacketPromotionReport(BaseModel):
    """Batch packet promotion output for runtime steps."""

    report_id: str
    accepted: bool = False
    verified_packets: list[VerifiedCapabilityPacket] = Field(default_factory=list)
    rejected_packets: list[PacketRejection] = Field(default_factory=list)
    identity_contribution_summary: dict[str, int] = Field(default_factory=dict)
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
    accepted_paths: list[AcceptedPacketPath] = Field(default_factory=list)
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
