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


class CapabilityPacketRegistry(BaseModel):
    """Deterministic packet registry for an ECPT packet ecology run."""

    registry_id: str
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    edges: list[EdgeWitness] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


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
