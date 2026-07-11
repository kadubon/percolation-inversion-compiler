from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from percolation_inversion_compiler.afst import build_afst_flux_stabilization_report
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
    RuntimeRunReport,
    certify_runtime_acceleration,
)
from percolation_inversion_compiler.sqot_controller import (
    check_diagnostic_reserve,
    diagnose_queue_occupation,
)
from percolation_inversion_compiler.trc import adapt_tool_trace_events


def _contract() -> dict[str, Any]:
    return json.loads(
        (Path(__file__).parents[1] / "contracts/v1.1/pic-cross-language-contract.json").read_text(
            encoding="utf-8"
        )
    )["boundary_normal_forms"]


def _contract_pack() -> dict[str, Any]:
    return json.loads(
        (Path(__file__).parents[1] / "contracts/v1.1/pic-cross-language-contract.json").read_text(
            encoding="utf-8"
        )
    )


def _candidate_graph():
    return build_effective_packet_graph(
        [
            {
                "accepted": False,
                "candidate_only": True,
                "candidate_only_reasons": ["missing evidence"],
                "report_id": "candidate:v11-normal-form",
                "workflow_usable": True,
            }
        ]
    ).graph


def test_all_six_theory_boundary_normal_forms_match_contract_pack() -> None:
    expected = _contract()
    afst = build_afst_flux_stabilization_report({}).model_dump(mode="json")
    assert {
        "accepted": afst["accepted"],
        "operation_ready": afst["operation_ready"],
        "physical_dispatch_ready": afst["physical_dispatch_ready"],
        "provider_dispatch_ready": afst["provider_dispatch_ready"],
        "residual_kinds": sorted({item["kind"] for item in afst["residuals"]}),
        "settled": afst["settled"],
        "system": "AFST",
    } == expected["afst_empty"]

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
    phase = build_threshold_status(
        PhaseWindowObservation(window=PhaseWindow(window_id="window:normal-form")),
        threshold,
    )
    assert {
        "accepted": phase.accepted,
        "certificate_status": phase.certificate_status,
        "settled": phase.settled,
        "system": "Phase",
    } == expected["phase_unknown"]

    graph = _candidate_graph()
    bit_candidate = invert_bottlenecks(diagnose_bottlenecks(graph)).inversion_candidates[0]
    bit_certificate = build_inversion_certificate(bit_candidate)
    assert {
        "certificate_status": bit_certificate.certificate_status,
        "certified_activation_gain": bit_certificate.certified_activation_gain,
        "coordinate_reported": bit_candidate.expected_activation_gain.coordinate_reported,
        "lower_bound": bit_candidate.expected_activation_gain.lower_bound,
        "settled": bit_certificate.settled,
        "system": "BIT",
    } == expected["bit_unwitnessed"]

    queue = diagnose_queue_occupation(graph)
    reserve = check_diagnostic_reserve(graph)
    assert {
        "accepted": queue.accepted,
        "measurement_state": queue.attention_budget_ledger.measurement_state,
        "reserve_accepted": reserve.accepted,
        "settled": queue.settled,
        "system": "SQOT",
    } == expected["sqot_unknown"]

    alt = verify_alt_ecpt_lift(
        [
            {
                "packet_id": "alt:self-report",
                "accepted": True,
                "positive_ecpt_component_lift": True,
                "evidence_refs": ["evidence:self"],
            }
        ],
        graph,
    )
    assert {
        "accepted": alt.accepted,
        "positive_lift": bool(alt.affected_ecpt_components),
        "promotes_to_capital": bool(alt.affected_ecpt_components),
        "settled": alt.settled,
        "system": "ALT",
    } == expected["alt_self_reported"]

    trc = adapt_tool_trace_events([])
    assert {
        "accepted": trc.accepted,
        "executed_action_count": trc.executed_action_count,
        "physical_truth_proven": trc.proves_physical_truth,
        "settled": trc.settled,
        "system": "TRC",
    } == expected["trc_empty"]


def test_runtime_acceleration_normal_form_matches_contract_pack() -> None:
    case = _contract_pack()["runtime_acceleration_case"]
    certificate = certify_runtime_acceleration(
        RuntimeRunReport.model_validate(case["baseline"]),
        RuntimeRunReport.model_validate(case["candidate"]),
    )
    assert {
        "accepted": certificate.accepted,
        "acceleration_metrics_certified": certificate.acceleration_metrics_certified,
        "hitting_time_gain_lower_bound": certificate.hitting_time_gain_lower_bound,
        "metric_names": [item.metric_name for item in certificate.metric_comparisons],
        "operationally_usable": certificate.operationally_usable,
        "resource_matched": certificate.resource_matched,
        "settled": certificate.settled,
    } == case["expected"]
