from __future__ import annotations

from percolation_inversion_compiler.adapters import (
    replay_trc_physical_trace,
    verify_archive_domain_evidence,
    verify_ecpt_generator_limit,
    verify_ecpt_numerical_envelope,
    verify_trc_telemetry_calibration,
)
from percolation_inversion_compiler.bit import (
    CertificateCompilerRecord,
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
    SinkhornCertificate,
    StoppedEvidenceSheafCertificate,
    StoppedEvidenceWitness,
    UnitConversion,
    UnitFunctorCertificate,
    VectorCompatibleFamily,
    check_certificate_compiler,
    check_fused_geometric_comparison,
    check_martingale_deficiency_certificate,
    check_mechanism_cube,
    check_mechanism_cube_certificate,
    check_ordered_potential_cone,
    check_selective_cup_certificate,
    check_sinkhorn_certificate,
    check_sinkhorn_plan,
    check_stopped_evidence_sheaf,
    check_stopped_evidence_sheaf_certificate,
    check_vector_compatible_family,
    compiler_invalidation_reachability,
    exactness_release_interval,
    good_turing_frontier_release,
    mechanism_non_substitution,
    minimal_effective_conditions,
    sinkhorn_plan,
)
from percolation_inversion_compiler.core.algorithms import dkw_radius, good_turing_unseen
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.order import FiniteOrder
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecpt import (
    ActionGrammar,
    ActivationConstructionCertificate,
    ActivationThresholdCertificate,
    CapabilityEdge,
    CapabilityHypergraph,
    CapabilityPacket,
    CapabilityStateVector,
    CapacityCertificate,
    ControlledTransition,
    FinitePhaseControlCertificate,
    InnerViabilityKernel,
    MeanFieldEnvelopeCertificate,
    ObservationProtocol,
    PhaseControlEnvelope,
    PostconditionObligation,
    ProtocolFunctorCertificate,
    RAFSettlementCertificate,
    ReachableMassRecursionCertificate,
    SettlementEventAlgebra,
    SettlementReturnRAFCertificate,
    check_action_grammar,
    check_activation_threshold_certificate,
    check_capability_state_vector,
    check_capacity_certificate,
    check_controlled_transition,
    check_finite_phase_control_certificate,
    check_inner_viability_kernel,
    check_mean_field_envelope,
    check_phase_control_envelope,
    check_protocol_functor_certificate,
    check_reachable_mass_recursion,
    check_settlement_return_raf_certificate,
    finite_gibbs_phase_response,
    reachable_mass,
)
from percolation_inversion_compiler.trc import (
    ActionabilityVector,
    BoundaryScriptAutomatonRecord,
    BoundaryScriptRecord,
    BudgetedToleranceScheduler,
    CausalEventPosetRecord,
    EventContractRecord,
    ExecutableTraceNormalForm,
    FutureFreedomVector,
    LifecycleDAGRecord,
    MultiHorizonOrder,
    ProcessGrammarRecord,
    ResourceCalendarRecord,
    ResourceEscrowRecord,
    ResourceReservationRecord,
    ScriptGroundMetricCertificate,
    ToleranceAllocationCertificate,
    ToleranceCostKernel,
    ToleranceMenuItem,
    TraceNormalizationCertificate,
    TransitionProofRecord,
    check_actionability_vector,
    check_boundary_script,
    check_budgeted_tolerance_scheduler,
    check_causal_event_poset,
    check_future_freedom_vector,
    check_process_grammar,
    check_resource_calendar,
    check_script_ground_metric,
    check_tolerance_allocation_certificate,
    check_trace_normal_form,
    datacenter_demo,
    finite_tolerance_allocation,
    network_calculus_bounds,
    semiring_path_product,
    weighted_edit_distance,
)


def test_statistical_bounds() -> None:
    assert 0.0 < dkw_radius(100, 0.05) < 0.2
    assert good_turing_unseen([1, 1, 2, 4]) == 2 / 8


def test_v02_domain_adapters_success_and_fail_closed() -> None:
    assert verify_ecpt_numerical_envelope(
        residual=0.1,
        residual_bound=0.2,
        finite_horizon=4,
    ).accepted
    assert not verify_ecpt_numerical_envelope(
        residual=0.3,
        residual_bound=0.2,
        finite_horizon=4,
    ).accepted
    assert verify_ecpt_generator_limit(
        observed_generation=9.0,
        certified_limit=10.0,
    ).accepted
    assert not verify_ecpt_generator_limit(
        observed_generation=12.0,
        certified_limit=10.0,
    ).accepted
    assert verify_trc_telemetry_calibration(
        [1.0, 2.0],
        [1.05, 2.05],
        tolerance=0.1,
    ).accepted
    assert not verify_trc_telemetry_calibration(
        [1.0],
        [2.0],
        tolerance=0.1,
    ).accepted
    assert replay_trc_physical_trace(["a", "b"], ["a", "b"]).accepted
    assert not replay_trc_physical_trace(["a", "c"], ["a", "b"]).accepted
    assert verify_archive_domain_evidence({"r1": "cooling"}, {"cooling"}).accepted
    assert not verify_archive_domain_evidence({"r1": "unknown"}, {"cooling"}).accepted


def test_bit_release_and_mechanism() -> None:
    cube = MechanismCube(
        path_channel="path",
        log_channel="log",
        observation_channel="obs",
        factorization_rank=2,
        negative_control_rank=2,
        proximal_bridge=True,
        triangular_commutator_zero=True,
    )
    assert mechanism_non_substitution(cube)
    assert check_mechanism_cube(cube).accepted
    certificate = MechanismCubeCertificate(
        certificate_id="mc",
        cube=cube,
        release_channel="path",
        negative_control_channels={"log"},
        paired_null_witnesses={"log": "null-log"},
        accepted=True,
    )
    assert check_mechanism_cube_certificate(certificate).accepted
    assert not check_mechanism_cube_certificate(
        certificate.model_copy(update={"paired_null_witnesses": {}})
    ).accepted
    assert exactness_release_interval(1.0, 1.5, exactness_residual=0.1) == (0.9, 1.6)
    assert good_turing_frontier_release([1, 1, 2], recall_floor=0.5) == 0.25
    plan = sinkhorn_plan([1.0, 1.0], [1.0, 1.0], [[0.0, 1.0], [1.0, 0.0]])
    assert check_sinkhorn_plan(plan, [1.0, 1.0], [1.0, 1.0], tolerance=1e-4).accepted


def test_bit_mec_antichain() -> None:
    records = [
        MECRecord(
            record_id="a",
            positive_release=True,
            mechanism_factorized_non_substitution=True,
            benefits={"release": 2.0},
            burdens={"cost": 1.0},
            status=ClaimStatus.SETTLED,
        ),
        MECRecord(
            record_id="b",
            positive_release=True,
            mechanism_factorized_non_substitution=True,
            benefits={"release": 1.0},
            burdens={"cost": 2.0},
            status=ClaimStatus.PROVISIONAL,
        ),
    ]
    assert [record.record_id for record in minimal_effective_conditions(records)] == ["a"]


def test_bit_fused_geometric_comparison_certificate() -> None:
    certificate = FusedGeometricComparisonCertificate(
        certificate_id="fgw",
        source_nodes={"a", "b"},
        target_nodes={"x", "y"},
        coupling=[("a", "x", 0.5), ("b", "y", 0.5)],
        geometry_distortion=0.1,
        feature_distortion=0.2,
        marginal_residual=0.01,
        solver_gap=0.01,
        distortion_upper_bound=0.5,
        accepted=True,
    )
    result = check_fused_geometric_comparison(certificate)
    assert result.accepted
    assert result.residual_ledger.burden_sum() > 0.0
    bad_certificate = certificate.model_copy(update={"distortion_upper_bound": 0.1})
    assert not check_fused_geometric_comparison(bad_certificate).accepted


def test_bit_structured_unit_sheaf_sinkhorn_and_compiler() -> None:
    unit = UnitFunctorCertificate(
        ordered_units={"watt", "kilowatt"},
        conversions=[
            UnitConversion(
                source_unit="kilowatt",
                target_unit="watt",
                factor=1000.0,
                audit_id="u1",
            )
        ],
        monotone=True,
    )
    cone = OrderedPotentialCone(
        cone_id="cone",
        coordinate_kinds={"release": "benefit"},
        product_order=FiniteOrder(elements=["low", "high"], leq_pairs=[("low", "high")]),
        unit_functor=unit,
    )
    assert check_ordered_potential_cone(cone).accepted
    family = VectorCompatibleFamily(
        family_id="family",
        protocol=ProtocolObject(
            protocol_id="p",
            candidate_universe={"x"},
            law_labels={"law"},
            validity_domains={"global"},
        ),
        laws=[
            InterventionLaw(
                law_id="law",
                support={"x"},
                probabilities={"x": 1.0},
                normalized=True,
            )
        ],
        potential_cone=cone,
        report_mask={"release"},
    )
    assert check_vector_compatible_family(family).accepted

    witnesses = [
        StoppedEvidenceWitness(
            probability_space="omega",
            stopping_time="tau",
            ledger_id="ledger",
            evidence_ids={"a"},
        )
    ]
    gluing = PullbackGluingWitness(
        witness_id="g",
        local_sections={"left": {"a"}, "right": {"a", "b"}},
        overlaps={"left|right": {"a"}},
        glued_section={"a", "b"},
    )
    assert check_stopped_evidence_sheaf(witnesses, gluing).accepted
    bad_gluing = gluing.model_copy(update={"glued_section": {"a"}})
    assert not check_stopped_evidence_sheaf(witnesses, bad_gluing).accepted

    certificate = SinkhornCertificate(
        source=[1.0, 1.0],
        target=[1.0, 1.0],
        plan=[[0.5, 0.0], [0.0, 0.5]],
        duality_gap=0.0,
        solver_gap=0.0,
    )
    assert check_sinkhorn_certificate(certificate).accepted
    bad_certificate = certificate.model_copy(update={"solver_gap": -1.0})
    assert not check_sinkhorn_certificate(bad_certificate).accepted

    compiler = CertificateCompilerRecord(
        compiler_id="compiler",
        dependency_graph=DependencyDAG.from_dependencies({"coord": {"witness"}}),
        witness_nodes={"witness"},
        coordinate_nodes={"coord"},
        accepted_nodes={"witness", "coord"},
    )
    assert check_certificate_compiler(compiler).accepted
    assert compiler_invalidation_reachability(compiler, "witness") == {"coord"}


def test_bit_theorem_level_certificates() -> None:
    witness = StoppedEvidenceWitness(
        probability_space="omega",
        stopping_time="tau",
        ledger_id="ledger",
        evidence_ids={"a"},
    )
    gluing = PullbackGluingWitness(
        witness_id="glue",
        local_sections={"left": {"a"}, "right": {"a", "b"}},
        overlaps={"left|right": {"a"}},
        glued_section={"a", "b"},
    )
    sheaf = StoppedEvidenceSheafCertificate(
        certificate_id="sheaf",
        witnesses=[witness],
        gluing_witness=gluing,
        residual=0.02,
    )
    sheaf_result = check_stopped_evidence_sheaf_certificate(sheaf)
    assert sheaf_result.accepted
    assert sheaf_result.residual_ledger.burden_sum() > 0.0
    assert not check_stopped_evidence_sheaf_certificate(
        sheaf.model_copy(update={"missing_sections": {"right"}})
    ).accepted

    unit = UnitFunctorCertificate(
        ordered_units={"watt"},
        conversions=[
            UnitConversion(source_unit="watt", target_unit="watt", factor=1.0, audit_id="u")
        ],
        monotone=True,
    )
    family = VectorCompatibleFamily(
        family_id="cup-family",
        protocol=ProtocolObject(
            protocol_id="p",
            candidate_universe={"x"},
            law_labels={"law"},
            validity_domains={"global"},
        ),
        laws=[
            InterventionLaw(
                law_id="law",
                support={"x"},
                probabilities={"x": 1.0},
                normalized=True,
            )
        ],
        potential_cone=OrderedPotentialCone(
            cone_id="cone",
            coordinate_kinds={"release": "benefit"},
            product_order=FiniteOrder(elements=["low", "high"], leq_pairs=[("low", "high")]),
            unit_functor=unit,
        ),
        report_mask={"release"},
    )
    cup = SelectiveCUPCertificate(
        certificate_id="cup",
        family=family,
        lower_process={"release": 1.0},
        selection_charge={"release": 0.1},
        unit_audit={"release"},
        required_reported={"release"},
    )
    assert check_selective_cup_certificate(cup).accepted
    rejected_cup = cup.model_copy(update={"unit_audit": set()})
    assert not check_selective_cup_certificate(rejected_cup).accepted

    martingale = MartingaleDeficiencyCertificate(
        certificate_id="mpda",
        audit=MartingalePartitionAudit(
            block_bounds=[0.6, 0.5],
            boundary_drift=0.1,
            selection_charge=0.1,
            confidence_radius=0.1,
        ),
        lower_mass_floor=0.8,
        residual_tolerance=0.05,
    )
    assert check_martingale_deficiency_certificate(martingale).accepted
    bad_martingale = martingale.model_copy(update={"lower_mass_floor": 1.5})
    assert not check_martingale_deficiency_certificate(bad_martingale).accepted


def test_ecpt_reachable_mass_and_gibbs_response() -> None:
    graph = CapabilityHypergraph(
        seed_mass={"seed": 1.0},
        edges=[
            CapabilityEdge(
                edge_id="e1",
                sources=("seed",),
                target="target",
                activation_weight=0.8,
            )
        ],
    )
    assert reachable_mass(graph)["target"] == 0.8
    baseline, perturbed, improvement = finite_gibbs_phase_response(
        {"bad": 0.0, "good": 1.0},
        {"bad": 1.0, "good": 0.0},
        {"good"},
    )
    assert perturbed > baseline
    assert improvement > 0


def test_ecpt_finite_control_and_capacity_certificates() -> None:
    grammar = ActionGrammar(
        actions={"activate"},
        preconditions={"activate": {"observed"}},
        postconditions={"activate": {"stable"}},
    )
    assert check_action_grammar(grammar).accepted
    transition = ControlledTransition(
        transition_id="t",
        action_id="activate",
        preconditions_met=True,
        postcondition_obligation=PostconditionObligation(
            action_id="activate",
            required_postconditions={"stable"},
            satisfied_postconditions={"stable"},
        ),
        status=ClaimStatus.SETTLED,
    )
    assert check_controlled_transition(transition).accepted
    bad_transition = transition.model_copy(update={"preconditions_met": False})
    assert not check_controlled_transition(bad_transition).accepted

    kernel = InnerViabilityKernel(
        kernel_id="k",
        states={"safe", "unsafe"},
        inner_states={"safe"},
        transition_map={"safe": {"safe"}},
    )
    assert check_inner_viability_kernel(kernel).accepted
    bad_kernel = kernel.model_copy(update={"transition_map": {"safe": {"unsafe"}}})
    assert not check_inner_viability_kernel(bad_kernel).accepted

    capacity = CapacityCertificate(
        capacity_id="cap",
        available={"kw": 1.0},
        required={"kw": 2.0},
    )
    assert not check_capacity_certificate(capacity).accepted

    graph = CapabilityHypergraph(
        seed_mass={"seed": 1.0},
        edges=[
            CapabilityEdge(
                edge_id="e",
                sources=("seed",),
                target="target",
                activation_weight=0.7,
            )
        ],
    )
    certificate = ReachableMassRecursionCertificate(
        certificate_id="rm",
        graph=graph,
        target_nodes={"target"},
        lower_bounds={"target": 0.6},
        status_floor=ClaimStatus.PROVISIONAL,
    )
    assert check_reachable_mass_recursion(certificate).accepted
    bad_certificate = certificate.model_copy(update={"lower_bounds": {"target": 0.9}})
    assert not check_reachable_mass_recursion(bad_certificate).accepted


def test_ecpt_protocol_functor_phase_and_duplicate_prevention() -> None:
    source = ObservationProtocol(
        time_index="t",
        window_family=["w"],
        receiver_contexts=["agent"],
        validity_domains=["source"],
    )
    target = ObservationProtocol(
        time_index="t",
        window_family=["w"],
        receiver_contexts=["agent2"],
        validity_domains=["target"],
    )
    functor = ProtocolFunctorCertificate(
        certificate_id="pf",
        source_protocol=source,
        target_protocol=target,
        object_map={"agent": "agent2", "source": "target"},
        accepted_extension=True,
    )
    assert check_protocol_functor_certificate(functor).accepted
    bad_functor = functor.model_copy(update={"object_map": {"missing": "agent2"}})
    assert not check_protocol_functor_certificate(bad_functor).accepted

    finite_envelope = PhaseControlEnvelope(
        envelope_id="phase",
        finite_state_space={"cold", "hot"},
        control_surface={"hot": 1.0},
        phase_response={"cold": 0.2, "hot": 0.8},
        finite_horizon=4,
    )
    assert check_phase_control_envelope(finite_envelope).accepted
    thermodynamic_envelope = finite_envelope.model_copy(
        update={"thermodynamic_obligation_ids": {"thermo-limit"}}
    )
    assert not check_phase_control_envelope(thermodynamic_envelope).accepted

    state = CapabilityStateVector(
        packets=[
            CapabilityPacket(
                packet_id="p",
                coordinates={"mass": 1.0},
                duplicate_mass=0.2,
                burden=0.1,
            )
        ]
    )
    assert check_capability_state_vector(state).accepted
    assert abs(state.packets[0].effective_mass("mass") - 0.7) < 1e-12
    bad_state = state.model_copy(
        update={"packets": [state.packets[0].model_copy(update={"duplicate_mass": -1.0})]}
    )
    assert not check_capability_state_vector(bad_state).accepted


def test_ecpt_theorem_level_phase_activation_and_settlement_certificates() -> None:
    envelope = PhaseControlEnvelope(
        envelope_id="phase",
        finite_state_space={"cold", "hot"},
        control_surface={"hot": 1.0},
        phase_response={"cold": 0.2, "hot": 0.8},
        finite_horizon=3,
    )
    finite_phase = FinitePhaseControlCertificate(
        certificate_id="finite-phase",
        envelope=envelope,
        baseline_response=0.2,
        controlled_response=0.8,
        minimum_improvement=0.5,
        residual=0.05,
    )
    assert check_finite_phase_control_certificate(finite_phase).accepted
    thermodynamic_phase = finite_phase.model_copy(
        update={"thermodynamic_obligation_ids": {"thermodynamic-limit"}}
    )
    phase_result = check_finite_phase_control_certificate(thermodynamic_phase)
    assert not phase_result.accepted
    assert "thermodynamic-limit" in phase_result.missing_obligations

    graph = CapabilityHypergraph(
        seed_mass={"seed": 1.0},
        edges=[
            CapabilityEdge(
                edge_id="edge",
                sources=("seed",),
                target="target",
                activation_weight=0.9,
            )
        ],
    )
    threshold = ActivationThresholdCertificate(
        certificate_id="threshold",
        activation=ActivationConstructionCertificate(
            construction_id="activation",
            configuration_space_size=4,
            energy_ledger_present=True,
            exact=True,
        ),
        graph=graph,
        target_nodes={"target"},
        lower_bounds={"target": 0.8},
        threshold=0.8,
        finite_size=4,
    )
    assert check_activation_threshold_certificate(threshold).accepted
    threshold_external = threshold.model_copy(
        update={"thermodynamic_obligation_ids": {"and-support-limit"}}
    )
    assert not check_activation_threshold_certificate(threshold_external).accepted

    event_algebra = SettlementEventAlgebra(algebra_id="events", settled_events={"done"})
    raf = SettlementReturnRAFCertificate(
        certificate_id="raf",
        raf_certificate=RAFSettlementCertificate(
            certificate_id="raf-base",
            event_algebra=event_algebra,
            event_id="done",
            transition_ledger_present=True,
            debt_ledger_present=True,
            risk_ledger_present=True,
        ),
        required_ledger_obligations={"transition", "debt", "risk"},
        present_ledger_obligations={"transition", "debt", "risk"},
    )
    assert check_settlement_return_raf_certificate(raf).accepted
    missing_raf = raf.model_copy(update={"present_ledger_obligations": {"transition"}})
    raf_result = check_settlement_return_raf_certificate(missing_raf)
    assert not raf_result.accepted
    assert {"debt", "risk"}.issubset(set(raf_result.missing_obligations))

    mean_field = MeanFieldEnvelopeCertificate(
        envelope_id="mf",
        chart_id="chart",
        finite_horizon=4,
        generator_identified=False,
    )
    mean_field_result = check_mean_field_envelope(mean_field)
    assert not mean_field_result.accepted
    assert "generator identification certificate is absent" in mean_field_result.reasons


def test_trc_network_tolerance_and_demo() -> None:
    assert weighted_edit_distance(["g_C"], ["g_C", "g_N"]) == 1.0
    bounds = network_calculus_bounds(
        EventContractRecord(
            contract_id="n",
            arrival_curve=[0.0, 1.0],
            service_curve=[0.5, 1.2],
        )
    )
    assert bounds["backlog_bound"] == 0.5
    assert semiring_path_product([1.0, 2.0, 3.0], semiring="max-plus") == 6.0
    allocation, ledger = finite_tolerance_allocation(
        [
            ToleranceCostKernel(
                coordinate="obs",
                finite_menu=[
                    ToleranceMenuItem(
                        name="coarse",
                        fidelity_level="coarse",
                        resource_cost=0.1,
                        residual_increment=0.2,
                    ),
                    ToleranceMenuItem(
                        name="fine",
                        fidelity_level="fine",
                        resource_cost=2.0,
                        residual_increment=0.01,
                    ),
                ],
            )
        ],
        budget=0.5,
    )
    assert allocation["obs"].name == "coarse"
    assert ledger.value("obs") == 0.2
    demo = datacenter_demo()
    assert demo.compile_result.main_frontier
    assert demo.compile_result.diagnostic_archive


def test_trc_trace_normal_form_structured_checker() -> None:
    trace = ExecutableTraceNormalForm(
        trace_id="trace-1",
        normalized_word=["shed-load"],
        normalization=TraceNormalizationCertificate(
            trace_id="trace-1",
            source_word=["shed-load"],
            normalized_word=["shed-load"],
            confluence_witness=True,
            termination_witness=True,
        ),
        step_proofs=[
            TransitionProofRecord(
                action_class="shed-load",
                precondition={"safe": True},
                postcondition={"stable": True},
                status=ClaimStatus.SETTLED,
            )
        ],
        precondition={"safe": True},
        postcondition={"stable": True},
        causal_schedule=CausalEventPosetRecord(event_ids={"shed-load"}),
        resource_flow_profile=[],
        escrows=[
            ResourceEscrowRecord(
                escrow_id="escrow-1",
                dependency_class="power",
                resource_use={"kw": 1.0},
                capacity_ledger={"kw": 2.0},
                commutation_certificate=True,
                resolution_status=ClaimStatus.SETTLED,
            )
        ],
        lifecycle=LifecycleDAGRecord(certificate_versions={"cert": "v1"}),
        certificate_versions=["v1"],
        tolerance_versions=["tol-v1"],
        error_budget=0.1,
        trace_residual=0.01,
    )
    assert check_trace_normal_form(trace).accepted
    missing_schedule = trace.model_copy(update={"causal_schedule": None})
    result = check_trace_normal_form(missing_schedule)
    assert not result.accepted
    assert "causal schedule is missing" in result.reasons


def test_trc_calendar_future_freedom_and_tolerance_certificates() -> None:
    cyclic = CausalEventPosetRecord(
        event_ids={"a", "b"},
        happens_before=[("a", "b"), ("b", "a")],
    )
    assert not check_causal_event_poset(cyclic).accepted

    calendar = ResourceCalendarRecord(
        calendar_id="cal",
        capacities={"kw": 1.0},
        reservations=[
            ResourceReservationRecord(
                reservation_id="r1",
                resource="kw",
                start_tick=0,
                end_tick=1,
                amount=0.4,
            ),
            ResourceReservationRecord(
                reservation_id="r2",
                resource="kw",
                start_tick=1,
                end_tick=2,
                amount=0.6,
            ),
        ],
    )
    assert check_resource_calendar(calendar).accepted
    overloaded = calendar.model_copy(
        update={
            "reservations": [
                *calendar.reservations,
                ResourceReservationRecord(
                    reservation_id="r3",
                    resource="kw",
                    start_tick=1,
                    end_tick=1,
                    amount=0.6,
                ),
            ]
        }
    )
    assert not check_resource_calendar(overloaded).accepted

    vector = FutureFreedomVector(
        vector_id="ff",
        horizons=["h1", "h2"],
        values={"h1": 1.0, "h2": 1.1},
        residuals={"h1": 0.0, "h2": 0.1},
        order=MultiHorizonOrder(
            order_id="mh",
            horizons=["h1", "h2"],
            precedence=[("h1", "h2")],
        ),
    )
    assert check_future_freedom_vector(vector).accepted

    tolerance = ToleranceAllocationCertificate(
        certificate_id="tol",
        selected_items={"obs": "coarse"},
        budget=1.0,
        objective_value=0.2,
        solver_gap=0.01,
        dual_bound=0.19,
        residual_charge=0.02,
    )
    assert check_tolerance_allocation_certificate(tolerance).accepted
    assert not check_tolerance_allocation_certificate(
        tolerance.model_copy(update={"integer_feasible": False})
    ).accepted

    automaton = BoundaryScriptAutomatonRecord(
        alphabet={"g_C", "g_N"},
        prefix_bound=2,
        branch_prefix_budget=1,
        accepted_prefixes={"g_C g_N"},
    )
    script = BoundaryScriptRecord(
        script_id="script",
        automaton_id="default",
        tokens=["g_C", "g_N"],
    )
    assert check_boundary_script(script, automaton).accepted


def test_trc_process_grammar_metric_scheduler_and_actionability() -> None:
    grammar = ProcessGrammarRecord(
        grammar_id="pg",
        action_classes={"observe", "repair", "settle"},
        start_actions={"observe"},
        terminal_actions={"settle"},
        transitions={"observe": {"repair"}, "repair": {"settle"}},
    )
    assert check_process_grammar(grammar).accepted
    bad_grammar = grammar.model_copy(update={"forbidden_actions": {"repair"}})
    assert not check_process_grammar(bad_grammar).accepted

    metric = ScriptGroundMetricCertificate(
        certificate_id="metric",
        source_script=["observe"],
        target_script=["observe", "repair"],
        distance=1.0,
        lower_bound=0.5,
        triangle_witness=True,
    )
    assert check_script_ground_metric(metric).accepted
    bad_metric = metric.model_copy(update={"triangle_witness": False})
    assert not check_script_ground_metric(bad_metric).accepted

    scheduler = BudgetedToleranceScheduler(
        scheduler_id="sched",
        budget=2.0,
        task_costs={"observe": 0.5, "repair": 1.7},
        schedule=["observe", "repair"],
        dependency_edges=[("observe", "repair")],
        partial_frontier_on_exhaustion=True,
    )
    result = check_budgeted_tolerance_scheduler(scheduler)
    assert result.accepted
    assert result.residual_ledger.burden_sum() > 0.0
    rejected_scheduler = scheduler.model_copy(update={"partial_frontier_on_exhaustion": False})
    assert not check_budgeted_tolerance_scheduler(rejected_scheduler).accepted

    actionability = ActionabilityVector(
        vector_id="act",
        coordinates={"operate": 1.0, "relax": 0.5},
        relaxed_coordinates={"relax"},
    )
    assert check_actionability_vector(actionability).accepted
    assert not check_actionability_vector(
        actionability.model_copy(update={"relaxed_coordinates": {"missing"}})
    ).accepted
