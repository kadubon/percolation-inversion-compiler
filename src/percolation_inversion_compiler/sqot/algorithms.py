"""Finite SQOT salience-queue algorithms."""

from __future__ import annotations

from collections.abc import Sequence

from percolation_inversion_compiler.core.ledger import CoordinateKind
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.sqot.records import (
    DiagnosticReservePolicy,
    OccupationLedger,
    QuarantineLedger,
    RiskBudgetLedger,
    SalienceDecision,
    SalienceQueueRecord,
    SalienceScheduleReport,
    SalienceSchedulingDecision,
)


def salience_priority(record: SalienceQueueRecord) -> float:
    """Compute a finite salience priority with explicit cost and hazard charges."""

    positive = max(0.0, record.expected_downstream_gain) + max(0.0, record.residual_reduction)
    negative = (
        max(0.0, record.verification_cost)
        + max(0.0, record.hazard_charge)
        + max(0.0, record.latency_cost)
        + max(0.0, record.deadline_loss)
        + max(0.0, record.adversarial_transfer_risk)
        + max(0.0, record.thermodynamic_discharge_cost)
        + record.residual_ledger.burden_sum()
    )
    freshness = min(1.0, max(0.0, record.freshness))
    return (positive * freshness) - negative


def check_salience_record(record: SalienceQueueRecord) -> CheckResult:
    """Check one SQOT queue record without promoting queued work to settled."""

    reasons: list[str] = []
    if record.verification_cost < 0:
        reasons.append("verification cost is negative")
    if record.expected_downstream_gain < 0:
        reasons.append("expected downstream gain is negative")
    if record.residual_reduction < 0:
        reasons.append("residual reduction is negative")
    if record.hazard_charge < 0:
        reasons.append("hazard charge is negative")
    if record.latency_cost < 0:
        reasons.append("latency cost is negative")
    if record.deadline_loss < 0:
        reasons.append("deadline loss is negative")
    if record.adversarial_transfer_risk < 0:
        reasons.append("adversarial transfer risk is negative")
    if record.thermodynamic_discharge_cost < 0:
        reasons.append("thermodynamic discharge cost is negative")
    if record.audit_recursion_depth < 0:
        reasons.append("audit recursion depth is negative")
    if record.stale:
        reasons.append("queue record is stale")
    if not record.evidence_hash_valid:
        reasons.append("queue record evidence hash is invalid")
    if not record.route_safe:
        reasons.append("queue record route is unsafe")
    if record.authority_required and not record.authority_granted:
        reasons.append("queue record authority is not granted")
    if record.item_type == "rollback" and not record.rollback_available:
        reasons.append("rollback task lacks rollback certificate")
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.PROVISIONAL if not reasons else ClaimStatus.DIAGNOSTIC,
        finite_checks_passed=not reasons,
        operationally_usable=False,
        settled=False,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(record.obligation_ids if reasons else []),
        residual_ledger=record.residual_ledger,
    )


def _decision_for_record(
    record: SalienceQueueRecord,
    *,
    remaining_attention: float,
    reserve_remaining: float,
    risk_remaining: float,
    audit_depth_limit: int,
) -> SalienceSchedulingDecision:
    check = check_salience_record(record)
    score = salience_priority(record)
    reasons = list(check.reasons)
    decision = SalienceDecision.RUN
    if not check.accepted:
        decision = (
            SalienceDecision.ROLLBACK if record.rollback_available else SalienceDecision.QUARANTINE
        )
    elif record.audit_recursion_depth > audit_depth_limit:
        decision = SalienceDecision.DEFER
        reasons.append("audit recursion budget would be exceeded")
    elif score <= 0.0:
        decision = SalienceDecision.DEFER
        reasons.append("priority score is not positive")
    elif record.verification_cost > remaining_attention:
        decision = SalienceDecision.ABSTAIN
        reasons.append("insufficient attention budget")
    elif record.item_type != "diagnostic" and reserve_remaining < 0:
        decision = SalienceDecision.DEFER
        reasons.append("diagnostic reserve would be violated")
    elif record.hazard_charge > risk_remaining:
        decision = SalienceDecision.DEFER
        reasons.append("risk budget would be exceeded")
    residual = check.residual_ledger
    if decision != SalienceDecision.RUN:
        residual = residual.add_coordinate(
            f"sqot:{record.record_id}:{decision.value}",
            abs(score) + max(0.0, record.verification_cost),
            kind=CoordinateKind.RESIDUAL,
        )
    return SalienceSchedulingDecision(
        record_id=record.record_id,
        decision=decision,
        priority_score=score,
        reasons=sorted(set(reasons)),
        residual_ledger=residual,
        status=(
            ClaimStatus.PROVISIONAL if decision == SalienceDecision.RUN else ClaimStatus.DIAGNOSTIC
        ),
        operationally_usable=decision == SalienceDecision.RUN,
        settled=False,
    )


def build_salience_schedule(
    records: Sequence[SalienceQueueRecord],
    *,
    attention_budget: float,
    diagnostic_reserve: DiagnosticReservePolicy | None = None,
    risk_budget: float = 0.0,
    profile: str = "development",
) -> SalienceScheduleReport:
    """Build a deterministic SQOT schedule for packet, obligation, and verifier queues."""

    reserve = diagnostic_reserve or DiagnosticReservePolicy()
    sorted_records = sorted(records, key=lambda item: (-salience_priority(item), item.record_id))
    occupied_by_class: dict[str, float] = {}
    risk_charges: dict[str, float] = {}
    decisions: list[SalienceSchedulingDecision] = []
    quarantined: list[str] = []
    rollback: list[str] = []
    quarantine_reasons: dict[str, list[str]] = {}
    remaining_attention = max(0.0, attention_budget)
    diagnostic_spent = 0.0
    effective_diagnostic_spent = 0.0
    risk_remaining = max(0.0, risk_budget)
    required_reserve = reserve.required_reserve(max(0.0, attention_budget))
    audit_recursion_violations: list[str] = []
    rollback_class_summary: dict[str, int] = {}
    aggregation_group_counts: dict[str, int] = {}
    aggregation_group_occupation: dict[str, float] = {}
    aggregation_group_classes: dict[str, set[str]] = {}
    label_suspicions: list[str] = []
    protocol_integrity_refs: list[str] = []
    privacy_rejoin_refs: list[str] = []
    sovereignty_kernel_refs: list[str] = []
    distributed_origin_count = 0
    adversarial_transfer_charge = 0.0
    thermodynamic_discharge_charge = 0.0
    for record in sorted_records:
        reserve_remaining = remaining_attention - required_reserve
        decision = _decision_for_record(
            record,
            remaining_attention=remaining_attention,
            reserve_remaining=reserve_remaining,
            risk_remaining=risk_remaining,
            audit_depth_limit=reserve.audit_depth,
        )
        decisions.append(decision)
        if record.audit_recursion_depth > reserve.audit_depth:
            audit_recursion_violations.append(record.record_id)
        rollback_class_summary[record.rollback_class] = (
            rollback_class_summary.get(record.rollback_class, 0) + 1
        )
        group = record.aggregation_group or record.underlying_signal_ref
        if group:
            aggregation_group_counts[group] = aggregation_group_counts.get(group, 0) + 1
            aggregation_group_occupation[group] = aggregation_group_occupation.get(
                group, 0.0
            ) + max(0.0, record.verification_cost)
            aggregation_group_classes.setdefault(group, set()).add(record.salience_class)
        if record.label_laundering_suspected:
            label_suspicions.append(record.record_id)
        if record.protocol_integrity_ref:
            protocol_integrity_refs.append(record.protocol_integrity_ref)
        if record.privacy_rejoin_ref:
            privacy_rejoin_refs.append(record.privacy_rejoin_ref)
        if record.sovereignty_kernel_ref:
            sovereignty_kernel_refs.append(record.sovereignty_kernel_ref)
        if record.distributed_origin_ref:
            distributed_origin_count += 1
        adversarial_transfer_charge += max(0.0, record.adversarial_transfer_risk)
        thermodynamic_discharge_charge += max(0.0, record.thermodynamic_discharge_cost)
        if decision.decision == SalienceDecision.RUN:
            remaining_attention -= max(0.0, record.verification_cost)
            if record.item_type == "diagnostic":
                diagnostic_spent += max(0.0, record.verification_cost)
                if record.effective_reserve_eligible:
                    effective_diagnostic_spent += max(0.0, record.verification_cost)
            risk_remaining -= max(0.0, record.hazard_charge)
            occupied_by_class[record.salience_class] = occupied_by_class.get(
                record.salience_class, 0.0
            ) + max(0.0, record.verification_cost)
            risk_charges[record.record_id] = max(0.0, record.hazard_charge)
        elif decision.decision == SalienceDecision.QUARANTINE:
            quarantined.append(record.record_id)
            quarantine_reasons[record.record_id] = decision.reasons
        elif decision.decision == SalienceDecision.ROLLBACK:
            rollback.append(record.record_id)
            quarantine_reasons[record.record_id] = decision.reasons
    total_records = len(sorted_records)
    stale_count = sum(1 for record in sorted_records if record.stale)
    unsafe_count = sum(
        1
        for record in sorted_records
        if record.stale or not record.evidence_hash_valid or not record.route_safe
    )
    low_contribution = sum(
        max(0.0, record.verification_cost)
        for record in sorted_records
        if salience_priority(record) <= 0.0
    )
    unresolved = sum(len(record.obligation_ids) for record in sorted_records)
    latency_deadline_loss = sum(
        max(0.0, record.latency_cost) + max(0.0, record.deadline_loss) for record in sorted_records
    )
    for group, classes in aggregation_group_classes.items():
        if len(classes) > 1:
            label_suspicions.append(f"aggregation-group:{group}")
    residual_debt = sum(decision.residual_ledger.burden_sum() for decision in decisions)
    accepted = any(decision.decision == SalienceDecision.RUN for decision in decisions)
    occupied = max(0.0, attention_budget) - remaining_attention
    return SalienceScheduleReport(
        report_id="sqot-salience-schedule",
        profile=profile,
        accepted=accepted,
        decisions=decisions,
        occupation_ledger=OccupationLedger(
            attention_budget=max(0.0, attention_budget),
            occupied=occupied,
            occupied_by_class=dict(sorted(occupied_by_class.items())),
        ),
        diagnostic_reserve=reserve,
        quarantine_ledger=QuarantineLedger(
            quarantined_items=sorted(quarantined),
            rollback_items=sorted(rollback),
            reasons=dict(sorted(quarantine_reasons.items())),
        ),
        risk_ledger=RiskBudgetLedger(risk_budget=max(0.0, risk_budget), risk_charges=risk_charges),
        low_contribution_occupation=low_contribution,
        unresolved_obligation_backlog=unresolved,
        verifier_latency_proxy=occupied / max(1, len(decisions)),
        effective_diagnostic_reserve=effective_diagnostic_spent,
        audit_recursion_violations=sorted(set(audit_recursion_violations)),
        latency_deadline_loss=latency_deadline_loss,
        rollback_class_summary=dict(sorted(rollback_class_summary.items())),
        aggregation_group_counts=dict(sorted(aggregation_group_counts.items())),
        aggregation_group_occupation=dict(sorted(aggregation_group_occupation.items())),
        label_laundering_suspicions=sorted(set(label_suspicions)),
        protocol_integrity_refs=sorted(set(protocol_integrity_refs)),
        privacy_rejoin_refs=sorted(set(privacy_rejoin_refs)),
        sovereignty_kernel_refs=sorted(set(sovereignty_kernel_refs)),
        distributed_origin_count=distributed_origin_count,
        adversarial_transfer_charge=adversarial_transfer_charge,
        thermodynamic_discharge_charge=thermodynamic_discharge_charge,
        stale_packet_ratio=0.0 if total_records == 0 else stale_count / total_records,
        false_liquidity_rate=0.0 if total_records == 0 else unsafe_count / total_records,
        residual_debt_growth=residual_debt,
    )


def reserve_is_adequate(report: SalienceScheduleReport) -> bool:
    """Return true when the realized schedule preserved the diagnostic reserve."""

    reserve_required = report.diagnostic_reserve.required_reserve(
        report.occupation_ledger.attention_budget
    )
    free_attention = report.occupation_ledger.attention_budget - report.occupation_ledger.occupied
    return free_attention + report.effective_diagnostic_reserve >= reserve_required
