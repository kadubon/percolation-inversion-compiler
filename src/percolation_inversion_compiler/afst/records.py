"""AFST satisfaction-flux diagnostic records.

AFST records describe finite, non-executing checks for moving certified typed
surplus toward declared satisfaction deficits.  They do not grant authority,
prove physical outcomes, or promote any claim to settlement.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus

AFST_NON_CLAIMS = [
    "not_execution_authority",
    "not_physical_outcome_proof",
    "not_provider_dispatch",
    "not_market_or_ownership_override",
    "not_contract_override",
    "not_human_consent_bypass",
    "not_refusal_suppression",
    "not_resource_creation",
    "not_settlement_without_verifier",
    "not_alt_capital_admission",
    "not_ecpt_phase_promotion",
]
ACCEPTED_AUTHORITY_STATUSES = {"active", "approved", "accepted", "granted"}
ACTIVE_REFUSAL_KINDS = {"active_refusal", "legal_hold", "stop_threshold_crossed"}
AFST_SCHEMA_VERSION = "pic.afst_flux_stabilization.v1"


class AFSTProfilePolicy(BaseModel):
    """Explicit AFST profile policy for evidence and blocker handling."""

    profile: str = "development"
    require_authority: bool = True
    require_consent_channel: bool = False
    require_refusal_channel: bool = True
    require_buffer: bool = True
    require_handover_for_controller_change: bool = True
    require_balance_witness: bool = True
    require_lifecycle_freshness: bool = True
    allow_auxiliary_price_signal: bool = True
    allow_speculative_effect_prediction: bool = True
    operationally_usable_requires_observed_effect: bool = False
    hard_refusal_blocks: bool = True


class RawInputAudit(BaseModel):
    """Raw input presence audit used before defaults can hide missing fields."""

    audit_id: str = "afst-raw-input-audit"
    supplied_paths: list[str] = Field(default_factory=list)
    missing_required_paths: list[str] = Field(default_factory=list)
    unknown_paths: list[str] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class UnitFrame(BaseModel):
    """Finite unit frame with no implicit conversion in AFST v1."""

    resource_type: str = ""
    unit: str = "dimensionless"
    unit_family: str | None = None
    validity_domain: str = "protocol-relative-finite"


class SatisfactionCoordinate(BaseModel):
    """Declared, observed, or predicted satisfaction coordinate."""

    coordinate_id: str = ""
    cell_id: str = ""
    resource_type: str = ""
    value: float = 0.0
    floor_critical: float = 0.0
    floor_min: float = 0.0
    floor_safe: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    measurement_mode: str = "declared"
    observation_window_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class SatisfactionDeficit(BaseModel):
    """Finite deficit derived from a satisfaction coordinate."""

    deficit_id: str = ""
    coordinate_id: str = ""
    cell_id: str = ""
    resource_type: str = ""
    amount: float = 0.0
    uncertainty_charge: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    floor_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class CertifiedAbundanceCoordinate(BaseModel):
    """Local certified surplus after floors, reserves, holds, and residuals."""

    abundance_id: str = ""
    cell_id: str = ""
    resource_type: str = ""
    available_amount: float = 0.0
    safe_floor: float = 0.0
    reserve_amount: float = 0.0
    legal_hold_amount: float = 0.0
    spoilage_upper_bound: float = 0.0
    transfer_loss_upper_bound: float = 0.0
    observation_residual: float = 0.0
    lifecycle_residual: float = 0.0
    other_hard_residual: float = 0.0
    certified_amount: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    observation_window_ref: str | None = None
    authority_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    expires_at: str | None = None
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class AuthorityEnvelope(BaseModel):
    """Finite authority envelope; not an execution grant by itself."""

    authority_id: str = ""
    issuer: str = ""
    subject: str = ""
    scope: list[str] = Field(default_factory=list)
    action: str = ""
    resource_type: str = ""
    status: str = "unknown"
    issued_at: str | None = None
    expires_at: str | None = None
    revocation_ref: str | None = None
    fixture_only: bool = False
    audit_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class ConsentChannel(BaseModel):
    """Consent channel attached to a target or subject cell."""

    consent_id: str = ""
    subject_cell_id: str = ""
    mode: str = "declared"
    consent_granted: bool = False
    scope: list[str] = Field(default_factory=list)
    resource_type: str = ""
    action: str = ""
    expires_at: str | None = None
    revocation_ref: str | None = None
    explanation_available: bool = False
    appeal_available: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class RefusalChannel(BaseModel):
    """Refusal and legal-hold channel that must not be suppressed."""

    channel_id: str = ""
    subject_cell_id: str = ""
    mode: str = "declared"
    active_refusal: bool = False
    legal_hold: bool = False
    explanation_requested: bool = False
    appeal_available: bool = False
    stop_threshold: float = 1.0
    observed_signal: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class CandidateFlux(BaseModel):
    """Candidate non-market flux from a source cell to a target cell."""

    flux_id: str = ""
    source_cell_id: str = ""
    target_cell_id: str = ""
    resource_type: str = ""
    amount: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    latency: float = 0.0
    loss_upper_bound: float = 0.0
    transfer_residual: float = 0.0
    conversion_factor: float = 1.0
    liquidity_mode: str = "non_market"
    price_signal: float | None = None
    authority_envelope_refs: list[str] = Field(default_factory=list)
    consent_refs: list[str] = Field(default_factory=list)
    refusal_refs: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
    trc_resource_flow_refs: list[str] = Field(default_factory=list)
    trc_operation_gate_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ResourceBalanceWitness(BaseModel):
    """Finite source-debit / target-credit conservation witness."""

    witness_id: str = ""
    flux_id: str = ""
    source_debit: float = 0.0
    target_credit: float = 0.0
    loss_upper_bound: float = 0.0
    conversion_factor: float = 1.0
    conservation_residual: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    trc_resource_flow_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class BufferComponent(BaseModel):
    """Typed stabilization-buffer component."""

    component_id: str = ""
    kind: str = ""
    amount: float = 0.0
    resource_type: str = ""
    unit: str = "dimensionless"
    unit_family: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ShockEnvelope(BaseModel):
    """Finite shock envelope for buffer sizing."""

    envelope_id: str = ""
    resource_type: str = ""
    unit: str = "dimensionless"
    unit_family: str | None = None
    shock_upper_bound: float = 0.0
    panic_load: float = 0.0
    queue_load: float = 0.0
    legal_hold_load: float = 0.0
    spoilage_upper_bound: float = 0.0
    residual_charge: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)


class StabilizationBuffer(BaseModel):
    """Typed stabilization buffer with compatible components and shock load."""

    buffer_id: str = ""
    cell_id: str = ""
    resource_type: str = ""
    unit: str = "dimensionless"
    unit_family: str | None = None
    components: list[BufferComponent] = Field(default_factory=list)
    shock_envelope: ShockEnvelope | None = None
    horizon: str = "finite"
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    available_buffer: float = 0.0
    required_buffer: float = 0.0
    coverage_ratio: float | None = None
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class BoundedFrictionHandover(BaseModel):
    """Bounded-friction handover witness; never frictionless execution authority."""

    handover_id: str = ""
    from_controller: str = ""
    to_controller: str = ""
    mode: str = "diagnostic-only"
    dual_run: bool = False
    shadow_mode: bool = False
    rollback_available: bool = False
    override_live: bool = False
    authority_valid: bool = False
    telemetry_fresh: bool = False
    explanation_channel_available: bool = False
    covert_transition: bool = False
    irreversible_transition: bool = False
    skill_debt_upper_bound: float = 0.0
    skill_debt_budget: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class SatisfactionEffectWitness(BaseModel):
    """Predicted or observed satisfaction effect witness."""

    witness_id: str = ""
    flux_id: str = ""
    target_cell_id: str = ""
    resource_type: str = ""
    predicted_delta: float = 0.0
    observed_delta: float | None = None
    effect_evidence_level: str = "predicted"
    model_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)


class NonMarketLiquidityCertificate(BaseModel):
    """Finite AFST non-market liquidity check result."""

    certificate_id: str = ""
    abundance_id: str = ""
    deficit_id: str = ""
    flux_id: str = ""
    balance_witness_id: str | None = None
    effect_witness_id: str | None = None
    source_floor_preserved: bool = False
    target_deficit_reduced: bool = False
    physical_balance_preserved: bool = False
    authority_valid: bool = False
    consent_valid: bool = False
    refusal_preserved: bool = False
    lifecycle_fresh: bool = False
    price_not_primary: bool = True
    residual_ledger: Ledger = Field(default_factory=Ledger)
    missing_obligations: list[str] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    reasons: list[str] = Field(default_factory=list)


class SatisfactionFluxRecord(BaseModel):
    """Accepted or rejected satisfaction-flux ledger row."""

    record_id: str = ""
    flux_id: str = ""
    certificate_id: str | None = None
    trace_id: str | None = None
    slot: str = "finite"
    resource_type: str = ""
    source_cell_id: str = ""
    target_cell_id: str = ""
    amount: float = 0.0
    effective_amount: float = 0.0
    unit: str = "dimensionless"
    unit_family: str | None = None
    latency: float = 0.0
    loss_upper_bound: float = 0.0
    predicted_satisfaction_pre: dict[str, float] = Field(default_factory=dict)
    predicted_satisfaction_post: dict[str, float] = Field(default_factory=dict)
    observed_satisfaction_post: dict[str, float] = Field(default_factory=dict)
    authority_refs: list[str] = Field(default_factory=list)
    consent_refs: list[str] = Field(default_factory=list)
    refusal_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AFSTFluxStabilizationReport(BaseModel):
    """Top-level AFST diagnostic report."""

    report_id: str = "afst-flux-stabilization"
    schema_version: str = AFST_SCHEMA_VERSION
    ok: bool = True
    profile: str = "development"
    raw_input_audit: RawInputAudit = Field(default_factory=RawInputAudit)
    observation_window_refs: list[str] = Field(default_factory=list)
    trc_report_refs: list[str] = Field(default_factory=list)
    alt_report_refs: list[str] = Field(default_factory=list)
    liquidity_certificates: list[NonMarketLiquidityCertificate] = Field(default_factory=list)
    satisfaction_flux_ledger: list[SatisfactionFluxRecord] = Field(default_factory=list)
    stabilization_buffers: list[StabilizationBuffer] = Field(default_factory=list)
    handover_protocols: list[BoundedFrictionHandover] = Field(default_factory=list)
    accepted: bool = False
    finite_checks_passed: bool = False
    diagnostic_usable: bool = False
    operationally_usable: bool = False
    flux_admissible: bool = False
    operation_ready: bool = False
    provider_dispatch_ready: bool = False
    physical_dispatch_ready: bool = False
    settled: bool = False
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    blockers: list[str] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)
    residuals: list[dict[str, Any]] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    next_safe_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=lambda: list(AFST_NON_CLAIMS))
    reasons: list[str] = Field(default_factory=list)


def afst_profile_policy(profile: str) -> AFSTProfilePolicy:
    """Return deterministic AFST policy settings for a profile name."""

    normalized = profile.lower()
    if normalized in {"production", "adversarial"}:
        return AFSTProfilePolicy(
            profile=normalized,
            require_consent_channel=True,
            require_refusal_channel=True,
            allow_speculative_effect_prediction=False,
            operationally_usable_requires_observed_effect=True,
        )
    if normalized in {"research", "controlled", "federated"}:
        return AFSTProfilePolicy(
            profile=normalized,
            require_consent_channel=True,
            require_refusal_channel=True,
        )
    return AFSTProfilePolicy(profile="development")


__all__ = [
    "ACCEPTED_AUTHORITY_STATUSES",
    "ACTIVE_REFUSAL_KINDS",
    "AFST_NON_CLAIMS",
    "AFST_SCHEMA_VERSION",
    "AFSTFluxStabilizationReport",
    "AFSTProfilePolicy",
    "AuthorityEnvelope",
    "BoundedFrictionHandover",
    "BufferComponent",
    "CandidateFlux",
    "CertifiedAbundanceCoordinate",
    "ConsentChannel",
    "NonMarketLiquidityCertificate",
    "RawInputAudit",
    "RefusalChannel",
    "ResourceBalanceWitness",
    "SatisfactionCoordinate",
    "SatisfactionDeficit",
    "SatisfactionEffectWitness",
    "SatisfactionFluxRecord",
    "ShockEnvelope",
    "StabilizationBuffer",
    "UnitFrame",
    "afst_profile_policy",
]
