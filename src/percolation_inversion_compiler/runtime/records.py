"""Agent-facing ECPT active runtime records.

The runtime layer composes existing finite ECPT, SQOT, packet-ecology,
verifier-route, and residual-ledger checkers.  It intentionally does not add a
new status-promotion path: planning output is operational advice until verifier
routes discharge the relevant finite scope.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.adapter_routes import (
    VerifierEvidenceEnvelope,
    VerifierResolution,
)
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology.records import (
    BasinReachabilityReport,
    BottleneckInversionPlan,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitnessCertificate,
    PacketIngestionReport,
    PacketPromotionReport,
    PsiDashboard,
    VerifiedCapabilityPacket,
)
from percolation_inversion_compiler.ecpt.records import (
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlRunReport,
    PhaseControlState,
)
from percolation_inversion_compiler.sqot.records import QuarantineLedger, SalienceScheduleReport


class ActionCommitPolicy(StrEnum):
    """How aggressively a runtime may turn ranked advice into agent commitments."""

    RECOMMEND_ONLY = "recommend_only"
    REQUIRE_VERIFIER_RESOLUTION = "require_verifier_resolution"
    ALLOW_FINITE_SCOPE_COMMIT = "allow_finite_scope_commit"


class AgentRuntimeConfig(BaseModel):
    """Runtime knobs for deterministic active agent loops."""

    profile: str = "development"
    action_commit_policy: ActionCommitPolicy = ActionCommitPolicy.REQUIRE_VERIFIER_RESOLUTION
    allow_live_connectors: bool = False
    attention_budget: float = 1.0
    risk_budget: float = 1.0
    psi_threshold: dict[str, float] = Field(default_factory=dict)
    max_tasks: int = 8
    required_routes: list[str] = Field(default_factory=list)
    minimum_task_score: float = 0.0


class RuntimeEvent(BaseModel):
    """Append-only runtime event for audit and replay."""

    event_id: str
    event_type: str
    step_index: int
    payload_ref: str
    payload_sha256: str
    residual_delta: Ledger = Field(default_factory=Ledger)
    timestamp: str | None = None


class RuntimeEventLog(BaseModel):
    """Deterministic event log with aggregate hash."""

    events: list[RuntimeEvent] = Field(default_factory=list)
    aggregate_sha256: str = "0" * 64


class EvidenceResolutionBatch(BaseModel):
    """Batch verifier evidence resolution for one runtime step."""

    batch_id: str
    envelope_refs: list[str] = Field(default_factory=list)
    resolutions: list[VerifierResolution] = Field(default_factory=list)
    accepted_obligations: list[str] = Field(default_factory=list)
    rejected_obligations: list[str] = Field(default_factory=list)
    unresolved_envelope_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False


class RuntimeActionResult(BaseModel):
    """Result returned by an agent or executor after attempting an AgentTask."""

    result_id: str
    task_id: str
    action_id: str | None = None
    executed: bool = False
    output_ref: str | None = None
    output_sha256: str | None = None
    output_packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    evidence_envelopes: list[VerifierEvidenceEnvelope] = Field(default_factory=list)
    verifier_resolution: VerifierResolution | None = None
    observed_delta: dict[str, float] = Field(default_factory=dict)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    rollback_available: bool = False
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class RuntimeState(BaseModel):
    """Persistent runtime state for one ECPT active agent session."""

    state_id: str
    phase_state: PhaseControlState
    phase_objective: PhaseControlObjective
    phase_actions: list[PhaseControlAction] = Field(default_factory=list)
    packet_registry: CapabilityPacketRegistry = Field(
        default_factory=lambda: CapabilityPacketRegistry(registry_id="runtime-registry")
    )
    psi_threshold: dict[str, float] = Field(default_factory=dict)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    step_index: int = 0
    runtime_memory: list[str] = Field(default_factory=list)
    event_log: RuntimeEventLog = Field(default_factory=RuntimeEventLog)
    verified_packets: list[VerifiedCapabilityPacket] = Field(default_factory=list)
    quarantine_ledger: QuarantineLedger = Field(default_factory=QuarantineLedger)
    last_acceleration_certificate_refs: list[str] = Field(default_factory=list)


class RuntimeStepInput(BaseModel):
    """One batch of observations, agent output, packets, and source refs."""

    input_id: str
    agent_output: str | None = None
    local_sources: list[str] = Field(default_factory=list)
    live_sources: list[str] = Field(default_factory=list)
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    allow_live_connectors: bool = False
    evidence_envelope_refs: list[str] = Field(default_factory=list)
    evidence_envelopes: list[VerifierEvidenceEnvelope] = Field(default_factory=list)
    edge_certificates: list[EdgeWitnessCertificate] = Field(default_factory=list)


class RouteExecutionRequest(BaseModel):
    """Verifier-route work item emitted by the runtime."""

    request_id: str
    route_id: str
    verifier_route: str
    obligation_category: str
    required_evidence_kind: list[str] = Field(default_factory=list)
    safe_default: str
    residual_policy: str
    settlement_scope: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    priority_score: float = 0.0
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC


class AgentTask(BaseModel):
    """Concrete next action for an AI agent or orchestration system."""

    task_id: str
    task_type: str
    priority_score: float
    target_component: str
    action_kind: str
    action_id: str | None = None
    expected_proxy_gain: float = 0.0
    required_routes: list[str] = Field(default_factory=list)
    required_evidence_kind: list[str] = Field(default_factory=list)
    residual_coordinates: list[str] = Field(default_factory=list)
    rollback_condition: str = "runtime-score-nonpositive"
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ActionCommit(BaseModel):
    """Commit decision for a planned action under the configured policy."""

    action_id: str
    policy: ActionCommitPolicy
    recommended: bool = True
    committed: bool = False
    finite_scope_usable: bool = False
    verifier_resolution_required: bool = True
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseAccelerationScore(BaseModel):
    """Finite ECPT ASI-proxy acceleration score for ranking runtime outputs."""

    score_id: str
    total_score: float
    finite_proxy_gain: float = 0.0
    psi_distance_reduction: float = 0.0
    verification_throughput_score: float = 0.0
    residual_debt_charge: float = 0.0
    risk_charge: float = 0.0
    stale_packet_charge: float = 0.0
    false_liquidity_charge: float = 0.0
    missing_route_charge: float = 0.0
    components: dict[str, float] = Field(default_factory=dict)


class RuntimeRunReport(BaseModel):
    """Multi-step runtime trajectory used for finite acceleration comparison."""

    run_id: str
    initial_state_id: str
    reports: list[RuntimeStepReport] = Field(default_factory=list)
    psi_trajectory: list[PsiDashboard] = Field(default_factory=list)
    score_trajectory: list[PhaseAccelerationScore] = Field(default_factory=list)
    cumulative_residual_ledger: Ledger = Field(default_factory=Ledger)
    threshold_crossing_step: int | None = None
    resource_units: float = 0.0
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False


class AccelerationCertificate(BaseModel):
    """Finite protocol-relative acceleration certificate against a baseline."""

    certificate_id: str
    baseline_run_id: str
    candidate_run_id: str
    threshold: dict[str, float] = Field(default_factory=dict)
    tau_baseline: float | None = None
    tau_candidate: float | None = None
    hitting_time_gain_lower_bound: float = 0.0
    psi_distance_reduction_lower_bound: float = 0.0
    score_gain_lower_bound: float = 0.0
    resource_matched: bool = False
    salience_non_obstructed: bool = False
    false_liquidity_bounded: bool = False
    verification_backlog_bounded: bool = False
    residual_external_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class RuntimeComparisonReport(BaseModel):
    """Deterministic comparison between baseline and candidate runtime runs."""

    comparison_id: str
    baseline: RuntimeRunReport
    candidate: RuntimeRunReport
    resource_matched: bool = False
    acceleration_certificate: AccelerationCertificate
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False


class RuntimeStepReport(BaseModel):
    """One deterministic runtime step result."""

    report_id: str
    state_id: str
    input_id: str
    step_index: int
    accepted: bool
    schema_valid: bool = True
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    ingestion_reports: list[PacketIngestionReport] = Field(default_factory=list)
    registry: CapabilityPacketRegistry
    psi: PsiDashboard
    bottleneck_plan: BottleneckInversionPlan
    phase_run_report: PhaseControlRunReport
    salience_schedule: SalienceScheduleReport
    phase_acceleration_score: PhaseAccelerationScore
    evidence_resolution_batch: EvidenceResolutionBatch = Field(
        default_factory=lambda: EvidenceResolutionBatch(batch_id="evidence-resolution:none")
    )
    promotion_report: PacketPromotionReport = Field(
        default_factory=lambda: PacketPromotionReport(report_id="packet-promotion:none")
    )
    event_log_delta: RuntimeEventLog = Field(default_factory=RuntimeEventLog)
    basin_reachability: BasinReachabilityReport | None = None
    verified_packet_count: int = 0
    acceleration_certificate_eligible: bool = False
    agent_tasks: list[AgentTask] = Field(default_factory=list)
    action_commits: list[ActionCommit] = Field(default_factory=list)
    route_execution_requests: list[RouteExecutionRequest] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)
    allow_live_connectors: bool = False
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "runtime planning does not prove unobserved ASI, physical, or oracle outcomes",
            "settled remains false unless verifier rules discharge the full finite route scope",
            "live network ingestion is disabled unless explicitly requested",
            "residual ledgers and missing obligations are preserved across runtime steps",
        ]
    )


class RuntimeHealthReport(BaseModel):
    """Runtime readiness and safety summary for agent orchestration."""

    report_id: str
    state_id: str
    profile: str = "development"
    accepted: bool = False
    schema_valid: bool = True
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    packet_count: int = 0
    edge_count: int = 0
    route_count: int = 0
    residual_debt: float = 0.0
    psi_components: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    checks: dict[str, str] = Field(default_factory=dict)
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "health checks are finite operational diagnostics",
            "health output cannot promote runtime state to settled",
            "missing route or evidence data remains diagnostic",
        ]
    )


class RuntimeServiceSettings(BaseModel):
    """Local HTTP service settings."""

    host: str = "127.0.0.1"
    port: int = 8765
    profile: str = "development"
    require_token: bool | None = None
    token_env_var: str = "PIC_RUNTIME_TOKEN"
    allow_live_connectors: bool = False
