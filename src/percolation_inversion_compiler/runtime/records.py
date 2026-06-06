"""Agent-facing ECPT active runtime records.

The runtime layer composes existing finite ECPT, SQOT, packet-ecology,
verifier-route, and residual-ledger checkers.  It intentionally does not add a
new status-promotion path: planning output is operational advice until verifier
routes discharge the relevant finite scope.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology.records import (
    BottleneckInversionPlan,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    PacketIngestionReport,
    PsiDashboard,
)
from percolation_inversion_compiler.ecpt.records import (
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlRunReport,
    PhaseControlState,
)
from percolation_inversion_compiler.sqot.records import SalienceScheduleReport


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


class RuntimeStepInput(BaseModel):
    """One batch of observations, agent output, packets, and source refs."""

    input_id: str
    agent_output: str | None = None
    local_sources: list[str] = Field(default_factory=list)
    live_sources: list[str] = Field(default_factory=list)
    packets: list[CapabilityPacketCandidate] = Field(default_factory=list)
    allow_live_connectors: bool = False
    evidence_envelope_refs: list[str] = Field(default_factory=list)


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
