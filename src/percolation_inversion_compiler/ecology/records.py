"""Capability packet ecology records for ECPT active runtimes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.live_policy import (
    default_allow_live_connectors,
    live_default_mode,
)
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.identity.records import IdentityContributionStatus


class PacketSourceKind(StrEnum):
    LOCAL = "local"
    GITHUB = "github"
    ZENODO = "zenodo"
    ARXIV = "arxiv"
    HTTP = "http"
    WEB_PAGE = "web-page"
    RSS = "rss"
    ATOM = "atom"
    JSON_FEED = "json-feed"
    NDJSON = "ndjson"
    AGENT_MESSAGE = "agent-message"
    AGENT_INBOX = "agent-inbox"
    WEB_CRAWL = "web-crawl"
    AGENT_OUTPUT = "agent-output"
    AUTO = "auto"


class GeneralIntakeProfile(StrEnum):
    """Operational presets for bounded external intake."""

    LOCAL_ONLY = "local_only"
    CONTROLLED_WEB = "controlled_web"
    FEDERATED_AGENTS = "federated_agents"
    PRODUCTION_NETWORK = "production_network"
    ADVERSARIAL_NETWORK = "adversarial_network"


class ExternalCandidateClassification(StrEnum):
    """SQOT/runtime queue class for external packet candidates."""

    DIAGNOSTIC_WORK = "diagnostic_work"
    VERIFIER_WORK = "verifier_work"
    QUARANTINE_WORK = "quarantine_work"
    CANDIDATE_ONLY = "candidate_only"


class WebFetchPolicy(BaseModel):
    """Bounded policy for explicit-source web intake."""

    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    explicit_source_required: bool = True
    candidate_only_by_default: bool = True
    background_crawling_allowed: bool = False
    prefer_https: bool = True
    allow_http: bool = False
    max_redirects: int = 3
    max_depth: int = 1
    max_pages: int = 8
    max_bytes_per_resource: int = 1_000_000
    timeout_seconds: float = 20.0
    respect_robots: bool = True
    allowed_content_types: list[str] = Field(
        default_factory=lambda: [
            "application/atom+xml",
            "application/feed+json",
            "application/json",
            "application/rss+xml",
            "application/x-ndjson",
            "application/xml",
            "text/html",
            "text/plain",
            "text/xml",
        ]
    )
    allowed_schemes: list[str] = Field(default_factory=lambda: ["https"])
    allowed_hosts: list[str] = Field(default_factory=list)
    blocked_hosts: list[str] = Field(default_factory=list)
    allowed_path_prefixes: list[str] = Field(default_factory=list)
    max_total_bytes_per_run: int = 8_000_000
    max_total_packets_per_run: int = 256
    require_https_for_live: bool = True
    require_robots_decision: bool = False
    reject_private_networks: bool = True
    user_agent: str = "percolation-inversion-compiler-agent-intake/0.6.0"
    robots_uncertainty_is_diagnostic: bool = False
    diagnose_rate_limits: bool = True


class RobotsDecision(BaseModel):
    """Recorded robots/rate decision for bounded web intake.

    This is an audit record, not a guarantee that the remote site authorizes
    every downstream use.  Unknown or unavailable policy can remain diagnostic
    under stricter profiles.
    """

    decision_id: str = "robots:not-checked"
    source_ref: str = ""
    allowed: bool = True
    mode: str = "not-checked"
    reason: str = "robots policy was recorded but not enforced"
    residual_coordinate: str | None = None


class WebFetchReport(BaseModel):
    """Portable audit record for one bounded HTTP(S) resource fetch."""

    report_id: str
    requested_url: str
    final_url: str = ""
    redirect_chain: list[str] = Field(default_factory=list)
    status_code: int | None = None
    content_type: str | None = None
    content_sha256: str | None = None
    byte_count: int = 0
    robots_decision: RobotsDecision = Field(default_factory=RobotsDecision)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class IntakeProvenanceRecord(BaseModel):
    """Sanitized provenance for external packet candidates."""

    provenance_id: str
    source_kind: PacketSourceKind
    source_ref: str
    public_source_ref: str
    content_sha256: str | None = None
    media_type: str | None = None
    byte_count: int = 0
    final_url: str | None = None
    redirect_chain: list[str] = Field(default_factory=list)
    status_code: int | None = None
    robots_decision: RobotsDecision | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    residual_coordinates: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class GeneralIntakePolicy(BaseModel):
    """Policy for local, web, feed, and agent-message packet intake."""

    policy_id: str = "general-intake-policy"
    profile: str = "development"
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    explicit_source_required: bool = True
    candidate_only_by_default: bool = True
    allowed_source_kinds: list[PacketSourceKind] = Field(
        default_factory=lambda: [
            PacketSourceKind.LOCAL,
            PacketSourceKind.AGENT_OUTPUT,
            PacketSourceKind.AGENT_MESSAGE,
            PacketSourceKind.AGENT_INBOX,
            PacketSourceKind.HTTP,
            PacketSourceKind.WEB_PAGE,
            PacketSourceKind.RSS,
            PacketSourceKind.ATOM,
            PacketSourceKind.JSON_FEED,
            PacketSourceKind.NDJSON,
            PacketSourceKind.WEB_CRAWL,
            PacketSourceKind.GITHUB,
            PacketSourceKind.ZENODO,
            PacketSourceKind.ARXIV,
        ]
    )
    web_policy: WebFetchPolicy = Field(default_factory=WebFetchPolicy)
    require_signed_agent_messages: bool = False
    reject_replay_nonce: bool = True
    seen_message_nonces: list[str] = Field(default_factory=list)
    max_message_clock_skew_seconds: int = 300
    max_feed_entries: int = 256
    max_agent_messages_per_inbox: int = 256
    require_message_identity_context: bool = False
    residual_behavior: str = "external intake failures become diagnostic residual ledger entries"


class GeneralIntakePolicyDecision(BaseModel):
    """One deterministic policy decision for a general-intake source."""

    decision_id: str
    profile: str = "development"
    source_ref: str
    source_kind: PacketSourceKind = PacketSourceKind.AUTO
    accepted: bool = False
    allow_live_connectors: bool = False
    candidate_only: bool = True
    ecpt_phase_contribution_allowed: bool = False
    reasons: list[str] = Field(default_factory=list)
    residual_coordinates: list[str] = Field(default_factory=list)


class GeneralIntakeSource(BaseModel):
    """One source descriptor for bounded general packet intake."""

    source: str
    kind: PacketSourceKind = PacketSourceKind.AUTO
    label: str | None = None
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)


class AgentMessageEnvelope(BaseModel):
    """Protocol-relative agent-to-agent message envelope."""

    protocol_version: str = "pic-agent-message-v1"
    message_id: str
    sender_agent_id: str
    receiver_agent_id: str | None = None
    thread_id: str | None = None
    reply_to: str | None = None
    audience: list[str] = Field(default_factory=list)
    content: str
    content_sha256: str
    nonce: str | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    declared_packet_kind: str = "capability-packet-candidate"
    declared_receiver_family: list[str] = Field(default_factory=lambda: ["agent", "verifier"])
    declared_validity_domain: str = "protocol-relative-finite"
    issuer_public_key_id: str | None = None
    issuer_attestation_id: str | None = None
    signature_ref: str | None = None
    declared_routes: list[str] = Field(default_factory=list)
    route_request_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentPeerRecord(BaseModel):
    """Declared peer identity and communication capability."""

    peer_id: str
    agent_id: str
    public_key_id: str | None = None
    endpoint_ref: str | None = None
    accepted_source_kinds: list[PacketSourceKind] = Field(
        default_factory=lambda: [PacketSourceKind.AGENT_MESSAGE]
    )
    trust_profile: str = "development"
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentInboxRecord(BaseModel):
    """Portable local inbox/outbox record for agent packet exchange."""

    inbox_id: str = "agent-inbox"
    messages: list[AgentMessageEnvelope] = Field(default_factory=list)
    peers: list[AgentPeerRecord] = Field(default_factory=list)
    seen_nonces: list[str] = Field(default_factory=list)


class AgentMessageNonceLedger(BaseModel):
    """Deterministic nonce ledger used to reject replayed agent messages."""

    ledger_id: str = "agent-message-nonce-ledger"
    consumed_nonces: list[str] = Field(default_factory=list)
    replayed_nonces: list[str] = Field(default_factory=list)
    rejected_message_ids: list[str] = Field(default_factory=list)
    accepted: bool = True
    reasons: list[str] = Field(default_factory=list)


class AgentMessageVerificationContext(BaseModel):
    """Accepted population identity context for agent-to-agent messages."""

    context_id: str = "agent-message-verification-context"
    profile: str = "development"
    accepted: bool = False
    accepted_agent_ids: list[str] = Field(default_factory=list)
    accepted_public_key_ids: list[str] = Field(default_factory=list)
    accepted_attestation_ids: list[str] = Field(default_factory=list)
    require_agent_membership: bool = True
    require_public_key_membership: bool = True
    reasons: list[str] = Field(default_factory=list)


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
    provenance: list[IntakeProvenanceRecord] = Field(default_factory=list)
    web_fetch_reports: list[WebFetchReport] = Field(default_factory=list)


class GeneralIntakeReport(BaseModel):
    """General intake report that preserves diagnostic residuals."""

    report_id: str
    source: str
    source_kind: PacketSourceKind
    accepted: bool = False
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    ingestion_reports: list[PacketIngestionReport] = Field(default_factory=list)
    discovered_links: list[str] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    provenance: list[IntakeProvenanceRecord] = Field(default_factory=list)
    web_fetch_reports: list[WebFetchReport] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    settled: bool = False
    candidate_only: bool = True
    intake_profile: str = "development"
    policy_digest: str = ""
    source_policy_decisions: list[GeneralIntakePolicyDecision] = Field(default_factory=list)
    total_bytes_read: int = 0
    total_candidate_packets: int = 0
    sqot_queue_class: ExternalCandidateClassification = (
        ExternalCandidateClassification.CANDIDATE_ONLY
    )
    ecpt_phase_contribution_allowed: bool = False
    candidate_residual_coordinates: list[str] = Field(default_factory=list)


class WebDiscoveryReport(BaseModel):
    """Bounded web discovery report for link-tracked packet candidates."""

    report_id: str
    seed: str
    accepted: bool = False
    visited: list[str] = Field(default_factory=list)
    discovered_links: list[str] = Field(default_factory=list)
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    rejected_sources: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    provenance: list[IntakeProvenanceRecord] = Field(default_factory=list)
    web_fetch_reports: list[WebFetchReport] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    settled: bool = False


class AgentPacketExchangeReport(BaseModel):
    """Report for agent-message verification and packet candidate exchange."""

    report_id: str
    accepted: bool = False
    message_id: str | None = None
    sender_agent_id: str | None = None
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    replay_detected: bool = False
    signature_required: bool = False
    signature_present: bool = False
    consumed_nonces: list[str] = Field(default_factory=list)
    nonce_ledger: AgentMessageNonceLedger = Field(default_factory=AgentMessageNonceLedger)
    identity_verified: bool = False
    identity_reasons: list[str] = Field(default_factory=list)
    message_contract_valid: bool = False
    nonce_status: str = "not-provided"
    identity_status: str = "not-required"
    candidate_packet_ids: list[str] = Field(default_factory=list)
    quarantine_recommended: bool = False
    next_safe_commands: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)
    settled: bool = False


class AgentMessageDeliveryReport(BaseModel):
    """Report for deterministic local send/receive/verify agent-message workflows."""

    report_id: str
    action: str = "send"
    inbox_ref: str = ""
    inbox_id: str = "agent-inbox"
    profile: str = "development"
    message_ids: list[str] = Field(default_factory=list)
    delivered_message_ids: list[str] = Field(default_factory=list)
    rejected_message_ids: list[str] = Field(default_factory=list)
    exchange_reports: list[AgentPacketExchangeReport] = Field(default_factory=list)
    nonce_ledger: AgentMessageNonceLedger = Field(default_factory=AgentMessageNonceLedger)
    candidate_packet_ids: list[str] = Field(default_factory=list)
    identity_context_accepted: bool = False
    candidate_only: bool = True
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
    next_safe_commands: list[str] = Field(default_factory=list)


class AgentRelayReadinessReport(BaseModel):
    """Readiness report for local agent-to-agent inbox relay workflows."""

    report_id: str = "agent-relay-readiness"
    profile: str = "development"
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    inbox_ref: str | None = None
    inbox_exists: bool = False
    message_count: int = 0
    seen_nonce_count: int = 0
    signature_required: bool = False
    identity_context_required: bool = False
    identity_context_accepted: bool = False
    loopback_ready: bool = False
    bounded_candidate_intake: bool = True
    candidate_only: bool = True
    accepted: bool = True
    operationally_usable: bool = False
    settled: bool = False
    readiness: dict[str, str] = Field(default_factory=dict)
    recommended_next_commands: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class GeneralIntakeRuntimeBridgeReport(BaseModel):
    """SQOT/runtime bridge report for external packet candidates."""

    report_id: str
    source_report_id: str
    accepted: bool = False
    candidate_only: bool = True
    settled: bool = False
    packet_ingestion: PacketIngestionReport
    classifications: dict[str, ExternalCandidateClassification] = Field(default_factory=dict)
    sqot_queue_records: list[str] = Field(default_factory=list)
    verifier_work_packet_ids: list[str] = Field(default_factory=list)
    diagnostic_work_packet_ids: list[str] = Field(default_factory=list)
    quarantine_packet_ids: list[str] = Field(default_factory=list)
    ecpt_phase_contribution_allowed: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "external intake remains candidate-only until downstream checks promote it",
            "external candidate volume alone cannot improve Psi, BR, AC, "
            "or collective certificates",
            "settled remains false unless scoped finite verifier rules discharge obligations",
        ]
    )


class AgentMessageContractReport(BaseModel):
    """Portable contract check for one agent-to-agent message envelope."""

    report_id: str
    message_id: str
    accepted: bool = False
    protocol_version: str = "pic-agent-message-v1"
    message_contract_valid: bool = False
    sender_agent_id: str
    receiver_agent_id: str | None = None
    declared_packet_kind: str = "capability-packet-candidate"
    declared_validity_domain: str = "protocol-relative-finite"
    declared_receiver_family: list[str] = Field(default_factory=list)
    route_request_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    candidate_only: bool = True
    settled: bool = False


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
