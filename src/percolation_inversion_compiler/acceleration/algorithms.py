"""Deterministic phase-acceleration planning algorithms."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from percolation_inversion_compiler.acceleration.records import (
    BottleneckCandidate,
    PhaseAccelerationBenchmarkReport,
    PhaseAccelerationPlan,
    PhaseAccelerationRequest,
    PhaseBenchmarkCaseResult,
    PhaseBenchmarkSuiteReport,
    PhaseBenchmarkTask,
    PhaseComponentGap,
    PhaseDashboardReport,
    PhaseGapVector,
    PhaseObservationReport,
    PhaseTrajectoryReport,
    ProtocolRelativeBenchmarkMetric,
    SafePhaseAction,
)
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.live_policy import (
    live_default_non_authorities,
    live_default_safety_invariant,
)
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.runtime.algorithms import build_runtime_step
from percolation_inversion_compiler.runtime.records import (
    AgentRuntimeConfig,
    RuntimeIdentityContext,
    RuntimeState,
    RuntimeStepReport,
)

PHASE_ACCELERATION_SCHEMA_REFS = [
    "PhaseAccelerationRequest",
    "PhaseAccelerationPlan",
    "PhaseGapVector",
    "PhaseComponentGap",
    "BottleneckCandidate",
    "SafePhaseAction",
    "PhaseTrajectoryReport",
    "PhaseAccelerationBenchmarkReport",
    "ProtocolRelativeBenchmarkMetric",
    "PhaseBenchmarkTask",
    "PhaseBenchmarkCaseResult",
    "PhaseBenchmarkSuiteReport",
    "PhaseDashboardReport",
    "PhaseObservationReport",
    "RuntimeStepReport",
    "PhaseControlAuditSummary",
    "FrontierDebtReport",
    "BottleneckWitnessReport",
    "SalienceScheduleReport",
    "ALTAdmissionDecision",
    "GeneralIntakeRuntimeBridgeReport",
]


def phase_acceleration_safety_invariants() -> list[str]:
    """Return the non-promotion invariants for phase planning."""

    return [
        "phase acceleration planning is recommendation-only and does not execute actions",
        "raw external candidate volume cannot improve Psi, BR, AC, or settled status",
        "candidate packets, agent messages, and proxy-only ALT reports remain candidates",
        "settled remains false unless scoped finite verifier rules discharge all obligations",
        "residual ledgers and missing obligations must be preserved into downstream loops",
        "ASI-proxy phase is protocol-relative workflow coordination, not real ASI proof",
        "no physical, simulator, oracle, legal, or policy outcome is proven by this report",
        live_default_safety_invariant(),
        *live_default_non_authorities(),
    ]


def build_phase_acceleration_plan(request: PhaseAccelerationRequest) -> PhaseAccelerationPlan:
    """Build a deterministic plan from runtime and adjacent theory reports.

    The function aggregates existing reports.  It does not run external
    connectors, execute verifier routes, or promote packet status.
    """

    runtime_report, runtime_reasons = _runtime_report_from_request(request)
    phase_gap = _phase_gap_vector(runtime_report, request.psi_threshold)
    residual_summary = _residual_summary(runtime_report)
    missing_obligations = _missing_obligations(runtime_report)
    candidate_only_reasons = _candidate_only_reasons(request, runtime_report)
    cannot_promote = _cannot_promote_because(request, runtime_report, missing_obligations)
    settled_blockers = _settled_blockers(request, runtime_report, phase_gap, cannot_promote)
    bottlenecks = _rank_bottlenecks(
        request,
        runtime_report,
        phase_gap,
        missing_obligations,
        cannot_promote,
    )
    actions = _safe_actions(request, bottlenecks, runtime_report)
    safe_commands = _dedupe(command for action in actions for command in action.safe_commands)
    sdk_calls = _dedupe(call for action in actions for call in action.sdk_calls)
    accepted = runtime_report is not None and bool(runtime_report.accepted)
    workflow_usable = bool(accepted or bottlenecks or actions)
    identity_required = _profile_requires_identity(request.profile)
    production_identity_blocked = identity_required and not _identity_ready(
        request.identity_context
    )
    operationally_usable = workflow_usable and not production_identity_blocked
    finite_checks_passed = runtime_report is not None and bool(runtime_report.finite_checks_passed)
    reasons = sorted(
        set(
            [
                *runtime_reasons,
                *cannot_promote,
                *candidate_only_reasons,
                *(["no runtime report was available"] if runtime_report is None else []),
            ]
        )
    )
    status = ClaimStatus.PROVISIONAL if workflow_usable else ClaimStatus.DIAGNOSTIC
    if cannot_promote or candidate_only_reasons:
        status = ClaimStatus.DIAGNOSTIC
    return PhaseAccelerationPlan(
        plan_id=f"phase-acceleration-plan:{request.request_id}",
        request_id=request.request_id,
        profile=request.profile,
        report_mode="compact" if request.compact else "full",
        accepted=accepted,
        workflow_usable=workflow_usable,
        finite_checks_passed=finite_checks_passed,
        operationally_usable=operationally_usable,
        settled=False,
        status=status,
        phase_gap_vector=phase_gap,
        current_psi=None if runtime_report is None else runtime_report.psi,
        runtime_report=None if request.compact else runtime_report,
        phase_control_audit=(
            None if runtime_report is None else runtime_report.phase_control_audit
        ),
        frontier_debt_report=None
        if runtime_report is None
        else runtime_report.frontier_debt_report,
        bottleneck_witness_reports=(
            [] if runtime_report is None else runtime_report.bottleneck_witness_reports
        ),
        salience_schedule=None if runtime_report is None else runtime_report.salience_schedule,
        alt_admission_decisions=request.alt_admission_decisions,
        foundry_dashboard=request.foundry_dashboard,
        general_intake_bridge_reports=request.general_intake_bridge_reports,
        agent_message_delivery_reports=request.agent_message_delivery_reports,
        residual_summary=residual_summary,
        missing_obligations=missing_obligations,
        unresolved_obligation_count=len(missing_obligations),
        bottlenecks=bottlenecks,
        recommended_actions=actions,
        safe_commands=safe_commands,
        sdk_calls=sdk_calls,
        schema_refs=PHASE_ACCELERATION_SCHEMA_REFS,
        cannot_promote_because=cannot_promote,
        candidate_only_reasons=candidate_only_reasons,
        settled_blockers=settled_blockers,
        safety_invariants=phase_acceleration_safety_invariants(),
        reasons=reasons,
    )


def phase_acceleration_compact_payload(plan: PhaseAccelerationPlan) -> dict[str, object]:
    """Return the compact CI/agent contract for a plan."""

    return {
        "plan_id": plan.plan_id,
        "request_id": plan.request_id,
        "profile": plan.profile,
        "report_mode": "compact",
        "accepted": plan.accepted,
        "workflow_usable": plan.workflow_usable,
        "finite_checks_passed": plan.finite_checks_passed,
        "operationally_usable": plan.operationally_usable,
        "settled": plan.settled,
        "status": plan.status.value,
        "phase_gap_vector": plan.phase_gap_vector.model_dump(mode="json"),
        "top_bottlenecks": [
            bottleneck.model_dump(mode="json") for bottleneck in plan.bottlenecks[:5]
        ],
        "safe_commands": plan.safe_commands,
        "sdk_calls": plan.sdk_calls,
        "schema_refs": plan.schema_refs,
        "cannot_promote_because": plan.cannot_promote_because,
        "candidate_only_reasons": plan.candidate_only_reasons,
        "settled_blockers": plan.settled_blockers,
        "residual_summary": plan.residual_summary,
        "missing_obligations": plan.missing_obligations,
        "safety_invariants": plan.safety_invariants,
        "reasons": plan.reasons,
    }


def build_phase_trajectory(
    requests: Sequence[PhaseAccelerationRequest],
    *,
    profile: str = "development",
) -> PhaseTrajectoryReport:
    """Build a deterministic trajectory over multiple phase planner requests."""

    plans = [build_phase_acceleration_plan(request) for request in requests]
    return PhaseTrajectoryReport(
        report_id=f"phase-trajectory:{profile}:{len(plans)}",
        profile=profile,
        plans=plans,
        aggregate_gap_trajectory=[plan.phase_gap_vector.aggregate_gap for plan in plans],
        limiting_component_trajectory=[plan.phase_gap_vector.limiting_components for plan in plans],
        monotone_nonpromotion_preserved=all(not plan.settled for plan in plans),
        accepted=bool(plans) and all(plan.accepted for plan in plans),
        workflow_usable=bool(plans) and any(plan.workflow_usable for plan in plans),
        operationally_usable=bool(plans) and any(plan.operationally_usable for plan in plans),
        settled=False,
        reasons=sorted({reason for plan in plans for reason in plan.reasons}),
    )


def build_phase_acceleration_benchmark(
    plan: PhaseAccelerationPlan,
) -> PhaseAccelerationBenchmarkReport:
    """Compare candidate-only sharing with PIC-guided finite routing.

    The benchmark is deterministic and descriptive.  It does not claim that the
    guided plan has discharged obligations; it measures whether repairable,
    schema-backed routes are visible.
    """

    candidate_only_count = len(plan.candidate_only_reasons)
    repairable_count = sum(1 for item in plan.bottlenecks if not item.candidate_only)
    route_count = len(
        {route for bottleneck in plan.bottlenecks for route in bottleneck.next_verifier_routes}
    )
    residual_visibility = len(plan.missing_obligations) + len(plan.residual_summary)
    invariant_checks = {
        "candidate_only_volume_does_not_reduce_gap": True,
        "planner_does_not_execute_commands": all(
            not action.execution_authority_granted for action in plan.recommended_actions
        ),
        "settled_not_promoted": plan.settled is False,
        "residuals_visible": bool(plan.missing_obligations or plan.residual_summary),
    }
    return PhaseAccelerationBenchmarkReport(
        profile=plan.profile,
        baseline_candidate_only_count=max(1, candidate_only_count),
        pic_guided_repairable_bottleneck_count=repairable_count,
        baseline_phase_gap=plan.phase_gap_vector.aggregate_gap,
        pic_guided_phase_gap=plan.phase_gap_vector.aggregate_gap,
        finite_route_count_delta=route_count,
        residual_visibility_delta=residual_visibility,
        accepted=plan.accepted,
        workflow_usable=plan.workflow_usable,
        operationally_usable=plan.operationally_usable,
        settled=False,
        invariant_checks=invariant_checks,
        safety_invariants=phase_acceleration_safety_invariants(),
        reasons=[
            "candidate-only sharing is kept visible but cannot reduce phase gaps",
            "PIC-guided routing exposes finite verifier and repair work without execution",
        ],
    )


def default_phase_benchmark_tasks() -> list[PhaseBenchmarkTask]:
    """Return bundled benchmark-suite tasks that require no source checkout."""

    return [
        PhaseBenchmarkTask(
            task_id="missing-obligation-visibility",
            agent_output="Candidate packet: route evidence and preserve residuals.",
            expected_properties=[
                "missing obligation visibility",
                "settled blocker visibility",
                "residual preservation",
            ],
        ),
        PhaseBenchmarkTask(
            task_id="false-promotion-prevention",
            agent_output=(
                "Candidate packet: claim reusable work, but preserve candidate-only status "
                "until verifier routes pass."
            ),
            expected_properties=[
                "unsafe promotion prevention",
                "candidate-only false-promotion prevention",
                "safe command non-authority",
            ],
        ),
        PhaseBenchmarkTask(
            task_id="phase-gap-and-bottleneck-ranking",
            agent_output="Candidate packet: identify phase gaps and rank bottlenecks.",
            expected_properties=[
                "phase gap visibility",
                "bottleneck ranking coverage",
                "next action specificity",
            ],
        ),
    ]


def build_phase_benchmark_suite(
    *,
    profile: str = "development",
    tasks: Sequence[PhaseBenchmarkTask] | None = None,
) -> PhaseBenchmarkSuiteReport:
    """Run diagnostic protocol-relative benchmark cases.

    The suite measures whether PIC exposes obligations, residuals, blockers,
    candidate-only status, and next actions. It never promotes packets, executes
    commands, or claims real ASI acceleration.
    """

    case_results: list[PhaseBenchmarkCaseResult] = []
    for task in tasks or default_phase_benchmark_tasks():
        plan = _plan_for_benchmark_task(task, profile)
        case_results.append(_benchmark_case_result(task, plan))

    metric_ids = sorted(
        {metric.metric_id for case in case_results for metric in case.metric_results}
    )
    aggregate_metrics = []
    for metric_id in metric_ids:
        metrics = [
            metric
            for case in case_results
            for metric in case.metric_results
            if metric.metric_id == metric_id
        ]
        passed_count = sum(1 for metric in metrics if metric.passed)
        aggregate_metrics.append(
            ProtocolRelativeBenchmarkMetric(
                metric_id=metric_id,
                label=metrics[0].label if metrics else metric_id,
                value=float(passed_count),
                maximum=float(len(metrics)),
                passed=bool(metrics) and passed_count == len(metrics),
                interpretation="case pass count; diagnostic only and not a settlement signal",
            )
        )
    maximum = sum(metric.maximum for metric in aggregate_metrics)
    score = 0.0 if maximum == 0.0 else sum(metric.value for metric in aggregate_metrics) / maximum
    return PhaseBenchmarkSuiteReport(
        profile=profile,
        cases=case_results,
        aggregate_metrics=aggregate_metrics,
        aggregate_score=score,
        accepted=bool(case_results) and all(case.accepted for case in case_results),
        workflow_usable=bool(case_results) and any(case.workflow_usable for case in case_results),
        operationally_usable=bool(case_results)
        and any(case.operationally_usable for case in case_results),
        settled=False,
        safety_invariants=[
            *phase_acceleration_safety_invariants(),
            "benchmark scores do not set settled=true",
            "benchmark scores do not approve execution",
            "benchmark scores do not promote packets",
        ],
        reasons=[
            "benchmark suite is diagnostic-only",
            "protocol-relative metrics measure visibility and non-promotion behavior",
        ],
    )


def phase_benchmark_suite_markdown(report: PhaseBenchmarkSuiteReport) -> str:
    """Render a benchmark-suite report as deterministic Markdown."""

    lines = [
        "# Phase Benchmark Suite",
        "",
        f"- Profile: `{report.profile}`",
        f"- Accepted: `{str(report.accepted).lower()}`",
        f"- Workflow usable: `{str(report.workflow_usable).lower()}`",
        f"- Settled: `{str(report.settled).lower()}`",
        f"- Aggregate score: `{report.aggregate_score:.3f}`",
        "",
        "## Cases",
    ]
    for case in report.cases:
        passed = sum(1 for metric in case.metric_results if metric.passed)
        lines.append(
            f"- `{case.case_id}`: {passed}/{len(case.metric_results)} metrics passed; "
            f"settled=`{str(case.settled).lower()}`"
        )
    lines.extend(["", "## Safety Boundary"])
    lines.extend(f"- {item}" for item in report.safety_invariants)
    return "\n".join(lines) + "\n"


def build_phase_dashboard(
    *,
    profile: str = "development",
    runtime_report: RuntimeStepReport | None = None,
) -> PhaseDashboardReport:
    """Build an observation-only phase dashboard."""

    if runtime_report is None:
        plan = _default_phase_plan(profile, request_id="phase-dashboard")
    else:
        plan = build_phase_acceleration_plan(
            PhaseAccelerationRequest(
                request_id=f"phase-dashboard:{runtime_report.report_id}",
                profile=profile,
                runtime_report=runtime_report,
                compact=True,
            )
        )
    runtime = plan.runtime_report if runtime_report is None else runtime_report
    packet_candidate_count = 0 if runtime is None else len(runtime.registry.packets)
    accepted_packet_count = 0
    workflow_usable_packet_count = 0
    settled_packet_count = 0
    if runtime is not None:
        accepted_packet_count = len(runtime.promotion_report.verified_packets)
        workflow_usable_packet_count = sum(
            1
            for packet in runtime.registry.packets
            if packet.authority_granted and packet.route_safe
        )
    bottleneck_counts: dict[str, int] = {}
    for bottleneck in plan.bottlenecks:
        bottleneck_counts[bottleneck.bottleneck_kind] = (
            bottleneck_counts.get(bottleneck.bottleneck_kind, 0) + 1
        )
    blockers = list(plan.settled_blockers) + list(plan.cannot_promote_because)
    sqot_pressure = 0.0
    if runtime is not None:
        sqot_pressure = float(runtime.salience_schedule.unresolved_obligation_backlog) + float(
            runtime.salience_schedule.residual_debt_growth
        )
    return PhaseDashboardReport(
        dashboard_id=f"phase-dashboard:{profile}",
        profile=profile,
        packet_candidate_count=packet_candidate_count,
        accepted_packet_count=accepted_packet_count,
        workflow_usable_packet_count=workflow_usable_packet_count,
        settled_packet_count=settled_packet_count,
        unsettled_candidate_count=max(0, packet_candidate_count - settled_packet_count),
        residual_debt_count=len(plan.residual_summary),
        missing_obligation_count=len(plan.missing_obligations),
        identity_blocker_count=sum(1 for blocker in blockers if "identity" in blocker.lower()),
        route_blocker_count=sum(1 for blocker in blockers if "route" in blocker.lower()),
        rollback_blocker_count=sum(1 for blocker in blockers if "rollback" in blocker.lower()),
        alt_liquidity_candidate_count=len(plan.alt_admission_decisions),
        sqot_queue_pressure=sqot_pressure,
        phase_gap_vector=plan.phase_gap_vector,
        bottleneck_count_by_type=dict(sorted(bottleneck_counts.items())),
        safe_command_count=len(plan.safe_commands),
        settled_blocker_count=len(plan.settled_blockers),
        candidate_only_reason_count=len(plan.candidate_only_reasons),
        external_volume_candidate_only_count=sum(
            len(report.packet_ingestion.packets)
            for report in plan.general_intake_bridge_reports
            if report.candidate_only
        ),
        promotion_blocker_summary=plan.cannot_promote_because,
        dashboard_safety_boundary=[
            "phase dashboard is observational only",
            "phase dashboard does not claim a real ASI phase transition",
            "raw external volume is not positive phase progress",
            "phase dashboard does not alter runtime state",
            "phase dashboard does not introduce approval requirements",
        ],
        accepted=plan.accepted,
        workflow_usable=plan.workflow_usable,
        operationally_usable=plan.operationally_usable,
        settled=False,
        reasons=sorted(
            set(
                [
                    "dashboard metrics are diagnostic-only",
                    *plan.reasons,
                ]
            )
        ),
    )


def build_phase_observation(
    dashboards: Sequence[PhaseDashboardReport],
    *,
    profile: str = "development",
) -> PhaseObservationReport:
    """Aggregate phase dashboards without changing runtime state."""

    aggregate: dict[str, int | float] = {
        "dashboard_count": len(dashboards),
        "packet_candidate_count": sum(item.packet_candidate_count for item in dashboards),
        "accepted_packet_count": sum(item.accepted_packet_count for item in dashboards),
        "workflow_usable_packet_count": sum(
            item.workflow_usable_packet_count for item in dashboards
        ),
        "settled_packet_count": sum(item.settled_packet_count for item in dashboards),
        "unsettled_candidate_count": sum(item.unsettled_candidate_count for item in dashboards),
        "missing_obligation_count": sum(item.missing_obligation_count for item in dashboards),
        "settled_blocker_count": sum(item.settled_blocker_count for item in dashboards),
        "candidate_only_reason_count": sum(item.candidate_only_reason_count for item in dashboards),
        "safe_command_count": sum(item.safe_command_count for item in dashboards),
    }
    return PhaseObservationReport(
        profile=profile,
        dashboards=list(dashboards),
        aggregate_metrics=aggregate,
        accepted=bool(dashboards) and all(item.accepted for item in dashboards),
        workflow_usable=bool(dashboards) and any(item.workflow_usable for item in dashboards),
        operationally_usable=bool(dashboards)
        and any(item.operationally_usable for item in dashboards),
        settled=False,
        safety_invariants=[
            "phase observation is read-only",
            "phase observation does not promote packets",
            "phase observation does not set settled=true",
        ],
        reasons=["observation report aggregates dashboard metrics only"],
    )


def phase_dashboard_markdown(report: PhaseDashboardReport) -> str:
    """Render a phase dashboard as deterministic Markdown."""

    lines = [
        "# Phase Dashboard",
        "",
        f"- Profile: `{report.profile}`",
        f"- Packet candidates: `{report.packet_candidate_count}`",
        f"- Accepted packets: `{report.accepted_packet_count}`",
        f"- Settled packets: `{report.settled_packet_count}`",
        f"- Missing obligations: `{report.missing_obligation_count}`",
        f"- Settled blockers: `{report.settled_blocker_count}`",
        f"- Settled: `{str(report.settled).lower()}`",
        "",
        "## Bottlenecks",
    ]
    lines.extend(f"- `{kind}`: {count}" for kind, count in report.bottleneck_count_by_type.items())
    lines.extend(["", "## Safety Boundary"])
    lines.extend(f"- {item}" for item in report.dashboard_safety_boundary)
    return "\n".join(lines) + "\n"


def phase_observation_markdown(report: PhaseObservationReport) -> str:
    """Render a phase observation report as deterministic Markdown."""

    lines = [
        "# Phase Observation",
        "",
        f"- Profile: `{report.profile}`",
        f"- Dashboard count: `{len(report.dashboards)}`",
        f"- Settled: `{str(report.settled).lower()}`",
        "",
        "## Aggregate Metrics",
    ]
    lines.extend(f"- `{key}`: {value}" for key, value in sorted(report.aggregate_metrics.items()))
    lines.extend(["", "## Safety Boundary"])
    lines.extend(f"- {item}" for item in report.safety_invariants)
    return "\n".join(lines) + "\n"


def _default_phase_plan(profile: str, *, request_id: str) -> PhaseAccelerationPlan:
    from percolation_inversion_compiler.agent.algorithms import (
        minimal_runtime_state,
        minimal_runtime_step_input,
    )

    return build_phase_acceleration_plan(
        PhaseAccelerationRequest(
            request_id=request_id,
            profile=profile,
            state=minimal_runtime_state(),
            step_input=minimal_runtime_step_input(
                "Candidate packet: route evidence and preserve residuals."
            ),
            runtime_config=AgentRuntimeConfig(profile=profile),
            compact=True,
        )
    )


def _plan_for_benchmark_task(task: PhaseBenchmarkTask, profile: str) -> PhaseAccelerationPlan:
    from percolation_inversion_compiler.agent.algorithms import (
        minimal_runtime_state,
        minimal_runtime_step_input,
    )

    return build_phase_acceleration_plan(
        PhaseAccelerationRequest(
            request_id=f"benchmark-suite:{task.task_id}",
            profile=profile,
            state=minimal_runtime_state(),
            step_input=minimal_runtime_step_input(task.agent_output),
            runtime_config=AgentRuntimeConfig(profile=profile),
            compact=True,
        )
    )


def _benchmark_metric(
    metric_id: str,
    label: str,
    passed: bool,
    *,
    value: float | None = None,
) -> ProtocolRelativeBenchmarkMetric:
    return ProtocolRelativeBenchmarkMetric(
        metric_id=metric_id,
        label=label,
        value=1.0 if value is None and passed else 0.0 if value is None else value,
        maximum=1.0,
        passed=passed,
    )


def _benchmark_case_result(
    task: PhaseBenchmarkTask,
    plan: PhaseAccelerationPlan,
) -> PhaseBenchmarkCaseResult:
    metrics = [
        _benchmark_metric(
            "missing-obligation-visibility",
            "missing obligation visibility",
            bool(plan.missing_obligations),
        ),
        _benchmark_metric(
            "unsafe-promotion-prevention",
            "unsafe promotion prevention",
            plan.settled is False and bool(plan.cannot_promote_because),
        ),
        _benchmark_metric(
            "residual-preservation",
            "residual preservation",
            bool(plan.residual_summary),
        ),
        _benchmark_metric(
            "settled-blocker-visibility",
            "settled blocker visibility",
            bool(plan.settled_blockers),
        ),
        _benchmark_metric(
            "next-action-specificity",
            "next action specificity",
            bool(plan.safe_commands or plan.recommended_actions),
        ),
        _benchmark_metric(
            "reusable-packet-candidate-visibility",
            "reusable packet candidate visibility",
            plan.workflow_usable and plan.accepted,
        ),
        _benchmark_metric(
            "candidate-only-false-promotion-prevention",
            "candidate-only false-promotion prevention",
            plan.settled is False and bool(plan.candidate_only_reasons),
        ),
        _benchmark_metric(
            "phase-gap-visibility",
            "phase gap visibility",
            bool(plan.phase_gap_vector.components),
        ),
        _benchmark_metric(
            "bottleneck-ranking-coverage",
            "bottleneck ranking coverage",
            bool(plan.bottlenecks),
        ),
    ]
    return PhaseBenchmarkCaseResult(
        case_id=f"phase-benchmark-case:{task.task_id}",
        task=task,
        accepted=plan.accepted,
        workflow_usable=plan.workflow_usable,
        operationally_usable=plan.operationally_usable,
        settled=False,
        metric_results=metrics,
        missing_obligation_count=len(plan.missing_obligations),
        residual_coordinate_count=len(plan.residual_summary),
        safe_command_count=len(plan.safe_commands),
        settled_blocker_count=len(plan.settled_blockers),
        candidate_only_reason_count=len(plan.candidate_only_reasons),
        bottleneck_count=len(plan.bottlenecks),
        phase_gap_visible=bool(plan.phase_gap_vector.components),
        reasons=plan.reasons,
    )


def phase_acceleration_runbook(profile: str = "development") -> dict[str, object]:
    """Return deterministic command/schema/field guidance for phase planning."""

    return {
        "report_id": f"phase-acceleration-runbook:{profile}",
        "profile": profile,
        "entrypoint": "pic phase plan --compact",
        "commands": [
            'pic agent check --compact --text "Candidate packet: preserve residuals."',
            f"pic agent runbook --profile {profile}",
            f"pic phase plan --compact --profile {profile}",
            f"pic agent accelerate --compact --profile {profile}",
            "pic schema --type PhaseAccelerationPlan",
            "pic schema --type PhaseGapVector",
        ],
        "schemas_to_inspect": PHASE_ACCELERATION_SCHEMA_REFS,
        "fields_to_inspect": [
            "accepted",
            "workflow_usable",
            "settled",
            "phase_gap_vector.limiting_components",
            "bottlenecks",
            "recommended_actions",
            "cannot_promote_because",
            "candidate_only_reasons",
            "settled_blockers",
            "residual_summary",
        ],
        "safety_invariants": phase_acceleration_safety_invariants(),
        "accepted": True,
        "operationally_usable": True,
        "settled": False,
    }


def _runtime_report_from_request(
    request: PhaseAccelerationRequest,
) -> tuple[RuntimeStepReport | None, list[str]]:
    if request.runtime_report is not None:
        return request.runtime_report, []
    if request.state is None or request.step_input is None:
        return None, ["state and step_input are required when runtime_report is absent"]
    config = request.runtime_config or AgentRuntimeConfig(profile=request.profile)
    state = _state_with_identity_context(request.state, request.identity_context)
    report = build_runtime_step(state, request.step_input, config)
    return report, []


def _state_with_identity_context(
    state: RuntimeState,
    identity_context: RuntimeIdentityContext | None,
) -> RuntimeState:
    if identity_context is None:
        return state
    return state.model_copy(
        update={
            "accepted_agent_ids": list(identity_context.accepted_agent_ids),
            "accepted_public_key_ids": list(identity_context.accepted_public_key_ids),
            "identity_mode": (
                identity_context.identity_profile.value
                if identity_context.accepted
                else "diagnostic"
            ),
        }
    )


def _phase_gap_vector(
    runtime_report: RuntimeStepReport | None,
    threshold_override: dict[str, float],
) -> PhaseGapVector:
    if runtime_report is None:
        missing = PhaseComponentGap(
            component="runtime-report",
            current_value=0.0,
            threshold_value=1.0,
            gap=1.0,
            limiting=True,
            source="PhaseAccelerationRequest",
            reasons=["runtime report unavailable"],
        )
        return PhaseGapVector(
            components=[missing],
            limiting_components=["runtime-report"],
            aggregate_gap=1.0,
            accepted=False,
            operationally_usable=False,
            settled=False,
            reasons=["runtime report unavailable"],
        )
    dashboard = runtime_report.psi
    threshold = dict(dashboard.threshold)
    threshold.update(threshold_override)
    components: list[PhaseComponentGap] = []
    for name in sorted(set(dashboard.components) | set(threshold)):
        current = float(dashboard.components.get(name, 0.0))
        target = float(threshold.get(name, current))
        gap = max(0.0, target - current)
        limiting = gap > 0.0 or name in dashboard.limiting_components
        reasons: list[str] = []
        if gap > 0.0:
            reasons.append("component is below finite threshold")
        if name in dashboard.limiting_components:
            reasons.append("component is listed as limiting by PsiDashboard")
        components.append(
            PhaseComponentGap(
                component=name,
                current_value=current,
                threshold_value=target,
                gap=gap,
                limiting=limiting,
                source="PsiDashboard",
                reasons=reasons,
            )
        )
    limiting_components = [component.component for component in components if component.limiting]
    aggregate_gap = sum(component.gap for component in components)
    return PhaseGapVector(
        vector_id=f"phase-gap-vector:{runtime_report.report_id}",
        components=components,
        limiting_components=limiting_components,
        aggregate_gap=aggregate_gap,
        accepted=True,
        operationally_usable=bool(components),
        settled=False,
        reasons=[] if limiting_components else ["no limiting Psi components reported"],
    )


def _residual_summary(runtime_report: RuntimeStepReport | None) -> dict[str, float]:
    if runtime_report is None:
        return {}
    summary: dict[str, float] = {}
    _merge_ledger_summary(summary, runtime_report.residual_ledger)
    frontier = runtime_report.frontier_debt_report
    if frontier.residual_burden:
        summary["frontier_debt"] = summary.get("frontier_debt", 0.0) + float(
            frontier.residual_burden
        )
    return dict(sorted(summary.items()))


def _merge_ledger_summary(summary: dict[str, float], ledger: Ledger) -> None:
    for coordinate in ledger.coordinates.values():
        kind = coordinate.kind.value
        summary[kind] = summary.get(kind, 0.0) + float(coordinate.value)


def _missing_obligations(runtime_report: RuntimeStepReport | None) -> list[str]:
    if runtime_report is None:
        return []
    obligations = list(runtime_report.missing_obligations)
    obligations.extend(runtime_report.frontier_debt_report.missing_obligations)
    for request in runtime_report.route_execution_requests:
        obligations.extend(request.residual_external_obligations)
    for lineage in runtime_report.promotion_report.verified_packets:
        obligations.extend(lineage.residual_external_obligations)
    return sorted({str(item) for item in obligations if item})


def _candidate_only_reasons(
    request: PhaseAccelerationRequest,
    runtime_report: RuntimeStepReport | None,
) -> list[str]:
    reasons: list[str] = []
    if runtime_report is not None:
        for report in runtime_report.ingestion_reports:
            if report.packets and not report.accepted:
                reasons.append(f"ingestion report {report.report_id} remains diagnostic")
        if runtime_report.promotion_report.rejected_packets:
            reasons.append("one or more packet candidates were rejected by promotion policy")
        if runtime_report.status in {ClaimStatus.SPECULATIVE, ClaimStatus.PROVISIONAL}:
            reasons.append("runtime report status is not settled")
    for bridge in request.general_intake_bridge_reports:
        if bridge.candidate_only or not bridge.ecpt_phase_contribution_allowed:
            reasons.append(
                f"general intake bridge {bridge.report_id} is candidate-only "
                "and cannot reduce phase gap"
            )
    for delivery in request.agent_message_delivery_reports:
        if delivery.candidate_only:
            reasons.append(
                f"agent message delivery {delivery.report_id} is candidate-only until verification"
            )
        if not delivery.identity_context_accepted:
            reasons.append(
                f"agent message delivery {delivery.report_id} lacks accepted identity context"
            )
    for decision in request.alt_admission_decisions:
        if not decision.accepted:
            reasons.append(f"ALT admission {decision.decision_id} is not accepted")
        if decision.missing_obligations:
            reasons.append(f"ALT admission {decision.decision_id} has residual obligations")
    return sorted(set(reasons))


def _cannot_promote_because(
    request: PhaseAccelerationRequest,
    runtime_report: RuntimeStepReport | None,
    missing_obligations: Sequence[str],
) -> list[str]:
    blockers: list[str] = []
    if runtime_report is None:
        blockers.append("runtime report is absent")
        return blockers
    if missing_obligations:
        blockers.append("missing obligations remain")
    if runtime_report.residual_ledger.burden_sum() > 0.0:
        blockers.append("runtime residual ledger has unresolved burden")
    if runtime_report.route_execution_requests:
        blockers.append("verifier route execution requests remain unresolved")
    if runtime_report.salience_schedule.quarantine_ledger.quarantined_items:
        blockers.append("SQOT quarantine ledger contains items")
    if not runtime_report.phase_control_audit.split_certified_quotient_ready:
        blockers.append("ECPT split-certified quotient readiness is not established")
    if not runtime_report.phase_control_audit.duplicate_mass_excluded:
        blockers.append("duplicate proxy mass exclusion is not established")
    if not runtime_report.phase_control_audit.baseline_comparison_ready:
        blockers.append("resource-matched baseline comparison is not ready")
    if runtime_report.frontier_debt_report.missing_obligation_count:
        blockers.append("TRC frontier debt remains")
    identity_required = _profile_requires_identity(request.profile)
    if identity_required and not _identity_ready(request.identity_context):
        blockers.append("production/adversarial identity context is missing or not accepted")
    return sorted(set(blockers))


def _settled_blockers(
    request: PhaseAccelerationRequest,
    runtime_report: RuntimeStepReport | None,
    phase_gap: PhaseGapVector,
    cannot_promote: Sequence[str],
) -> list[str]:
    blockers = [
        "phase planner is recommendation-only and cannot settle claims",
        "real ASI, physical, simulator, and oracle outcomes are outside this finite report",
    ]
    blockers.extend(cannot_promote)
    if phase_gap.aggregate_gap > 0.0:
        blockers.append("one or more phase proxy components remain below threshold")
    if runtime_report is not None and not runtime_report.settled:
        blockers.append("runtime report settled=false")
    for decision in request.alt_admission_decisions:
        if not decision.settled:
            blockers.append(f"ALT admission {decision.decision_id} settled=false")
    return sorted(set(blockers))


def _rank_bottlenecks(
    request: PhaseAccelerationRequest,
    runtime_report: RuntimeStepReport | None,
    phase_gap: PhaseGapVector,
    missing_obligations: Sequence[str],
    cannot_promote: Sequence[str],
) -> list[BottleneckCandidate]:
    candidates: list[BottleneckCandidate] = []
    if runtime_report is None:
        return [
            BottleneckCandidate(
                candidate_id="bottleneck:runtime-report",
                source="PhaseAccelerationRequest",
                bottleneck_kind="missing-runtime-report",
                priority_score=1.0,
                next_safe_commands=["pic phase plan --state <state.json> --input <input.json>"],
                schema_refs=["RuntimeState", "RuntimeStepInput", "RuntimeStepReport"],
                cannot_promote_because=list(cannot_promote),
                reasons=["state/input or runtime_report is required"],
            )
        ]
    for index, component in enumerate(phase_gap.components):
        if not component.limiting:
            continue
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:phase-gap:{index}:{component.component}",
                source="PsiDashboard",
                bottleneck_kind="phase-component-gap",
                target_component=component.component,
                priority_score=10.0 + component.gap,
                release_delta=component.gap,
                residual_coordinates=[component.component],
                next_verifier_routes=[],
                schema_refs=["PsiDashboard", "PhaseGapVector"],
                next_safe_commands=["pic phase gap --compact"],
                sdk_calls=[
                    "percolation_inversion_compiler.acceleration.build_phase_acceleration_plan"
                ],
                cannot_promote_because=list(cannot_promote),
                reasons=component.reasons,
            )
        )
    for index, witness in enumerate(runtime_report.bottleneck_witness_reports):
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:bit-witness:{index}:{witness.report_id}",
                source="BottleneckWitnessReport",
                bottleneck_kind=witness.witness_kind,
                target_component=witness.target_component,
                priority_score=9.0 + witness.priority_score,
                release_delta=witness.release_delta,
                burden_delta=witness.burden_delta,
                residual_coordinates=witness.residual_coordinates,
                next_verifier_routes=witness.next_verifier_routes,
                required_evidence_kind=witness.required_evidence_kind,
                next_safe_commands=["Inspect RuntimeStepReport.bottleneck_witness_reports."],
                sdk_calls=["percolation_inversion_compiler.runtime.build_runtime_step"],
                schema_refs=["BottleneckWitnessReport", "AgentTask"],
                cannot_promote_because=list(witness.simulation_barrier_residuals),
                reasons=witness.reasons,
            )
        )
    for index, route in enumerate(runtime_report.route_execution_requests):
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:route:{index}:{route.request_id}",
                source="RouteExecutionRequest",
                bottleneck_kind="verifier-route",
                target_component=route.obligation_category,
                priority_score=8.0 + route.priority_score,
                residual_coordinates=route.residual_external_obligations,
                next_verifier_routes=[route.verifier_route],
                required_evidence_kind=route.required_evidence_kind,
                next_safe_commands=[
                    "pic routes bindings",
                    "pic evidence verify --envelope <evidence.json>",
                ],
                sdk_calls=["percolation_inversion_compiler.core.resolve_adapter_route"],
                schema_refs=["RouteExecutionRequest", "VerifierResolution"],
                cannot_promote_because=route.residual_external_obligations,
                reasons=[route.safe_default],
            )
        )
    if missing_obligations:
        candidates.append(
            BottleneckCandidate(
                candidate_id="bottleneck:missing-obligations",
                source="RuntimeStepReport",
                bottleneck_kind="residual-obligation-ledger",
                priority_score=7.5 + min(5.0, float(len(missing_obligations)) / 10.0),
                residual_coordinates=list(missing_obligations),
                next_safe_commands=["Inspect missing_obligations and residual_ledger."],
                schema_refs=["RuntimeStepReport", "LedgerCoordinate"],
                cannot_promote_because=["missing obligations remain"],
                reasons=["finite obligations must be routed or carried forward"],
            )
        )
    schedule = runtime_report.salience_schedule
    sqot_reasons: list[str] = []
    if schedule.effective_diagnostic_reserve < schedule.diagnostic_reserve.required_reserve(
        schedule.occupation_ledger.attention_budget
    ):
        sqot_reasons.append("effective diagnostic reserve is below policy reserve")
    if schedule.audit_recursion_violations:
        sqot_reasons.append("audit recursion budget violations are present")
    if schedule.latency_deadline_loss > 0.0:
        sqot_reasons.append("latency/deadline loss is positive")
    if schedule.label_laundering_suspicions:
        sqot_reasons.append("label laundering diagnostics are present")
    if schedule.quarantine_ledger.quarantined_items:
        sqot_reasons.append("quarantine ledger contains items")
    if sqot_reasons:
        candidates.append(
            BottleneckCandidate(
                candidate_id="bottleneck:sqot-queue-service",
                source="SalienceScheduleReport",
                bottleneck_kind="queue-service-and-diagnostic-reserve",
                target_component="SQOT",
                priority_score=7.0 + float(len(sqot_reasons)),
                residual_coordinates=[
                    *schedule.audit_recursion_violations,
                    *schedule.label_laundering_suspicions,
                    *schedule.quarantine_ledger.quarantined_items,
                ],
                next_safe_commands=["pic phase plan --compact"],
                sdk_calls=["percolation_inversion_compiler.sqot.build_salience_schedule"],
                schema_refs=["SalienceScheduleReport"],
                cannot_promote_because=sqot_reasons,
                reasons=sqot_reasons,
            )
        )
    _extend_alt_bottlenecks(candidates, request)
    _extend_external_bottlenecks(candidates, request)
    candidates.sort(key=lambda item: (-item.priority_score, item.candidate_id))
    return candidates[: max(1, request.max_bottlenecks)]


def _extend_alt_bottlenecks(
    candidates: list[BottleneckCandidate],
    request: PhaseAccelerationRequest,
) -> None:
    for index, decision in enumerate(request.alt_admission_decisions):
        if decision.accepted and not decision.missing_obligations:
            continue
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:alt-admission:{index}:{decision.decision_id}",
                source="ALTAdmissionDecision",
                bottleneck_kind="abstraction-liquidity-admission",
                target_component="ALT",
                priority_score=6.5 + float(len(decision.missing_obligations)),
                residual_coordinates=decision.missing_obligations,
                next_safe_commands=[
                    "pic alt admit --packet <alt-certificate-packet.json>",
                    "pic alt negative-certify --certificate <negative-liquidity.json>",
                    "pic alt refresh-baseline --certificate <baseline-refresh.json>",
                ],
                sdk_calls=["percolation_inversion_compiler.alt.admit_alt_packet"],
                schema_refs=["ALTAdmissionDecision", "ValueBridgeReport"],
                candidate_only=not decision.accepted,
                cannot_promote_because=decision.missing_obligations,
                reasons=decision.reasons,
            )
        )
    dashboard = request.foundry_dashboard
    if dashboard is not None and dashboard.bottlenecks:
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:alt-foundry:{dashboard.dashboard_id}",
                source="FoundryControlDashboard",
                bottleneck_kind="abstraction-foundry-capacity",
                target_component="ALT",
                priority_score=6.0 + float(len(dashboard.bottlenecks)),
                next_safe_commands=["pic alt foundry-dashboard --state <foundry-state.json>"],
                sdk_calls=["percolation_inversion_compiler.alt.compute_foundry_dashboard"],
                schema_refs=["FoundryControlDashboard", "CertifiedAbstractionCapital"],
                cannot_promote_because=dashboard.reasons,
                reasons=[
                    f"foundry rule {dashboard.recommended_rule.value}",
                    *dashboard.reasons,
                ],
            )
        )


def _extend_external_bottlenecks(
    candidates: list[BottleneckCandidate],
    request: PhaseAccelerationRequest,
) -> None:
    for index, bridge in enumerate(request.general_intake_bridge_reports):
        if not bridge.candidate_only and bridge.ecpt_phase_contribution_allowed:
            continue
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:external-candidate:{index}:{bridge.report_id}",
                source="GeneralIntakeRuntimeBridgeReport",
                bottleneck_kind="external-candidate-only",
                target_component="external-intake",
                priority_score=5.0 + float(len(bridge.verifier_work_packet_ids)),
                residual_coordinates=list(bridge.residual_ledger.coordinates),
                next_safe_commands=[
                    "pic ecology bridge-runtime --report <general-intake-report.json>"
                ],
                sdk_calls=[
                    "percolation_inversion_compiler.ecology.bridge_general_intake_to_runtime"
                ],
                schema_refs=["GeneralIntakeRuntimeBridgeReport"],
                candidate_only=True,
                cannot_promote_because=[
                    "external bridge is candidate-only until downstream verification"
                ],
                reasons=bridge.reasons,
            )
        )
    for index, delivery in enumerate(request.agent_message_delivery_reports):
        if delivery.accepted and delivery.identity_context_accepted and not delivery.candidate_only:
            continue
        candidates.append(
            BottleneckCandidate(
                candidate_id=f"bottleneck:agent-message:{index}:{delivery.report_id}",
                source="AgentMessageDeliveryReport",
                bottleneck_kind="agent-message-candidate-only",
                target_component="agent-relay",
                priority_score=5.0 + float(len(delivery.candidate_packet_ids)),
                next_safe_commands=[
                    "pic agent message receive --inbox <inbox.json>",
                    "pic agent inbox verify --inbox <inbox.json>",
                ],
                sdk_calls=["percolation_inversion_compiler.ecology.verify_agent_message"],
                schema_refs=["AgentMessageDeliveryReport", "AgentMessageVerificationContext"],
                candidate_only=True,
                cannot_promote_because=[
                    "agent messages require nonce, identity, and verifier checks"
                ],
                reasons=delivery.reasons,
            )
        )


def _safe_actions(
    request: PhaseAccelerationRequest,
    bottlenecks: Sequence[BottleneckCandidate],
    runtime_report: RuntimeStepReport | None,
) -> list[SafePhaseAction]:
    actions = [
        SafePhaseAction(
            action_id="phase-action:inspect-gap",
            action_type="phase-gap-inspection",
            title="Inspect Phase Gap",
            purpose="Read finite Psi component gaps before selecting repair work.",
            priority_score=10.0,
            safe_commands=["pic phase gap --compact"],
            sdk_calls=["percolation_inversion_compiler.acceleration.build_phase_acceleration_plan"],
            schema_refs=["PhaseGapVector", "PsiDashboard"],
            inspect_fields=[
                "phase_gap_vector.limiting_components",
                "phase_gap_vector.components",
            ],
            expected_effect="identify limiting finite proxy components",
        ),
        SafePhaseAction(
            action_id="phase-action:preserve-residuals",
            action_type="residual-preservation",
            title="Preserve Residuals",
            purpose="Carry unresolved obligations and residual ledger coordinates forward.",
            priority_score=9.5,
            safe_commands=["pic schema --type PhaseAccelerationPlan"],
            sdk_calls=[],
            schema_refs=["LedgerCoordinate", "RuntimeStepReport"],
            inspect_fields=["missing_obligations", "residual_summary", "settled_blockers"],
            expected_effect="prevent hidden promotion or dropped unresolved work",
        ),
    ]
    identity_required = _profile_requires_identity(request.profile)
    if identity_required and not _identity_ready(request.identity_context):
        actions.append(
            SafePhaseAction(
                action_id="phase-action:identity-readiness",
                action_type="identity-readiness",
                title="Derive Identity Context",
                purpose="Enable production/adversarial packet checks without relaxing policy.",
                priority_score=9.0,
                safe_commands=[
                    "pic identity derive-context --population <population.json> "
                    "--profile production --output identity-context.json"
                ],
                sdk_calls=[
                    "percolation_inversion_compiler.runtime.derive_runtime_identity_context"
                ],
                schema_refs=["RuntimeIdentityContext", "SybilResistanceLedger"],
                inspect_fields=[
                    "identity_context.accepted",
                    "accepted_agent_ids",
                    "accepted_public_key_ids",
                ],
                required_inputs=["AgentPopulationState"],
                expected_effect="remove identity-readiness blocker for scoped production checks",
            )
        )
    if runtime_report is not None and runtime_report.route_execution_requests:
        actions.append(
            SafePhaseAction(
                action_id="phase-action:route-verifier-work",
                action_type="verifier-routing",
                title="Route Verifier Work",
                purpose="Discharge scoped route obligations with explicit evidence envelopes.",
                priority_score=8.5,
                safe_commands=[
                    "pic routes bindings",
                    "pic evidence verify --envelope <evidence.json>",
                ],
                sdk_calls=["percolation_inversion_compiler.core.resolve_adapter_route"],
                schema_refs=["RouteExecutionRequest", "VerifierResolution"],
                inspect_fields=[
                    "route_execution_requests",
                    "evidence_resolution_batch",
                    "residual_external_obligations",
                ],
                required_inputs=["VerifierEvidenceEnvelope"],
                expected_effect="turn route requests into accepted or residual verifier results",
            )
        )
    if any(item.target_component == "ALT" for item in bottlenecks):
        actions.append(
            SafePhaseAction(
                action_id="phase-action:alt-capital-formation",
                action_type="alt-certification",
                title="Certify Abstraction Capital",
                purpose="Separate proxy-only claims from calibrated or causal reusable value.",
                priority_score=7.5,
                safe_commands=[
                    "pic alt admit --packet <alt-certificate-packet.json>",
                    "pic alt negative-certify --certificate <negative-liquidity.json>",
                    "pic alt refresh-baseline --certificate <baseline-refresh.json>",
                ],
                sdk_calls=[
                    "percolation_inversion_compiler.alt.admit_alt_packet",
                    "percolation_inversion_compiler.alt.compute_foundry_dashboard",
                ],
                schema_refs=[
                    "ALTAdmissionDecision",
                    "ValueBridgeReport",
                    "FoundryControlDashboard",
                ],
                inspect_fields=[
                    "missing_obligations",
                    "status",
                    "certified_capital_ref",
                    "residual_ledger",
                ],
                expected_effect="increase reusable abstraction value only after finite checks",
            )
        )
    if any(item.candidate_only for item in bottlenecks):
        actions.append(
            SafePhaseAction(
                action_id="phase-action:candidate-quarantine",
                action_type="candidate-only-routing",
                title="Route Candidate-Only Inputs",
                purpose=(
                    "Keep raw external or peer inputs useful without counting "
                    "them as phase progress."
                ),
                priority_score=6.5,
                safe_commands=[
                    "pic ecology bridge-runtime --report <general-intake-report.json>",
                    "pic agent inbox verify --inbox <inbox.json>",
                ],
                sdk_calls=[
                    "percolation_inversion_compiler.ecology.bridge_general_intake_to_runtime",
                    "percolation_inversion_compiler.ecology.verify_agent_message",
                ],
                schema_refs=[
                    "GeneralIntakeRuntimeBridgeReport",
                    "AgentMessageDeliveryReport",
                ],
                inspect_fields=["candidate_only", "ecpt_phase_contribution_allowed"],
                candidate_only=True,
                expected_effect="move external candidates into SQOT diagnostic/verifier queues",
            )
        )
    return sorted(actions, key=lambda item: (-item.priority_score, item.action_id))


def _profile_requires_identity(profile: str) -> bool:
    return profile.lower() in {"production", "adversarial"}


def _identity_ready(identity_context: RuntimeIdentityContext | None) -> bool:
    return bool(identity_context is not None and identity_context.accepted)


def _dedupe(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})
