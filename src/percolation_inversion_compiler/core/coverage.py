"""Theory coverage records and conservative implementation classification."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CoverageStatus(StrEnum):
    IMPLEMENTED_CONSTRUCTIVE = "implemented_constructive"
    IMPLEMENTED_CHECKER = "implemented_checker"
    IMPLEMENTED_SCHEMA = "implemented_schema"
    PARTIAL = "partial"
    EXTERNAL_OBLIGATION = "external_obligation"
    UNSUPPORTED = "unsupported"


class ImplementationMaturity(StrEnum):
    IMPLEMENTED_VERIFIED_ALGORITHM = "implemented_verified_algorithm"
    IMPLEMENTED_SHAPE_CHECKER = "implemented_shape_checker"
    IMPLEMENTED_SCHEMA_ONLY = "implemented_schema_only"
    EXTERNAL_CONTRACT_ONLY = "external_contract_only"
    SNAPSHOT_METADATA_ONLY = "snapshot_metadata_only"
    UNSUPPORTED_NO_INTERFACE = "unsupported_no_interface"


class ImplementationMaturityRecord(BaseModel):
    """Portable wrapper schema for implementation maturity enum values."""

    implementation_maturity: ImplementationMaturity


def maturity_from_coverage(status: CoverageStatus) -> ImplementationMaturity:
    if status == CoverageStatus.IMPLEMENTED_CONSTRUCTIVE:
        return ImplementationMaturity.IMPLEMENTED_VERIFIED_ALGORITHM
    if status == CoverageStatus.IMPLEMENTED_CHECKER:
        return ImplementationMaturity.IMPLEMENTED_SHAPE_CHECKER
    if status == CoverageStatus.IMPLEMENTED_SCHEMA:
        return ImplementationMaturity.IMPLEMENTED_SCHEMA_ONLY
    if status == CoverageStatus.EXTERNAL_OBLIGATION:
        return ImplementationMaturity.EXTERNAL_CONTRACT_ONLY
    if status == CoverageStatus.PARTIAL:
        return ImplementationMaturity.SNAPSHOT_METADATA_ONLY
    return ImplementationMaturity.UNSUPPORTED_NO_INTERFACE


class TheoryItem(BaseModel):
    item_id: str
    artifact: str
    kind: str
    label: str
    line_number: int
    section: str | None = None
    coverage_status: CoverageStatus = CoverageStatus.UNSUPPORTED
    implementation_maturity: ImplementationMaturity = (
        ImplementationMaturity.UNSUPPORTED_NO_INTERFACE
    )
    implementation_refs: list[str] = Field(default_factory=list)
    checker_refs: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    proof_obligation_ids: list[str] = Field(default_factory=list)
    residual_coordinates: list[str] = Field(default_factory=list)
    external_failure_modes: list[str] = Field(default_factory=list)
    obligation_category: str | None = None
    verifier_route: str | None = None
    verifier_contract: dict[str, object] = Field(default_factory=dict)
    accepted_evidence_kind: list[str] = Field(default_factory=list)
    residual_policy: str | None = None
    safe_default: str | None = None
    failure_modes: list[str] = Field(default_factory=list)


class TheoryCoverageRecord(BaseModel):
    source: str
    artifact: str
    definitions: int = 0
    claims: int = 0
    mr_records: int = 0
    items: list[TheoryItem] = Field(default_factory=list)

    def counts_by_status(self) -> dict[str, int]:
        counts = {status.value: 0 for status in CoverageStatus}
        for item in self.items:
            counts[item.coverage_status.value] += 1
        return counts

    def counts_by_maturity(self) -> dict[str, int]:
        counts = {maturity.value: 0 for maturity in ImplementationMaturity}
        for item in self.items:
            counts[item.implementation_maturity.value] += 1
        return counts


class TheoryImplementationRecord(BaseModel):
    """Portable implementation mapping for one finite theory item."""

    item_id: str
    artifact: str
    label: str
    coverage_status: CoverageStatus
    implementation_maturity: ImplementationMaturity = (
        ImplementationMaturity.UNSUPPORTED_NO_INTERFACE
    )
    implementation_ref: str | None = None
    checker_ref: str | None = None
    schema_ref: str | None = None
    implementation_refs: list[str] = Field(default_factory=list)
    checker_refs: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    proof_obligation_ids: list[str] = Field(default_factory=list)
    residual_coordinates: list[str] = Field(default_factory=list)
    external_failure_modes: list[str] = Field(default_factory=list)
    obligation_category: str | None = None
    verifier_route: str | None = None
    verifier_contract: dict[str, object] = Field(default_factory=dict)
    accepted_evidence_kind: list[str] = Field(default_factory=list)
    residual_policy: str | None = None
    safe_default: str | None = None
    failure_modes: list[str] = Field(default_factory=list)


class ExternalObligationCatalog(BaseModel):
    """Catalog of non-finite or domain-specific obligations."""

    artifact: str
    obligations: list[TheoryImplementationRecord] = Field(default_factory=list)
    category_summary: dict[str, int] = Field(default_factory=dict)
    verifier_route_summary: dict[str, int] = Field(default_factory=dict)


_IMPLEMENTED: dict[str, tuple[CoverageStatus, str]] = {
    "observation consistency": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "trc.observation_consistency_residual",
    ),
    "resource-efficiency": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "trc.resource_efficiency_selection",
    ),
    "tolerance-aware executable trace": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_trace_normal_form",
    ),
    "executable trace normal form": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_trace_normal_form",
    ),
    "typed trace": (CoverageStatus.IMPLEMENTED_SCHEMA, "trc.ExecutableTraceNormalForm"),
    "typed tolerance": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "trc.finite_tolerance_allocation",
    ),
    "tolerance-cost": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "trc.finite_tolerance_allocation",
    ),
    "network-calculus": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "trc.network_calculus_bounds"),
    "ordered-semiring": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "trc.semiring_path_product"),
    "semiring": (CoverageStatus.IMPLEMENTED_CHECKER, "core.AlgebraLawCertificate"),
    "trace-indexed resource-flow": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_resource_flow",
    ),
    "resource-flow": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_resource_flow"),
    "grid epsilon": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "core.archive_with_truncation"),
    "budgeted truncation": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "core.archive_with_truncation",
    ),
    "good--turing": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "bit.good_turing_frontier_release"),
    "unseen-frontier": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.good_turing_frontier_release",
    ),
    "minimal effective": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.minimal_effective_conditions",
    ),
    "finite mec": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "bit.minimal_effective_conditions"),
    "split-certified": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.split_certified_quotient_error",
    ),
    "finite gibbs": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "ecpt.finite_gibbs_phase_response"),
    "hitting-time": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "ecpt.hitting_time_acceleration"),
    "backpressure": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "ecpt.backpressure_reserve_loss"),
    "bottleneck shadow": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "ecpt.bottleneck_shadow_price"),
    "no status promotion": (CoverageStatus.IMPLEMENTED_CHECKER, "core.StatusRule"),
    "status algebra": (CoverageStatus.IMPLEMENTED_CHECKER, "core.StatusRule"),
    "claim extractor": (CoverageStatus.IMPLEMENTED_CHECKER, "core.ExtractorOutput"),
    "typed extraction judgment": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.Judgment"),
    "checker": (CoverageStatus.IMPLEMENTED_CHECKER, "core.CheckerContext"),
    "registry": (CoverageStatus.IMPLEMENTED_CHECKER, "core.ProjectionAudit"),
    "capsule projection": (CoverageStatus.IMPLEMENTED_CHECKER, "core.ProjectionAudit"),
    "machine-readable claim record": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.ClaimRecord"),
    "certificate schema": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.CertificateFamily"),
    "operable certificate shell": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.CertificateShell"),
    "ecpt certificate": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.Certificate"),
    "trc certificate": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.Certificate"),
    "certificate compiler": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.CertificateCompilerRecord"),
    "compiler preservation": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_certificate_compiler"),
    "protocol object": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_protocol_object"),
    "intervention law": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_intervention_law"),
    "unit functor": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_unit_functor"),
    "ordered potential cone": (CoverageStatus.IMPLEMENTED_SCHEMA, "bit.OrderedPotentialCone"),
    "vector compatible": (CoverageStatus.IMPLEMENTED_SCHEMA, "bit.VectorCompatibleFamily"),
    "plain evidence products": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_stopped_evidence_sheaf",
    ),
    "stopped evidence sheaf": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_stopped_evidence_sheaf_certificate",
    ),
    "unit-compatible selective cup": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_selective_cup_certificate",
    ),
    "partition lower mass": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.martingale_partition_lower_bound",
    ),
    "martingale partition deficiency": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_martingale_deficiency_certificate",
    ),
    "fixed partition certificate": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_martingale_partition_audit",
    ),
    "mechanism-controlled release": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_mechanism_cube_certificate",
    ),
    "paired null certificate": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_mechanism_cube_certificate",
    ),
    "mechanism-factorized channel cube": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_mechanism_cube",
    ),
    "mechanism-factorized non-substitution": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_mechanism_cube_certificate",
    ),
    "exactness-certified": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_epigraph_release_program",
    ),
    "cross-validated release score": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.anchor_transfer_bound",
    ),
    "fixed-candidate acceleration identity": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.dynamic_regime_arrival_gain",
    ),
    "cegar simulation": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_cegar_refinement_trace"),
    "selective potential": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "bit.selective_potential"),
    "dynamic-regime": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.dynamic_regime_arrival_gain",
    ),
    "transition-table barrier": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "bit.cegar_barrier_bound",
    ),
    "anchor transfer": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "bit.anchor_transfer_bound"),
    "geometric fused comparison": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "bit.check_fused_geometric_comparison",
    ),
    "sinkhorn": (CoverageStatus.IMPLEMENTED_CHECKER, "bit.check_sinkhorn_plan"),
    "capability packet": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.CapabilityPacket"),
    "capability-state vector": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_capability_state_vector",
    ),
    "diagnostic order": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.DiagnosticOrder"),
    "waste, false liquidity, obstruction, and paralysis": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "ecpt.DiagnosticOrder",
    ),
    "baseline protocol": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.ObservationProtocol"),
    "protocol functor": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_protocol_functor_certificate",
    ),
    "protocol-functor soundness": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_protocol_functor_certificate",
    ),
    "finite and thermodynamic phase-control system": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_finite_phase_control_certificate",
    ),
    "control surface and phase response": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_phase_control_envelope",
    ),
    "certified phase-response control step": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_phase_control_envelope",
    ),
    "global free-energy activation": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_activation_threshold_certificate",
    ),
    "activation construction certificate": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_activation_construction",
    ),
    "activation field": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_activation_threshold_certificate",
    ),
    "activated closure law": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.reachable_mass",
    ),
    "execution-available hyperpath": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.reachable_mass",
    ),
    "seed and cyclic support": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_cycle_monitor",
    ),
    "finite quotient construction interface": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.split_certified_quotient_error",
    ),
    "duplicate mass": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_capability_state_vector",
    ),
    "no probabilistic duplicate inflation": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_capability_state_vector",
    ),
    "stratified statistical packet atlas": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_packet_atlas",
    ),
    "stratified information-projection quotient": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_information_projection_quotient",
    ),
    "information-projection distortion": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_information_projection_quotient",
    ),
    "edge types": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.CapabilityEdge"),
    "hard-domain edge": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_constraint_frame"),
    "constraint-band requirement": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_constraint_frame",
    ),
    "postcondition obligations": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "ecpt.PostconditionObligation",
    ),
    "constructed path-law response": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_path_law_policy",
    ),
    "operable action correspondence": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_controlled_transition",
    ),
    "inner-kernel invariance": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_inner_viability_kernel",
    ),
    "self-normalized margin witness": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.self_normalized_margin_risk",
    ),
    "target hitting time": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "ecpt.hitting_time_acceleration",
    ),
    "settlement-return": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_settlement_return_raf_certificate",
    ),
    "and-support finite-size": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_activation_threshold_certificate",
    ),
    "mean-field envelope soundness": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_mean_field_envelope",
    ),
    "ecpt state": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_capability_state_vector",
    ),
    "pareto frontier recursion": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "core.pareto_frontier",
    ),
    "certified value vector": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.FrontierRecord"),
    "pareto-empty suspension": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "core.pareto_frontier",
    ),
    "raw-relaxed separation": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "core.ProjectionAudit",
    ),
    "friction-charged monotone intervention": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "core.MonotoneMap",
    ),
    "linear lower-bound abstraction": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "bit.SelectivePotentialResult",
    ),
    "pareto operability": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "core.pareto_frontier"),
    "cycle monitor": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_cycle_monitor"),
    "resource normalization ledger": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_resource_normalized_cut",
    ),
    "resource-normalized cut": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_resource_normalized_cut",
    ),
    "packet hypergraph": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.CapabilityHypergraph"),
    "reachable mass": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "ecpt.reachable_mass"),
    "queue": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_queue_certificate"),
    "capacity": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_capacity_certificate"),
    "observation protocol": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.ObservationProtocol"),
    "constraint frame": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.ConstraintFrame"),
    "admissibility grade": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_admissibility_grade"),
    "target-validity status": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.TargetValidityStatus"),
    "finite trace law": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.FiniteTraceLaw"),
    "action grammar": (CoverageStatus.IMPLEMENTED_SCHEMA, "ecpt.ActionGrammar"),
    "controlled transition": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "ecpt.check_controlled_transition",
    ),
    "viability": (CoverageStatus.IMPLEMENTED_CHECKER, "ecpt.check_inner_viability_kernel"),
    "observation window": (CoverageStatus.IMPLEMENTED_SCHEMA, "trc.ObservationWindow"),
    "observable typed infrastructure graph": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "trc.TypedGraphRecord",
    ),
    "trc state": (CoverageStatus.IMPLEMENTED_SCHEMA, "trc.TRCStateRecord"),
    "typed ledger space": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.Ledger"),
    "boundary script automaton": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_boundary_script_automaton",
    ),
    "script ground metric certificate": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_script_ground_metric",
    ),
    "budgeted tolerance recomputation scheduler": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_budgeted_tolerance_scheduler",
    ),
    "budgeted tolerance recomputation consistency": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_budgeted_tolerance_scheduler",
    ),
    "executable process grammar": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_process_grammar",
    ),
    "typed executable trace transducer": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_typed_trace_transducer",
    ),
    "actionability vector": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_actionability_vector",
    ),
    "relaxed frontier order": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_actionability_vector",
    ),
    "boundary generator": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_boundary_generator"),
    "boundary script": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_boundary_script"),
    "cascade residual potential": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_cascade_residual_potential",
    ),
    "cascade potential residual": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_cascade_residual_potential",
    ),
    "independence certificate": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_independence_certificate",
    ),
    "multi-horizon order": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_multi_horizon_order"),
    "budgeted coordinate kernel": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "trc.ToleranceCostKernel",
    ),
    "future-freedom evaluator": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_future_freedom_vector",
    ),
    "residual future-freedom vector": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_future_freedom_vector",
    ),
    "operational tolerance allocator": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_tolerance_allocation_certificate",
    ),
    "operational tolerance allocation": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_tolerance_allocation_certificate",
    ),
    "compositional tolerance propagation": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_tolerance_allocation_certificate",
    ),
    "epsilon charge": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "core.archive_with_truncation"),
    "capped archive": (CoverageStatus.IMPLEMENTED_CONSTRUCTIVE, "core.archive_with_truncation"),
    "causal schedule extraction": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_causal_event_poset",
    ),
    "action class": (CoverageStatus.IMPLEMENTED_SCHEMA, "trc.TransitionProofRecord"),
    "typed transition proof": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_transition_proof",
    ),
    "finite-state transition gain table": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "trc.TransitionProofRecord",
    ),
    "temporal resource tensor": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_resource_calendar",
    ),
    "resource-bounded compensation tensor": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "trc.ResourceCalendarRecord",
    ),
    "resource-conservative scenario calendar": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_resource_calendar",
    ),
    "same-slot resource tensor soundness": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_resource_calendar",
    ),
    "commutative compensation monoid": (
        CoverageStatus.IMPLEMENTED_SCHEMA,
        "core.MonoidRecord",
    ),
    "branching policy dag": (CoverageStatus.IMPLEMENTED_SCHEMA, "core.DependencyDAG"),
    "compiler instance": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.compile_frontier"),
    "budgeted trc compiler": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.compile_frontier"),
    "budgeted compiler complexity": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.compile_frontier"),
    "passive-first dominance": (
        CoverageStatus.IMPLEMENTED_CONSTRUCTIVE,
        "core.pareto_frontier",
    ),
    "certified partial-frontier return": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.compile_frontier",
    ),
    "residual future-freedom from coordinate kernels": (
        CoverageStatus.IMPLEMENTED_CHECKER,
        "trc.check_future_freedom_vector",
    ),
    "causal event": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_causal_event_poset"),
    "lifecycle": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_lifecycle_dag"),
    "escrow": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_resource_escrow"),
    "relaxation": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_relaxation_schedule"),
    "risk": (CoverageStatus.IMPLEMENTED_CHECKER, "trc.check_risk_gate"),
}

_PARTIAL: dict[str, str] = {
    "stopped evidence": "bit.StoppedEvidenceWitness",
    "unit-compatible": "bit.UnitFunctorCertificate",
    "martingale partition": "bit.MartingalePartitionAudit",
    "mechanism-factorized": "bit.MechanismCube",
    "exactness-certified": "bit.EpigraphReleaseProgram",
    "cegar": "bit.CEGARRefinementTrace",
    "activation": "ecpt.ActivationConstructionCertificate",
    "path-law": "ecpt.PathLawResponsePolicyCertificate",
    "settlement": "ecpt.SettlementEventAlgebra",
    "mean-field": "ecpt.MeanFieldEnvelopeCertificate",
    "risk": "trc.RiskGateRecord",
    "lifecycle": "trc.LifecycleDAGRecord",
    "causal": "trc.CausalEventPosetRecord",
    "escrow": "trc.ResourceEscrowRecord",
}

_EXTERNAL = {
    "accumulation, availability, liquidity",
    "additive residual bound",
    "alt lift",
    "alt-compatible",
    "assume-guarantee",
    "auxiliary trace-complex",
    "calibrated-event-envelope",
    "compressed archive",
    "concrete ecology",
    "constructed observation partition",
    "density-dependent",
    "ecpt target",
    "efficiency-preserving archive",
    "evsi",
    "friction-adjusted",
    "future-freedom archive",
    "identified-generator",
    "intervention-identified generator calibration",
    "latent atlas",
    "latent archive",
    "latent-closed",
    "light-tail",
    "linear growth lower bound",
    "liquidity bridge",
    "local contraction",
    "macroscopic",
    "markov additive",
    "natural accelerator",
    "paralysis and repair route",
    "null-channel",
    "online regime",
    "ontology",
    "physical null-channel",
    "progressive fidelity",
    "protocol-competitive target acceleration",
    "protocol-relative soundness",
    "proxy bundle",
    "publication",
    "purification transition",
    "redesign",
    "search-friction",
    "scalar bellman",
    "sound finite abstraction",
    "soundness",
    "sparse synergy",
    "speculative execution channel",
    "sqot",
    "telemetry",
    "time-extended latent",
    "topology redesign",
    "dual distributionally robust",
    "telemetry-updated",
    "latent operator",
    "hybrid",
    "logarithmic-norm",
    "submodular",
    "oracle",
    "external",
    "mean-field envelope",
}


_EXTERNAL_ROUTE_RULES: list[
    tuple[str, tuple[str, ...], str, tuple[str, ...], str, str, tuple[str, ...]]
] = [
    (
        "ecpt-trace-diagnostic",
        ("auxiliary trace-complex", "trace-complex diagnostic"),
        "ecpt.adapters.trace_complex.verify_diagnostic_projection",
        ("trace-complex-audit", "diagnostic-projection-certificate", "residual-trace-ledger"),
        "charge-trace-diagnostic-residual-until-projection-certified",
        "diagnostic-with-trace-complex-obligation",
        (
            "trace-complex-audit-missing",
            "diagnostic-projection-unverified",
            "residual-trace-ledger-incomplete",
        ),
    ),
    (
        "distributionally-robust-metric",
        ("dual distributionally robust", "ground-metric dual"),
        "trc.adapters.metric.verify_distributionally_robust_dual",
        ("ground-metric-certificate", "dual-witness", "ambiguity-set-audit"),
        "charge-metric-dual-residual-until-dual-witness-accepted",
        "diagnostic-with-metric-dual-obligation",
        (
            "ground-metric-certificate-missing",
            "dual-witness-unaccepted",
            "ambiguity-set-audit-incomplete",
        ),
    ),
    (
        "physical-hybrid-system",
        ("null-channel", "hybrid", "physical"),
        "trc.adapters.physical_hybrid.verify_envelope",
        ("instrumented-trace", "resource-calendar", "physics-simulator-certificate"),
        "charge-physical-residual-until-verifier-accepts",
        "diagnostic-with-physical-obligation",
        (
            "physical-system-witness-missing",
            "hybrid-envelope-not-certified",
            "resource-calendar-or-null-channel-unresolved",
        ),
    ),
    (
        "latent-oracle-model",
        ("latent", "oracle", "submodular"),
        "trc.adapters.latent_oracle.verify_model_witness",
        ("oracle-certificate", "latent-model-card", "submodular-proof-witness"),
        "charge-oracle-residual-until-replayable-witness-exists",
        "diagnostic-with-oracle-obligation",
        (
            "oracle-witness-missing",
            "latent-model-not-replayable",
            "submodular-certificate-unverified",
        ),
    ),
    (
        "telemetry-calibration",
        ("telemetry", "online regime", "calibrated-event", "rebasing"),
        "trc.adapters.telemetry.verify_calibration_window",
        ("signed-telemetry-window", "calibration-report", "drift-bound-certificate"),
        "charge-telemetry-drift-residual-until-window-validated",
        "diagnostic-with-telemetry-obligation",
        (
            "telemetry-window-missing",
            "calibration-drift-unbounded",
            "rebasing-certificate-unaccepted",
        ),
    ),
    (
        "assume-guarantee-contract",
        ("assume-guarantee", "contract"),
        "trc.adapters.contracts.verify_assume_guarantee_library",
        ("contract-library", "composition-proof", "counterexample-search-report"),
        "charge-contract-gap-until-composition-proof-accepted",
        "diagnostic-with-contract-obligation",
        (
            "contract-library-missing",
            "composition-proof-unaccepted",
            "domain-contract-incomplete",
        ),
    ),
    (
        "archive-domain-cover",
        ("archive", "progressive fidelity", "compressed", "efficiency-preserving"),
        "trc.adapters.archive.verify_domain_cover",
        ("cover-certificate", "distortion-bound", "archive-replay-log"),
        "charge-archive-distortion-residual-until-cover-certified",
        "diagnostic-with-archive-obligation",
        (
            "archive-cover-missing",
            "distortion-bound-unverified",
            "fidelity-loop-not-certified",
        ),
    ),
    (
        "redesign-response",
        ("redesign", "topology"),
        "trc.adapters.redesign.verify_response_interval",
        ("redesign-candidate-set", "response-interval-proof", "feasibility-certificate"),
        "charge-redesign-response-residual-until-interval-certified",
        "diagnostic-with-redesign-obligation",
        (
            "redesign-candidate-space-unbounded",
            "response-interval-unverified",
            "topology-redesign-oracle-missing",
        ),
    ),
    (
        "numerical-envelope",
        (
            "logarithmic-norm",
            "local contraction",
            "additive residual",
            "light-tail",
            "linear growth",
        ),
        "core.adapters.envelope.verify_finite_bound",
        ("finite-bound-table", "tail-bound-certificate", "residual-envelope-proof"),
        "charge-envelope-residual-until-bound-certified",
        "diagnostic-with-envelope-obligation",
        (
            "finite-envelope-proof-missing",
            "tail-bound-unverified",
            "residual-bound-not-certified",
        ),
    ),
    (
        "ecpt-generator-limit",
        ("generator", "density-dependent", "macroscopic", "markov additive", "bellman"),
        "ecpt.adapters.generators.verify_limit_envelope",
        ("generator-identification-report", "finite-envelope", "transition-kernel-audit"),
        "charge-generator-limit-residual-until-calibration-accepted",
        "diagnostic-with-generator-obligation",
        (
            "generator-calibration-missing",
            "limit-envelope-unverified",
            "transition-kernel-not-certified",
        ),
    ),
    (
        "ecpt-proxy-target",
        ("proxy bundle", "ecpt target", "protocol-competitive", "target acceleration"),
        "ecpt.adapters.proxy.verify_target_contract",
        ("target-contract", "proxy-grounding-report", "protocol-comparison-certificate"),
        "charge-proxy-target-residual-until-contract-accepted",
        "diagnostic-with-proxy-obligation",
        (
            "proxy-grounding-missing",
            "target-contract-unaccepted",
            "protocol-comparison-not-certified",
        ),
    ),
    (
        "ecpt-economics-policy",
        ("liquidity", "availability", "friction", "evsi", "accelerator", "search"),
        "ecpt.adapters.policy.verify_execution_policy",
        ("execution-availability-audit", "policy-counterfactual-report", "value-bound"),
        "charge-policy-residual-until-counterfactual-accepted",
        "diagnostic-with-policy-obligation",
        (
            "execution-availability-unverified",
            "policy-counterfactual-missing",
            "value-bound-not-certified",
        ),
    ),
    (
        "ecpt-ecology-ontology",
        ("ecology", "ontology", "sound finite abstraction", "abstraction soundness"),
        "ecpt.adapters.ecology.verify_domain_abstraction",
        ("domain-semantics-report", "abstraction-map", "simulation-refinement-witness"),
        "charge-abstraction-residual-until-domain-witness-accepted",
        "diagnostic-with-abstraction-obligation",
        (
            "domain-semantics-missing",
            "abstraction-refinement-unverified",
            "ontology-extension-not-certified",
        ),
    ),
    (
        "ecpt-speculative-channel",
        ("speculative", "paralysis", "repair route", "sparse synergy"),
        "ecpt.adapters.speculative.verify_channel_and_repair",
        ("speculative-channel-audit", "repair-route-certificate", "synergy-lower-bound"),
        "charge-speculative-residual-until-channel-certified",
        "diagnostic-with-speculative-obligation",
        (
            "speculative-channel-unverified",
            "repair-route-missing",
            "synergy-bound-not-certified",
        ),
    ),
    (
        "ecpt-bridge-reserve",
        ("alt", "sqot", "liquidity bridge", "publication", "protocol-relative soundness"),
        "ecpt.adapters.bridge.verify_cross_theory_bridge",
        ("bridge-map", "reserve-invariance-proof", "machine-readable-capsule-audit"),
        "charge-bridge-residual-until-cross-theory-proof-accepted",
        "diagnostic-with-bridge-obligation",
        (
            "bridge-map-unverified",
            "reserve-invariance-unaccepted",
            "capsule-projection-not-certified",
        ),
    ),
    (
        "observation-partition",
        ("constructed observation partition", "purification transition", "partition coverage"),
        "trc.adapters.observation.verify_partition_cover",
        ("partition-cover-proof", "purification-trace", "coverage-certificate"),
        "charge-partition-residual-until-cover-certified",
        "diagnostic-with-partition-obligation",
        (
            "partition-cover-missing",
            "purification-trace-unverified",
            "coverage-certificate-unaccepted",
        ),
    ),
]


def _external_obligation_metadata(item_id: str, label: str) -> dict[str, object]:
    normalized = f"{item_id} {label}".lower()
    for (
        category,
        keywords,
        route,
        evidence,
        residual_policy,
        safe_default,
        failure_modes,
    ) in _EXTERNAL_ROUTE_RULES:
        if any(keyword in normalized for keyword in keywords):
            return {
                "obligation_category": category,
                "verifier_route": route,
                "verifier_contract": {
                    "input": (
                        "ExternalProofObligation plus domain evidence matching "
                        "accepted_evidence_kind"
                    ),
                    "output": "ExternalVerifierHook with accepted/rejected obligation ids",
                    "promotion_rule": (
                        "accepted hooks may discharge obligations but cannot bypass "
                        "finite checker status derivation"
                    ),
                },
                "accepted_evidence_kind": sorted(evidence),
                "residual_policy": residual_policy,
                "safe_default": safe_default,
                "failure_modes": sorted(failure_modes),
            }
    return {
        "obligation_category": "domain-specific-proof",
        "verifier_route": "core.adapters.external.verify_domain_obligation",
        "verifier_contract": {
            "input": "ExternalProofObligation and independently replayable domain evidence",
            "output": "ExternalVerifierHook with explicit residual coordinates",
            "promotion_rule": "unresolved or rejected hooks keep diagnostic status",
        },
        "accepted_evidence_kind": ["domain-certificate", "replayable-witness"],
        "residual_policy": "charge-domain-residual-until-specific-verifier-accepted",
        "safe_default": "diagnostic-with-domain-obligation",
        "failure_modes": [
            "domain-certificate-missing",
            "replayable-witness-missing",
            "specific-verifier-route-not-configured",
        ],
    }


def external_route_specs_data() -> list[dict[str, object]]:
    """Return deterministic adapter route specs derived from external metadata rules."""

    specs: list[dict[str, object]] = []
    for (
        category,
        _keywords,
        route,
        evidence,
        residual_policy,
        safe_default,
        failure_modes,
    ) in _EXTERNAL_ROUTE_RULES:
        specs.append(
            {
                "route_id": route,
                "verifier_route": route,
                "obligation_category": category,
                "availability": "unavailable",
                "optional_dependency": None,
                "license_note": "domain adapter contract only; no upstream code vendored",
                "required_evidence_kind": sorted(evidence),
                "residual_policy": residual_policy,
                "safe_default": safe_default,
                "status_non_promotion_rule": (
                    "adapter output may discharge listed obligations but cannot bypass "
                    "checker-derived status"
                ),
                "notes": sorted(failure_modes),
            }
        )
    return sorted(specs, key=lambda item: str(item["route_id"]))


def implementation_metadata(
    item_id: str,
    status: CoverageStatus,
    refs: list[str],
    label: str = "",
) -> dict[str, object]:
    """Derive portable implementation metadata from coverage status and refs."""

    checker_refs = [ref for ref in refs if "check" in ref.lower() or "checker" in ref.lower()]
    schema_refs: list[str] = []
    for ref in refs:
        lower_ref = ref.lower()
        if "check" in lower_ref or "checker" in lower_ref:
            continue
        if ref and ("." in ref or not ref[0].islower()):
            schema_refs.append(ref)
    proof_obligations = (
        [f"obligation:{item_id}"]
        if status
        in {
            CoverageStatus.PARTIAL,
            CoverageStatus.EXTERNAL_OBLIGATION,
            CoverageStatus.UNSUPPORTED,
        }
        else []
    )
    external_failure_modes: list[str] = []
    external_metadata: dict[str, object] = {}
    if status == CoverageStatus.EXTERNAL_OBLIGATION:
        normalized = f"{item_id} {label}".lower()
        external_metadata = _external_obligation_metadata(item_id, label)
        failure_seed = external_metadata.get("failure_modes", [])
        category_failure_modes = (
            [str(mode) for mode in failure_seed] if isinstance(failure_seed, list) else []
        )
        external_failure_modes = [
            *category_failure_modes,
            "no-implicit-settled-promotion",
            "external-verifier-hook-required",
        ]
        if any(key in normalized for key in {"hybrid", "physical", "null-channel"}):
            external_failure_modes.append("physical-or-hybrid-system-witness-required")
        if any(key in normalized for key in {"latent", "telemetry", "oracle", "submodular"}):
            external_failure_modes.append("oracle-or-latent-model-witness-required")
        if any(key in normalized for key in {"thermodynamic", "mean-field", "macroscopic"}):
            external_failure_modes.append("limit-envelope-or-generator-calibration-required")
        if any(key in normalized for key in {"redesign", "assume-guarantee", "contract"}):
            external_failure_modes.append("domain-contract-or-redesign-certificate-required")
    return {
        "implementation_maturity": maturity_from_coverage(status),
        "checker_refs": checker_refs,
        "schema_refs": schema_refs,
        "proof_obligation_ids": proof_obligations,
        "residual_coordinates": [f"residual:{item_id}"] if proof_obligations else [],
        "external_failure_modes": external_failure_modes,
        **external_metadata,
    }


def classify_theory_item(
    label: str,
    *,
    item_id: str | None = None,
    artifact: str | None = None,
) -> tuple[CoverageStatus, list[str]]:
    if item_id is not None and artifact is not None:
        try:
            from percolation_inversion_compiler.io.snapshots import snapshot_item_override

            override = snapshot_item_override(artifact, item_id)
        except (FileNotFoundError, ModuleNotFoundError):
            override = None
        if override is not None:
            return CoverageStatus(override.coverage_status), override.implementation_refs
    normalized = label.lower()
    for key, (status, ref) in _IMPLEMENTED.items():
        if key in normalized:
            return status, [ref]
    for key, ref in _PARTIAL.items():
        if key in normalized:
            return CoverageStatus.PARTIAL, [ref]
    if any(key in normalized for key in _EXTERNAL):
        return CoverageStatus.EXTERNAL_OBLIGATION, ["core.ExternalProofObligation"]
    return CoverageStatus.UNSUPPORTED, []
