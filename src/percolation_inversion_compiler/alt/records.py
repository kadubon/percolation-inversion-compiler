"""Abstraction Liquidity Theory records.

ALT records model reusable abstraction assets as finite, protocol-relative
certificates.  They do not assert that an external-world, physical, oracle, or
ASI claim is settled.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus


class ALTAdmissionAction(StrEnum):
    """Lifecycle action for an abstraction token or certificate packet."""

    ADMIT = "admit"
    REJECT = "reject"
    DEFER = "defer"
    SUSPEND = "suspend"
    DEPRECATE = "deprecate"
    ROLLBACK = "rollback"
    RESURRECT_AS_CANDIDATE = "resurrect_as_candidate"


class FoundryBottleneck(StrEnum):
    """Finite foundry bottleneck labels used by phase-control dashboards."""

    EVIDENCE_LIMITED = "evidence-limited"
    TRANSPORT_LIMITED = "transport-limited"
    RISK_LIMITED = "risk-limited"
    CAPACITY_LIMITED = "capacity-limited"
    SUBCRITICAL = "subcritical"
    UNSATURATED_SUPERCRITICAL = "unsaturated-supercritical"
    COLLECT_EVIDENCE = "collect-evidence"
    SUSPEND = "suspend"


class ProblemSolvingTrace(BaseModel):
    """Observed finite trace from which an abstraction token may be extracted."""

    trace_id: str
    task_id: str
    receiver_family: list[str] = Field(default_factory=list)
    observation_refs: list[str] = Field(default_factory=list)
    action_refs: list[str] = Field(default_factory=list)
    result_refs: list[str] = Field(default_factory=list)
    cost_ledger: Ledger = Field(default_factory=Ledger)
    provenance_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class ObservedTraceProjection(BaseModel):
    """Projection of an observed trace into token-relevant coordinates."""

    projection_id: str
    trace_id: str
    retained_fields: list[str] = Field(default_factory=list)
    omitted_fields: list[str] = Field(default_factory=list)
    information_loss_bound: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class TraceSufficiencyCertificate(BaseModel):
    """Finite certificate that a trace projection supports token extraction."""

    certificate_id: str
    trace_id: str
    projection_id: str
    required_fields: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    sufficiency_lower_bound: float = 0.0
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class TokenLineage(BaseModel):
    """Lineage of an abstraction token through traces, packets, and versions."""

    lineage_id: str
    token_id: str
    source_trace_ids: list[str] = Field(default_factory=list)
    source_packet_ids: list[str] = Field(default_factory=list)
    parent_token_ids: list[str] = Field(default_factory=list)
    version: str = "0"
    content_sha256: str | None = None
    provenance_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class AbstractionToken(BaseModel):
    """Candidate reusable abstraction with declared receivers and dependencies."""

    token_id: str
    claim: str
    receiver_family: list[str] = Field(default_factory=list)
    validity_domain: str = "protocol-relative-finite"
    dependency_ids: list[str] = Field(default_factory=list)
    interface_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    authority_refs: list[str] = Field(default_factory=list)
    capability_envelope_refs: list[str] = Field(default_factory=list)
    verifier_routes: list[str] = Field(default_factory=list)
    lineage: TokenLineage | None = None
    candidate_only: bool = True
    residual_ledger: Ledger = Field(default_factory=Ledger)
    status: ClaimStatus = ClaimStatus.PROVISIONAL


class MissionValidityCertificate(BaseModel):
    """Finite mission-validity certificate for a token and receiver context."""

    certificate_id: str
    token_id: str
    mission_id: str
    receiver_family: list[str] = Field(default_factory=list)
    target_basis: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class TransportCertificate(BaseModel):
    """Finite transport certificate for token reuse across receiver contexts."""

    certificate_id: str
    token_id: str
    source_receiver_family: list[str] = Field(default_factory=list)
    target_receiver_family: list[str] = Field(default_factory=list)
    support_coverage_lower_bound: float = 0.0
    density_ratio_upper_bound: float = 1.0
    max_density_ratio: float = 10.0
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class FormationCostLedger(BaseModel):
    """ALT cost ledger for forming, validating, deploying, and maintaining a token."""

    ledger_id: str
    formation_cost: float = 0.0
    deployment_cost: float = 0.0
    validation_cost: float = 0.0
    certification_cost: float = 0.0
    settlement_cost: float = 0.0
    maintenance_cost: float = 0.0
    depreciation_cost: float = 0.0
    contamination_cost: float = 0.0
    hidden_resource_cost: float = 0.0
    telemetry_cost: float = 0.0
    absorption_cost: float = 0.0
    misapplication_cost: float = 0.0
    hazard_cost: float = 0.0
    unit: str = "dimensionless"
    evidence_refs: list[str] = Field(default_factory=list)

    def total_cost(self) -> float:
        """Return the finite ALT cost burden."""

        return (
            self.formation_cost
            + self.deployment_cost
            + self.validation_cost
            + self.certification_cost
            + self.settlement_cost
            + self.maintenance_cost
            + self.depreciation_cost
            + self.contamination_cost
            + self.hidden_resource_cost
            + self.telemetry_cost
            + self.absorption_cost
            + self.misapplication_cost
            + self.hazard_cost
        )


class LifecycleCostBounds(BaseModel):
    """Lifecycle/finality bounds for abstraction capital accounting."""

    bounds_id: str
    half_life_lower_bound: float = 0.0
    expiry_horizon: str | None = None
    finality_record_ref: str | None = None
    depreciation_upper_bound: float = 0.0
    maintenance_upper_bound: float = 0.0
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class OpportunityMeasureContract(BaseModel):
    """Declared finite opportunity measure used to value a token."""

    contract_id: str
    mission_id: str
    receiver_family: list[str] = Field(default_factory=list)
    task_portfolio_refs: list[str] = Field(default_factory=list)
    horizon: str = "finite"
    baseline_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class RootFinalityCertificate(BaseModel):
    """Role-separated root and finality certificate for ALT settlement."""

    certificate_id: str
    token_id: str
    root_role_refs: list[str] = Field(default_factory=list)
    evaluator_quorum_refs: list[str] = Field(default_factory=list)
    finality_record_ref: str | None = None
    byzantine_budget_upper_bound: float = 0.0
    correlated_capture_budget_upper_bound: float = 0.0
    partition_alarm: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class TelemetryCostCertificate(BaseModel):
    """Finite telemetry accounting certificate for ALT cost coordinates."""

    certificate_id: str
    token_id: str
    observer_refs: list[str] = Field(default_factory=list)
    measured_cost_upper_bound: float = 0.0
    observer_cost_upper_bound: float = 0.0
    tamper_positive: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class HazardEnvelopeCertificate(BaseModel):
    """Finite hazard, misuse, externality, and rollback envelope."""

    certificate_id: str
    token_id: str
    hazard_refs: list[str] = Field(default_factory=list)
    authority_envelope_refs: list[str] = Field(default_factory=list)
    capability_envelope_refs: list[str] = Field(default_factory=list)
    rollback_refs: list[str] = Field(default_factory=list)
    noncompensable_hazard_detected: bool = False
    irreversible_risk_upper_bound: float = 0.0
    risk_budget_upper_bound: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class BaselineRefreshCertificate(BaseModel):
    """Finite bridge from an old baseline/opportunity law to a refreshed one."""

    certificate_id: str
    old_baseline_ref: str
    new_baseline_ref: str
    opportunity_contract_id: str | None = None
    resource_matched: bool = False
    refresh_bridge_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class LiquidityCertificate(BaseModel):
    """Certified lower-bound surplus certificate for reusable abstraction capital."""

    certificate_id: str
    token_id: str
    downstream_search_cost_reduction_lower_bound: float = 0.0
    cost_ledger: FormationCostLedger = Field(
        default_factory=lambda: FormationCostLedger(ledger_id="formation-cost-ledger")
    )
    transport_certificate: TransportCertificate | None = None
    mission_validity_certificate: MissionValidityCertificate | None = None
    lifecycle_bounds: LifecycleCostBounds | None = None
    opportunity_contract: OpportunityMeasureContract | None = None
    root_finality_certificate: RootFinalityCertificate | None = None
    telemetry_cost_certificate: TelemetryCostCertificate | None = None
    hazard_envelope_certificate: HazardEnvelopeCertificate | None = None
    root_of_trust_refs: list[str] = Field(default_factory=list)
    evaluator_quorum_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    robustness_refs: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    signed_surplus_lower_bound: float = 0.0
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    reasons: list[str] = Field(default_factory=list)


class NegativeLiquidityCertificate(BaseModel):
    """Finite upper-bound certificate for pruning harmful or illiquid tokens."""

    certificate_id: str
    token_id: str
    scope_id: str
    surplus_upper_bound: float = 0.0
    lower_cost_bound: float = 0.0
    transport_scope_refs: list[str] = Field(default_factory=list)
    failure_mode: str = "unspecified"
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class ALTDeprecationRecord(BaseModel):
    """Deprecation record preserving token lineage and negative certificate scope."""

    record_id: str
    token_id: str
    negative_certificate_id: str
    scope_id: str
    deprecation_reason: str
    rollback_refs: list[str] = Field(default_factory=list)
    lineage_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class ALTResurrectionRecord(BaseModel):
    """Candidate resurrection record that overrides a prior failure mode."""

    record_id: str
    token_id: str
    prior_deprecation_id: str
    override_failure_mode: str
    current_positive_packet_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class ExecutableALTCertificatePacket(BaseModel):
    """Executable packet carrying a token and its ALT certificates."""

    packet_id: str
    token: AbstractionToken
    trace_sufficiency: TraceSufficiencyCertificate | None = None
    liquidity_certificate: LiquidityCertificate | None = None
    negative_liquidity_certificate: NegativeLiquidityCertificate | None = None
    verifier_routes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class FoundryState(BaseModel):
    """Finite abstraction foundry state for token/capital formation."""

    foundry_id: str
    token_candidates: list[AbstractionToken] = Field(default_factory=list)
    certificate_packets: list[ExecutableALTCertificatePacket] = Field(default_factory=list)
    certified_capital: list[CertifiedAbstractionCapital] = Field(default_factory=list)
    deprecation_records: list[ALTDeprecationRecord] = Field(default_factory=list)
    resurrection_records: list[ALTResurrectionRecord] = Field(default_factory=list)
    exploration_ledger: Ledger = Field(default_factory=Ledger)
    settlement_ledger: Ledger = Field(default_factory=Ledger)
    evidence_backlog: int = 0
    transport_backlog: int = 0
    risk_backlog: int = 0
    receiver_absorption_capacity: float = 1.0
    settlement_capacity: float = 1.0
    residual_ledger: Ledger = Field(default_factory=Ledger)


class FoundryControlDashboard(BaseModel):
    """Foundry dashboard for ALT bottleneck control."""

    dashboard_id: str
    foundry_id: str
    certified_capital_count: int = 0
    token_candidate_count: int = 0
    evidence_backlog: int = 0
    transport_backlog: int = 0
    risk_backlog: int = 0
    receiver_absorption_capacity: float = 0.0
    settlement_capacity: float = 0.0
    net_certified_surplus: float = 0.0
    bottlenecks: list[FoundryBottleneck] = Field(default_factory=list)
    recommended_rule: FoundryBottleneck = FoundryBottleneck.COLLECT_EVIDENCE
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ALTAdmissionDecision(BaseModel):
    """Fail-closed admission decision for one ALT certificate packet."""

    decision_id: str
    packet_id: str
    action: ALTAdmissionAction = ALTAdmissionAction.DEFER
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    certified_capital_ref: str | None = None
    residual_ledger: Ledger = Field(default_factory=Ledger)
    missing_obligations: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class CertifiedAbstractionCapital(BaseModel):
    """Finite-scope certified abstraction capital usable by ECPT phase runtime."""

    capital_id: str
    token_id: str
    liquidity_certificate_id: str
    surplus_lower_bound: float = 0.0
    receiver_family: list[str] = Field(default_factory=list)
    validity_domain: str = "protocol-relative-finite"
    evidence_refs: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    operationally_usable: bool = False
    settled: bool = False


class ALTAccelerationCertificate(BaseModel):
    """Finite comparison certificate for abstraction-liquidity acceleration."""

    certificate_id: str
    baseline_foundry_id: str
    candidate_foundry_id: str
    certified_surplus_gain_lower_bound: float = 0.0
    settlement_latency_reduction_lower_bound: float = 0.0
    resource_matched: bool = False
    residual_external_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ReproductionMatrixCertificate(BaseModel):
    """Finite certificate for abstraction-capital reproduction diagnostics."""

    certificate_id: str
    foundry_id: str
    matrix_refs: list[str] = Field(default_factory=list)
    spectral_radius_upper_bound: float = 0.0
    spectral_radius_lower_bound: float = 0.0
    capacity_feasible: bool = False
    gauge_compatible: bool = False
    causal_identification_refs: list[str] = Field(default_factory=list)
    transport_validity_refs: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class ALTCARACertificate(BaseModel):
    """Target-valid ALT certified ASI-realization acceleration certificate."""

    certificate_id: str
    target_id: str
    acceleration_certificate: ALTAccelerationCertificate
    certified_capital_witness_refs: list[str] = Field(default_factory=list)
    target_validity_refs: list[str] = Field(default_factory=list)
    baseline_upper_envelope_refs: list[str] = Field(default_factory=list)
    resource_matched_baseline_refs: list[str] = Field(default_factory=list)
    live_predicate_refs: list[str] = Field(default_factory=list)
    hazard_envelope_refs: list[str] = Field(default_factory=list)
    transport_validity_refs: list[str] = Field(default_factory=list)
    non_tradable_constraint_refs: list[str] = Field(default_factory=list)
    residual_external_obligations: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class ALTKernelTransitionReport(BaseModel):
    """Report that an ALT kernel transition preserved dual-ledger invariants."""

    report_id: str
    prior_state_id: str
    next_state_id: str
    action: ALTAdmissionAction
    exploration_ledger: Ledger = Field(default_factory=Ledger)
    settlement_ledger: Ledger = Field(default_factory=Ledger)
    deprecation_record_refs: list[str] = Field(default_factory=list)
    resurrection_record_refs: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)
