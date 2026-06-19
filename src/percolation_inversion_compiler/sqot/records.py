"""SQOT record types for finite salience-queue occupation checks."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus


class SalienceDecision(StrEnum):
    RUN = "run"
    DEFER = "defer"
    QUARANTINE = "quarantine"
    ROLLBACK = "rollback"
    ABSTAIN = "abstain"


class SQOTTheorySnapshot(BaseModel):
    """Portable SQOT source identity and derived coverage metadata."""

    snapshot_id: str = "sqot-zenodo-derived-snapshot"
    source_title: str = "Salience-Queue Occupation Theory"
    source_kind: str = "zenodo-canonical-manuscript"
    source_sha256: str
    definitions: int
    claims: int
    items: int
    unsupported: int = 0


class SalienceQueueRecord(BaseModel):
    """One finite packet, obligation, or verifier task occupying attention budget."""

    record_id: str
    item_type: str = "packet"
    salience_class: str = "default"
    expected_downstream_gain: float = 0.0
    residual_reduction: float = 0.0
    verification_cost: float = 0.0
    freshness: float = 1.0
    hazard_charge: float = 0.0
    authority_required: bool = False
    authority_granted: bool = True
    stale: bool = False
    evidence_hash_valid: bool = True
    route_safe: bool = True
    rollback_available: bool = False
    effective_reserve_eligible: bool = True
    audit_recursion_depth: int = 0
    latency_cost: float = 0.0
    deadline_loss: float = 0.0
    rollback_class: str = "none"
    aggregation_group: str | None = None
    source_label: str | None = None
    underlying_signal_ref: str | None = None
    label_laundering_suspected: bool = False
    protocol_integrity_ref: str | None = None
    privacy_rejoin_ref: str | None = None
    sovereignty_kernel_ref: str | None = None
    distributed_origin_ref: str | None = None
    adversarial_transfer_risk: float = 0.0
    thermodynamic_discharge_cost: float = 0.0
    obligation_ids: list[str] = Field(default_factory=list)
    verifier_routes: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)


class OccupationLedger(BaseModel):
    """Finite attention occupation by queue class."""

    attention_budget: float
    occupied: float = 0.0
    occupied_by_class: dict[str, float] = Field(default_factory=dict)
    unknown_occupation: list[str] = Field(default_factory=list)


class DiagnosticReservePolicy(BaseModel):
    """Reserve rule for diagnostic work and audit recursion."""

    minimum_reserve: float = 0.0
    reserve_fraction: float = 0.1
    audit_depth: int = 1

    def required_reserve(self, budget: float) -> float:
        return max(self.minimum_reserve, budget * self.reserve_fraction)


class QuarantineLedger(BaseModel):
    """Fail-closed quarantine and rollback ledger."""

    quarantined_items: list[str] = Field(default_factory=list)
    rollback_items: list[str] = Field(default_factory=list)
    reasons: dict[str, list[str]] = Field(default_factory=dict)


class RiskBudgetLedger(BaseModel):
    """Finite SQOT risk budget ledger."""

    risk_budget: float = 0.0
    risk_charges: dict[str, float] = Field(default_factory=dict)

    def total_charge(self) -> float:
        return sum(max(0.0, charge) for charge in self.risk_charges.values())


class SalienceSchedulingDecision(BaseModel):
    """One scheduler decision with explicit residual accounting."""

    record_id: str
    decision: SalienceDecision
    priority_score: float
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    status: ClaimStatus = ClaimStatus.DIAGNOSTIC
    operationally_usable: bool = False
    settled: bool = False


class SalienceScheduleReport(BaseModel):
    """Deterministic SQOT scheduling output for agent runners."""

    report_id: str
    profile: str = "development"
    accepted: bool = False
    decisions: list[SalienceSchedulingDecision] = Field(default_factory=list)
    occupation_ledger: OccupationLedger
    diagnostic_reserve: DiagnosticReservePolicy = Field(default_factory=DiagnosticReservePolicy)
    quarantine_ledger: QuarantineLedger = Field(default_factory=QuarantineLedger)
    risk_ledger: RiskBudgetLedger = Field(default_factory=RiskBudgetLedger)
    low_contribution_occupation: float = 0.0
    unresolved_obligation_backlog: int = 0
    verifier_latency_proxy: float = 0.0
    effective_diagnostic_reserve: float = 0.0
    audit_recursion_violations: list[str] = Field(default_factory=list)
    latency_deadline_loss: float = 0.0
    rollback_class_summary: dict[str, int] = Field(default_factory=dict)
    aggregation_group_counts: dict[str, int] = Field(default_factory=dict)
    aggregation_group_occupation: dict[str, float] = Field(default_factory=dict)
    label_laundering_suspicions: list[str] = Field(default_factory=list)
    protocol_integrity_refs: list[str] = Field(default_factory=list)
    privacy_rejoin_refs: list[str] = Field(default_factory=list)
    sovereignty_kernel_refs: list[str] = Field(default_factory=list)
    distributed_origin_count: int = 0
    adversarial_transfer_charge: float = 0.0
    thermodynamic_discharge_charge: float = 0.0
    stale_packet_ratio: float = 0.0
    false_liquidity_rate: float = 0.0
    residual_debt_growth: float = 0.0
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "queue priority never promotes obligations to settled status",
            "stale, hash-invalid, authority-invalid, or unsafe-route items fail closed",
            "diagnostic reserve is preserved before non-diagnostic work is scheduled",
        ]
    )
