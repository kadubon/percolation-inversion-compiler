"""Minimal TRC datacenter cooling and management-link demo."""

from __future__ import annotations

from itertools import pairwise
from typing import Any

from pydantic import BaseModel

from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.trc.algorithms import (
    compile_frontier,
    finite_tolerance_allocation,
    network_calculus_bounds,
    observation_consistency_residual,
    resource_flow_feasible,
    semiring_path_product,
    trace_normal_form_accepts,
)
from percolation_inversion_compiler.trc.records import (
    CausalEventPosetRecord,
    EventContractRecord,
    ExecutableTraceNormalForm,
    FutureFreedomVector,
    LifecycleDAGRecord,
    MultiHorizonOrder,
    ResourceCalendarRecord,
    ResourceFlowRecord,
    ResourceReservationRecord,
    ToleranceCostKernel,
    ToleranceMenuItem,
    TraceNormalizationCertificate,
    TransitionProofRecord,
    TRCCompileResult,
)


class DatacenterDemoResult(BaseModel):
    observation_residual: float
    network_bounds: dict[str, float]
    semiring_summary: float
    resource_flow_feasible: bool
    resource_flow_residual: float
    tolerance_allocation: dict[str, str]
    compile_result: TRCCompileResult


def _trace(trace_id: str, word: list[str], *, residual: float = 0.0) -> ExecutableTraceNormalForm:
    flow = ResourceFlowRecord(
        trace_id=trace_id,
        scenario_id=f"scenario:{trace_id}",
        reservation_interval=(0.0, 5.0),
        inflow_profile=[0.5, 0.4, 0.3],
        service_profile=[0.4, 0.4, 0.4],
        capacity=1.5,
    )
    calendar = ResourceCalendarRecord(
        calendar_id=f"calendar:{trace_id}",
        capacities={"crew": 2.0},
        reservations=[
            ResourceReservationRecord(
                reservation_id=f"reservation:{trace_id}",
                resource="crew",
                start_tick=0,
                end_tick=2,
                amount=1.0,
            )
        ],
        freshness_version="calendar-v1",
    )
    return ExecutableTraceNormalForm(
        trace_id=trace_id,
        normalized_word=word,
        normalization=TraceNormalizationCertificate(
            trace_id=trace_id,
            source_word=word,
            normalized_word=word,
            confluence_witness=True,
            termination_witness=True,
        ),
        step_proofs=[
            TransitionProofRecord(
                action_class=action,
                precondition={"observed": True},
                postcondition={"bounded_residual": True},
                latency=1.0,
                status=ClaimStatus.SETTLED,
            )
            for action in word
        ],
        precondition={"observed": True},
        postcondition={"bounded_residual": True},
        causal_schedule=CausalEventPosetRecord(
            event_ids=set(word),
            happens_before=list(pairwise(word)),
        ),
        latency_ledger={"ticks": float(len(word))},
        resource_flow_profile=[flow],
        resource_calendar=calendar,
        lifecycle=LifecycleDAGRecord(certificate_versions={"cert": "cert-v1"}),
        future_freedom=FutureFreedomVector(
            vector_id=f"ff:{trace_id}",
            horizons=["now", "next"],
            values={"now": 0.5, "next": 0.7},
            residuals={"now": 0.0, "next": residual},
            order=MultiHorizonOrder(
                order_id=f"horizon:{trace_id}",
                horizons=["now", "next"],
                precedence=[("now", "next")],
            ),
        ),
        certificate_versions=["cert-v1"],
        tolerance_versions=["tol-v1"],
        error_budget=0.5,
        trace_residual=residual,
    )


def _trace_metadata(trace: ExecutableTraceNormalForm) -> dict[str, Any]:
    return {
        "trace_normal_form": trace.model_dump(mode="json"),
        "trace_normal_form_accepted": trace_normal_form_accepts(trace),
    }


def datacenter_demo() -> DatacenterDemoResult:
    """Run the TRC example as a finite stratified frontier compilation."""

    observation_residual = observation_consistency_residual(mismatch_norm=0.4)
    network = EventContractRecord(
        contract_id="mgmt-link",
        arrival_curve=[0.2, 0.5, 0.8, 1.0],
        service_curve=[0.3, 0.6, 0.9, 1.2],
        drop_residual=0.05,
        event_check_cost=0.11,
    )
    network_bounds = network_calculus_bounds(network)
    semiring_summary = semiring_path_product([0.72, 1.10, 0.90], semiring="product")
    resource_flow = ResourceFlowRecord(
        trace_id="two-five-hour-repairs",
        scenario_id="shared-crew",
        reservation_interval=(0.0, 5.0),
        inflow_profile=[1.2, 1.2],
        service_profile=[0.8, 0.9],
        depletion_profile=[0.2, 0.2],
        capacity=1.5,
        conservation_residual=0.1,
    )
    flow_ok, flow_residual = resource_flow_feasible(resource_flow)
    allocation, tolerance_ledger = finite_tolerance_allocation(
        [
            ToleranceCostKernel(
                coordinate="observation",
                finite_menu=[
                    ToleranceMenuItem(
                        name="coarse",
                        fidelity_level="coarse",
                        resource_cost=0.4,
                        residual_increment=0.06,
                    ),
                    ToleranceMenuItem(
                        name="fine",
                        fidelity_level="fine",
                        resource_cost=1.0,
                        residual_increment=0.01,
                    ),
                ],
            ),
            ToleranceCostKernel(
                coordinate="calibration",
                finite_menu=[
                    ToleranceMenuItem(
                        name="coarse",
                        fidelity_level="coarse",
                        computation_cost=0.2,
                        residual_increment=0.04,
                    ),
                    ToleranceMenuItem(
                        name="fine",
                        fidelity_level="fine",
                        computation_cost=0.9,
                        residual_increment=0.01,
                    ),
                ],
            ),
        ],
        budget=0.7,
    )

    airflow_trace = _trace("open-reserve-airflow", ["g_C", "open_reserve_airflow"], residual=0.2)
    sensor_trace = _trace("low-power-sensor-refresh", ["g_C", "sensor_refresh"], residual=0.10)
    feedback_trace = _trace("thermal-feedback-loop", ["g_C", "feedback_loop"], residual=0.35)
    reroute_trace = _trace("management-packet-reroute", ["g_C", "g_N", "reroute"], residual=0.05)
    delay_trace = _trace("thermal-control-packet-delay", ["g_C", "g_N", "g_Q"], residual=0.2)
    records: list[FrontierRecord] = [
        FrontierRecord(
            record_id="open-reserve-airflow",
            benefits={"future_freedom": 1.0, "reserve": 1.0},
            burdens={"residual": 0.2, "cost": 0.6},
            status=ClaimStatus.SETTLED
            if trace_normal_form_accepts(airflow_trace)
            else ClaimStatus.DIAGNOSTIC,
            stratum="main",
            trace_id=airflow_trace.trace_id,
            metadata=_trace_metadata(airflow_trace),
        ),
        FrontierRecord(
            record_id="chiller-overdrive",
            benefits={"future_freedom": 0.7},
            burdens={"residual": 1.3, "risk_cvar": 0.31, "support_miss": 0.08},
            status=ClaimStatus.RISK_PROVISIONAL,
            stratum="risk-provisional",
            metadata={"dual_witness": True},
        ),
        FrontierRecord(
            record_id="thermal-feedback-loop",
            benefits={"future_freedom": 0.8},
            burdens={"residual": 0.35, "cost": 0.7},
            status=ClaimStatus.PROVISIONAL,
            stratum="main",
            trace_id=feedback_trace.trace_id,
            metadata={
                "contraction_factor": 0.72,
                "fallback_log_norm": 1.35,
                **_trace_metadata(feedback_trace),
            },
        ),
        FrontierRecord(
            record_id="management-packet-reroute",
            benefits={"future_freedom": 0.6},
            burdens={
                "backlog": network_bounds["backlog_bound"],
                "delay": network_bounds["delay_bound"],
            },
            status=ClaimStatus.PROVISIONAL,
            stratum="main",
            trace_id=reroute_trace.trace_id,
            metadata=_trace_metadata(reroute_trace),
        ),
        FrontierRecord(
            record_id="low-power-sensor-refresh",
            benefits={"future_freedom": 0.5, "energy_saved": 0.6},
            burdens={"residual": tolerance_ledger.burden_sum(), "cost": 0.6},
            status=ClaimStatus.PROVISIONAL
            if trace_normal_form_accepts(sensor_trace)
            else ClaimStatus.DIAGNOSTIC,
            stratum="main",
            trace_id=sensor_trace.trace_id,
            metadata=_trace_metadata(sensor_trace),
        ),
        FrontierRecord(
            record_id="thermal-control-packet-delay",
            benefits={"future_freedom": semiring_summary},
            burdens={"antichain_width": 2.0},
            status=ClaimStatus.PROVISIONAL,
            stratum="main",
            trace_id=delay_trace.trace_id,
            metadata=_trace_metadata(delay_trace),
        ),
        FrontierRecord(
            record_id="pipe-repairs-and-queue-shift",
            benefits={"future_freedom": 0.9},
            burdens={"resource_flow_residual": flow_residual},
            status=ClaimStatus.PARTIAL if flow_ok else ClaimStatus.DIAGNOSTIC,
            stratum="partial",
        ),
        FrontierRecord(
            record_id="cross-cooling-duct-redesign",
            benefits={"future_freedom": -0.3},
            burdens={"response_width": 1.7, "clock_residual": 0.05},
            status=ClaimStatus.PROVISIONAL,
            stratum="relaxed",
        ),
        FrontierRecord(
            record_id="isolate-lost-network-only",
            benefits={"future_freedom": 0.0},
            burdens={"observation_residual": observation_residual, "communication_residual": 1.0},
            status=ClaimStatus.DIAGNOSTIC,
            stratum="diagnostic",
            metadata={"reason": "no accepted trace normal form"},
        ),
    ]
    result = compile_frontier(records, archive_cap=6)
    result.residual_ledger = result.residual_ledger.combine(
        Ledger().add_coordinate("observation", observation_residual, kind=CoordinateKind.RESIDUAL)
    )
    return DatacenterDemoResult(
        observation_residual=observation_residual,
        network_bounds=network_bounds,
        semiring_summary=semiring_summary,
        resource_flow_feasible=flow_ok,
        resource_flow_residual=flow_residual,
        tolerance_allocation={key: value.name for key, value in allocation.items()},
        compile_result=result,
    )
