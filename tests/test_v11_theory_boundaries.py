from __future__ import annotations

from percolation_inversion_compiler.alt import verify_alt_ecpt_lift
from percolation_inversion_compiler.bit_engine import (
    build_inversion_certificate,
    diagnose_bottlenecks,
    invert_bottlenecks,
)
from percolation_inversion_compiler.phase_lab import (
    ASIProxyThresholdSpec,
    PhaseWindow,
    PhaseWindowObservation,
    build_effective_packet_graph,
    build_threshold_status,
)
from percolation_inversion_compiler.runtime import (
    AccelerationMeasurementMetrics,
    RuntimeRunReport,
    certify_runtime_acceleration,
)
from percolation_inversion_compiler.sqot_controller import (
    QueueItemCost,
    check_diagnostic_reserve,
    diagnose_queue_occupation,
)


def _candidate_graph():
    return build_effective_packet_graph(
        [
            {
                "accepted": False,
                "candidate_only": True,
                "candidate_only_reasons": ["missing evidence"],
                "report_id": "candidate:v11",
                "workflow_usable": True,
            }
        ]
    ).graph


def test_unknown_phase_coordinates_abstain() -> None:
    observation = PhaseWindowObservation(window=PhaseWindow(window_id="window:unknown"))
    threshold = ASIProxyThresholdSpec(
        minimum_accepted_packet_count=0,
        minimum_closure_witness_count=0,
        minimum_effective_edge_count=0,
        minimum_execution_available_path_density=0,
        minimum_verification_throughput=0,
        maximum_false_liquidity_load=1,
        maximum_residual_debt=1,
        maximum_salience_obstruction=1,
    )
    status = build_threshold_status(observation, threshold)
    assert status.certificate_status == "abstain"
    assert status.failed_components
    assert all(reason.startswith("unknown finite") for reason in status.abstention_reasons)


def test_bit_priority_is_not_a_certified_lower_bound_without_witness() -> None:
    candidates = invert_bottlenecks(diagnose_bottlenecks(_candidate_graph()))
    candidate = candidates.inversion_candidates[0]
    certificate = build_inversion_certificate(candidate)
    assert candidate.expected_activation_gain.priority_heuristic > 0
    assert candidate.expected_activation_gain.lower_bound == 0
    assert candidate.expected_activation_gain.coordinate_reported is False
    assert certificate.certificate_status == "abstain"
    assert certificate.certified_activation_gain == 0


def test_sqot_reserve_requires_measured_item_costs() -> None:
    graph = _candidate_graph()
    unknown = diagnose_queue_occupation(graph)
    unknown_reserve = check_diagnostic_reserve(graph)
    packet_id = graph.nodes[0].node_id
    costs = {
        packet_id: QueueItemCost(
            packet_id=packet_id,
            attention_cost=0.1,
            verification_cost=0.1,
            age_cost=0.0,
            hazard_cost=0.0,
            validity_domain="window:v11",
            evidence_refs=["evidence:cost"],
        )
    }
    measured = diagnose_queue_occupation(graph, item_costs=costs)
    measured_reserve = check_diagnostic_reserve(graph, item_costs=costs)
    assert unknown.accepted is False
    assert unknown.attention_budget_ledger.measurement_state == "unknown"
    assert unknown_reserve.accepted is False
    assert measured.accepted is True
    assert measured_reserve.accepted is True


def test_alt_self_reported_lift_is_not_capitalized() -> None:
    graph = _candidate_graph()
    report = verify_alt_ecpt_lift(
        [
            {
                "packet_id": "alt:self-report",
                "accepted": True,
                "operationally_usable": True,
                "positive_ecpt_component_lift": True,
                "evidence_refs": ["evidence:self"],
            }
        ],
        graph,
    )
    assert report.accepted is False
    assert report.affected_ecpt_components == []


def test_acceleration_metrics_require_fixed_horizon_and_evidence() -> None:
    baseline_metrics = AccelerationMeasurementMetrics(
        time_to_verified=3.0,
        verification_yield=0.4,
        residual_half_life=4.0,
        receiver_reuse=0.5,
        certified_capital_gain=0.1,
        resource_cost=1.0,
        error_correlation=0.5,
        fixed_horizon=True,
        stopping_rule_ref="stopping-rule:v11",
        evidence_refs=["evidence:baseline-measurement"],
    )
    baseline = RuntimeRunReport(
        run_id="baseline:v11",
        initial_state_id="state:v11",
        threshold_crossing_step=3,
        resource_units=1.0,
        acceleration_metrics=baseline_metrics,
    )
    metrics = AccelerationMeasurementMetrics(
        time_to_verified=1.0,
        verification_yield=0.5,
        residual_half_life=2.0,
        receiver_reuse=1.0,
        certified_capital_gain=0.2,
        resource_cost=1.0,
        error_correlation=0.0,
        fixed_horizon=True,
        stopping_rule_ref="stopping-rule:v11",
        evidence_refs=["evidence:measurement"],
    )
    candidate = RuntimeRunReport(
        run_id="candidate:v11",
        initial_state_id="state:v11",
        threshold_crossing_step=1,
        resource_units=1.0,
        acceleration_metrics=metrics,
    )
    certificate = certify_runtime_acceleration(baseline, candidate)
    assert certificate.accepted
    assert certificate.acceleration_metrics_certified
    assert certificate.acceleration_metrics.accepted

    post_selected = candidate.model_copy(
        update={"acceleration_metrics": metrics.model_copy(update={"fixed_horizon": False})}
    )
    assert not certify_runtime_acceleration(baseline, post_selected).acceleration_metrics_certified

    regressed = candidate.model_copy(
        update={
            "acceleration_metrics": metrics.model_copy(
                update={"verification_yield": 0.3, "time_to_verified": 4.0}
            )
        }
    )
    regression_certificate = certify_runtime_acceleration(baseline, regressed)
    assert not regression_certificate.acceleration_metrics_certified
    assert any(
        reason.startswith("metrics regressed beyond tolerance")
        for reason in regression_certificate.acceleration_metric_reasons
    )

    missing_evidence = baseline.model_copy(
        update={"acceleration_metrics": baseline_metrics.model_copy(update={"evidence_refs": []})}
    )
    assert not certify_runtime_acceleration(
        missing_evidence, candidate
    ).acceleration_metrics_certified
