"""Practical BIT bottleneck inversion records for Phase Ecology Lab."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilityExpressionPath(BaseModel):
    """Protocol-relative path from packet capital to an expressed capability proxy."""

    path_id: str
    packet_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    execution_available: bool = False
    settled: bool = False


class MinimalEnablingCondition(BaseModel):
    """Small finite condition required to remove one bottleneck."""

    condition_id: str
    bottleneck_id: str
    condition_type: str
    required_evidence: list[str] = Field(default_factory=list)
    verifier_routes: list[str] = Field(default_factory=list)
    residual_preserved: bool = True
    settled: bool = False


class ActivationGainEstimate(BaseModel):
    """Protocol-relative estimate of phase proxy activation after an inversion."""

    estimate_id: str
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    unit: str = "protocol-relative-phase-proxy"
    assumptions: list[str] = Field(default_factory=list)
    settled: bool = False


class PostInversionAuditPlan(BaseModel):
    """Audit steps that must follow a bottleneck inversion candidate."""

    plan_id: str
    required_checks: list[str] = Field(default_factory=list)
    evidence_to_record: list[str] = Field(default_factory=list)
    preserves_residuals: bool = True
    executes_actions: bool = False


class RollbackOrDeactivationPlan(BaseModel):
    """Rollback/deactivation plan for a candidate intervention."""

    plan_id: str
    rollback_required: bool = True
    rollback_refs_required: list[str] = Field(default_factory=list)
    deactivation_steps: list[str] = Field(default_factory=list)
    automatic_rollback: bool = False


class BottleneckClassDiagnosis(BaseModel):
    """One diagnosed bottleneck class and its finite evidence gap."""

    bottleneck_id: str
    bottleneck_class: str
    object_id: str
    severity: float = 1.0
    blockers: list[str] = Field(default_factory=list)
    minimal_enabling_conditions: list[MinimalEnablingCondition] = Field(default_factory=list)
    recommendation_only: bool = True
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class BottleneckInversionCandidate(BaseModel):
    """Recommendation-only BIT inversion candidate."""

    candidate_id: str
    bottleneck_id: str
    bottleneck_class: str
    minimal_enabling_conditions: list[MinimalEnablingCondition] = Field(default_factory=list)
    expected_activation_gain: ActivationGainEstimate
    verification_cost: float = 1.0
    rollback_or_deactivation_plan: RollbackOrDeactivationPlan
    post_inversion_audit_plan: PostInversionAuditPlan
    risk_hazard_authority_notes: list[str] = Field(default_factory=list)
    recommendation_only: bool = True
    mutates_repositories_shells_networks_or_models: bool = False
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class InversionCertificate(BaseModel):
    """Finite certificate candidate for a proposed BIT inversion."""

    certificate_id: str
    candidate_id: str
    certificate_status: str = "abstain"
    finite_requirements_passed: bool = False
    residual_preserved: bool = True
    grants_execution_authority: bool = False
    protocol_relative_only: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class BottleneckInversionReport(BaseModel):
    """BIT bottleneck diagnosis and recommendation report."""

    report_id: str = "bit-bottleneck-inversion-report"
    graph_id: str = ""
    capability_expression_paths: list[CapabilityExpressionPath] = Field(default_factory=list)
    bottlenecks: list[BottleneckClassDiagnosis] = Field(default_factory=list)
    inversion_candidates: list[BottleneckInversionCandidate] = Field(default_factory=list)
    certificates: list[InversionCertificate] = Field(default_factory=list)
    baseline_comparison: dict[str, float] = Field(default_factory=dict)
    recommendation_only: bool = True
    protocol_relative_only: bool = True
    accepted: bool = False
    workflow_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
