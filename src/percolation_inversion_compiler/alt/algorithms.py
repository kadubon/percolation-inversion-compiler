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
    AltEcptLiftReport,
    ALTKernelTransitionReport,
    AltLiftBlocker,
    ALTResurrectionRecord,
    BaselineRefreshCertificate,
    CapitalToPathContribution,
    CertifiedAbstractionCapital,
    CrossContextTransferWitness,
    DownstreamSearchCostDelta,
    ExecutableALTCertificatePacket,
    FormationCostLedger,
    FoundryBottleneck,
    FoundryControlDashboard,
    FoundryState,
    HazardEnvelopeCertificate,
    LiquidityCertificate,
    LiquidityToClosureContribution,
    NegativeLiquidityCertificate,
    OpportunityMeasureContract,
    ProblemSolvingTrace,
    ReceiverLiquidityLift,
    ReproductionMatrixCertificate,
    RootFinalityCertificate,
    TelemetryCostCertificate,
    TokenLineage,
    TransportCertificate,
    ValueBridgeReport,
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
from percolation_inversion_compiler.phase_lab import detect_autocatalytic_closure
from percolation_inversion_compiler.phase_lab.records import EffectivePacketGraph
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


def _value_bridge_report(certificate: LiquidityCertificate) -> ValueBridgeReport:
    evidence_level = certificate.value_evidence_level.lower()
    reasons: list[str] = []
    if evidence_level not in {"proxy-only", "calibrated-proxy", "causal"}:
        reasons.append("value_evidence_level must be proxy-only, calibrated-proxy, or causal")
    if evidence_level == "proxy-only":
        reasons.append("proxy-only evidence cannot certify reusable abstraction capital")
    if evidence_level == "calibrated-proxy" and not certificate.proxy_bridge_refs:
        reasons.append("calibrated proxy value evidence requires proxy_bridge_refs")
    if evidence_level == "causal" and not certificate.causal_effect_refs:
        reasons.append("causal value evidence requires causal_effect_refs")
    if evidence_level in {"calibrated-proxy", "causal"} and not certificate.common_estimand_refs:
        reasons.append("value bridge requires common_estimand_refs")
    instrumentation_refs = sorted(
        {
            *certificate.telemetry_refs,
            *certificate.root_of_trust_refs,
            *certificate.robustness_refs,
        }
    )
    contamination_diagnostics: list[str] = []
    if not instrumentation_refs:
        contamination_diagnostics.append("instrumentation or contamination-control refs absent")
    transportability_ready = certificate.transport_certificate is not None
    if not transportability_ready:
        contamination_diagnostics.append("transportability certificate absent from value bridge")
    baseline_refresh_ready = bool(
        certificate.opportunity_contract
        or certificate.lifecycle_bounds
        or certificate.telemetry_cost_certificate
    )
    portfolio_gaming_diagnostics: list[str] = []
    if certificate.hazard_envelope_certificate is None:
        portfolio_gaming_diagnostics.append("hazard envelope absent for portfolio-gaming screen")
    foundry_capacity_label = (
        "causal-reproduction-ready"
        if evidence_level == "causal" and certificate.causal_effect_refs and transportability_ready
        else "transport-limited"
        if not transportability_ready
        else "evidence-limited"
        if evidence_level == "proxy-only"
        else "capacity-limited"
    )
    accepted = not reasons
    return ValueBridgeReport(
        report_id=f"alt-value-bridge:{certificate.certificate_id}",
        value_evidence_level=certificate.value_evidence_level,
        proxy_only=evidence_level == "proxy-only",
        calibrated_proxy_bridge_ready=bool(
            evidence_level == "calibrated-proxy"
            and certificate.proxy_bridge_refs
            and certificate.common_estimand_refs
        ),
        causal_effect_ready=bool(evidence_level == "causal" and certificate.causal_effect_refs),
        common_estimand_ready=bool(certificate.common_estimand_refs),
        proxy_bridge_refs=sorted(certificate.proxy_bridge_refs),
        causal_effect_refs=sorted(certificate.causal_effect_refs),
        common_estimand_refs=sorted(certificate.common_estimand_refs),
        instrumentation_refs=instrumentation_refs,
        contamination_diagnostics=sorted(set(contamination_diagnostics)),
        transportability_ready=transportability_ready,
        causal_reproduction_ready=bool(
            evidence_level == "causal" and certificate.causal_effect_refs and transportability_ready
        ),
        portfolio_gaming_diagnostics=sorted(set(portfolio_gaming_diagnostics)),
        baseline_refresh_ready=baseline_refresh_ready,
        negative_liquidity_preserved=True,
        cara_residual_preserved=True,
        foundry_capacity_label=foundry_capacity_label,
        accepted=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
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
    value_bridge_report = _value_bridge_report(certificate)
    reasons.extend(value_bridge_report.reasons)
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
            "value_bridge_report": value_bridge_report,
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


def verify_receiver_liquidity_lift(
    packet_data: dict[str, object],
    receiver_context: dict[str, object],
) -> ReceiverLiquidityLift:
    """Check whether one ALT artifact improves a receiver context."""

    packet_id = _packet_id(packet_data)
    receiver_id = str(
        receiver_context.get("receiver_context_id")
        or receiver_context.get("context_id")
        or "receiver-context"
    )
    evidence_refs = _string_list(receiver_context.get("evidence_refs")) + _packet_evidence_refs(
        packet_data
    )
    context_present = bool(receiver_context)
    accepted = (
        _packet_is_accepted_alt_capital(packet_data)
        and context_present
        and bool(evidence_refs)
    )
    blockers: list[str] = []
    if not _packet_is_accepted_alt_capital(packet_data):
        blockers.append("ALT packet is not accepted operational abstraction capital")
    if not context_present:
        blockers.append("receiver context is missing")
    if not evidence_refs:
        blockers.append("receiver lift evidence_refs are required")
    return ReceiverLiquidityLift(
        lift_id=f"receiver-lift:{packet_id}:{receiver_id}",
        packet_id=packet_id,
        receiver_context_id=receiver_id,
        receiver_context_present=context_present,
        improves_receiver_context=accepted,
        evidence_refs=sorted(set(evidence_refs)),
        blockers=sorted(set(blockers)),
        accepted=accepted,
        settled=False,
    )


def verify_alt_ecpt_lift(
    packets: list[dict[str, object]],
    graph: EffectivePacketGraph,
) -> AltEcptLiftReport:
    """Check whether ALT capital affects ECPT phase proxy components."""

    receiver_lifts: list[ReceiverLiquidityLift] = []
    transfer_witnesses: list[CrossContextTransferWitness] = []
    deltas: list[DownstreamSearchCostDelta] = []
    path_contributions: list[CapitalToPathContribution] = []
    closure_contributions: list[LiquidityToClosureContribution] = []
    blockers: list[AltLiftBlocker] = []
    closure = detect_autocatalytic_closure(graph)
    accepted_paths = [
        edge.edge_id
        for edge in graph.edges
        if edge.contribution.positive_contribution and edge.evidence.evidence_supported
    ]
    closure_ids = [witness.witness_id for witness in closure.closure_witnesses]
    components: set[str] = set()
    for packet in packets:
        packet_id = _packet_id(packet)
        accepted_capital = _packet_is_accepted_alt_capital(packet)
        evidence_refs = _packet_evidence_refs(packet)
        reduction = _search_cost_reduction(packet)
        if reduction > 0.0:
            deltas.append(
                DownstreamSearchCostDelta(
                    delta_id=f"search-cost-delta:{packet_id}",
                    baseline_cost=reduction,
                    candidate_cost=0.0,
                    lower_bound_reduction=reduction,
                    evidence_refs=evidence_refs,
                    accepted=accepted_capital and bool(evidence_refs),
                    settled=False,
                )
            )
            if accepted_capital and evidence_refs:
                components.add("downstream_search_cost")
        receiver_lift = verify_receiver_liquidity_lift(
            packet,
            {"receiver_context_id": "graph-receiver-context", "evidence_refs": evidence_refs},
        )
        receiver_lifts.append(receiver_lift)
        if receiver_lift.accepted:
            components.add("receiver_context")
        receiver_family = _string_list(packet.get("receiver_family"))
        if not receiver_family:
            token = packet.get("token")
            if isinstance(token, dict):
                receiver_family = _string_list(token.get("receiver_family"))
        if len(receiver_family) >= 2:
            transfer = CrossContextTransferWitness(
                witness_id=f"cross-context:{packet_id}",
                source_context=receiver_family[0],
                target_context=receiver_family[1],
                transfer_supported=accepted_capital and bool(evidence_refs),
                evidence_refs=evidence_refs,
                settled=False,
            )
            transfer_witnesses.append(transfer)
            if transfer.transfer_supported:
                components.add("cross_context_transfer")
        path_contribution = CapitalToPathContribution(
            contribution_id=f"capital-to-path:{packet_id}",
            packet_id=packet_id,
            graph_id=graph.graph_id,
            path_ids=accepted_paths,
            increases_execution_available_path_density=accepted_capital and bool(accepted_paths),
            accepted=accepted_capital and bool(accepted_paths),
            settled=False,
            reasons=[
                "path contribution requires accepted graph edges",
                "ALT capital does not execute paths",
            ],
        )
        path_contributions.append(path_contribution)
        if path_contribution.accepted:
            components.add("execution_available_path_density")
        closure_contribution = LiquidityToClosureContribution(
            contribution_id=f"liquidity-to-closure:{packet_id}",
            packet_id=packet_id,
            graph_id=graph.graph_id,
            closure_witness_ids=closure_ids,
            supports_closure=accepted_capital and bool(closure_ids),
            accepted=accepted_capital and bool(closure_ids),
            settled=False,
            reasons=["closure contribution requires evidence-supported closure witnesses"],
        )
        closure_contributions.append(closure_contribution)
        if closure_contribution.accepted:
            components.add("closure")
        if not accepted_capital:
            blockers.append(
                AltLiftBlocker(
                    blocker_id=f"alt-lift-blocker:{packet_id}:capital",
                    packet_id=packet_id,
                    blocker_type="missing accepted ALT capital",
                    remediation=(
                        "admit an ALT packet with finite liquidity, transport, root, "
                        "telemetry, lifecycle, and hazard checks"
                    ),
                )
            )
        if not components:
            blockers.append(
                AltLiftBlocker(
                    blocker_id=f"alt-lift-blocker:{packet_id}:ecpt-component",
                    packet_id=packet_id,
                    blocker_type="no ECPT component affected",
                    remediation="provide edge, receiver, path, closure, or bottleneck evidence",
                )
            )
    accepted = bool(components) and not any(
        blocker.blocker_type == "missing accepted ALT capital" for blocker in blockers
    )
    return AltEcptLiftReport(
        graph_id=graph.graph_id,
        receiver_liquidity_lifts=receiver_lifts,
        cross_context_transfer_witnesses=transfer_witnesses,
        downstream_search_cost_deltas=deltas,
        capital_to_path_contributions=path_contributions,
        liquidity_to_closure_contributions=closure_contributions,
        affected_ecpt_components=sorted(components),
        blockers=blockers,
        diagnostic_only_lift_failure=not accepted,
        accepted=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=[
            "ALT lift is protocol-relative only",
            "positive ALT liquidity does not automatically become ECPT packet capital",
            *([] if accepted else ["no accepted ECPT component lift was established"]),
        ],
    )


def verify_alt_liquidity_to_paths(
    packet_data: dict[str, object],
    graph: EffectivePacketGraph,
) -> AltEcptLiftReport:
    """Check a single ALT packet against graph path contributions."""

    return verify_alt_ecpt_lift([packet_data], graph)


def compute_alt_capital_impact(
    reports: list[dict[str, object]],
) -> AltEcptLiftReport:
    """Summarize ALT lift-like impacts from existing reports without promotion."""

    components: set[str] = set()
    blockers: list[AltLiftBlocker] = []
    for index, report in enumerate(reports):
        accepted = bool(report.get("accepted", False)) and bool(
            report.get("operationally_usable", False)
        )
        if accepted:
            components.add(str(report.get("component", "reported_alt_capital")))
        else:
            blockers.append(
                AltLiftBlocker(
                    blocker_id=f"alt-capital-impact-blocker:{index}",
                    packet_id=str(report.get("packet_id", report.get("report_id", index))),
                    blocker_type="report not accepted operational capital",
                    remediation="rerun finite ALT and ECPT component checks",
                )
            )
    return AltEcptLiftReport(
        report_id="alt-capital-impact",
        affected_ecpt_components=sorted(components),
        blockers=blockers,
        diagnostic_only_lift_failure=not bool(components),
        accepted=bool(components),
        operationally_usable=bool(components),
        settled=False,
        reasons=["capital impact summary is diagnostic and does not settle ALT lift"],
    )


def _packet_id(packet_data: dict[str, object]) -> str:
    return str(
        packet_data.get("packet_id")
        or packet_data.get("decision_id")
        or packet_data.get("token_id")
        or "alt-packet"
    )


def _packet_evidence_refs(packet_data: dict[str, object]) -> list[str]:
    refs = _string_list(packet_data.get("evidence_refs"))
    token = packet_data.get("token")
    if isinstance(token, dict):
        refs.extend(_string_list(token.get("evidence_refs")))
    certificate = packet_data.get("liquidity_certificate")
    if isinstance(certificate, dict):
        refs.extend(_string_list(certificate.get("evidence_refs")))
        refs.extend(_string_list(certificate.get("proxy_bridge_refs")))
        refs.extend(_string_list(certificate.get("common_estimand_refs")))
    return sorted(set(refs))


def _packet_is_accepted_alt_capital(packet_data: dict[str, object]) -> bool:
    if bool(packet_data.get("accepted", False)) and bool(
        packet_data.get("operationally_usable", False)
    ):
        return True
    if packet_data.get("certified_capital_ref"):
        return bool(packet_data.get("accepted", False))
    certificate = packet_data.get("liquidity_certificate")
    if isinstance(certificate, dict):
        return bool(certificate.get("accepted", False)) and bool(
            certificate.get("operationally_usable", False)
        )
    return False


def _search_cost_reduction(packet_data: dict[str, object]) -> float:
    value = packet_data.get("downstream_search_cost_reduction_lower_bound")
    certificate = packet_data.get("liquidity_certificate")
    if value is None and isinstance(certificate, dict):
        value = certificate.get("downstream_search_cost_reduction_lower_bound")
    if value is None:
        value = packet_data.get("signed_surplus_lower_bound", 0.0)
    if not isinstance(value, int | float | str):
        return 0.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0
