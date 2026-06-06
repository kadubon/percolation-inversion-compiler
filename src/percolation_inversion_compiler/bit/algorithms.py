"""Finite constructive algorithms for Bottleneck Inversion Theory."""

from __future__ import annotations

from collections.abc import Sequence
from math import exp

from percolation_inversion_compiler.bit.records import (
    CEGARRefinementTrace,
    CertificateCompilerRecord,
    EpigraphReleaseProgram,
    FusedGeometricComparisonCertificate,
    InterventionLaw,
    MartingaleDeficiencyCertificate,
    MartingalePartitionAudit,
    MechanismCube,
    MechanismCubeCertificate,
    MECRecord,
    OrderedPotentialCone,
    ProtocolObject,
    PullbackGluingWitness,
    SelectiveCUPCertificate,
    SelectivePotentialResult,
    SinkhornCertificate,
    StoppedEvidenceSheafCertificate,
    StoppedEvidenceWitness,
    UnitFunctorCertificate,
    VectorCompatibleFamily,
)
from percolation_inversion_compiler.core.algorithms import good_turing_unseen, trapezoid_integral
from percolation_inversion_compiler.core.checker import boolean_check_result, residual_from_reasons
from percolation_inversion_compiler.core.frontier import dominates
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


def check_protocol_object(protocol: ProtocolObject) -> CheckResult:
    reasons: list[str] = []
    if not protocol.protocol_id:
        reasons.append("protocol id is empty")
    if not protocol.candidate_universe:
        reasons.append("protocol candidate universe is empty")
    if not protocol.law_labels:
        reasons.append("protocol has no intervention law labels")
    if not protocol.validity_domains:
        reasons.append("protocol has no validity domains")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"protocol:{protocol.protocol_id}",
        failure_reason="; ".join(reasons) if reasons else "protocol object failed",
        residual_ledger=residual_from_reasons("bit-protocol", reasons),
    )


def check_intervention_law(law: InterventionLaw) -> CheckResult:
    reasons: list[str] = []
    if not law.support:
        reasons.append("intervention law support is empty")
    if set(law.probabilities) - law.support:
        reasons.append("intervention law probabilities mention states outside support")
    if any(value < 0 for value in law.probabilities.values()):
        reasons.append("intervention law probabilities must be nonnegative")
    total = sum(law.probabilities.values())
    if law.normalized and abs(total - 1.0) > 1e-9:
        reasons.append("normalized intervention law probabilities must sum to one")
    residual = residual_from_reasons("intervention-law", reasons)
    if law.probabilities:
        residual = residual.add_coordinate(
            f"intervention-law:{law.law_id}:normalization-gap",
            abs(total - 1.0),
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"intervention-law:{law.law_id}",
        failure_reason="; ".join(reasons) if reasons else "intervention law failed",
        residual_ledger=residual,
    )


def check_ordered_potential_cone(cone: OrderedPotentialCone) -> CheckResult:
    reasons: list[str] = []
    order_result = cone.product_order.check(partial=True)
    reasons.extend(order_result.reasons)
    if not cone.coordinate_kinds:
        reasons.append("ordered potential cone has no coordinates")
    if cone.unit_functor is not None:
        unit_result = check_unit_functor(cone.unit_functor)
        reasons.extend(unit_result.reasons)
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"potential-cone:{cone.cone_id}",
        failure_reason="; ".join(reasons) if reasons else "ordered potential cone failed",
        residual_ledger=residual_from_reasons("potential-cone", reasons),
    )


def check_vector_compatible_family(family: VectorCompatibleFamily) -> CheckResult:
    reasons: list[str] = []
    protocol_result = check_protocol_object(family.protocol)
    cone_result = check_ordered_potential_cone(family.potential_cone)
    reasons.extend(protocol_result.reasons)
    reasons.extend(cone_result.reasons)
    protocol_laws = family.protocol.law_labels
    seen_laws = {law.law_id for law in family.laws}
    if seen_laws - protocol_laws:
        reasons.append("family contains laws absent from protocol object")
    for law in family.laws:
        reasons.extend(check_intervention_law(law).reasons)
    if family.report_mask - set(family.potential_cone.coordinate_kinds):
        reasons.append("report mask contains coordinates absent from potential cone")
    try:
        family.dependency_graph.topological_order()
    except ValueError as exc:
        reasons.append(str(exc))
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"vector-compatible-family:{family.family_id}",
        failure_reason="; ".join(reasons) if reasons else "vector-compatible family failed",
        residual_ledger=residual_from_reasons("vector-family", reasons),
    )


def check_pullback_gluing(witness: PullbackGluingWitness) -> CheckResult:
    reasons: list[str] = []
    if not witness.local_sections:
        reasons.append("pullback gluing witness has no local sections")
    expected = set().union(*witness.local_sections.values()) if witness.local_sections else set()
    if witness.glued_section != expected:
        reasons.append("glued section does not equal the union of local sections")
    for overlap_key, overlap_values in witness.overlaps.items():
        left, sep, right = overlap_key.partition("|")
        if not sep or left not in witness.local_sections or right not in witness.local_sections:
            reasons.append(f"overlap {overlap_key} references unknown local sections")
            continue
        actual = witness.local_sections[left] & witness.local_sections[right]
        if actual != overlap_values:
            reasons.append(f"overlap {overlap_key} is not a finite pullback intersection")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"pullback-gluing:{witness.witness_id}",
        failure_reason="; ".join(reasons) if reasons else "pullback gluing failed",
        residual_ledger=residual_from_reasons("pullback-gluing", reasons),
    )


def check_stopped_evidence_sheaf(
    witnesses: Sequence[StoppedEvidenceWitness],
    gluing_witness: PullbackGluingWitness | None = None,
) -> CheckResult:
    """Check finite gluing shape for a stopped evidence sheaf."""

    if not witnesses:
        return boolean_check_result(
            accepted=False,
            obligation_id="stopped-evidence:witnesses",
            failure_reason="at least one stopped evidence witness is required",
        )
    first = witnesses[0]
    accepted = all(
        witness.probability_space == first.probability_space
        and witness.stopping_time == first.stopping_time
        and witness.ledger_id == first.ledger_id
        for witness in witnesses
    )
    result = boolean_check_result(
        accepted=accepted,
        obligation_id="stopped-evidence:shared-interface",
        failure_reason=(
            "stopped evidence witnesses do not share probability space, stopping time, and ledger"
        ),
    )
    if gluing_witness is None or not result.accepted:
        return result
    gluing_result = check_pullback_gluing(gluing_witness)
    return result.model_copy(
        update={
            "accepted": result.accepted and gluing_result.accepted,
            "status": ClaimStatus.SETTLED if gluing_result.accepted else ClaimStatus.DIAGNOSTIC,
            "reasons": result.reasons + gluing_result.reasons,
            "missing_obligations": result.missing_obligations + gluing_result.missing_obligations,
            "residual_ledger": result.residual_ledger.combine(gluing_result.residual_ledger),
        }
    )


def check_stopped_evidence_sheaf_certificate(
    certificate: StoppedEvidenceSheafCertificate,
) -> CheckResult:
    """Check theorem-level stopped evidence sheaf gluing and missing sections."""

    result = check_stopped_evidence_sheaf(certificate.witnesses, certificate.gluing_witness)
    reasons = list(result.reasons)
    if certificate.missing_sections:
        reasons.append("stopped evidence sheaf has missing sections")
    if certificate.residual < 0:
        reasons.append("stopped evidence sheaf residual is negative")
    residual = result.residual_ledger
    if certificate.residual:
        residual = residual.add_coordinate(
            f"stopped-evidence-sheaf:{certificate.certificate_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    residual = residual.combine(residual_from_reasons("stopped-evidence-sheaf", reasons))
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=(
            [] if not reasons else [f"stopped-evidence-sheaf:{certificate.certificate_id}"]
        ),
        residual_ledger=residual,
    )


def stopped_evidence_sheaf_accepts(witnesses: Sequence[StoppedEvidenceWitness]) -> bool:
    """Accept when all witness components share the stopped event interface."""

    return check_stopped_evidence_sheaf(witnesses).accepted


def check_unit_functor(certificate: UnitFunctorCertificate) -> CheckResult:
    """Check monotone unit conversion audit as a structured judgment."""

    reasons: list[str] = []
    if not certificate.monotone:
        reasons.append("unit functor is not declared monotone")
    if any(conversion.factor <= 0 for conversion in certificate.conversions):
        reasons.append("unit conversion factors must be positive")
    if not certificate.ordered_units:
        reasons.append("ordered unit set is empty")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="unit-functor:audit",
        failure_reason="; ".join(reasons) if reasons else "unit functor audit failed",
        residual_ledger=residual_from_reasons("unit-functor", reasons),
    )


def unit_functor_accepts(certificate: UnitFunctorCertificate) -> bool:
    """Check monotone unit conversion audit."""

    return check_unit_functor(certificate).accepted


def check_martingale_partition_audit(audit: MartingalePartitionAudit) -> CheckResult:
    """Check finite martingale partition audit shape and residual charges."""

    reasons: list[str] = []
    if not audit.block_bounds:
        reasons.append("martingale partition has no finite block lower bounds")
    if audit.uncarved_splits:
        reasons.append("martingale partition has uncarved splits")
    if audit.boundary_drift < 0 or audit.selection_charge < 0 or audit.confidence_radius < 0:
        reasons.append("martingale audit charges must be nonnegative")
    residual = residual_from_reasons("martingale-partition", reasons)
    if audit.boundary_drift or audit.selection_charge or audit.confidence_radius:
        residual = residual.add_coordinate(
            "martingale-partition:charge",
            audit.boundary_drift + audit.selection_charge + audit.confidence_radius,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="martingale-partition:audit",
        failure_reason="; ".join(reasons) if reasons else "martingale partition audit failed",
        residual_ledger=residual,
    )


def martingale_partition_audit_accepts(audit: MartingalePartitionAudit) -> bool:
    """Check finite martingale partition audit shape."""

    return check_martingale_partition_audit(audit).accepted


def check_epigraph_release_program(program: EpigraphReleaseProgram) -> CheckResult:
    """Check finite exactness-certified release program premises."""

    reasons: list[str] = []
    if not program.slater_witness:
        reasons.append("Slater or finite-duality witness is missing")
    if not program.unit_ledger_accepted:
        reasons.append("unit ledger is not accepted")
    if program.inner_primal_value > program.outer_dual_value:
        reasons.append("inner primal value exceeds outer dual value")
    if program.exactness_residual < 0:
        reasons.append("exactness residual must be nonnegative")
    residual = residual_from_reasons("epigraph-release", reasons)
    if program.exactness_residual:
        residual = residual.add_coordinate(
            "epigraph-release:exactness",
            program.exactness_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="epigraph-release:program",
        failure_reason="; ".join(reasons) if reasons else "epigraph release program failed",
        residual_ledger=residual,
    )


def epigraph_release_program_accepts(program: EpigraphReleaseProgram) -> bool:
    """Check finite exactness-certified release program premises."""

    return check_epigraph_release_program(program).accepted


def check_cegar_refinement_trace(trace: CEGARRefinementTrace) -> CheckResult:
    """Check finite CEGAR trace has no uncovered counterexamples."""

    reasons: list[str] = []
    if not 0.0 <= trace.contraction <= 1.0:
        reasons.append("CEGAR contraction must be in [0, 1]")
    if trace.counterexamples:
        reasons.append("CEGAR trace has uncovered counterexamples")
    if trace.barrier_floor < 0:
        reasons.append("barrier floor must be nonnegative")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="cegar:refinement-trace",
        failure_reason="; ".join(reasons) if reasons else "CEGAR refinement trace failed",
        residual_ledger=residual_from_reasons("cegar", reasons),
    )


def cegar_refinement_trace_accepts(trace: CEGARRefinementTrace) -> bool:
    """Check finite CEGAR trace has no uncovered counterexamples."""

    return check_cegar_refinement_trace(trace).accepted


def selective_potential(
    lower_process: dict[str, float],
    selection_charge: dict[str, float],
    *,
    report_mask: set[str] | None = None,
    unit_audit: set[str] | None = None,
) -> SelectivePotentialResult:
    """Report only unit-audited lower coordinates after finite charges."""

    report_mask = report_mask or set(lower_process)
    unit_audit = unit_audit or set(lower_process)
    reported: dict[str, float] = {}
    unreported: dict[str, str] = {}
    charges = Ledger()
    for coordinate, lower in lower_process.items():
        charge = selection_charge.get(coordinate, 0.0)
        charges = charges.add_coordinate(coordinate, charge, kind=CoordinateKind.RESOURCE)
        if coordinate not in report_mask:
            unreported[coordinate] = "masked"
            continue
        if coordinate not in unit_audit:
            unreported[coordinate] = "unit-audit-missing"
            continue
        adjusted = lower - charge
        if adjusted <= 0:
            unreported[coordinate] = "nonpositive-after-charge"
            continue
        reported[coordinate] = adjusted
    return SelectivePotentialResult(reported=reported, unreported=unreported, charges=charges)


def check_selective_cup_certificate(certificate: SelectiveCUPCertificate) -> CheckResult:
    """Check unit-compatible selective CUP reporting against a finite family."""

    family_result = check_vector_compatible_family(certificate.family)
    reasons = list(family_result.reasons)
    if certificate.residual < 0:
        reasons.append("selective CUP residual is negative")
    if certificate.required_reported - certificate.unit_audit:
        reasons.append("selective CUP required coordinates lack unit audit")
    result = selective_potential(
        certificate.lower_process,
        certificate.selection_charge,
        report_mask=certificate.report_mask or certificate.family.report_mask,
        unit_audit=certificate.unit_audit,
    )
    missing_required = certificate.required_reported - set(result.reported)
    if missing_required:
        reasons.append("selective CUP required coordinates were not reported")
    residual = family_result.residual_ledger.combine(result.charges)
    if certificate.residual:
        residual = residual.add_coordinate(
            f"selective-cup:{certificate.certificate_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    residual = residual.combine(residual_from_reasons("selective-cup", reasons))
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=sorted(missing_required),
        residual_ledger=residual,
    )


def martingale_partition_lower_bound(
    block_lower_bounds: Sequence[float],
    *,
    boundary_drift: float = 0.0,
    selection_charge: float = 0.0,
    confidence_radius: float = 0.0,
) -> float:
    """Finite martingale-partition lower bound with explicit charges."""

    if not block_lower_bounds:
        raise ValueError("at least one block lower bound is required")
    return max(
        0.0,
        sum(block_lower_bounds) - boundary_drift - selection_charge - confidence_radius,
    )


def check_martingale_deficiency_certificate(
    certificate: MartingaleDeficiencyCertificate,
) -> CheckResult:
    """Check finite martingale deficiency lower mass and audit residuals."""

    audit_result = check_martingale_partition_audit(certificate.audit)
    reasons = list(audit_result.reasons)
    if certificate.lower_mass_floor < 0:
        reasons.append("martingale lower mass floor is negative")
    if certificate.residual_tolerance < 0:
        reasons.append("martingale residual tolerance is negative")
    lower_mass = 0.0
    if certificate.audit.block_bounds:
        lower_mass = martingale_partition_lower_bound(
            certificate.audit.block_bounds,
            boundary_drift=certificate.audit.boundary_drift,
            selection_charge=certificate.audit.selection_charge,
            confidence_radius=certificate.audit.confidence_radius,
        )
    gap = max(0.0, certificate.lower_mass_floor - lower_mass)
    if gap > certificate.residual_tolerance:
        reasons.append("martingale deficiency lower mass is below floor")
    residual = audit_result.residual_ledger.add_coordinate(
        f"martingale-deficiency:{certificate.certificate_id}:gap",
        gap,
        kind=CoordinateKind.RESIDUAL,
    )
    residual = residual.combine(residual_from_reasons("martingale-deficiency", reasons))
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=(
            [] if not reasons else [f"martingale-deficiency:{certificate.certificate_id}"]
        ),
        residual_ledger=residual,
    )


def mechanism_non_substitution(cube: MechanismCube) -> bool:
    """Check finite mechanism-factorized non-substitution premises."""

    return check_mechanism_cube(cube).accepted


def check_mechanism_cube(cube: MechanismCube) -> CheckResult:
    """Check mechanism-factorized non-substitution as a finite certificate."""

    accepted = (
        cube.factorization_rank > 0
        and cube.negative_control_rank >= cube.factorization_rank
        and cube.proximal_bridge
        and cube.triangular_commutator_zero
    )
    reasons: list[str] = []
    if cube.factorization_rank <= 0:
        reasons.append("factorization rank must be positive")
    if cube.negative_control_rank < cube.factorization_rank:
        reasons.append("negative controls do not cover factorization rank")
    if not cube.proximal_bridge:
        reasons.append("proximal bridge witness is absent")
    if not cube.triangular_commutator_zero:
        reasons.append("triangular commutator is not certified zero")
    return boolean_check_result(
        accepted=accepted,
        obligation_id="mechanism-cube:non-substitution",
        failure_reason="; ".join(reasons) if reasons else "mechanism cube failed",
        residual_ledger=residual_from_reasons("mechanism-cube", reasons),
    )


def check_mechanism_cube_certificate(certificate: MechanismCubeCertificate) -> CheckResult:
    """Check release/null-control compatibility for a mechanism cube."""

    reasons: list[str] = []
    cube_result = check_mechanism_cube(certificate.cube)
    reasons.extend(cube_result.reasons)
    channels = {
        certificate.cube.path_channel,
        certificate.cube.log_channel,
        certificate.cube.observation_channel,
    }
    if certificate.release_channel not in channels:
        reasons.append("release channel is not a cube channel")
    if certificate.negative_control_channels - channels:
        reasons.append("negative controls reference channels outside the cube")
    if not certificate.paired_null_witnesses:
        reasons.append("mechanism cube lacks paired null witnesses")
    if certificate.non_substitution_residual < 0:
        reasons.append("non-substitution residual is negative")
    if not certificate.accepted:
        reasons.append("mechanism cube certificate is not accepted")
    residual = cube_result.residual_ledger
    if certificate.non_substitution_residual:
        residual = residual.add_coordinate(
            f"mechanism-cube:{certificate.certificate_id}",
            certificate.non_substitution_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"mechanism-cube:{certificate.certificate_id}",
        failure_reason="; ".join(reasons) if reasons else "mechanism cube certificate failed",
        residual_ledger=residual.combine(residual_from_reasons("mechanism-cube", reasons)),
    )


def exactness_release_interval(
    inner_primal_value: float,
    outer_dual_value: float,
    *,
    exactness_residual: float = 0.0,
    unit_charge: float = 0.0,
) -> tuple[float, float]:
    """Epigraph release interval under finite primal/dual witnesses."""

    lower = inner_primal_value - exactness_residual - unit_charge
    upper = outer_dual_value + exactness_residual + unit_charge
    if lower > upper:
        raise ValueError("release interval is inconsistent")
    return lower, upper


def good_turing_frontier_release(
    species_counts: Sequence[int],
    *,
    recall_floor: float = 0.0,
    duplicate_rate: float = 0.0,
    false_entry_rate: float = 0.0,
) -> float:
    """Unseen-frontier release with duplicate and false-entry charges."""

    unseen = good_turing_unseen(species_counts)
    return max(0.0, unseen * max(0.0, recall_floor) - duplicate_rate - false_entry_rate)


def anchor_transfer_bound(
    source_interval: tuple[float, float],
    *,
    transfer_band: float,
    heterogeneity: float = 0.0,
) -> tuple[float, float]:
    """Cross-validated anchor transfer interval."""

    lower, upper = source_interval
    charge = abs(transfer_band) + abs(heterogeneity)
    return lower - charge, upper + charge


def dynamic_regime_arrival_gain(
    times: Sequence[float],
    intervention_cdf: Sequence[float],
    baseline_cdf: Sequence[float],
    *,
    bridge_residual: float = 0.0,
    censoring_residual: float = 0.0,
) -> float:
    """Arrival-gain lower bound by integrating finite CDF dominance."""

    if len(intervention_cdf) != len(baseline_cdf):
        raise ValueError("cdf sequences must have the same length")
    dominance = [
        max(0.0, intervention - baseline)
        for intervention, baseline in zip(intervention_cdf, baseline_cdf, strict=True)
    ]
    return max(0.0, trapezoid_integral(times, dominance) - bridge_residual - censoring_residual)


def cegar_barrier_bound(
    initial_distance: float,
    contraction: float,
    steps: int,
    *,
    barrier_floor: float = 0.0,
    uncovered_counterexamples: int = 0,
) -> float:
    """Finite CEGAR simulation-barrier transfer bound."""

    if uncovered_counterexamples:
        raise ValueError("uncovered counterexamples require refinement")
    if not 0.0 <= contraction <= 1.0:
        raise ValueError("contraction must be in [0, 1]")
    return max(barrier_floor, initial_distance * (contraction**steps))


def sinkhorn_plan(
    source: Sequence[float],
    target: Sequence[float],
    cost: Sequence[Sequence[float]],
    *,
    epsilon: float = 1.0,
    iterations: int = 200,
) -> list[list[float]]:
    """Small pure-Python finite Sinkhorn interface for release-duality tests."""

    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    if not source or not target:
        raise ValueError("source and target must not be empty")
    if len(cost) != len(source) or any(len(row) != len(target) for row in cost):
        raise ValueError("cost shape must match source x target")
    source_total = sum(source)
    target_total = sum(target)
    if source_total <= 0 or target_total <= 0:
        raise ValueError("source and target masses must be positive")
    a = [value / source_total for value in source]
    b = [value / target_total for value in target]
    kernel = [[exp(-entry / epsilon) for entry in row] for row in cost]
    u = [1.0 for _ in a]
    v = [1.0 for _ in b]
    for _ in range(iterations):
        for i, row in enumerate(kernel):
            denom = sum(row[j] * v[j] for j in range(len(b)))
            u[i] = a[i] / denom if denom > 0 else 0.0
        for j in range(len(b)):
            denom = sum(u[i] * kernel[i][j] for i in range(len(a)))
            v[j] = b[j] / denom if denom > 0 else 0.0
    return [[u[i] * kernel[i][j] * v[j] for j in range(len(b))] for i in range(len(a))]


def sinkhorn_residual(
    plan: Sequence[Sequence[float]],
    source: Sequence[float],
    target: Sequence[float],
) -> float:
    """Return finite marginal mismatch for a Sinkhorn transport plan."""

    if len(plan) != len(source) or any(len(row) != len(target) for row in plan):
        raise ValueError("plan shape must match source x target")
    source_total = sum(source)
    target_total = sum(target)
    if source_total <= 0 or target_total <= 0:
        raise ValueError("source and target masses must be positive")
    normalized_source = [value / source_total for value in source]
    normalized_target = [value / target_total for value in target]
    row_error = sum(abs(sum(row) - normalized_source[i]) for i, row in enumerate(plan))
    col_error = 0.0
    for j, expected in enumerate(normalized_target):
        col_error += abs(sum(row[j] for row in plan) - expected)
    return row_error + col_error


def check_sinkhorn_plan(
    plan: Sequence[Sequence[float]],
    source: Sequence[float],
    target: Sequence[float],
    *,
    tolerance: float = 1e-6,
) -> CheckResult:
    """Check that a finite Sinkhorn plan has acceptable marginal residual."""

    residual_value = sinkhorn_residual(plan, source, target)
    residual = Ledger().add_coordinate(
        "sinkhorn:marginal-residual",
        residual_value,
        kind=CoordinateKind.RESIDUAL,
    )
    return CheckResult(
        accepted=residual_value <= tolerance,
        status=ClaimStatus.SETTLED if residual_value <= tolerance else ClaimStatus.DIAGNOSTIC,
        reasons=(
            [] if residual_value <= tolerance else ["Sinkhorn marginal residual exceeds tolerance"]
        ),
        missing_obligations=[] if residual_value <= tolerance else ["sinkhorn:marginal-residual"],
        residual_ledger=residual,
    )


def check_sinkhorn_certificate(certificate: SinkhornCertificate) -> CheckResult:
    marginal = check_sinkhorn_plan(
        certificate.plan,
        certificate.source,
        certificate.target,
        tolerance=certificate.marginal_tolerance,
    )
    reasons = list(marginal.reasons)
    if certificate.duality_gap < 0 or certificate.solver_gap < 0:
        reasons.append("Sinkhorn gaps must be nonnegative")
    if certificate.unit_ledger_charge < 0:
        reasons.append("unit ledger charge must be nonnegative")
    residual = marginal.residual_ledger
    for name, value in [
        ("sinkhorn:duality-gap", certificate.duality_gap),
        ("sinkhorn:solver-gap", certificate.solver_gap),
        ("sinkhorn:unit-ledger-charge", certificate.unit_ledger_charge),
    ]:
        residual = residual.add_coordinate(name, value, kind=CoordinateKind.RESIDUAL)
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=[] if not reasons else ["sinkhorn:certificate"],
        residual_ledger=residual,
    )


def check_fused_geometric_comparison(
    certificate: FusedGeometricComparisonCertificate,
) -> CheckResult:
    """Check finite fused-geometric comparison residuals."""

    reasons: list[str] = []
    if not certificate.source_nodes:
        reasons.append("fused comparison has no source nodes")
    if not certificate.target_nodes:
        reasons.append("fused comparison has no target nodes")
    if not certificate.coupling:
        reasons.append("fused comparison has no coupling witness")
    for source, target, _weight in certificate.coupling:
        if source not in certificate.source_nodes or target not in certificate.target_nodes:
            reasons.append("fused comparison coupling references an unknown node")
            break
    if any(weight < 0 for _source, _target, weight in certificate.coupling):
        reasons.append("fused comparison coupling has negative mass")
    if (
        certificate.geometry_distortion < 0
        or certificate.feature_distortion < 0
        or certificate.marginal_residual < 0
        or certificate.solver_gap < 0
        or certificate.distortion_upper_bound < 0
    ):
        reasons.append("fused comparison residuals must be nonnegative")
    total_distortion = (
        certificate.geometry_distortion
        + certificate.feature_distortion
        + certificate.marginal_residual
        + certificate.solver_gap
    )
    if total_distortion > certificate.distortion_upper_bound:
        reasons.append("fused comparison distortion exceeds certified upper bound")
    if not certificate.accepted:
        reasons.append("fused comparison certificate is not accepted")
    residual = residual_from_reasons("fused-geometric-comparison", reasons)
    if total_distortion:
        residual = residual.add_coordinate(
            f"fused-geometric-comparison:{certificate.certificate_id}",
            total_distortion,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"fused-geometric-comparison:{certificate.certificate_id}",
        failure_reason=("; ".join(reasons) if reasons else "fused geometric comparison failed"),
        residual_ledger=residual,
    )


def check_certificate_compiler(record: CertificateCompilerRecord) -> CheckResult:
    reasons: list[str] = []
    try:
        record.dependency_graph.topological_order()
    except ValueError as exc:
        reasons.append(str(exc))
    known_nodes = record.dependency_graph.nodes() | record.witness_nodes | record.coordinate_nodes
    for label_map_name, label_map in [
        ("law", record.law_labels),
        ("unit", record.unit_labels),
        ("resource", record.resource_labels),
    ]:
        if set(label_map) - known_nodes:
            reasons.append(f"{label_map_name} labels mention unknown compiler nodes")
    for node in record.coordinate_nodes:
        missing = record.dependency_graph.missing_dependencies(record.accepted_nodes).get(node)
        if missing:
            reasons.append(f"coordinate {node} has missing predecessors: {sorted(missing)}")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"certificate-compiler:{record.compiler_id}",
        failure_reason="; ".join(reasons) if reasons else "certificate compiler failed",
        residual_ledger=residual_from_reasons("certificate-compiler", reasons),
    )


def compiler_invalidation_reachability(
    record: CertificateCompilerRecord,
    invalidated_node: str,
) -> set[str]:
    """Return coordinates affected by invalidating one compiler node."""

    reachable = record.dependency_graph.reachable_from(invalidated_node)
    return reachable & record.coordinate_nodes


def minimal_effective_conditions(records: Sequence[MECRecord]) -> list[MECRecord]:
    """Finite MEC frontier extraction as a computable antichain."""

    accepted = [
        record
        for record in records
        if record.positive_release and record.mechanism_factorized_non_substitution
    ]
    frontier: list[MECRecord] = []
    for candidate in accepted:
        if any(dominates(other, candidate) for other in accepted):
            continue
        frontier.append(candidate)
    return sorted(frontier, key=lambda record: record.record_id)
