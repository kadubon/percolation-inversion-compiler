"""Deterministic phase-acceleration planner records.

These records are an agent-facing planning layer over the existing runtime,
SQOT, ALT, ECPT, BIT, and TRC reports.  They do not execute actions and they do
not promote candidate packets or external messages to settled status.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.alt.records import (
    ALTAdmissionDecision,
    FoundryControlDashboard,
)
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology.records import (
    AgentMessageDeliveryReport,
    GeneralIntakeRuntimeBridgeReport,
    PsiDashboard,
)
from percolation_inversion_compiler.runtime.records import (
    AgentRuntimeConfig,
    BottleneckWitnessReport,
    FrontierDebtReport,
    PhaseControlAuditSummary,
    RuntimeIdentityContext,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)
from percolation_inversion_compiler.sqot.records import SalienceScheduleReport


class PhaseAccelerationRequest(BaseModel):
    """Input contract for deterministic phase-acceleration planning."""

    request_id: str = "phase-acceleration"
    profile: str = "development"
    state: RuntimeState | None = None
    step_input: RuntimeStepInput | None = None
    runtime_config: AgentRuntimeConfig | None = None
    runtime_report: RuntimeStepReport | None = None
    identity_context: RuntimeIdentityContext | None = None
    alt_admission_decisions: list[ALTAdmissionDecision] = Field(default_factory=list)
    foundry_dashboard: FoundryControlDashboard | None = None
    general_intake_bridge_reports: list[GeneralIntakeRuntimeBridgeReport] = Field(
        default_factory=list
    )
    agent_message_delivery_reports: list[AgentMessageDeliveryReport] = Field(default_factory=list)
    psi_threshold: dict[str, float] = Field(default_factory=dict)
    compact: bool = False
    max_bottlenecks: int = 8


class PhaseComponentGap(BaseModel):
    """One finite gap between a phase proxy component and its threshold."""

    component: str
    current_value: float = 0.0
    threshold_value: float = 0.0
    gap: float = 0.0
    limiting: bool = False
    source: str = "PsiDashboard"
    reasons: list[str] = Field(default_factory=list)


class PhaseGapVector(BaseModel):
    """Portable vector of remaining protocol-relative phase gaps."""

    vector_id: str = "phase-gap-vector"
    components: list[PhaseComponentGap] = Field(default_factory=list)
    limiting_components: list[str] = Field(default_factory=list)
    aggregate_gap: float = 0.0
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class BottleneckCandidate(BaseModel):
    """Ranked repair target derived from existing runtime and theory reports."""

    candidate_id: str
    source: str
    bottleneck_kind: str
    target_component: str = ""
    priority_score: float = 0.0
    release_delta: float = 0.0
    burden_delta: float = 0.0
    residual_coordinates: list[str] = Field(default_factory=list)
    next_verifier_routes: list[str] = Field(default_factory=list)
    required_evidence_kind: list[str] = Field(default_factory=list)
    next_safe_commands: list[str] = Field(default_factory=list)
    sdk_calls: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    candidate_only: bool = False
    cannot_promote_because: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SafePhaseAction(BaseModel):
    """Recommendation-only action for an agent or orchestration layer."""

    action_id: str
    action_type: str
    title: str
    purpose: str
    priority_score: float = 0.0
    safe_commands: list[str] = Field(default_factory=list)
    sdk_calls: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    inspect_fields: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_effect: str = "diagnostic planning only"
    candidate_only: bool = False
    execution_authority_granted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseAccelerationPlan(BaseModel):
    """Agent-operable plan for removing finite phase bottlenecks."""

    plan_id: str = "phase-acceleration-plan"
    request_id: str = "phase-acceleration"
    profile: str = "development"
    report_mode: str = "full"
    accepted: bool = False
    workflow_usable: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    phase_gap_vector: PhaseGapVector = Field(default_factory=PhaseGapVector)
    current_psi: PsiDashboard | None = None
    runtime_report: RuntimeStepReport | None = None
    phase_control_audit: PhaseControlAuditSummary | None = None
    frontier_debt_report: FrontierDebtReport | None = None
    bottleneck_witness_reports: list[BottleneckWitnessReport] = Field(default_factory=list)
    salience_schedule: SalienceScheduleReport | None = None
    alt_admission_decisions: list[ALTAdmissionDecision] = Field(default_factory=list)
    foundry_dashboard: FoundryControlDashboard | None = None
    general_intake_bridge_reports: list[GeneralIntakeRuntimeBridgeReport] = Field(
        default_factory=list
    )
    agent_message_delivery_reports: list[AgentMessageDeliveryReport] = Field(default_factory=list)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    missing_obligations: list[str] = Field(default_factory=list)
    unresolved_obligation_count: int = 0
    bottlenecks: list[BottleneckCandidate] = Field(default_factory=list)
    recommended_actions: list[SafePhaseAction] = Field(default_factory=list)
    safe_commands: list[str] = Field(default_factory=list)
    sdk_calls: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    cannot_promote_because: list[str] = Field(default_factory=list)
    candidate_only_reasons: list[str] = Field(default_factory=list)
    settled_blockers: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class PhaseTrajectoryReport(BaseModel):
    """Deterministic trajectory over one or more phase-acceleration plans."""

    report_id: str = "phase-trajectory"
    profile: str = "development"
    plans: list[PhaseAccelerationPlan] = Field(default_factory=list)
    aggregate_gap_trajectory: list[float] = Field(default_factory=list)
    limiting_component_trajectory: list[list[str]] = Field(default_factory=list)
    monotone_nonpromotion_preserved: bool = True
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PhaseAccelerationBenchmarkReport(BaseModel):
    """Deterministic comparison of unstructured sharing and PIC-guided routing."""

    report_id: str = "phase-acceleration-benchmark"
    profile: str = "development"
    scenario: str = "candidate-sharing-vs-pic-guided-routing"
    baseline_label: str = "unstructured-candidate-sharing"
    candidate_label: str = "pic-guided-finite-routing"
    baseline_candidate_only_count: int = 0
    pic_guided_repairable_bottleneck_count: int = 0
    baseline_phase_gap: float = 0.0
    pic_guided_phase_gap: float = 0.0
    finite_route_count_delta: int = 0
    residual_visibility_delta: int = 0
    accepted: bool = False
    workflow_usable: bool = False
    operationally_usable: bool = False
    settled: bool = False
    invariant_checks: dict[str, bool] = Field(default_factory=dict)
    safety_invariants: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
