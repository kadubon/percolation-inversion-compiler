"""Deterministic ECPT active runtime algorithms."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from percolation_inversion_compiler.core import (
    AdapterRouteSpec,
    binding_for_route,
    list_adapter_route_specs,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.ecology import (
    BottleneckIntervention,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    PacketIngestionReport,
    PacketSourceKind,
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_registry,
    build_psi_dashboard,
    infer_live_kind,
    ingest_agent_output,
    ingest_live_source,
    ingest_local_file,
)
from percolation_inversion_compiler.ecpt import (
    PhaseControlAction,
    PhaseControlPlan,
    PhaseControlRunReport,
    build_phase_control_plan,
    reachable_mass,
)
from percolation_inversion_compiler.runtime.records import (
    ActionCommit,
    ActionCommitPolicy,
    AgentRuntimeConfig,
    AgentTask,
    PhaseAccelerationScore,
    RouteExecutionRequest,
    RuntimeHealthReport,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)
from percolation_inversion_compiler.sqot import (
    DiagnosticReservePolicy,
    SalienceQueueRecord,
    build_salience_schedule,
)


def build_runtime_step(
    state: RuntimeState,
    step_input: RuntimeStepInput,
    config: AgentRuntimeConfig | None = None,
) -> RuntimeStepReport:
    """Run one finite active runtime step.

    The step composes packet ingestion, edge-witness construction, Psi dashboard
    evaluation, bottleneck inversion, ECPT phase planning, SQOT scheduling, and
    route-request emission.  It is intentionally fail-closed: planning alone does
    not set ``settled``.
    """

    active_config = config or AgentRuntimeConfig()
    ingestion_reports = _ingest_step_sources(step_input, active_config)
    packets, residual, reasons = _merge_packets(state, step_input, ingestion_reports)
    edges = build_edge_witnesses(packets)
    registry = build_packet_registry(
        packets,
        edges,
        registry_id=f"runtime-registry:{state.state_id}:{step_input.input_id}",
    )
    residual = residual.combine(registry.residual_ledger)
    threshold = dict(state.psi_threshold)
    threshold.update(active_config.psi_threshold)
    dashboard = build_psi_dashboard(registry, threshold=threshold or None, target_tags=["phase"])
    bottleneck = build_bottleneck_plan(registry, dashboard, profile=active_config.profile)
    phase_report = _build_phase_report(state, active_config)
    residual = residual.combine(dashboard.residual_ledger)
    residual = residual.combine(bottleneck.residual_ledger)
    residual = residual.combine(phase_report.plan.residual_ledger)

    route_requests = _route_requests(
        _routes_from_runtime_outputs(phase_report, bottleneck, active_config),
        priority_score=1.0,
    )
    tasks = _agent_tasks(
        phase_actions=phase_report.plan.selected_actions,
        bottleneck_interventions=bottleneck.interventions,
        route_specs={spec.route_id: spec for spec in list_adapter_route_specs()},
        max_tasks=active_config.max_tasks,
        minimum_task_score=active_config.minimum_task_score,
    )
    schedule = build_salience_schedule(
        _salience_records(tasks, registry),
        attention_budget=active_config.attention_budget,
        diagnostic_reserve=DiagnosticReservePolicy(minimum_reserve=0.0, reserve_fraction=0.1),
        risk_budget=active_config.risk_budget,
        profile=active_config.profile,
    )
    residual = residual.combine(_schedule_residual(schedule))
    score = phase_acceleration_score(
        score_id=f"phase-acceleration:{state.state_id}:{step_input.input_id}",
        phase_report=phase_report,
        bottleneck_plan=bottleneck,
        registry=registry,
        route_requests=route_requests,
        schedule_residual=schedule.residual_debt_growth,
        prior_residual_debt=state.residual_ledger.burden_sum(),
    )
    commits = [
        _action_commit(action, active_config.action_commit_policy)
        for action in phase_report.plan.selected_actions
    ]
    route_residuals = {
        obligation
        for request in route_requests
        for obligation in request.residual_external_obligations
    }
    missing_obligations = sorted(
        set(phase_report.plan.missing_obligations)
        | route_residuals
        | {obligation for task in tasks for obligation in task.residual_coordinates}
    )
    if step_input.live_sources and not _live_enabled(step_input, active_config):
        reasons.append(
            "live connector sources were diagnostic because runtime live ingestion is disabled"
        )
    accepted = bool(tasks)
    finite_checks_passed = bool(
        phase_report.plan.accepted or bottleneck.accepted or schedule.accepted or registry.packets
    )
    operationally_usable = (
        accepted
        and bool(finite_checks_passed)
        and schedule.accepted
        and not missing_obligations
        and active_config.action_commit_policy != ActionCommitPolicy.RECOMMEND_ONLY
    )
    return RuntimeStepReport(
        report_id=f"runtime-step:{state.state_id}:{state.step_index}:{step_input.input_id}",
        state_id=state.state_id,
        input_id=step_input.input_id,
        step_index=state.step_index,
        accepted=accepted,
        finite_checks_passed=finite_checks_passed,
        operationally_usable=operationally_usable,
        settled=False,
        status=ClaimStatus.PROVISIONAL if operationally_usable else ClaimStatus.DIAGNOSTIC,
        ingestion_reports=ingestion_reports,
        registry=registry,
        psi=dashboard,
        bottleneck_plan=bottleneck,
        phase_run_report=phase_report,
        salience_schedule=schedule,
        phase_acceleration_score=score,
        agent_tasks=tasks,
        action_commits=commits,
        route_execution_requests=route_requests,
        missing_obligations=missing_obligations,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
        allow_live_connectors=_live_enabled(step_input, active_config),
    )


def run_runtime_loop(
    state: RuntimeState,
    inputs: Sequence[RuntimeStepInput],
    config: AgentRuntimeConfig | None = None,
    *,
    max_steps: int | None = None,
) -> list[RuntimeStepReport]:
    """Run multiple deterministic runtime steps while preserving residual ledgers."""

    active_config = config or AgentRuntimeConfig()
    reports: list[RuntimeStepReport] = []
    current = state
    for step_input in list(inputs)[: max_steps or len(inputs)]:
        report = build_runtime_step(current, step_input, active_config)
        reports.append(report)
        current = current.model_copy(
            update={
                "packet_registry": report.registry,
                "residual_ledger": report.residual_ledger,
                "step_index": current.step_index + 1,
                "runtime_memory": [*current.runtime_memory, report.report_id],
            }
        )
    return reports


def runtime_health(
    state: RuntimeState,
    config: AgentRuntimeConfig | None = None,
) -> RuntimeHealthReport:
    """Return a finite runtime health report without performing agent actions."""

    active_config = config or AgentRuntimeConfig()
    dashboard = build_psi_dashboard(
        state.packet_registry,
        threshold=active_config.psi_threshold or state.psi_threshold or None,
    )
    routes = sorted(
        {route for packet in state.packet_registry.packets for route in packet.verifier_routes}
        | set(state.phase_state.route_ids)
        | set(active_config.required_routes)
    )
    missing = [
        route
        for route in routes
        if route not in {spec.route_id for spec in list_adapter_route_specs()}
        and route not in {spec.verifier_route for spec in list_adapter_route_specs()}
    ]
    checks = {
        "live_connectors": "enabled" if active_config.allow_live_connectors else "disabled",
        "packet_registry": "present" if state.packet_registry.packets else "empty",
        "residual_ledger": "nonempty" if state.residual_ledger.coordinates else "empty",
        "required_routes": "complete" if not missing else "missing",
    }
    accepted = not missing and bool(state.phase_actions or state.packet_registry.packets)
    return RuntimeHealthReport(
        report_id=f"runtime-health:{state.state_id}:{active_config.profile}",
        state_id=state.state_id,
        profile=active_config.profile,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted and active_config.profile != "production",
        settled=False,
        status=ClaimStatus.PROVISIONAL if accepted else ClaimStatus.DIAGNOSTIC,
        packet_count=len(state.packet_registry.packets),
        edge_count=len(state.packet_registry.edges),
        route_count=len(routes),
        residual_debt=state.residual_ledger.burden_sum()
        + state.packet_registry.residual_ledger.burden_sum(),
        psi_components=dashboard.components,
        missing_obligations=missing,
        checks=checks,
    )


def phase_acceleration_score(
    *,
    score_id: str,
    phase_report: PhaseControlRunReport,
    bottleneck_plan: object,
    registry: CapabilityPacketRegistry,
    route_requests: Sequence[RouteExecutionRequest],
    schedule_residual: float = 0.0,
    prior_residual_debt: float = 0.0,
) -> PhaseAccelerationScore:
    """Compute a finite ECPT ASI-proxy acceleration score."""

    interventions = getattr(bottleneck_plan, "interventions", [])
    before = getattr(bottleneck_plan, "before_psi", {})
    after = getattr(bottleneck_plan, "after_psi_lower_bound", {})
    finite_proxy_gain = phase_report.plan.finite_proxy_gain_total + sum(
        max(0.0, item.expected_gain) for item in interventions
    )
    psi_distance_reduction = sum(
        max(0.0, float(after.get(key, 0.0)) - float(before.get(key, 0.0)))
        for key in sorted(set(before) | set(after))
    )
    throughput = max(
        0.0,
        (registry.residual_ledger.benefit_sum() + len(registry.edges) + 1.0)
        / (len(route_requests) + registry.residual_ledger.burden_sum() + 1.0),
    )
    residual_debt = (
        registry.residual_ledger.burden_sum()
        + phase_report.plan.residual_ledger.burden_sum()
        + float(schedule_residual)
        + max(0.0, prior_residual_debt)
    )
    risk_charge = sum(max(0.0, candidate.risk_charge) for candidate in phase_report.plan.candidates)
    stale_charge = _stale_ratio(registry)
    false_liquidity_charge = _false_liquidity_rate(registry)
    missing_route_charge = 0.25 * float(
        sum(1 for request in route_requests if request.residual_external_obligations)
        + len(phase_report.plan.missing_obligations)
    )
    total = (
        finite_proxy_gain
        + psi_distance_reduction
        + throughput
        - residual_debt
        - risk_charge
        - stale_charge
        - false_liquidity_charge
        - missing_route_charge
    )
    components = {
        "finite_proxy_gain": finite_proxy_gain,
        "missing_route_charge": missing_route_charge,
        "psi_distance_reduction": psi_distance_reduction,
        "residual_debt_charge": residual_debt,
        "risk_charge": risk_charge,
        "stale_packet_charge": stale_charge,
        "verification_throughput_score": throughput,
    }
    return PhaseAccelerationScore(
        score_id=score_id,
        total_score=total,
        finite_proxy_gain=finite_proxy_gain,
        psi_distance_reduction=psi_distance_reduction,
        verification_throughput_score=throughput,
        residual_debt_charge=residual_debt,
        risk_charge=risk_charge,
        stale_packet_charge=stale_charge,
        false_liquidity_charge=false_liquidity_charge,
        missing_route_charge=missing_route_charge,
        components=dict(sorted(components.items())),
    )


def _ingest_step_sources(
    step_input: RuntimeStepInput,
    config: AgentRuntimeConfig,
) -> list[PacketIngestionReport]:
    reports: list[PacketIngestionReport] = []
    if step_input.agent_output:
        reports.append(ingest_agent_output(step_input.agent_output, output_id=step_input.input_id))
    for source in step_input.local_sources:
        reports.append(_ingest_local_source(Path(source)))
    for source in step_input.live_sources:
        if not _live_enabled(step_input, config):
            reports.append(
                _diagnostic_ingestion(
                    PacketSourceKind.AUTO,
                    source,
                    "live connector source requires allow_live_connectors=true in input and config",
                )
            )
            continue
        reports.append(ingest_live_source(source, kind=infer_live_kind(source)))
    return reports


def _live_enabled(step_input: RuntimeStepInput, config: AgentRuntimeConfig) -> bool:
    return config.allow_live_connectors and step_input.allow_live_connectors


def _ingest_local_source(source: Path) -> PacketIngestionReport:
    if not source.exists() or not source.is_file():
        return _diagnostic_ingestion(
            PacketSourceKind.LOCAL,
            source.name,
            "local packet source does not exist or is not a file",
        )
    return ingest_local_file(source)


def _diagnostic_ingestion(
    source_kind: PacketSourceKind,
    source_ref: str,
    reason: str,
) -> PacketIngestionReport:
    residual = Ledger().add_coordinate(
        f"runtime-ingest:{source_kind.value}:{Path(source_ref).name}:diagnostic",
        1.0,
        kind=CoordinateKind.RESIDUAL,
    )
    return PacketIngestionReport(
        report_id=f"packet-ingestion:diagnostic:{source_kind.value}",
        accepted=False,
        source_kind=source_kind,
        rejected_sources=[Path(source_ref).name],
        reasons=[reason],
        residual_ledger=residual,
    )


def _merge_packets(
    state: RuntimeState,
    step_input: RuntimeStepInput,
    reports: Sequence[PacketIngestionReport],
) -> tuple[list[CapabilityPacketCandidate], Ledger, list[str]]:
    packets: dict[str, CapabilityPacketCandidate] = {}
    residual = state.residual_ledger.combine(state.packet_registry.residual_ledger)
    reasons: list[str] = []
    for packet in [*state.packet_registry.packets, *step_input.packets]:
        packets.setdefault(packet.packet_id, packet)
    for report in reports:
        residual = residual.combine(report.residual_ledger)
        for packet in report.packets:
            if packet.packet_id in packets:
                residual = residual.add_coordinate(
                    f"runtime-packet:{packet.packet_id}:duplicate",
                    1.0,
                    kind=CoordinateKind.RESIDUAL,
                )
                reasons.append(f"duplicate packet id preserved first packet: {packet.packet_id}")
                continue
            packets[packet.packet_id] = packet
    return sorted(packets.values(), key=lambda item: item.packet_id), residual, reasons


def _build_phase_report(
    state: RuntimeState,
    config: AgentRuntimeConfig,
) -> PhaseControlRunReport:
    if state.phase_actions:
        return build_phase_control_plan(
            state.phase_state,
            state.phase_objective,
            state.phase_actions,
            profile=config.profile,
        )
    plan = PhaseControlPlan(
        plan_id=f"phase-control-plan:{state.state_id}:empty",
        objective_id=state.phase_objective.objective_id,
        profile=config.profile,
        accepted=False,
        status=ClaimStatus.DIAGNOSTIC,
        partial=True,
        reasons=["runtime state has no phase-control actions"],
        missing_obligations=["phase-control-action-catalog"],
    )
    return PhaseControlRunReport(
        report_id=f"phase-control-run:{state.state_id}:empty",
        state_id=state.phase_state.state_id,
        target_id=state.phase_objective.target.target_id,
        plan=plan,
        baseline_reachable_mass=dict(sorted(reachable_mass(state.phase_state.graph).items())),
        controlled_reachable_mass=dict(sorted(reachable_mass(state.phase_state.graph).items())),
    )


def _routes_from_runtime_outputs(
    phase_report: PhaseControlRunReport,
    bottleneck_plan: object,
    config: AgentRuntimeConfig,
) -> list[str]:
    routes = set(config.required_routes)
    routes.update(phase_report.plan.required_evidence_routes)
    for action in phase_report.plan.selected_actions:
        routes.update(action.verifier_routes)
    for intervention in getattr(bottleneck_plan, "interventions", []):
        routes.update(intervention.required_routes)
    return sorted(routes)


def _route_requests(
    route_ids: Sequence[str],
    *,
    priority_score: float,
) -> list[RouteExecutionRequest]:
    by_key: dict[str, AdapterRouteSpec] = {}
    for route_spec in list_adapter_route_specs():
        by_key[route_spec.route_id] = route_spec
        by_key[route_spec.verifier_route] = route_spec
    requests: list[RouteExecutionRequest] = []
    for route in sorted(set(route_ids)):
        spec = by_key.get(route)
        if spec is None:
            requests.append(
                RouteExecutionRequest(
                    request_id=f"route-request:unknown:{route}",
                    route_id=route,
                    verifier_route=route,
                    obligation_category="unknown-route",
                    safe_default="diagnostic-with-unknown-route",
                    residual_policy="preserve-unknown-route-obligation",
                    residual_external_obligations=["unknown-route-binding"],
                    priority_score=priority_score,
                )
            )
            continue
        binding = binding_for_route(spec.route_id)
        requests.append(
            RouteExecutionRequest(
                request_id=f"route-request:{spec.route_id}",
                route_id=spec.route_id,
                verifier_route=spec.verifier_route,
                obligation_category=spec.obligation_category,
                required_evidence_kind=spec.required_evidence_kind,
                safe_default=spec.safe_default,
                residual_policy=spec.residual_policy,
                settlement_scope=[] if binding is None else binding.settlement_scope,
                residual_external_obligations=(
                    [] if binding is None else binding.residual_external_obligation_refs
                ),
                priority_score=priority_score,
                status=ClaimStatus.DIAGNOSTIC,
            )
        )
    return requests


def _agent_tasks(
    *,
    phase_actions: Sequence[PhaseControlAction],
    bottleneck_interventions: Sequence[BottleneckIntervention],
    route_specs: Mapping[str, AdapterRouteSpec],
    max_tasks: int,
    minimum_task_score: float,
) -> list[AgentTask]:
    tasks: list[AgentTask] = []
    for intervention in bottleneck_interventions:
        if intervention.score < minimum_task_score:
            continue
        tasks.append(
            AgentTask(
                task_id=f"task:{intervention.intervention_id}",
                task_type="bottleneck-intervention",
                priority_score=intervention.score,
                target_component=intervention.target_component,
                action_kind=intervention.action_kind,
                expected_proxy_gain=intervention.expected_gain,
                required_routes=intervention.required_routes,
                required_evidence_kind=_evidence_kinds(intervention.required_routes, route_specs),
                residual_coordinates=sorted(intervention.residual_ledger.coordinates),
                rollback_condition=intervention.rollback_condition,
                operationally_usable=intervention.score > 0.0,
                settled=False,
                reasons=[] if intervention.score > 0.0 else ["nonpositive intervention score"],
            )
        )
    for action in phase_actions:
        routes = sorted(action.verifier_routes)
        score = (
            action.activation_delta
            - action.burden_delta
            - action.residual_charge
            - action.risk_charge
        )
        if score < minimum_task_score:
            continue
        tasks.append(
            AgentTask(
                task_id=f"task:phase-action:{action.action_id}",
                task_type="phase-control-action",
                priority_score=score,
                target_component=action.target_node,
                action_kind="execute-phase-control-action",
                action_id=action.action_id,
                expected_proxy_gain=max(0.0, action.activation_delta),
                required_routes=routes,
                required_evidence_kind=_evidence_kinds(routes, route_specs),
                residual_coordinates=sorted(action.required_obligations),
                rollback_condition="verifier-resolution-missing-or-negative-proxy-gain",
                operationally_usable=score > 0.0,
                settled=False,
                reasons=[] if score > 0.0 else ["nonpositive phase-action score"],
            )
        )
    return sorted(tasks, key=lambda item: (-item.priority_score, item.task_id))[: max(0, max_tasks)]


def _evidence_kinds(routes: Sequence[str], specs: Mapping[str, AdapterRouteSpec]) -> list[str]:
    by_key: dict[str, AdapterRouteSpec] = {}
    for spec in specs.values():
        by_key[spec.route_id] = spec
        by_key[spec.verifier_route] = spec
    kinds: set[str] = set()
    for route in routes:
        route_spec = by_key.get(route)
        if route_spec is not None:
            kinds.update(route_spec.required_evidence_kind)
    return sorted(kinds)


def _salience_records(
    tasks: Sequence[AgentTask],
    registry: CapabilityPacketRegistry,
) -> list[SalienceQueueRecord]:
    records: list[SalienceQueueRecord] = []
    for task in tasks:
        records.append(
            SalienceQueueRecord(
                record_id=task.task_id,
                item_type="verifier-task" if task.required_routes else "agent-task",
                salience_class=task.task_type,
                expected_downstream_gain=task.expected_proxy_gain,
                residual_reduction=max(0.0, task.priority_score),
                verification_cost=max(0.01, len(task.required_evidence_kind) * 0.1),
                freshness=1.0,
                hazard_charge=0.0 if task.operationally_usable else 0.2,
                obligation_ids=task.residual_coordinates,
                verifier_routes=task.required_routes,
            )
        )
    for packet in registry.packets:
        records.append(
            SalienceQueueRecord(
                record_id=f"queue:{packet.packet_id}",
                item_type="packet",
                salience_class=packet.salience_class,
                expected_downstream_gain=packet.expected_downstream_gain,
                residual_reduction=max(0.0, 1.0 - packet.residual_charge),
                verification_cost=packet.verification_cost,
                freshness=packet.freshness,
                stale=packet.expires_at == "expired",
                obligation_ids=packet.evidence_refs,
                verifier_routes=packet.verifier_routes,
            )
        )
    return records


def _schedule_residual(schedule: object) -> Ledger:
    residual = Ledger()
    for decision in getattr(schedule, "decisions", []):
        residual = residual.combine(decision.residual_ledger)
    return residual


def _action_commit(action: PhaseControlAction, policy: ActionCommitPolicy) -> ActionCommit:
    finite_scope_usable = action.activation_delta > 0 and action.risk_charge >= 0
    reasons: list[str] = []
    if policy == ActionCommitPolicy.RECOMMEND_ONLY:
        reasons.append("policy is recommend_only")
    if policy == ActionCommitPolicy.REQUIRE_VERIFIER_RESOLUTION:
        reasons.append("verifier resolution required before action commit")
    committed = policy == ActionCommitPolicy.ALLOW_FINITE_SCOPE_COMMIT and finite_scope_usable
    return ActionCommit(
        action_id=action.action_id,
        policy=policy,
        recommended=True,
        committed=committed,
        finite_scope_usable=finite_scope_usable,
        verifier_resolution_required=policy == ActionCommitPolicy.REQUIRE_VERIFIER_RESOLUTION,
        operationally_usable=committed,
        settled=False,
        reasons=reasons,
    )


def _stale_ratio(registry: CapabilityPacketRegistry) -> float:
    if not registry.packets:
        return 0.0
    return sum(1 for packet in registry.packets if packet.expires_at == "expired") / len(
        registry.packets
    )


def _false_liquidity_rate(registry: CapabilityPacketRegistry) -> float:
    if not registry.packets:
        return 0.0
    false = sum(
        1
        for packet in registry.packets
        if packet.expected_downstream_gain <= 0.0
        or packet.verification_cost > packet.expected_downstream_gain
    )
    return false / len(registry.packets)


def loop_state_after_report(state: RuntimeState, report: RuntimeStepReport) -> RuntimeState:
    """Return the next persistent state after a runtime report."""

    return state.model_copy(
        update={
            "packet_registry": report.registry,
            "residual_ledger": report.residual_ledger,
            "step_index": state.step_index + 1,
            "runtime_memory": [*state.runtime_memory, report.report_id],
        }
    )


def collect_missing_routes(
    route_ids: Iterable[str],
) -> list[str]:
    """Return unknown route ids for diagnostics and tests."""

    known = {
        key for spec in list_adapter_route_specs() for key in (spec.route_id, spec.verifier_route)
    }
    return sorted(set(route_ids) - known)
