"""Finite ALT checkers and runtime bridge helpers."""

from __future__ import annotations

from collections.abc import Mapping

from percolation_inversion_compiler.alt.records import (
    AbstractionToken,
    ALTAccelerationCertificate,
    ALTAdmissionAction,
    ALTAdmissionDecision,
    ALTCARACertificate,
    ALTDeprecationRecord,
    ALTKernelTransitionReport,
    ALTResurrectionRecord,
    BaselineRefreshCertificate,
    CertifiedAbstractionCapital,
    ExecutableALTCertificatePacket,
    FormationCostLedger,
    FoundryBottleneck,
    FoundryControlDashboard,
    FoundryState,
    HazardEnvelopeCertificate,
    LiquidityCertificate,
    NegativeLiquidityCertificate,
    OpportunityMeasureContract,
    ProblemSolvingTrace,
    ReproductionMatrixCertificate,
    RootFinalityCertificate,
    TelemetryCostCertificate,
    TokenLineage,
    TransportCertificate,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology import (
    CapabilityPacketCandidate,
    GeneralIntakeRuntimeBridgeReport,
    PacketSourceKind,
    sha256_text,
)
from percolation_inversion_compiler.runtime import RuntimeState


def _string_list(value: object) -> list[str]:
    """Normalize loose JSON context values into a deterministic string list."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value]
    return [str(value)]


def _context_float(values: Mapping[str, object], key: str) -> float:
    """Read a float from a portable JSON mapping."""

    value = values.get(key, 0.0)
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def build_abstraction_token_from_trace(
    trace: ProblemSolvingTrace,
    context: dict[str, object] | None = None,
) -> AbstractionToken:
    """Build a deterministic ALT token candidate from a finite trace."""

    active_context = context or {}
    token_id = str(active_context.get("token_id") or f"alt-token:{trace.trace_id}")
    receiver_family = _string_list(active_context.get("receiver_family"))
    if not receiver_family:
        receiver_family = trace.receiver_family or ["agent", "verifier"]
    digest_seed = "|".join(
        [
            trace.trace_id,
            trace.task_id,
            ",".join(trace.observation_refs),
            ",".join(trace.action_refs),
            ",".join(trace.result_refs),
        ]
    )
    lineage = TokenLineage(
        lineage_id=f"lineage:{token_id}",
        token_id=token_id,
        source_trace_ids=[trace.trace_id],
        content_sha256=sha256_text(digest_seed),
        provenance_refs=trace.provenance_refs,
        accepted=trace.accepted,
        reasons=trace.reasons,
    )
    return AbstractionToken(
        token_id=token_id,
        claim=str(active_context.get("claim") or f"Reusable abstraction from {trace.task_id}"),
        receiver_family=receiver_family,
        validity_domain=str(active_context.get("validity_domain", "protocol-relative-finite")),
        dependency_ids=_string_list(active_context.get("dependency_ids")),
        interface_refs=_string_list(active_context.get("interface_refs")),
        evidence_refs=sorted(
            set(
                trace.observation_refs
                + trace.action_refs
                + trace.result_refs
                + trace.provenance_refs
            )
        ),
        authority_refs=_string_list(active_context.get("authority_refs")),
        capability_envelope_refs=_string_list(active_context.get("capability_envelope_refs")),
        verifier_routes=_string_list(active_context.get("verifier_routes")),
        lineage=lineage,
        candidate_only=True,
        status=ClaimStatus.PROVISIONAL,
    )


def build_abstraction_token_from_packet(
    packet: CapabilityPacketCandidate,
    context: dict[str, object] | None = None,
) -> AbstractionToken:
    """Convert an ECPT/general-intake packet candidate into an ALT token candidate."""

    active_context = context or {}
    token_id = str(active_context.get("token_id") or f"alt-token:{packet.packet_id}")
    source_trace_id = str(active_context.get("trace_id") or f"packet-trace:{packet.packet_id}")
    lineage = TokenLineage(
        lineage_id=f"lineage:{token_id}",
        token_id=token_id,
        source_trace_ids=[source_trace_id],
        source_packet_ids=[packet.packet_id],
        content_sha256=packet.content_sha256,
        provenance_refs=packet.evidence_refs,
        accepted=False,
        reasons=["packet-derived ALT token remains candidate-only until certified"],
    )
    residual = packet.residual_charge
    ledger = Ledger()
    if residual:
        ledger = ledger.add_coordinate(
            f"alt-token:{token_id}:packet-residual",
            residual,
            kind=CoordinateKind.RESIDUAL,
        )
    if "external-candidate" in set(packet.tags) or packet.source_kind not in {
        PacketSourceKind.LOCAL,
        PacketSourceKind.AGENT_OUTPUT,
    }:
        ledger = ledger.add_coordinate(
            f"alt-token:{token_id}:external-candidate",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description="external packet remains candidate-only before ALT certification",
        )
    return AbstractionToken(
        token_id=token_id,
        claim=packet.claim,
        receiver_family=packet.receiver_family,
        validity_domain="protocol-relative-finite",
        dependency_ids=packet.dependencies,
        interface_refs=sorted(set(packet.tags)),
        evidence_refs=packet.evidence_refs,
        verifier_routes=packet.verifier_routes,
        lineage=lineage,
        candidate_only=True,
        residual_ledger=ledger,
        status=ClaimStatus.PROVISIONAL,
    )


def check_token_admissibility(
    token: AbstractionToken,
    context: dict[str, object] | None = None,
) -> CheckResult:
    """Check finite token admissibility without promoting external claims."""

    active_context = context or {}
    reasons: list[str] = []
    missing: list[str] = []
    residual = token.residual_ledger
    if not token.claim.strip():
        reasons.append("token claim is empty")
    if not token.receiver_family:
        reasons.append("receiver_family is required")
        missing.append("receiver-family")
    if not token.evidence_refs:
        reasons.append("evidence_refs are required")
        missing.append("evidence-refs")
    if not token.interface_refs:
        reasons.append("interface_refs are required")
        missing.append("interface-refs")
    if active_context.get("require_authority", True) and not token.authority_refs:
        reasons.append("authority_refs are required by context")
        missing.append("authority-refs")
    if active_context.get("require_capability_envelope", True) and not (
        token.capability_envelope_refs
    ):
        reasons.append("capability_envelope_refs are required by context")
        missing.append("capability-envelope-refs")
    if not token.verifier_routes:
        reasons.append("verifier_routes are required for token capital formation")
        missing.append("verifier-routes")
    for item in missing:
        residual = residual.add_coordinate(
            f"alt-token:{token.token_id}:missing-{item}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    accepted = not reasons
    return CheckResult(
        accepted=accepted,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        finite_checks_passed=accepted,
        operationally_usable=False,
        settled=False,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(set(missing)),
        residual_ledger=residual,
    )


def certified_surplus_lower_bound(certificate: LiquidityCertificate) -> float:
    """Return ALT lower-bound surplus after all declared costs and charges."""

    return (
        certificate.downstream_search_cost_reduction_lower_bound
        - certificate.cost_ledger.total_cost()
        - certificate.residual_ledger.burden_sum()
        - float(len(certificate.residual_external_obligations))
    )


def check_transport_certificate(certificate: TransportCertificate) -> TransportCertificate:
    """Check finite support and density-ratio transport conditions."""

    reasons = list(certificate.reasons)
    residual = certificate.residual_ledger
    if not certificate.source_receiver_family:
        reasons.append("source_receiver_family is required")
    if not certificate.target_receiver_family:
        reasons.append("target_receiver_family is required")
    if certificate.support_coverage_lower_bound <= 0.0:
        reasons.append("support coverage lower bound must be positive")
    if certificate.density_ratio_upper_bound > certificate.max_density_ratio:
        reasons.append("density ratio exceeds declared maximum")
    if not certificate.evidence_refs:
        reasons.append("transport evidence_refs are required")
    for index, reason in enumerate(reasons):
        residual = residual.add_coordinate(
            f"alt-transport:{certificate.certificate_id}:{index}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description=reason,
        )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "reasons": sorted(set(reasons)),
            "residual_ledger": residual,
        }
    )


def _add_reason_residual(
    residual: Ledger,
    prefix: str,
    reasons: list[str],
) -> Ledger:
    """Charge one residual coordinate for each finite checker reason."""

    active = residual
    for index, reason in enumerate(reasons):
        active = active.add_coordinate(
            f"{prefix}:{index}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description=reason,
        )
    return active


def check_opportunity_measure_contract(
    contract: OpportunityMeasureContract,
) -> OpportunityMeasureContract:
    """Check that a valuation uses a declared finite opportunity measure."""

    reasons = list(contract.reasons)
    if not contract.receiver_family:
        reasons.append("opportunity receiver_family is required")
    if not contract.task_portfolio_refs:
        reasons.append("task_portfolio_refs are required")
    if contract.baseline_ref is None:
        reasons.append("baseline_ref is required")
    if not contract.evidence_refs:
        reasons.append("opportunity evidence_refs are required")
    residual = _add_reason_residual(
        contract.residual_ledger,
        f"alt-opportunity:{contract.contract_id}",
        reasons,
    )
    accepted = not reasons
    return contract.model_copy(
        update={
            "accepted": accepted,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_root_finality_certificate(
    certificate: RootFinalityCertificate,
) -> RootFinalityCertificate:
    """Check role-separated root and finality evidence."""

    reasons = list(certificate.reasons)
    if not certificate.root_role_refs:
        reasons.append("root_role_refs are required")
    if len(certificate.root_role_refs) != len(set(certificate.root_role_refs)):
        reasons.append("root roles must be distinct")
    if not certificate.evaluator_quorum_refs:
        reasons.append("evaluator_quorum_refs are required")
    if certificate.finality_record_ref is None:
        reasons.append("finality_record_ref is required")
    if certificate.partition_alarm:
        reasons.append("finality partition alarm is active")
    if certificate.byzantine_budget_upper_bound > 1.0:
        reasons.append("byzantine budget exceeds accepted bound")
    if certificate.correlated_capture_budget_upper_bound > 1.0:
        reasons.append("correlated capture budget exceeds accepted bound")
    if not certificate.evidence_refs:
        reasons.append("root/finality evidence_refs are required")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-root-finality:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_telemetry_cost_certificate(
    certificate: TelemetryCostCertificate,
) -> TelemetryCostCertificate:
    """Check telemetry accounting and observer-cost bounds."""

    reasons = list(certificate.reasons)
    if not certificate.observer_refs:
        reasons.append("telemetry observer_refs are required")
    if certificate.measured_cost_upper_bound < 0.0:
        reasons.append("measured cost upper bound is negative")
    if certificate.observer_cost_upper_bound < 0.0:
        reasons.append("observer cost upper bound is negative")
    if certificate.tamper_positive:
        reasons.append("telemetry observer is tamper-positive")
    if not certificate.evidence_refs:
        reasons.append("telemetry evidence_refs are required")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-telemetry:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_hazard_envelope_certificate(
    certificate: HazardEnvelopeCertificate,
) -> HazardEnvelopeCertificate:
    """Check hazard, authority, capability, and rollback envelopes."""

    reasons = list(certificate.reasons)
    if not certificate.hazard_refs:
        reasons.append("hazard_refs are required")
    if not certificate.authority_envelope_refs:
        reasons.append("authority_envelope_refs are required")
    if not certificate.capability_envelope_refs:
        reasons.append("capability_envelope_refs are required")
    if not certificate.rollback_refs:
        reasons.append("rollback_refs are required")
    if certificate.noncompensable_hazard_detected:
        reasons.append("noncompensable hazard detected")
    if certificate.irreversible_risk_upper_bound > certificate.risk_budget_upper_bound:
        reasons.append("irreversible risk exceeds declared risk budget")
    if not certificate.evidence_refs:
        reasons.append("hazard evidence_refs are required")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-hazard:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_baseline_refresh_certificate(
    certificate: BaselineRefreshCertificate,
) -> BaselineRefreshCertificate:
    """Check a baseline/opportunity-law refresh bridge."""

    reasons = list(certificate.reasons)
    if not certificate.old_baseline_ref:
        reasons.append("old_baseline_ref is required")
    if not certificate.new_baseline_ref:
        reasons.append("new_baseline_ref is required")
    if certificate.old_baseline_ref == certificate.new_baseline_ref:
        reasons.append("baseline refresh must change the baseline reference")
    if not certificate.resource_matched:
        reasons.append("baseline refresh is not resource-matched")
    if not certificate.refresh_bridge_refs:
        reasons.append("refresh_bridge_refs are required")
    if not certificate.evidence_refs:
        reasons.append("baseline refresh evidence_refs are required")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-baseline-refresh:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_liquidity_certificate(certificate: LiquidityCertificate) -> LiquidityCertificate:
    """Check ALT liquidity as a certified lower-bound surplus certificate."""

    reasons = list(certificate.reasons)
    residual = certificate.residual_ledger
    transport = (
        check_transport_certificate(certificate.transport_certificate)
        if certificate.transport_certificate is not None
        else None
    )
    if transport is None:
        reasons.append("transport certificate is required")
    elif not transport.accepted:
        reasons.append("transport certificate is not accepted")
        residual = residual.combine(transport.residual_ledger)
    if certificate.mission_validity_certificate is None:
        reasons.append("mission validity certificate is required")
    elif not certificate.mission_validity_certificate.accepted:
        reasons.append("mission validity certificate is not accepted")
    if certificate.opportunity_contract is None:
        reasons.append("opportunity measure contract is required")
    else:
        opportunity = check_opportunity_measure_contract(certificate.opportunity_contract)
        if not opportunity.accepted:
            reasons.append("opportunity measure contract is not accepted")
            residual = residual.combine(opportunity.residual_ledger)
    if certificate.lifecycle_bounds is None:
        reasons.append("lifecycle bounds are required")
    elif not certificate.lifecycle_bounds.accepted:
        reasons.append("lifecycle bounds are not accepted")
    if certificate.root_finality_certificate is None:
        reasons.append("root/finality certificate is required")
    else:
        root_finality = check_root_finality_certificate(certificate.root_finality_certificate)
        if not root_finality.accepted:
            reasons.append("root/finality certificate is not accepted")
            residual = residual.combine(root_finality.residual_ledger)
    if certificate.telemetry_cost_certificate is None:
        reasons.append("telemetry cost certificate is required")
    else:
        telemetry = check_telemetry_cost_certificate(certificate.telemetry_cost_certificate)
        if not telemetry.accepted:
            reasons.append("telemetry cost certificate is not accepted")
            residual = residual.combine(telemetry.residual_ledger)
    if certificate.hazard_envelope_certificate is None:
        reasons.append("hazard envelope certificate is required")
    else:
        hazard = check_hazard_envelope_certificate(certificate.hazard_envelope_certificate)
        if not hazard.accepted:
            reasons.append("hazard envelope certificate is not accepted")
            residual = residual.combine(hazard.residual_ledger)
    if not certificate.root_of_trust_refs:
        reasons.append("root_of_trust_refs are required")
    if not certificate.evaluator_quorum_refs:
        reasons.append("evaluator_quorum_refs are required")
    if not certificate.telemetry_refs:
        reasons.append("telemetry_refs are required")
    if not certificate.robustness_refs:
        reasons.append("robustness_refs are required")
    surplus = certified_surplus_lower_bound(certificate)
    if surplus <= 0.0:
        reasons.append("certified surplus lower bound is not positive")
    for obligation in certificate.residual_external_obligations:
        residual = residual.add_coordinate(
            f"alt-liquidity:{certificate.certificate_id}:external:{obligation}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
        )
    for index, reason in enumerate(reasons):
        residual = residual.add_coordinate(
            f"alt-liquidity:{certificate.certificate_id}:{index}",
            1.0,
            kind=CoordinateKind.RESIDUAL,
            description=reason,
        )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "signed_surplus_lower_bound": surplus,
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted and not certificate.residual_external_obligations,
            "settled": False,
            "status": ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
            "transport_certificate": transport,
        }
    )


def check_negative_liquidity_certificate(
    certificate: NegativeLiquidityCertificate,
) -> NegativeLiquidityCertificate:
    """Check a finite negative-liquidity certificate for scoped pruning."""

    reasons = list(certificate.reasons)
    if not certificate.scope_id:
        reasons.append("negative certificate scope_id is required")
    if certificate.surplus_upper_bound > 0.0:
        reasons.append("surplus upper bound is positive")
    if certificate.lower_cost_bound < 0.0:
        reasons.append("lower_cost_bound is negative")
    if certificate.failure_mode == "unspecified":
        reasons.append("failure_mode must be specific")
    if not certificate.transport_scope_refs:
        reasons.append("transport_scope_refs are required for scoped pruning")
    if not certificate.evidence_refs:
        reasons.append("negative-liquidity evidence_refs are required")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-negative-liquidity:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def deprecate_alt_packet(
    token_id: str,
    certificate: NegativeLiquidityCertificate,
    *,
    rollback_refs: list[str] | None = None,
    lineage_refs: list[str] | None = None,
) -> ALTDeprecationRecord:
    """Create a deprecation record from an accepted negative certificate."""

    checked = check_negative_liquidity_certificate(certificate)
    reasons = list(checked.reasons)
    if not checked.accepted:
        reasons.append("negative liquidity certificate is not accepted")
    if not (rollback_refs or []):
        reasons.append("rollback_refs are required for deprecation")
    accepted = not reasons
    return ALTDeprecationRecord(
        record_id=f"alt-deprecation:{token_id}:{certificate.certificate_id}",
        token_id=token_id,
        negative_certificate_id=certificate.certificate_id,
        scope_id=certificate.scope_id,
        deprecation_reason=certificate.failure_mode,
        rollback_refs=sorted(set(rollback_refs or [])),
        lineage_refs=sorted(set(lineage_refs or [])),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        residual_ledger=checked.residual_ledger,
        reasons=sorted(set(reasons)),
    )


def resurrect_alt_candidate(
    deprecation: ALTDeprecationRecord,
    packet: ExecutableALTCertificatePacket,
    *,
    override_failure_mode: str,
    evidence_refs: list[str] | None = None,
    profile: str = "development",
) -> ALTResurrectionRecord:
    """Resurrect a deprecated token as a candidate after current positive checks."""

    decision = admit_alt_packet(packet, profile=profile)
    reasons: list[str] = []
    residual = decision.residual_ledger.combine(deprecation.residual_ledger)
    if not deprecation.accepted:
        reasons.append("prior deprecation record is not accepted")
    if not override_failure_mode:
        reasons.append("override_failure_mode is required")
    if override_failure_mode != deprecation.deprecation_reason:
        reasons.append("override_failure_mode does not match prior failure mode")
    if not (evidence_refs or []):
        reasons.append("resurrection evidence_refs are required")
    if not decision.accepted:
        reasons.append("current positive ALT packet is not admissible")
    accepted = not reasons
    return ALTResurrectionRecord(
        record_id=f"alt-resurrection:{packet.token.token_id}:{deprecation.record_id}",
        token_id=packet.token.token_id,
        prior_deprecation_id=deprecation.record_id,
        override_failure_mode=override_failure_mode,
        current_positive_packet_id=packet.packet_id,
        evidence_refs=sorted(set(evidence_refs or [])),
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=False,
        settled=False,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def admit_alt_packet(
    packet: ExecutableALTCertificatePacket,
    profile: str = "development",
) -> ALTAdmissionDecision:
    """Admit an executable ALT packet only through finite certificates."""

    reasons = list(packet.reasons)
    missing: list[str] = []
    residual = packet.residual_ledger.combine(packet.token.residual_ledger)
    token_check = check_token_admissibility(
        packet.token,
        {
            "require_authority": profile.lower() in {"production", "adversarial"},
            "require_capability_envelope": profile.lower() in {"production", "adversarial"},
        },
    )
    residual = residual.combine(token_check.residual_ledger)
    if not token_check.accepted:
        reasons.append("token admissibility check failed")
        missing.extend(token_check.missing_obligations)
    negative = (
        check_negative_liquidity_certificate(packet.negative_liquidity_certificate)
        if packet.negative_liquidity_certificate is not None
        else None
    )
    if negative is not None:
        residual = residual.combine(negative.residual_ledger)
        if negative.accepted:
            reasons.append("negative liquidity certificate requires deprecation")
        else:
            reasons.append("negative liquidity certificate is not accepted")
    liquidity = (
        check_liquidity_certificate(packet.liquidity_certificate)
        if packet.liquidity_certificate is not None
        else None
    )
    if liquidity is None:
        reasons.append("liquidity certificate is required")
        missing.append("liquidity-certificate")
    else:
        residual = residual.combine(liquidity.residual_ledger)
        if not liquidity.accepted:
            reasons.append("liquidity certificate is not accepted")
        if liquidity.residual_external_obligations:
            reasons.append("liquidity certificate retains residual external obligations")
    if packet.trace_sufficiency is None:
        reasons.append("trace sufficiency certificate is required")
        missing.append("trace-sufficiency")
    elif not packet.trace_sufficiency.accepted:
        reasons.append("trace sufficiency certificate is not accepted")
    if profile.lower() in {"production", "adversarial"} and not packet.evidence_refs:
        reasons.append("production ALT admission requires packet evidence_refs")
        missing.append("packet-evidence-refs")
    accepted = (
        not reasons
        and liquidity is not None
        and liquidity.operationally_usable
        and liquidity.signed_surplus_lower_bound > 0.0
    )
    action = ALTAdmissionAction.ADMIT if accepted else ALTAdmissionAction.DEFER
    if negative is not None and negative.accepted:
        action = ALTAdmissionAction.DEPRECATE
    if any("hazard" in reason or "surplus" in reason for reason in reasons):
        action = ALTAdmissionAction.REJECT
    capital_ref = (
        f"alt-capital:{packet.token.token_id}:{liquidity.certificate_id}"
        if accepted and liquidity is not None
        else None
    )
    return ALTAdmissionDecision(
        decision_id=f"alt-admission:{packet.packet_id}",
        packet_id=packet.packet_id,
        action=action,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        certified_capital_ref=capital_ref,
        residual_ledger=residual,
        missing_obligations=sorted(set(missing)),
        reasons=sorted(set(reasons)),
    )


def certified_capital_from_packet(
    packet: ExecutableALTCertificatePacket,
) -> CertifiedAbstractionCapital | None:
    """Build certified abstraction capital from an accepted ALT packet."""

    if packet.liquidity_certificate is None:
        return None
    checked = check_liquidity_certificate(packet.liquidity_certificate)
    if not checked.accepted or not checked.operationally_usable:
        return None
    return CertifiedAbstractionCapital(
        capital_id=f"alt-capital:{packet.token.token_id}:{checked.certificate_id}",
        token_id=packet.token.token_id,
        liquidity_certificate_id=checked.certificate_id,
        surplus_lower_bound=checked.signed_surplus_lower_bound,
        receiver_family=packet.token.receiver_family,
        validity_domain=packet.token.validity_domain,
        evidence_refs=sorted(set(packet.evidence_refs + packet.token.evidence_refs)),
        residual_external_obligations=checked.residual_external_obligations,
        residual_ledger=checked.residual_ledger,
        operationally_usable=checked.operationally_usable,
        settled=False,
    )


def compute_foundry_dashboard(state: FoundryState) -> FoundryControlDashboard:
    """Compute a deterministic ALT foundry control dashboard."""

    certified = [capital for capital in state.certified_capital if capital.operationally_usable]
    net_surplus = sum(capital.surplus_lower_bound for capital in certified)
    bottlenecks: list[FoundryBottleneck] = []
    if state.evidence_backlog > max(1, len(state.token_candidates)):
        bottlenecks.append(FoundryBottleneck.EVIDENCE_LIMITED)
    if state.transport_backlog:
        bottlenecks.append(FoundryBottleneck.TRANSPORT_LIMITED)
    if state.risk_backlog:
        bottlenecks.append(FoundryBottleneck.RISK_LIMITED)
    if state.receiver_absorption_capacity <= 0.0 or state.settlement_capacity <= 0.0:
        bottlenecks.append(FoundryBottleneck.CAPACITY_LIMITED)
    if not certified:
        bottlenecks.append(FoundryBottleneck.SUBCRITICAL)
    if certified and len(state.token_candidates) > len(certified):
        bottlenecks.append(FoundryBottleneck.UNSATURATED_SUPERCRITICAL)
    if not bottlenecks:
        bottlenecks.append(FoundryBottleneck.UNSATURATED_SUPERCRITICAL)
    recommended = predict_foundry_phase_control_from_bottlenecks(bottlenecks)
    return FoundryControlDashboard(
        dashboard_id=f"alt-foundry-dashboard:{state.foundry_id}",
        foundry_id=state.foundry_id,
        certified_capital_count=len(certified),
        token_candidate_count=len(state.token_candidates),
        evidence_backlog=state.evidence_backlog,
        transport_backlog=state.transport_backlog,
        risk_backlog=state.risk_backlog,
        receiver_absorption_capacity=state.receiver_absorption_capacity,
        settlement_capacity=state.settlement_capacity,
        net_certified_surplus=net_surplus,
        bottlenecks=sorted(set(bottlenecks), key=lambda item: item.value),
        recommended_rule=recommended,
        residual_ledger=state.residual_ledger,
        accepted=bool(certified) and net_surplus > 0.0,
        settled=False,
        reasons=[] if certified else ["no operational certified abstraction capital"],
    )


def predict_foundry_phase_control(dashboard: FoundryControlDashboard) -> FoundryBottleneck:
    """Return the foundry phase-control rule from a dashboard."""

    return predict_foundry_phase_control_from_bottlenecks(dashboard.bottlenecks)


def recommend_foundry_actions(dashboard: FoundryControlDashboard) -> list[str]:
    """Return portable recommended foundry actions for active bottlenecks."""

    actions: list[str] = []
    active = set(dashboard.bottlenecks)
    if FoundryBottleneck.RISK_LIMITED in active:
        actions.append("suspend-risky-token-admission")
        actions.append("run-hazard-and-rollback-verifiers")
    if FoundryBottleneck.CAPACITY_LIMITED in active:
        actions.append("increase-receiver-absorption-or-settlement-capacity")
    if FoundryBottleneck.TRANSPORT_LIMITED in active:
        actions.append("collect-transport-support-and-density-ratio-evidence")
    if FoundryBottleneck.EVIDENCE_LIMITED in active:
        actions.append("route-candidates-to-trace-mission-telemetry-verifiers")
    if FoundryBottleneck.SUBCRITICAL in active:
        actions.append("form-certified-abstraction-capital-before-phase-claims")
    if FoundryBottleneck.UNSATURATED_SUPERCRITICAL in active:
        actions.append("admit-high-surplus-certified-tokens-within-capacity")
    return actions or ["collect-evidence"]


def predict_foundry_phase_control_from_bottlenecks(
    bottlenecks: list[FoundryBottleneck],
) -> FoundryBottleneck:
    """Return a deterministic primary foundry rule."""

    priority = [
        FoundryBottleneck.RISK_LIMITED,
        FoundryBottleneck.CAPACITY_LIMITED,
        FoundryBottleneck.TRANSPORT_LIMITED,
        FoundryBottleneck.EVIDENCE_LIMITED,
        FoundryBottleneck.SUBCRITICAL,
        FoundryBottleneck.UNSATURATED_SUPERCRITICAL,
    ]
    active = set(bottlenecks)
    for item in priority:
        if item in active:
            return FoundryBottleneck.SUSPEND if item == FoundryBottleneck.RISK_LIMITED else item
    return FoundryBottleneck.COLLECT_EVIDENCE


def compute_alt_reproduction_report(
    certificate: ReproductionMatrixCertificate,
) -> ReproductionMatrixCertificate:
    """Check finite abstraction-reproduction diagnostics."""

    reasons = list(certificate.reasons)
    if not certificate.matrix_refs:
        reasons.append("matrix_refs are required")
    if certificate.spectral_radius_lower_bound < 0.0:
        reasons.append("spectral radius lower bound is negative")
    if certificate.spectral_radius_upper_bound < certificate.spectral_radius_lower_bound:
        reasons.append("spectral radius upper bound is below lower bound")
    if not certificate.capacity_feasible:
        reasons.append("reproduction matrix is not capacity-feasible")
    if not certificate.gauge_compatible:
        reasons.append("reproduction matrix is not gauge-compatible")
    if not certificate.causal_identification_refs:
        reasons.append("causal_identification_refs are required")
    if not certificate.transport_validity_refs:
        reasons.append("transport_validity_refs are required")
    for obligation in certificate.residual_external_obligations:
        reasons.append(f"external reproduction obligation remains: {obligation}")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-reproduction:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_alt_acceleration_certificate(
    certificate: ALTAccelerationCertificate,
) -> ALTAccelerationCertificate:
    """Check finite resource-matched ALT acceleration evidence."""

    reasons = list(certificate.reasons)
    if certificate.certified_surplus_gain_lower_bound <= 0.0:
        reasons.append("certified surplus gain lower bound is not positive")
    if not certificate.resource_matched:
        reasons.append("candidate and baseline are not resource-matched")
    for obligation in certificate.residual_external_obligations:
        reasons.append(f"external acceleration obligation remains: {obligation}")
    residual = _add_reason_residual(
        certificate.residual_ledger,
        f"alt-acceleration:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_alt_cara_certificate(certificate: ALTCARACertificate) -> ALTCARACertificate:
    """Check target-valid, resource-matched ALT-CARA finite acceleration."""

    acceleration = check_alt_acceleration_certificate(certificate.acceleration_certificate)
    reasons = list(certificate.reasons)
    residual = certificate.residual_ledger.combine(acceleration.residual_ledger)
    if not acceleration.accepted:
        reasons.append("acceleration certificate is not accepted")
    if not certificate.certified_capital_witness_refs:
        reasons.append("certified_capital_witness_refs are required")
    if not certificate.target_validity_refs:
        reasons.append("target_validity_refs are required")
    if not certificate.baseline_upper_envelope_refs:
        reasons.append("baseline_upper_envelope_refs are required")
    if not certificate.resource_matched_baseline_refs:
        reasons.append("resource_matched_baseline_refs are required")
    if not certificate.live_predicate_refs:
        reasons.append("live_predicate_refs are required")
    if not certificate.hazard_envelope_refs:
        reasons.append("hazard_envelope_refs are required")
    if not certificate.transport_validity_refs:
        reasons.append("transport_validity_refs are required")
    for obligation in certificate.residual_external_obligations:
        reasons.append(f"external ALT-CARA obligation remains: {obligation}")
    residual = _add_reason_residual(
        residual,
        f"alt-cara:{certificate.certificate_id}",
        reasons,
    )
    accepted = not reasons
    return certificate.model_copy(
        update={
            "acceleration_certificate": acceleration,
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def check_alt_kernel_transition(
    report: ALTKernelTransitionReport,
) -> ALTKernelTransitionReport:
    """Check dual exploration/settlement ledger preservation for ALT transitions."""

    reasons = list(report.reasons)
    residual = report.residual_ledger
    if not report.prior_state_id or not report.next_state_id:
        reasons.append("prior_state_id and next_state_id are required")
    if report.prior_state_id == report.next_state_id:
        reasons.append("kernel transition must advance to a distinct state id")
    if (
        report.action
        in {
            ALTAdmissionAction.DEPRECATE,
            ALTAdmissionAction.ROLLBACK,
        }
        and not report.deprecation_record_refs
    ):
        reasons.append("deprecation/rollback transition requires deprecation_record_refs")
    if report.action == ALTAdmissionAction.RESURRECT_AS_CANDIDATE and not (
        report.resurrection_record_refs
    ):
        reasons.append("resurrection transition requires resurrection_record_refs")
    accepted = not reasons
    residual = _add_reason_residual(
        residual,
        f"alt-kernel-transition:{report.report_id}",
        reasons,
    )
    return report.model_copy(
        update={
            "accepted": accepted,
            "finite_checks_passed": accepted,
            "operationally_usable": accepted,
            "settled": False,
            "residual_ledger": residual,
            "reasons": sorted(set(reasons)),
        }
    )


def bridge_alt_to_runtime(
    report: GeneralIntakeRuntimeBridgeReport,
    state: RuntimeState,
) -> FoundryState:
    """Build an ALT foundry sidecar from candidate-only runtime intake."""

    tokens = [
        build_abstraction_token_from_packet(packet) for packet in report.packet_ingestion.packets
    ]
    residual = state.residual_ledger.combine(report.residual_ledger)
    return FoundryState(
        foundry_id=f"alt-foundry:{state.state_id}",
        token_candidates=tokens,
        evidence_backlog=len(report.verifier_work_packet_ids),
        transport_backlog=len(report.diagnostic_work_packet_ids),
        risk_backlog=len(report.quarantine_packet_ids),
        receiver_absorption_capacity=1.0,
        settlement_capacity=1.0,
        residual_ledger=residual,
    )


def formation_cost_ledger_from_values(
    ledger_id: str,
    values: dict[str, object],
) -> FormationCostLedger:
    """Convenience constructor for portable JSON examples and CLI intake."""

    return FormationCostLedger(
        ledger_id=ledger_id,
        formation_cost=_context_float(values, "formation_cost"),
        deployment_cost=_context_float(values, "deployment_cost"),
        validation_cost=_context_float(values, "validation_cost"),
        certification_cost=_context_float(values, "certification_cost"),
        settlement_cost=_context_float(values, "settlement_cost"),
        maintenance_cost=_context_float(values, "maintenance_cost"),
        depreciation_cost=_context_float(values, "depreciation_cost"),
        contamination_cost=_context_float(values, "contamination_cost"),
        hidden_resource_cost=_context_float(values, "hidden_resource_cost"),
        telemetry_cost=_context_float(values, "telemetry_cost"),
        absorption_cost=_context_float(values, "absorption_cost"),
        misapplication_cost=_context_float(values, "misapplication_cost"),
        hazard_cost=_context_float(values, "hazard_cost"),
        unit=str(values.get("unit", "dimensionless")),
        evidence_refs=_string_list(values.get("evidence_refs")),
    )
