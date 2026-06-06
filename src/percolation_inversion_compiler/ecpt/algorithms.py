"""Finite constructive ECPT algorithms."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from math import log, sqrt

from percolation_inversion_compiler.core.adapter_routes import (
    binding_for_route,
    list_adapter_route_specs,
)
from percolation_inversion_compiler.core.algorithms import (
    expected_value,
    finite_difference_interval,
    gibbs_distribution,
)
from percolation_inversion_compiler.core.checker import boolean_check_result, residual_from_reasons
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus, no_worse_status
from percolation_inversion_compiler.ecpt.records import (
    ActionGrammar,
    ActivationConstructionCertificate,
    ActivationThresholdCertificate,
    AdmissibilityGrade,
    ASIProxyTargetContract,
    CapabilityEdge,
    CapabilityHypergraph,
    CapabilityStateVector,
    CapacityCertificate,
    ConstraintFrame,
    ControlledTransition,
    CycleMonitorCertificate,
    FinitePhaseControlCertificate,
    FiniteTraceLaw,
    InformationProjectionQuotient,
    InnerViabilityKernel,
    InterventionCandidate,
    MeanFieldEnvelopeCertificate,
    ObservationProtocol,
    PacketAtlas,
    PathLawResponsePolicyCertificate,
    PhaseControlAction,
    PhaseControlEnvelope,
    PhaseControlObjective,
    PhaseControlPlan,
    PhaseControlRunReport,
    PhaseControlState,
    ProtocolFunctorCertificate,
    QueueCertificate,
    RAFSettlementCertificate,
    ReachableMassRecursionCertificate,
    ResourceNormalizedCut,
    SettlementReturnRAFCertificate,
    TargetValidityStatus,
)


def check_observation_protocol(protocol: ObservationProtocol) -> CheckResult:
    reasons: list[str] = []
    if not protocol.time_index:
        reasons.append("observation protocol time index is empty")
    if not protocol.window_family:
        reasons.append("observation protocol has no finite windows")
    if not protocol.receiver_contexts:
        reasons.append("observation protocol has no receiver contexts")
    if not protocol.validity_domains:
        reasons.append("observation protocol has no validity domains")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="ecpt:observation-protocol",
        failure_reason="; ".join(reasons) if reasons else "observation protocol failed",
        residual_ledger=residual_from_reasons("observation-protocol", reasons),
    )


def check_protocol_functor_certificate(certificate: ProtocolFunctorCertificate) -> CheckResult:
    """Check finite protocol-functor preservation and ontology-extension obligations."""

    reasons: list[str] = []
    source_result = check_observation_protocol(certificate.source_protocol)
    target_result = check_observation_protocol(certificate.target_protocol)
    reasons.extend(source_result.reasons)
    reasons.extend(target_result.reasons)
    source_objects = set(certificate.source_protocol.receiver_contexts) | set(
        certificate.source_protocol.validity_domains
    )
    target_objects = set(certificate.target_protocol.receiver_contexts) | set(
        certificate.target_protocol.validity_domains
    )
    if not certificate.object_map:
        reasons.append("protocol functor object map is empty")
    if set(certificate.object_map) - source_objects:
        reasons.append("protocol functor maps objects absent from source protocol")
    if set(certificate.object_map.values()) - target_objects:
        reasons.append("protocol functor targets objects absent from target protocol")
    if certificate.residual < 0:
        reasons.append("protocol functor residual is negative")
    if certificate.ontology_extension_obligations and not certificate.accepted_extension:
        reasons.append("ontology-extension obligations are not accepted")
    residual = source_result.residual_ledger.combine(target_result.residual_ledger)
    if certificate.residual:
        residual = residual.add_coordinate(
            f"protocol-functor:{certificate.certificate_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"protocol-functor:{certificate.certificate_id}",
        failure_reason="; ".join(reasons) if reasons else "protocol functor failed",
        residual_ledger=residual.combine(residual_from_reasons("protocol-functor", reasons)),
    )


def check_phase_control_envelope(envelope: PhaseControlEnvelope) -> CheckResult:
    """Check finite phase-control envelope, keeping thermodynamic claims external."""

    reasons: list[str] = []
    if not envelope.finite_state_space:
        reasons.append("phase-control envelope has empty finite state space")
    if envelope.finite_horizon < 0:
        reasons.append("phase-control envelope finite horizon is negative")
    if set(envelope.control_surface) - envelope.finite_state_space:
        reasons.append("control surface references states outside finite state space")
    if set(envelope.phase_response) - envelope.finite_state_space:
        reasons.append("phase response references states outside finite state space")
    if envelope.residual < 0:
        reasons.append("phase-control residual is negative")
    residual = Ledger()
    if envelope.residual:
        residual = residual.add_coordinate(
            f"phase-control:{envelope.envelope_id}",
            envelope.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    if envelope.thermodynamic_obligation_ids:
        reasons.append("thermodynamic phase-control obligations remain external")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"phase-control:{envelope.envelope_id}",
        failure_reason="; ".join(reasons) if reasons else "phase-control envelope failed",
        residual_ledger=residual.combine(residual_from_reasons("phase-control", reasons)),
    )


def check_finite_phase_control_certificate(
    certificate: FinitePhaseControlCertificate,
) -> CheckResult:
    """Check finite phase-control response while keeping limit claims external."""

    envelope_result = check_phase_control_envelope(certificate.envelope)
    reasons = list(envelope_result.reasons)
    if certificate.residual < 0:
        reasons.append("finite phase-control residual is negative")
    improvement = (
        certificate.controlled_response - certificate.baseline_response - abs(certificate.residual)
    )
    if improvement < certificate.minimum_improvement:
        reasons.append("finite phase-control improvement is below the certified floor")
    external_obligations = (
        certificate.thermodynamic_obligation_ids | certificate.envelope.thermodynamic_obligation_ids
    )
    if external_obligations:
        reasons.append("thermodynamic phase-control obligations remain external")
    residual = envelope_result.residual_ledger
    residual = residual.add_coordinate(
        f"finite-phase-control:{certificate.certificate_id}:improvement-gap",
        max(0.0, certificate.minimum_improvement - improvement),
        kind=CoordinateKind.RESIDUAL,
    )
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(external_obligations),
        residual_ledger=residual.combine(residual_from_reasons("finite-phase-control", reasons)),
    )


def check_constraint_frame(frame: ConstraintFrame) -> CheckResult:
    reasons: list[str] = []
    if not frame.hard_domain_live():
        reasons.append("hard-domain gate is false")
    if frame.expires:
        reasons.append("constraint frame has expired obligations")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="ecpt:constraint-frame",
        failure_reason="; ".join(reasons) if reasons else "constraint frame failed",
        residual_ledger=frame.hazards.combine(frame.capacity).combine(frame.queue),
    )


def check_admissibility_grade(grade: AdmissibilityGrade) -> CheckResult:
    reasons: list[str] = []
    if not grade.hard_indicator:
        reasons.append("admissibility hard indicator is false")
    if not 0.0 <= grade.activation_weight <= 1.0:
        reasons.append("activation weight must be in [0, 1]")
    if grade.burden < 0:
        reasons.append("burden must be nonnegative")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"admissibility-grade:{grade.grade_id}",
        failure_reason="; ".join(reasons) if reasons else "admissibility grade failed",
        residual_ledger=residual_from_reasons("admissibility-grade", reasons),
    )


def check_target_validity_status(status: TargetValidityStatus, present: set[str]) -> CheckResult:
    missing = sorted(status.mandatory_obligations - present)
    reasons = ["target-validity mandatory obligations are missing"] if missing else []
    return CheckResult(
        accepted=not missing,
        status=ClaimStatus.SETTLED if not missing else ClaimStatus.DIAGNOSTIC,
        reasons=reasons,
        missing_obligations=missing,
        residual_ledger=residual_from_reasons("target-validity", reasons),
    )


def split_certified_quotient_error(
    *,
    finite_sample_error: float,
    selection_error: float,
    transport_error: float,
    algorithmic_error: float,
    boundary_mass: float = 0.0,
) -> float:
    """Split-certified boundary-aware quotient error ledger aggregate."""

    return (
        abs(finite_sample_error)
        + abs(selection_error)
        + abs(transport_error)
        + abs(algorithmic_error)
        + abs(boundary_mass)
    )


def reachable_mass(
    graph: CapabilityHypergraph,
    *,
    status_floor: ClaimStatus = ClaimStatus.SPECULATIVE,
    max_rounds: int | None = None,
) -> dict[str, float]:
    """Finite AND-support reachable-mass recursion on a directed hypergraph."""

    masses = {node: max(0.0, mass) for node, mass in graph.seed_mass.items()}
    rounds = max_rounds or (len(graph.edges) + 1)
    for _ in range(rounds):
        changed = False
        for edge in graph.edges:
            if not no_worse_status(edge.status, status_floor):
                continue
            if not all(source in masses for source in edge.sources):
                continue
            source_mass = min(masses[source] for source in edge.sources) if edge.sources else 1.0
            candidate = max(0.0, source_mass * edge.activation_weight - edge.burden)
            if candidate > masses.get(edge.target, 0.0):
                masses[edge.target] = candidate
                changed = True
        if not changed:
            break
    return masses


def check_capability_state_vector(state: CapabilityStateVector) -> CheckResult:
    reasons: list[str] = []
    if not state.packets:
        reasons.append("capability state vector has no packets")
    for packet in state.packets:
        if packet.duplicate_mass < 0 or packet.burden < 0:
            reasons.append(f"packet {packet.packet_id} has negative duplicate mass or burden")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"capability-state:{state.validity_domain}",
        failure_reason="; ".join(reasons) if reasons else "capability state failed",
        residual_ledger=state.burden_ledger.combine(
            residual_from_reasons("capability-state", reasons)
        ),
    )


def check_finite_trace_law(law: FiniteTraceLaw) -> CheckResult:
    reasons: list[str] = []
    if not law.traces:
        reasons.append("finite trace law has empty support")
    if any(probability < 0 for probability in law.traces.values()):
        reasons.append("finite trace probabilities must be nonnegative")
    total = sum(law.traces.values())
    if law.normalized and abs(total - 1.0) > 1e-9:
        reasons.append("normalized finite trace law must sum to one")
    if law.support_residual < 0:
        reasons.append("support residual must be nonnegative")
    residual = residual_from_reasons("finite-trace-law", reasons)
    residual = residual.add_coordinate(
        f"finite-trace-law:{law.law_id}:normalization-gap",
        abs(total - 1.0),
        kind=CoordinateKind.RESIDUAL,
    )
    if law.support_residual:
        residual = residual.add_coordinate(
            f"finite-trace-law:{law.law_id}:support",
            law.support_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"finite-trace-law:{law.law_id}",
        failure_reason="; ".join(reasons) if reasons else "finite trace law failed",
        residual_ledger=residual,
    )


def check_packet_atlas(atlas: PacketAtlas) -> CheckResult:
    reasons: list[str] = []
    if not atlas.strata:
        reasons.append("packet atlas has no strata")
    known = set(atlas.strata)
    for src, row in atlas.transition_kernel.items():
        if src not in known:
            reasons.append(f"transition kernel source {src} is absent from strata")
        if set(row) - known:
            reasons.append(f"transition kernel from {src} targets unknown strata")
        if any(value < 0 for value in row.values()):
            reasons.append(f"transition kernel from {src} has negative mass")
    if atlas.boundary_residual < 0:
        reasons.append("atlas boundary residual must be nonnegative")
    residual = residual_from_reasons("packet-atlas", reasons)
    if atlas.boundary_residual:
        residual = residual.add_coordinate(
            f"packet-atlas:{atlas.atlas_id}:boundary",
            atlas.boundary_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"packet-atlas:{atlas.atlas_id}",
        failure_reason="; ".join(reasons) if reasons else "packet atlas failed",
        residual_ledger=residual,
    )


def check_information_projection_quotient(quotient: InformationProjectionQuotient) -> CheckResult:
    reasons: list[str] = []
    if quotient.distortion < 0:
        reasons.append("information-projection distortion must be nonnegative")
    if quotient.chart_validity_radius < 0:
        reasons.append("chart validity radius must be nonnegative")
    residual = residual_from_reasons("information-projection", reasons)
    residual = residual.add_coordinate(
        f"information-projection:{quotient.quotient_id}:distortion",
        quotient.distortion,
        kind=CoordinateKind.RESIDUAL,
    )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"information-projection:{quotient.quotient_id}",
        failure_reason="; ".join(reasons) if reasons else "information projection failed",
        residual_ledger=residual,
    )


def finite_gibbs_phase_response(
    baseline_energies: dict[str, float],
    perturbed_energies: dict[str, float],
    basin: set[str],
    *,
    beta: float = 1.0,
    residual: float = 0.0,
) -> tuple[float, float, float]:
    """Return baseline basin mass, perturbed basin mass, and charged improvement."""

    baseline = gibbs_distribution(baseline_energies, beta=beta)
    perturbed = gibbs_distribution(perturbed_energies, beta=beta)

    def observable(state: str) -> float:
        return 1.0 if state in basin else 0.0

    baseline_mass = expected_value(baseline, observable)
    perturbed_mass = expected_value(perturbed, observable)
    return baseline_mass, perturbed_mass, perturbed_mass - baseline_mass - abs(residual)


def check_action_grammar(grammar: ActionGrammar) -> CheckResult:
    reasons: list[str] = []
    if not grammar.actions:
        reasons.append("action grammar has no actions")
    if set(grammar.preconditions) - grammar.actions:
        reasons.append("preconditions mention unknown actions")
    if set(grammar.postconditions) - grammar.actions:
        reasons.append("postconditions mention unknown actions")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="action-grammar:finite",
        failure_reason="; ".join(reasons) if reasons else "action grammar failed",
        residual_ledger=residual_from_reasons("action-grammar", reasons),
    )


def check_controlled_transition(transition: ControlledTransition) -> CheckResult:
    reasons: list[str] = []
    if not transition.preconditions_met:
        reasons.append("controlled transition preconditions are not met")
    if transition.postcondition_obligation is not None:
        missing = (
            transition.postcondition_obligation.required_postconditions
            - transition.postcondition_obligation.satisfied_postconditions
        )
        if missing:
            reasons.append("controlled transition postconditions are missing")
    if transition.residual < 0:
        reasons.append("controlled transition residual must be nonnegative")
    residual = residual_from_reasons("controlled-transition", reasons)
    if transition.residual:
        residual = residual.add_coordinate(
            f"controlled-transition:{transition.transition_id}:residual",
            transition.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"controlled-transition:{transition.transition_id}",
        failure_reason="; ".join(reasons) if reasons else "controlled transition failed",
        residual_ledger=residual,
    )


def check_inner_viability_kernel(kernel: InnerViabilityKernel) -> CheckResult:
    reasons: list[str] = []
    if not kernel.inner_states.issubset(kernel.states):
        reasons.append("inner viability states are not a subset of all states")
    for state in kernel.inner_states:
        successors = kernel.transition_map.get(state, set())
        if successors and not successors.issubset(kernel.inner_states):
            reasons.append(f"inner state {state} has successor outside inner kernel")
    if kernel.residual < 0:
        reasons.append("viability residual must be nonnegative")
    residual = residual_from_reasons("viability", reasons)
    if kernel.residual:
        residual = residual.add_coordinate(
            f"viability:{kernel.kernel_id}:residual",
            kernel.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"viability:{kernel.kernel_id}",
        failure_reason="; ".join(reasons) if reasons else "viability kernel failed",
        residual_ledger=residual,
    )


def activation_construction_accepts(certificate: ActivationConstructionCertificate) -> bool:
    """Check a finite activation-construction certificate."""

    return check_activation_construction(certificate).accepted


def check_activation_construction(certificate: ActivationConstructionCertificate) -> CheckResult:
    """Check exact/factorized/sampler activation construction certificate."""

    reasons: list[str] = []
    if certificate.configuration_space_size <= 0:
        reasons.append("configuration space must be finite and nonempty")
    if not certificate.energy_ledger_present:
        reasons.append("energy ledger is absent")
    if not certificate.exact and certificate.sampler_residual < 0:
        reasons.append("sampler residual must be nonnegative")
    residual = residual_from_reasons("activation-construction", reasons)
    if certificate.sampler_residual:
        residual = residual.add_coordinate(
            "activation-construction:sampler-residual",
            certificate.sampler_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="activation-construction:finite",
        failure_reason="; ".join(reasons) if reasons else "activation construction failed",
        residual_ledger=residual,
    )


def check_activation_threshold_certificate(
    certificate: ActivationThresholdCertificate,
) -> CheckResult:
    """Check finite activation threshold and isolate thermodynamic obligations."""

    activation_result = check_activation_construction(certificate.activation)
    reasons = list(activation_result.reasons)
    if certificate.finite_size <= 0:
        reasons.append("activation threshold finite size must be positive")
    if certificate.threshold < 0:
        reasons.append("activation threshold must be nonnegative")
    if certificate.residual < 0:
        reasons.append("activation threshold residual is negative")
    masses = reachable_mass(certificate.graph)
    for node in certificate.target_nodes:
        lower = certificate.lower_bounds.get(node, certificate.threshold)
        if masses.get(node, 0.0) + certificate.residual < lower:
            reasons.append(f"activation threshold lower bound fails for {node}")
    if certificate.thermodynamic_obligation_ids:
        reasons.append("thermodynamic activation-threshold obligations remain external")
    residual = activation_result.residual_ledger
    for node in sorted(certificate.target_nodes):
        lower = certificate.lower_bounds.get(node, certificate.threshold)
        residual = residual.add_coordinate(
            f"activation-threshold:{certificate.certificate_id}:{node}",
            max(0.0, lower - certificate.residual - masses.get(node, 0.0)),
            kind=CoordinateKind.RESIDUAL,
        )
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(certificate.thermodynamic_obligation_ids),
        residual_ledger=residual.combine(residual_from_reasons("activation-threshold", reasons)),
    )


def path_law_policy_accepts(certificate: PathLawResponsePolicyCertificate) -> bool:
    """Check path-law response-policy overlap and finite sample ledgers."""

    return check_path_law_policy(certificate).accepted


def check_path_law_policy(certificate: PathLawResponsePolicyCertificate) -> CheckResult:
    """Check path-law response-policy overlap and finite sample ledgers."""

    reasons: list[str] = []
    if certificate.overlap <= 0:
        reasons.append("path laws have no accepted overlap")
    if certificate.effective_sample_size <= 0:
        reasons.append("effective sample size must be positive")
    if certificate.residual < 0:
        reasons.append("path-law residual must be nonnegative")
    residual = residual_from_reasons("path-law-policy", reasons)
    if certificate.residual:
        residual = residual.add_coordinate(
            "path-law-policy:residual",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="path-law-policy:finite",
        failure_reason="; ".join(reasons) if reasons else "path-law policy failed",
        residual_ledger=residual,
    )


def queue_certificate_accepts(certificate: QueueCertificate) -> bool:
    """Check queue certificate shape before using reserve/backpressure claims."""

    return check_queue_certificate(certificate).accepted


def check_queue_certificate(certificate: QueueCertificate) -> CheckResult:
    """Check finite queue reserve and arrival/service shape."""

    reasons: list[str] = []
    if len(certificate.arrivals) != len(certificate.service):
        reasons.append("arrival and service profiles must have equal length")
    if certificate.reserve < 0:
        reasons.append("queue reserve must be nonnegative")
    backlog = 0.0
    if not reasons:
        backlog = backpressure_reserve_loss(certificate.arrivals, certificate.service)
        if backlog > certificate.reserve:
            reasons.append("queue backlog exceeds reserve")
    residual = residual_from_reasons("queue", reasons)
    if backlog:
        residual = residual.add_coordinate("queue:backlog", backlog, kind=CoordinateKind.RESIDUAL)
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="queue:reserve",
        failure_reason="; ".join(reasons) if reasons else "queue certificate failed",
        residual_ledger=residual,
    )


def capacity_certificate_accepts(certificate: CapacityCertificate) -> bool:
    """Check capacity feasibility after debt charges."""

    return check_capacity_certificate(certificate).accepted


def check_capacity_certificate(certificate: CapacityCertificate) -> CheckResult:
    """Check capacity feasibility after debt charges."""

    reasons: list[str] = []
    residual = Ledger()
    for resource, amount in certificate.required.items():
        available = certificate.available.get(resource, 0.0)
        debt = certificate.debt.get(resource, 0.0)
        shortfall = amount + debt - available
        if shortfall > 0:
            reasons.append(f"capacity shortfall for {resource}")
            residual = residual.add_coordinate(
                f"capacity:{resource}:shortfall",
                shortfall,
                kind=CoordinateKind.RESIDUAL,
            )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="capacity:feasible",
        failure_reason="; ".join(reasons) if reasons else "capacity certificate failed",
        residual_ledger=residual,
    )


def mean_field_envelope_accepts(certificate: MeanFieldEnvelopeCertificate) -> bool:
    """Check finite mean-field envelope premises."""

    return check_mean_field_envelope(certificate).accepted


def check_mean_field_envelope(certificate: MeanFieldEnvelopeCertificate) -> CheckResult:
    """Check finite mean-field envelope premises."""

    reasons: list[str] = []
    if certificate.finite_horizon < 0:
        reasons.append("finite horizon must be nonnegative")
    if not certificate.generator_identified:
        reasons.append("generator identification certificate is absent")
    if certificate.coupling_residual < 0 or certificate.reachable_mass_residual < 0:
        reasons.append("mean-field residuals must be nonnegative")
    residual = residual_from_reasons("mean-field", reasons)
    if certificate.coupling_residual:
        residual = residual.add_coordinate(
            "mean-field:coupling-residual",
            certificate.coupling_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    if certificate.reachable_mass_residual:
        residual = residual.add_coordinate(
            "mean-field:reachable-mass-residual",
            certificate.reachable_mass_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="mean-field:envelope",
        failure_reason="; ".join(reasons) if reasons else "mean-field envelope failed",
        residual_ledger=residual,
    )


def path_law_response_interval(
    baseline_value: float,
    candidate_value: float,
    *,
    epsilon: float = 1.0,
    path_score_error: float = 0.0,
    finite_difference_error: float = 0.0,
    state_shift_error: float = 0.0,
    likelihood_ratio_truncation: float = 0.0,
) -> tuple[float, float]:
    """Constructed path-law response interval with explicit residual charges."""

    residual = (
        abs(path_score_error)
        + abs(finite_difference_error)
        + abs(state_shift_error)
        + abs(likelihood_ratio_truncation)
    )
    return finite_difference_interval(baseline_value, candidate_value, epsilon, residual=residual)


def self_normalized_margin_risk(
    margins: Sequence[float],
    *,
    quadratic_variation: float,
    alpha: float,
    tail_ledger: float = 0.0,
) -> float:
    """Lower margin after a self-normalized, time-uniform style charge."""

    if not margins:
        raise ValueError("margins must not be empty")
    if quadratic_variation < 0:
        raise ValueError("quadratic_variation must be nonnegative")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    mean_margin = sum(margins) / len(margins)
    boundary = sqrt(2.0 * quadratic_variation * log(2.0 / alpha))
    return mean_margin - boundary - abs(tail_ledger)


def _proxy_mass(masses: dict[str, float], target: ASIProxyTargetContract) -> float:
    return sum(max(0.0, masses.get(node, 0.0)) for node in target.target_nodes)


def _candidate_graph(state: PhaseControlState, action: PhaseControlAction) -> CapabilityHypergraph:
    edge = CapabilityEdge(
        edge_id=f"phase-control-action:{action.action_id}",
        sources=tuple(action.source_nodes),
        target=action.target_node,
        activation_weight=max(0.0, action.activation_delta),
        burden=max(0.0, action.burden_delta + action.residual_charge),
        status=ClaimStatus.PROVISIONAL,
        required_capacity=action.resource_cost,
    )
    graph = state.graph.model_copy(deep=True)
    graph.edges.append(edge)
    graph.nodes.add(action.target_node)
    graph.nodes.update(action.source_nodes)
    return graph


def check_phase_control_action(
    state: PhaseControlState,
    objective: PhaseControlObjective,
    action: PhaseControlAction,
) -> CheckResult:
    """Check a finite ECPT planning action without promoting proxy claims."""

    reasons: list[str] = []
    missing: list[str] = []
    graph_nodes = state.graph.all_nodes()
    present = set(state.present_obligations) | graph_nodes
    if not state.constraint_frame.hard_domain_live():
        reasons.append("phase-control action blocked by hard-domain gate")
    if action.activation_delta < 0:
        reasons.append("phase-control action activation_delta is negative")
    if action.burden_delta < 0 or action.residual_charge < 0 or action.risk_charge < 0:
        reasons.append("phase-control action charges must be nonnegative")
    absent_sources = sorted(set(action.source_nodes) - graph_nodes)
    if absent_sources:
        reasons.append("phase-control action references absent source nodes")
        missing.extend(absent_sources)
    absent_preconditions = sorted(set(action.preconditions) - present)
    if absent_preconditions:
        reasons.append("phase-control action preconditions are missing")
        missing.extend(absent_preconditions)
    required = set(action.required_obligations) | set(objective.target.required_obligations)
    absent_obligations = sorted(required - set(state.present_obligations))
    if absent_obligations:
        reasons.append("phase-control action has unresolved target/action obligations")
        missing.extend(absent_obligations)
    forbidden = sorted(set(objective.target.forbidden_obligations) & set(state.present_obligations))
    if forbidden:
        reasons.append("phase-control action violates forbidden proxy obligations")
        missing.extend(forbidden)
    known_routes = {spec.route_id for spec in list_adapter_route_specs()}
    unknown_routes = sorted(set(action.verifier_routes) - known_routes)
    if unknown_routes:
        reasons.append("phase-control action references unknown verifier routes")
        missing.extend(unknown_routes)
    ledger = Ledger()
    for resource, cost in sorted(action.resource_cost.items()):
        budget = state.budgets.get(resource)
        if cost < 0:
            reasons.append(f"phase-control action resource cost is negative for {resource}")
        if budget is not None and cost > budget:
            reasons.append(f"phase-control action exceeds budget for {resource}")
            ledger = ledger.add_coordinate(
                f"ecpt-plan:{action.action_id}:budget:{resource}",
                cost - budget,
                kind=CoordinateKind.RESIDUAL,
            )
    if action.residual_charge:
        ledger = ledger.add_coordinate(
            f"ecpt-plan:{action.action_id}:residual",
            action.residual_charge,
            kind=CoordinateKind.RESIDUAL,
        )
    if action.risk_charge > objective.risk_tolerance:
        reasons.append("phase-control action risk charge exceeds objective tolerance")
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.PROVISIONAL if not reasons else ClaimStatus.DIAGNOSTIC,
        finite_checks_passed=not reasons,
        operationally_usable=False,
        settled=False,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(set(missing)),
        residual_ledger=ledger.combine(residual_from_reasons("phase-control-action", reasons)),
    )


def evaluate_phase_control_action(
    state: PhaseControlState,
    objective: PhaseControlObjective,
    action: PhaseControlAction,
) -> InterventionCandidate:
    """Evaluate one finite intervention candidate for an ASI-proxy target."""

    baseline = reachable_mass(state.graph)
    controlled_graph = _candidate_graph(state, action)
    controlled = reachable_mass(controlled_graph)
    baseline_proxy = _proxy_mass(baseline, objective.target)
    controlled_proxy = _proxy_mass(controlled, objective.target)
    action_check = check_phase_control_action(state, objective, action)
    raw_gain = controlled_proxy - baseline_proxy
    residual_charge = action.residual_charge + action_check.residual_ledger.burden_sum()
    finite_proxy_gain = raw_gain - residual_charge - action.risk_charge
    resource_penalty = sum(max(0.0, value) for value in action.resource_cost.values())
    score = finite_proxy_gain - resource_penalty
    route_residuals: list[str] = []
    for route in action.verifier_routes:
        binding = binding_for_route(route)
        if binding is not None:
            route_residuals.extend(binding.residual_external_obligation_refs)
    missing = sorted(set(action_check.missing_obligations + route_residuals))
    reasons = list(action_check.reasons)
    if finite_proxy_gain < objective.target.minimum_proxy_mass:
        reasons.append("finite proxy gain is below target floor")
    finite_scope_usable = bool(action_check.finite_checks_passed) and finite_proxy_gain >= 0
    operationally_usable = finite_scope_usable and not missing and score > 0
    return InterventionCandidate(
        candidate_id=f"candidate:{action.action_id}",
        action=action,
        baseline_proxy_mass=baseline_proxy,
        controlled_proxy_mass=controlled_proxy,
        finite_proxy_gain=finite_proxy_gain,
        score=score,
        residual_charge=residual_charge,
        risk_charge=action.risk_charge,
        resource_cost=dict(sorted(action.resource_cost.items())),
        required_evidence_routes=sorted(action.verifier_routes),
        missing_obligations=missing,
        reasons=sorted(set(reasons)),
        residual_ledger=action_check.residual_ledger,
        finite_scope_usable=finite_scope_usable,
        operationally_usable=operationally_usable,
        settled=False,
    )


def build_phase_control_plan(
    state: PhaseControlState,
    objective: PhaseControlObjective,
    actions: Sequence[PhaseControlAction],
    *,
    profile: str = "development",
) -> PhaseControlRunReport:
    """Build a deterministic ECPT ASI-proxy phase-control plan."""

    baseline = reachable_mass(state.graph)
    candidates = [
        evaluate_phase_control_action(state, objective, action)
        for action in sorted(actions, key=lambda item: item.action_id)
    ]
    candidates = sorted(candidates, key=lambda item: (-item.score, item.action.action_id))
    remaining_budget = dict(state.budgets)
    selected: list[InterventionCandidate] = []
    residual_ledger = Ledger()
    plan_reasons: list[str] = []
    for candidate in candidates:
        if not candidate.finite_scope_usable or candidate.score <= 0:
            continue
        fits_budget = True
        for resource, cost in candidate.resource_cost.items():
            if resource in remaining_budget and cost > remaining_budget[resource]:
                fits_budget = False
                residual_ledger = residual_ledger.add_coordinate(
                    f"ecpt-plan:{candidate.action.action_id}:remaining-budget:{resource}",
                    cost - remaining_budget[resource],
                    kind=CoordinateKind.RESIDUAL,
                )
        if not fits_budget:
            continue
        for resource, cost in candidate.resource_cost.items():
            if resource in remaining_budget:
                remaining_budget[resource] -= cost
        selected.append(candidate)
        residual_ledger = residual_ledger.combine(candidate.residual_ledger)
    if not state.constraint_frame.hard_domain_live():
        plan_reasons.append("phase-control plan blocked by hard-domain gate")
    if objective.horizon < 0:
        plan_reasons.append("phase-control objective horizon is negative")
    if objective.residual_budget < 0:
        plan_reasons.append("phase-control objective residual budget is negative")
    residual_sum = residual_ledger.burden_sum()
    if residual_sum > objective.residual_budget:
        plan_reasons.append("phase-control plan residual charge exceeds objective budget")
    missing = sorted(
        {obligation for candidate in selected for obligation in candidate.missing_obligations}
    )
    required_routes = sorted(
        {route for candidate in selected for route in candidate.required_evidence_routes}
    )
    selected_actions = [candidate.action for candidate in selected]
    controlled_graph = state.graph
    for action in selected_actions:
        controlled_graph = _candidate_graph(
            state.model_copy(update={"graph": controlled_graph}),
            action,
        )
    controlled = reachable_mass(controlled_graph)
    gain_total = sum(candidate.finite_proxy_gain for candidate in selected)
    score_total = sum(candidate.score for candidate in selected)
    accepted = bool(selected) and not plan_reasons
    operationally_usable = accepted and not missing and residual_sum <= objective.residual_budget
    plan = PhaseControlPlan(
        plan_id=f"phase-control-plan:{state.state_id}:{objective.objective_id}",
        objective_id=objective.objective_id,
        profile=profile,
        accepted=accepted,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        partial=not operationally_usable or len(selected) < len(actions),
        selected_actions=selected_actions,
        candidates=candidates,
        finite_proxy_gain_total=gain_total,
        score=score_total,
        required_evidence_routes=required_routes,
        missing_obligations=missing,
        reasons=sorted(set(plan_reasons)),
        residual_ledger=residual_ledger,
        operationally_usable=operationally_usable,
        settled=False,
    )
    return PhaseControlRunReport(
        report_id=f"phase-control-run:{state.state_id}:{objective.objective_id}",
        state_id=state.state_id,
        target_id=objective.target.target_id,
        plan=plan,
        baseline_reachable_mass=dict(sorted(baseline.items())),
        controlled_reachable_mass=dict(sorted(controlled.items())),
    )


def hitting_time_acceleration(
    baseline_hitting_times: Sequence[float],
    candidate_hitting_times: Sequence[float],
    *,
    residual: float = 0.0,
) -> float:
    """Positive lower bound means candidate hits faster on average."""

    if not baseline_hitting_times or not candidate_hitting_times:
        raise ValueError("hitting-time samples must not be empty")
    baseline = sum(baseline_hitting_times) / len(baseline_hitting_times)
    candidate = sum(candidate_hitting_times) / len(candidate_hitting_times)
    return baseline - candidate - abs(residual)


def speculative_raf_status(
    *,
    settled_before_ruin: bool,
    settled_before_expiration: bool,
    transition_ledger_present: bool,
    debt_ledger_present: bool,
    risk_ledger_present: bool,
) -> ClaimStatus:
    """Settlement-return speculative RAF status rule."""

    if settled_before_ruin and settled_before_expiration:
        return ClaimStatus.SETTLED
    if transition_ledger_present and debt_ledger_present and risk_ledger_present:
        return ClaimStatus.SPECULATIVE
    return ClaimStatus.DIAGNOSTIC


def check_raf_settlement(certificate: RAFSettlementCertificate) -> CheckResult:
    status = speculative_raf_status(
        settled_before_ruin=certificate.event_algebra.settles(certificate.event_id),
        settled_before_expiration=certificate.event_id
        not in certificate.event_algebra.expiration_events,
        transition_ledger_present=certificate.transition_ledger_present,
        debt_ledger_present=certificate.debt_ledger_present,
        risk_ledger_present=certificate.risk_ledger_present,
    )
    accepted = status in {ClaimStatus.SETTLED, ClaimStatus.SPECULATIVE}
    return CheckResult(
        accepted=accepted,
        status=status,
        reasons=[] if accepted else ["RAF settlement lacks required ledgers"],
        missing_obligations=[] if accepted else [f"raf-settlement:{certificate.certificate_id}"],
    )


def check_settlement_return_raf_certificate(
    certificate: SettlementReturnRAFCertificate,
) -> CheckResult:
    """Check finite settlement-return RAF ledgers and unresolved external events."""

    raf_result = check_raf_settlement(certificate.raf_certificate)
    reasons = list(raf_result.reasons)
    missing_ledgers = (
        certificate.required_ledger_obligations - certificate.present_ledger_obligations
    )
    if missing_ledgers:
        reasons.append("settlement-return RAF ledger obligations are missing")
    if certificate.external_settlement_obligations:
        reasons.append("settlement-return RAF has unresolved external obligations")
    if certificate.residual < 0:
        reasons.append("settlement-return RAF residual is negative")
    residual = raf_result.residual_ledger
    if certificate.residual:
        residual = residual.add_coordinate(
            f"settlement-return-raf:{certificate.certificate_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    missing = sorted(missing_ledgers | certificate.external_settlement_obligations)
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=missing,
        residual_ledger=residual.combine(residual_from_reasons("settlement-return-raf", reasons)),
    )


def check_cycle_monitor(certificate: CycleMonitorCertificate) -> CheckResult:
    reasons: list[str] = []
    if certificate.runtime_bound < 0:
        reasons.append("cycle monitor runtime bound must be nonnegative")
    if not certificate.cycle_ids.issubset(certificate.stopped_cycles):
        reasons.append("not all cycles are stopped")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"cycle-monitor:{certificate.monitor_id}",
        failure_reason="; ".join(reasons) if reasons else "cycle monitor failed",
        residual_ledger=residual_from_reasons("cycle-monitor", reasons),
    )


def backpressure_reserve_loss(arrivals: Sequence[float], service: Sequence[float]) -> float:
    """Cumulative queue reserve loss from positive arrival-service surplus."""

    if len(arrivals) != len(service):
        raise ValueError("arrivals and service must have equal length")
    backlog = 0.0
    worst = 0.0
    for arrival, served in zip(arrivals, service, strict=True):
        backlog = max(0.0, backlog + arrival - served)
        worst = max(worst, backlog)
    return worst


def bottleneck_shadow_price(release_delta: float, burden_delta: float) -> float:
    """Finite bottleneck shadow price as burden per positive release."""

    if release_delta <= 0:
        raise ValueError("release_delta must be positive")
    return burden_delta / release_delta


def check_resource_normalized_cut(cut: ResourceNormalizedCut) -> CheckResult:
    reasons: list[str] = []
    if cut.release_delta <= 0:
        reasons.append("resource-normalized cut requires positive release")
    if cut.resource_cost < 0:
        reasons.append("resource cost must be nonnegative")
    residual = residual_from_reasons("resource-cut", reasons)
    if not reasons:
        residual = residual.add_coordinate(
            f"resource-cut:{cut.cut_id}:shadow-price",
            bottleneck_shadow_price(cut.release_delta, cut.resource_cost),
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"resource-cut:{cut.cut_id}",
        failure_reason="; ".join(reasons) if reasons else "resource-normalized cut failed",
        residual_ledger=residual,
    )


def check_reachable_mass_recursion(
    certificate: ReachableMassRecursionCertificate,
) -> CheckResult:
    masses = reachable_mass(certificate.graph, status_floor=certificate.status_floor)
    reasons: list[str] = []
    for node in certificate.target_nodes:
        lower = certificate.lower_bounds.get(node, 0.0)
        if masses.get(node, 0.0) < lower:
            reasons.append(f"reachable mass lower bound fails for {node}")
    residual = residual_from_reasons("reachable-mass", reasons)
    for node in certificate.target_nodes:
        residual = residual.add_coordinate(
            f"reachable-mass:{node}:gap",
            max(0.0, certificate.lower_bounds.get(node, 0.0) - masses.get(node, 0.0)),
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"reachable-mass:{certificate.certificate_id}",
        failure_reason="; ".join(reasons) if reasons else "reachable mass recursion failed",
        residual_ledger=residual,
    )


def mean_field_euler_envelope(
    initial_state: Sequence[float],
    rate_field: Callable[[Sequence[float]], Sequence[float]],
    *,
    dt: float,
    steps: int,
    coupling_residual: float = 0.0,
) -> list[list[float]]:
    """Finite Euler envelope for an intervention-identified mean-field chart."""

    if dt <= 0 or steps < 0:
        raise ValueError("dt must be positive and steps must be nonnegative")
    state = [float(value) for value in initial_state]
    path = [state.copy()]
    for _ in range(steps):
        rates = list(rate_field(state))
        if len(rates) != len(state):
            raise ValueError("rate field dimension mismatch")
        state = [
            value + dt * rate - abs(coupling_residual)
            for value, rate in zip(state, rates, strict=True)
        ]
        path.append(state.copy())
    return path
