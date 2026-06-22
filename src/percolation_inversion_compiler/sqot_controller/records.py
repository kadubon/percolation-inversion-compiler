"""SQOT queue sovereignty diagnostics for effective packet graphs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AttentionBudgetLedger(BaseModel):
    ledger_id: str = "sqot-attention-budget"
    attention_budget: float = 1.0
    occupied: float = 0.0
    diagnostic_reserve_required: float = 0.1
    diagnostic_reserve_available: float = 0.0
    reserve_preserved: bool = False
    settled: bool = False


class VerificationQueuePressure(BaseModel):
    pressure_id: str = "sqot-verification-pressure"
    backlog_count: int = 0
    stale_packet_count: int = 0
    unsafe_packet_count: int = 0
    candidate_only_count: int = 0
    pressure: float = 0.0
    settled: bool = False


class QueueOccupationReport(BaseModel):
    report_id: str = "sqot-queue-occupation"
    graph_id: str = ""
    attention_budget_ledger: AttentionBudgetLedger = Field(default_factory=AttentionBudgetLedger)
    verification_queue_pressure: VerificationQueuePressure = Field(
        default_factory=VerificationQueuePressure
    )
    low_value_packet_ids: list[str] = Field(default_factory=list)
    repeated_candidate_only_packets: list[str] = Field(default_factory=list)
    blocked_high_value_packets: list[str] = Field(default_factory=list)
    rollback_unavailable_decisions: list[str] = Field(default_factory=list)
    accepted: bool = False
    workflow_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class SalienceObstructionDiagnosis(BaseModel):
    diagnosis_id: str = "sqot-salience-obstruction"
    graph_id: str = ""
    obstructed_packet_ids: list[str] = Field(default_factory=list)
    obstruction_reasons: dict[str, list[str]] = Field(default_factory=dict)
    obstruction_load: float = 0.0
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class DiagnosticReserveReport(BaseModel):
    report_id: str = "sqot-diagnostic-reserve"
    graph_id: str = ""
    attention_budget_ledger: AttentionBudgetLedger
    reserve_deficit: float = 0.0
    accepted: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class PacketQuarantineDecision(BaseModel):
    decision_id: str
    packet_id: str
    decision: str = "quarantine"
    reasons: list[str] = Field(default_factory=list)
    reversible: bool = True
    applied: bool = False
    deletes_packet: bool = False
    settled: bool = False


class QueueRebalancePlan(BaseModel):
    plan_id: str = "sqot-queue-rebalance"
    graph_id: str = ""
    recommended_actions: dict[str, str] = Field(default_factory=dict)
    quarantine_decisions: list[PacketQuarantineDecision] = Field(default_factory=list)
    executes_actions: bool = False
    deletes_packets: bool = False
    accepted: bool = False
    workflow_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class ReversibleSalienceSovereigntyCertificate(BaseModel):
    certificate_id: str = "sqot-reversible-salience-sovereignty"
    graph_id: str = ""
    rebalance_plan_id: str = ""
    reversible: bool = True
    rollback_available: bool = False
    grants_execution_authority: bool = False
    certificate_status: str = "abstain"
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
