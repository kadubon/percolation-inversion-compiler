"""Finite constructive algorithms for Typed Reality Compilation."""

from __future__ import annotations

from collections import Counter
from itertools import product
from math import inf
from typing import Literal

from percolation_inversion_compiler.core.checker import boolean_check_result, residual_from_reasons
from percolation_inversion_compiler.core.frontier import (
    FrontierRecord,
    archive_with_truncation,
    pareto_frontier,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.trc.records import (
    ActionabilityVector,
    BoundaryGeneratorRecord,
    BoundaryScriptAutomatonRecord,
    BoundaryScriptRecord,
    BudgetedToleranceScheduler,
    CascadeResidualPotential,
    CausalEventPosetRecord,
    EventContractRecord,
    ExecutableTraceNormalForm,
    FutureFreedomVector,
    IndependenceCertificate,
    LifecycleDAGRecord,
    MultiHorizonOrder,
    ObservationWindow,
    ProcessGrammarRecord,
    RelaxationScheduleRecord,
    ResourceCalendarRecord,
    ResourceEscrowRecord,
    ResourceFlowRecord,
    RiskGateRecord,
    ScriptGroundMetricCertificate,
    StatusAlgebraRecord,
    ToleranceAllocationCertificate,
    ToleranceCostKernel,
    ToleranceMenuItem,
    TraceNormalizationCertificate,
    TransitionProofRecord,
    TRCCompileResult,
    TRCStateRecord,
    TypedGraphRecord,
    TypedTraceTransducerRecord,
)


def observation_consistency_residual(
    *,
    mismatch_norm: float,
    feasible_section_residual: float = 0.0,
    topological_residual: float = 0.0,
    refresh_residual: float = 0.0,
) -> float:
    """Finite observation-consistency residual aggregate."""

    return (
        abs(mismatch_norm)
        + abs(feasible_section_residual)
        + abs(topological_residual)
        + abs(refresh_residual)
    )


def weighted_edit_distance(
    left: list[str],
    right: list[str],
    *,
    insert_cost: dict[str, float] | None = None,
    delete_cost: dict[str, float] | None = None,
    substitute_cost: dict[tuple[str, str], float] | None = None,
    default_cost: float = 1.0,
) -> float:
    """Finite weighted edit distance for boundary-script ground metrics."""

    insert_cost = insert_cost or {}
    delete_cost = delete_cost or {}
    substitute_cost = substitute_cost or {}
    dp = [[0.0 for _ in range(len(right) + 1)] for _ in range(len(left) + 1)]
    for i, token in enumerate(left, start=1):
        dp[i][0] = dp[i - 1][0] + delete_cost.get(token, default_cost)
    for j, token in enumerate(right, start=1):
        dp[0][j] = dp[0][j - 1] + insert_cost.get(token, default_cost)
    for i, left_token in enumerate(left, start=1):
        for j, right_token in enumerate(right, start=1):
            substitution = (
                0.0
                if left_token == right_token
                else substitute_cost.get((left_token, right_token), default_cost)
            )
            dp[i][j] = min(
                dp[i - 1][j] + delete_cost.get(left_token, default_cost),
                dp[i][j - 1] + insert_cost.get(right_token, default_cost),
                dp[i - 1][j - 1] + substitution,
            )
    return dp[-1][-1]


def network_calculus_bounds(contract: EventContractRecord) -> dict[str, float]:
    """Finite deterministic network-calculus backlog and delay bounds."""

    if len(contract.arrival_curve) != len(contract.service_curve):
        raise ValueError("arrival and service curves must have equal length")
    backlog = 0.0
    for end in range(len(contract.arrival_curve)):
        for start in range(end + 1):
            arrival_increment = contract.arrival_curve[end] - (
                contract.arrival_curve[start - 1] if start else 0.0
            )
            service_available = contract.service_curve[end - start]
            backlog = max(backlog, arrival_increment - service_available)
    delay = 0.0
    for i, arrival in enumerate(contract.arrival_curve):
        local_delay = inf
        for j in range(i, len(contract.service_curve)):
            if contract.service_curve[j] >= arrival:
                local_delay = j - i
                break
        delay = max(delay, local_delay)
    if delay == inf:
        delay = float(len(contract.service_curve))
    return {
        "backlog_bound": backlog + abs(contract.drop_residual),
        "delay_bound": delay,
        "event_check_cost": contract.event_check_cost,
    }


def semiring_path_product(
    values: list[float],
    *,
    semiring: Literal["product", "max-plus", "min-plus", "sum"] = "product",
) -> float:
    """Finite path-conditioned residual summary."""

    if not values:
        raise ValueError("values must not be empty")
    if semiring == "product":
        result = 1.0
        for value in values:
            result *= value
        return result
    if semiring == "max-plus":
        return sum(values)
    if semiring == "min-plus":
        return sum(values)
    return sum(values)


def _cycle_present(nodes: set[str], edges: list[tuple[str, str]]) -> bool:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for source, target in edges:
        adjacency.setdefault(source, set()).add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for target in adjacency.get(node, set()):
            if visit(target):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in sorted(nodes))


def _check_from_reasons(
    name: str,
    reasons: list[str],
    residual: Ledger | None = None,
) -> CheckResult:
    residual_ledger = residual or Ledger()
    residual_ledger = residual_ledger.combine(residual_from_reasons(name, reasons))
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=[] if not reasons else [f"{name}:accepted"],
        residual_ledger=residual_ledger,
    )


def check_observation_window(window: ObservationWindow) -> CheckResult:
    """Check a finite observation window and refresh boundary."""

    reasons: list[str] = []
    if window.end_tick < window.start_tick:
        reasons.append("observation window ends before it starts")
    if window.sample_period <= 0:
        reasons.append("observation sample period must be positive")
    if not window.sensor_ids:
        reasons.append("observation window has no sensors")
    return _check_from_reasons(f"observation-window:{window.window_id}", reasons)


def check_typed_graph_record(graph: TypedGraphRecord) -> CheckResult:
    """Check a finite typed infrastructure graph."""

    reasons: list[str] = []
    if not graph.components:
        reasons.append("typed graph has no components")
    if any(value < 0 for value in graph.capacities.values()):
        reasons.append("typed graph has negative capacity")
    for coordinate, flow in graph.observed_flows.items():
        if flow < 0:
            reasons.append(f"observed flow is negative for {coordinate}")
        if coordinate in graph.capacities and flow > graph.capacities[coordinate]:
            reasons.append(f"observed flow exceeds capacity for {coordinate}")
    return _check_from_reasons("typed-graph", reasons)


def check_trc_state(record: TRCStateRecord) -> CheckResult:
    """Check that a TRC state is grounded in a live window and graph."""

    reasons: list[str] = []
    residual = Ledger()
    window_result = check_observation_window(record.observation_window)
    graph_result = check_typed_graph_record(record.infrastructure_graph)
    reasons.extend(window_result.reasons)
    reasons.extend(graph_result.reasons)
    residual = residual.combine(window_result.residual_ledger).combine(graph_result.residual_ledger)
    unknown_active = record.active_components - record.infrastructure_graph.components
    if unknown_active:
        reasons.append("TRC state activates components absent from typed graph")
    if not record.ledger_coordinates:
        reasons.append("TRC state has no typed ledger coordinates")
    return _check_from_reasons(f"trc-state:{record.state_id}", reasons, residual)


def check_status_algebra(record: StatusAlgebraRecord) -> CheckResult:
    """Check the finite status algebra used by TRC projections."""

    reasons: list[str] = []
    known_statuses = {status.value for status in ClaimStatus}
    for source, targets in record.allowed_transitions.items():
        if source not in known_statuses:
            reasons.append(f"unknown source status {source}")
        for target in targets:
            if target not in known_statuses:
                reasons.append(f"unknown target status {target}")
            if (
                record.non_promotion
                and target == ClaimStatus.SETTLED.value
                and source != ClaimStatus.SETTLED.value
                and not record.settled_obligations
            ):
                reasons.append("status algebra allows settled promotion without obligations")
    if not record.non_promotion:
        reasons.append("status algebra disables non-promotion")
    return _check_from_reasons(f"status-algebra:{record.algebra_id}", reasons)


def check_process_grammar(record: ProcessGrammarRecord) -> CheckResult:
    """Check executable process grammar reachability and forbidden-action exclusion."""

    reasons: list[str] = []
    if not record.action_classes:
        reasons.append("process grammar has no action classes")
    if not record.start_actions:
        reasons.append("process grammar has no start actions")
    if not record.terminal_actions:
        reasons.append("process grammar has no terminal actions")
    if not record.start_actions.issubset(record.action_classes):
        reasons.append("process grammar start actions are outside action classes")
    if not record.terminal_actions.issubset(record.action_classes):
        reasons.append("process grammar terminal actions are outside action classes")
    if record.forbidden_actions & record.action_classes:
        reasons.append("process grammar action classes include forbidden actions")
    for source, targets in record.transitions.items():
        if source not in record.action_classes:
            reasons.append(f"process grammar transition source is unknown: {source}")
        if not targets.issubset(record.action_classes):
            reasons.append(f"process grammar transition targets unknown actions: {source}")
    reachable = set(record.start_actions)
    changed = True
    while changed:
        changed = False
        for source, targets in record.transitions.items():
            if source in reachable:
                before = len(reachable)
                reachable.update(targets)
                changed = changed or len(reachable) > before
    if record.terminal_actions and not (record.terminal_actions & reachable):
        reasons.append("process grammar has no reachable terminal action")
    return _check_from_reasons(f"process-grammar:{record.grammar_id}", reasons)


def check_script_ground_metric(certificate: ScriptGroundMetricCertificate) -> CheckResult:
    """Check finite script ground metric certificate."""

    reasons: list[str] = []
    if certificate.distance < 0:
        reasons.append("script ground metric distance is negative")
    if certificate.lower_bound < 0:
        reasons.append("script ground metric lower bound is negative")
    if certificate.distance + certificate.residual < certificate.lower_bound:
        reasons.append("script ground metric violates lower bound")
    if certificate.residual < 0:
        reasons.append("script ground metric residual is negative")
    if not certificate.triangle_witness:
        reasons.append("script ground metric lacks triangle witness")
    residual = Ledger()
    if certificate.residual:
        residual = residual.add_coordinate(
            f"script-ground-metric:{certificate.certificate_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(
        f"script-ground-metric:{certificate.certificate_id}",
        reasons,
        residual,
    )


def check_actionability_vector(record: ActionabilityVector) -> CheckResult:
    """Check finite actionability vector and relaxed frontier coordinates."""

    reasons: list[str] = []
    if not record.coordinates:
        reasons.append("actionability vector has no coordinates")
    if any(value < 0 for value in record.coordinates.values()):
        reasons.append("actionability vector contains negative coordinate")
    if record.relaxed_coordinates - set(record.coordinates):
        reasons.append("relaxed coordinates are absent from actionability vector")
    if record.residual < 0:
        reasons.append("actionability vector residual is negative")
    residual = Ledger()
    if record.residual:
        residual = residual.add_coordinate(
            f"actionability:{record.vector_id}",
            record.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"actionability:{record.vector_id}", reasons, residual)


def check_budgeted_tolerance_scheduler(record: BudgetedToleranceScheduler) -> CheckResult:
    """Check finite budgeted recomputation schedule."""

    reasons: list[str] = []
    if record.budget < 0:
        reasons.append("scheduler budget is negative")
    if any(cost < 0 for cost in record.task_costs.values()):
        reasons.append("scheduler task cost is negative")
    if any(task not in record.task_costs for task in record.schedule):
        reasons.append("scheduler includes a task without a cost")
    known_tasks = set(record.task_costs)
    if any(
        source not in known_tasks or target not in known_tasks
        for source, target in record.dependency_edges
    ):
        reasons.append("scheduler dependency references unknown task")
    completed: set[str] = set()
    for task in record.schedule:
        missing = {
            source
            for source, target in record.dependency_edges
            if target == task and source not in completed
        }
        if missing:
            reasons.append(f"scheduler executes {task} before dependencies")
        completed.add(task)
    total_cost = sum(
        record.task_costs[task] for task in record.schedule if task in record.task_costs
    )
    residual = Ledger()
    if total_cost > record.budget:
        if not record.partial_frontier_on_exhaustion:
            reasons.append("scheduler exceeds budget without partial-frontier return")
        residual = residual.add_coordinate(
            f"budgeted-scheduler:{record.scheduler_id}:exhaustion",
            total_cost - record.budget,
            kind=CoordinateKind.RESIDUAL,
        )
    if record.exhausted_budget_residual < 0:
        reasons.append("scheduler exhausted-budget residual is negative")
    elif record.exhausted_budget_residual:
        residual = residual.add_coordinate(
            f"budgeted-scheduler:{record.scheduler_id}:declared",
            record.exhausted_budget_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"budgeted-scheduler:{record.scheduler_id}", reasons, residual)


def check_trace_normalization(certificate: TraceNormalizationCertificate) -> CheckResult:
    """Check finite word normalization and commutation evidence."""

    reasons: list[str] = []
    residual = Ledger()
    if not certificate.source_word:
        reasons.append("normalization source word is empty")
    if not certificate.normalized_word:
        reasons.append("normalization target word is empty")
    if not certificate.confluence_witness:
        reasons.append("normalization lacks confluence witness")
    if not certificate.termination_witness:
        reasons.append("normalization lacks termination witness")
    if certificate.residual < 0:
        reasons.append("normalization residual is negative")
    if not certificate.rewrite_steps and Counter(certificate.source_word) != Counter(
        certificate.normalized_word
    ):
        reasons.append("commutation-only normalization does not preserve the word multiset")
    if certificate.residual:
        residual = residual.add_coordinate(
            f"trace-normalization:{certificate.trace_id}",
            certificate.residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"trace-normalization:{certificate.trace_id}", reasons, residual)


def check_typed_trace_transducer(record: TypedTraceTransducerRecord) -> CheckResult:
    """Check finite typed trace transducer shape."""

    reasons: list[str] = []
    if record.initial_state not in record.states:
        reasons.append("transducer initial state is absent")
    if not record.accepting_states.issubset(record.states):
        reasons.append("transducer accepting states are not a subset of states")
    for key, target in record.transitions.items():
        source, _, token = key.partition("|")
        if source not in record.states or token not in record.input_alphabet:
            reasons.append(f"transducer transition has unknown source or token: {key}")
        if target not in record.states:
            reasons.append(f"transducer transition targets unknown state: {target}")
    for key, output in record.outputs.items():
        if key not in record.transitions:
            reasons.append(f"transducer output is not tied to a transition: {key}")
        if output not in record.output_alphabet:
            reasons.append(f"transducer output token is unknown: {output}")
    return _check_from_reasons(f"trace-transducer:{record.transducer_id}", reasons)


def resource_flow_feasible(record: ResourceFlowRecord) -> tuple[bool, float]:
    """Check trace-indexed resource conservation against finite capacity."""

    if len(record.inflow_profile) != len(record.service_profile):
        raise ValueError("inflow and service profiles must have equal length")
    depletion = record.depletion_profile or [0.0 for _ in record.inflow_profile]
    if len(depletion) != len(record.inflow_profile):
        raise ValueError("depletion profile must be empty or match inflow length")
    residual = (
        record.conservation_residual + record.stale_calendar_residual + record.overlap_residual
    )
    balance = 0.0
    feasible = True
    for inflow, service, depleted in zip(
        record.inflow_profile, record.service_profile, depletion, strict=True
    ):
        balance += inflow - service - depleted
        if balance > record.capacity:
            feasible = False
            residual += balance - record.capacity
        if balance < 0.0:
            residual += abs(balance)
            balance = 0.0
    return feasible, residual


def check_resource_flow(record: ResourceFlowRecord) -> CheckResult:
    """Check trace-indexed resource conservation as a structured result."""

    feasible, residual_value = resource_flow_feasible(record)
    residual = Ledger().add_coordinate(
        f"resource-flow:{record.trace_id}:{record.scenario_id}",
        residual_value,
        kind=CoordinateKind.RESIDUAL,
    )
    return CheckResult(
        accepted=feasible,
        status=ClaimStatus.SETTLED if feasible else ClaimStatus.DIAGNOSTIC,
        reasons=[] if feasible else ["trace-indexed resource flow is infeasible"],
        missing_obligations=[] if feasible else [f"resource-flow:{record.trace_id}"],
        residual_ledger=residual,
    )


def finite_tolerance_allocation(
    kernels: list[ToleranceCostKernel],
    *,
    budget: float,
) -> tuple[dict[str, ToleranceMenuItem], Ledger]:
    """Brute-force finite tolerance-menu allocation under a total budget."""

    if budget < 0:
        raise ValueError("budget must be nonnegative")
    if not kernels:
        return {}, Ledger()
    menus = [kernel.finite_menu for kernel in kernels]
    if any(not menu for menu in menus):
        raise ValueError("each tolerance kernel must have a nonempty finite menu")
    best_choice: tuple[ToleranceMenuItem, ...] | None = None
    best_score: tuple[float, float] | None = None
    for choice in product(*menus):
        total_cost = sum(item.total_cost for item in choice)
        if total_cost > budget:
            continue
        residual = sum(item.residual_increment for item in choice)
        score = (residual, total_cost)
        if best_score is None or score < best_score:
            best_score = score
            best_choice = choice
    if best_choice is None:
        raise ValueError("no tolerance allocation fits the budget")
    ledger = Ledger()
    allocation: dict[str, ToleranceMenuItem] = {}
    for kernel, item in zip(kernels, best_choice, strict=True):
        allocation[kernel.coordinate] = item
        ledger = ledger.add_coordinate(
            kernel.coordinate,
            item.residual_increment,
            kind=CoordinateKind.TOLERANCE,
        )
    return allocation, ledger


def trace_normal_form_accepts(trace: ExecutableTraceNormalForm) -> bool:
    """A main-frontier trace must have finite word, valid pre/post, and version ledgers."""

    return check_trace_normal_form(trace).accepted


def check_transition_proof(record: TransitionProofRecord) -> CheckResult:
    """Check one finite typed transition proof."""

    reasons: list[str] = []
    if not all(record.precondition.values()):
        reasons.append("transition precondition is false")
    if not all(record.postcondition.values()):
        reasons.append("transition postcondition is false")
    if record.latency < 0:
        reasons.append("transition latency must be nonnegative")
    if record.status not in {ClaimStatus.SETTLED, ClaimStatus.PROVISIONAL}:
        reasons.append("transition proof is not accepted at finite checker status")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"transition:{record.action_class}",
        failure_reason="; ".join(reasons) if reasons else "transition proof failed",
        residual_ledger=residual_from_reasons(f"transition:{record.action_class}", reasons),
    )


def check_causal_event_poset(record: CausalEventPosetRecord) -> CheckResult:
    """Check a finite causal event poset."""

    reasons: list[str] = []
    if not record.accepts():
        reasons.append("causal event poset has unknown events or negative residuals")
    if _cycle_present(record.event_ids, record.happens_before):
        reasons.append("causal event poset contains a cycle")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="causal-event-poset:accepted",
        failure_reason="; ".join(reasons) if reasons else "causal event poset failed",
        residual_ledger=residual_from_reasons("causal-event-poset", reasons),
    )


def check_boundary_generator(record: BoundaryGeneratorRecord) -> CheckResult:
    """Check finite boundary generator shape and prefix budget."""

    reasons: list[str] = []
    if not record.alphabet:
        reasons.append("boundary generator alphabet is empty")
    if record.max_depth < 0:
        reasons.append("boundary generator max depth is negative")
    for source, target in record.allowed_edges:
        if source not in record.alphabet or target not in record.alphabet:
            reasons.append("boundary generator edge uses a token outside the alphabet")
    for prefix in record.generated_prefixes:
        tokens = prefix.split()
        if len(tokens) > record.max_depth:
            reasons.append("boundary generator produced a prefix past max depth")
        if any(token not in record.alphabet for token in tokens):
            reasons.append("boundary generator produced a token outside the alphabet")
    if record.residual < 0:
        reasons.append("boundary generator residual is negative")
    return _check_from_reasons(f"boundary-generator:{record.generator_id}", reasons)


def check_boundary_script(
    record: BoundaryScriptRecord,
    automaton: BoundaryScriptAutomatonRecord,
) -> CheckResult:
    """Check a finite boundary script against a finite automaton."""

    reasons: list[str] = []
    automaton_result = check_boundary_script_automaton(automaton)
    reasons.extend(automaton_result.reasons)
    if not record.automaton_id:
        reasons.append("boundary script automaton id is empty")
    if not record.tokens:
        reasons.append("boundary script has no tokens")
    if any(token not in automaton.alphabet for token in record.tokens):
        reasons.append("boundary script uses a token outside the automaton alphabet")
    prefix = " ".join(record.tokens)
    if automaton.accepted_prefixes and prefix not in automaton.accepted_prefixes:
        reasons.append("boundary script prefix is not accepted")
    if len(record.tokens) > automaton.prefix_bound:
        reasons.append("boundary script exceeds automaton prefix bound")
    if record.ground_metric_residual < 0:
        reasons.append("boundary script ground metric residual is negative")
    residual = automaton_result.residual_ledger
    if record.ground_metric_residual:
        residual = residual.add_coordinate(
            f"boundary-script:{record.script_id}",
            record.ground_metric_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"boundary-script:{record.script_id}", reasons, residual)


def check_cascade_residual_potential(record: CascadeResidualPotential) -> CheckResult:
    """Check a finite cascade residual potential."""

    reasons: list[str] = []
    if any(value < 0 for value in record.component_potentials.values()):
        reasons.append("cascade potential has negative component potential")
    if any(value < 0 for value in record.edge_couplings.values()):
        reasons.append("cascade potential has negative edge coupling")
    if record.residual_floor < 0:
        reasons.append("cascade residual floor is negative")
    residual = Ledger()
    if record.residual_floor:
        residual = residual.add_coordinate(
            f"cascade:{record.potential_id}",
            record.residual_floor,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"cascade-potential:{record.potential_id}", reasons, residual)


def check_independence_certificate(record: IndependenceCertificate) -> CheckResult:
    """Check finite conditional-independence witness metadata."""

    reasons: list[str] = []
    if not record.variable_groups:
        reasons.append("independence certificate has no variable groups")
    if any(not variables for variables in record.variable_groups.values()):
        reasons.append("independence certificate has an empty variable group")
    if record.dependence_residual < 0:
        reasons.append("dependence residual is negative")
    if not record.accepted:
        reasons.append("independence certificate is not accepted")
    residual = Ledger()
    if record.dependence_residual:
        residual = residual.add_coordinate(
            f"independence:{record.certificate_id}",
            record.dependence_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"independence:{record.certificate_id}", reasons, residual)


def check_multi_horizon_order(record: MultiHorizonOrder) -> CheckResult:
    """Check finite multi-horizon order."""

    reasons: list[str] = []
    horizons = set(record.horizons)
    if not horizons:
        reasons.append("multi-horizon order is empty")
    if any(
        source not in horizons or target not in horizons for source, target in record.precedence
    ):
        reasons.append("multi-horizon order references an unknown horizon")
    if _cycle_present(horizons, record.precedence):
        reasons.append("multi-horizon order contains a cycle")
    return _check_from_reasons(f"multi-horizon-order:{record.order_id}", reasons)


def check_future_freedom_vector(record: FutureFreedomVector) -> CheckResult:
    """Check residual future-freedom vector compatibility with horizon order."""

    reasons: list[str] = []
    residual = Ledger()
    horizons = set(record.horizons)
    if set(record.values) != horizons:
        reasons.append("future-freedom values do not cover exactly the horizons")
    if any(value < 0 for value in record.residuals.values()):
        reasons.append("future-freedom residual is negative")
    if set(record.residuals) - horizons:
        reasons.append("future-freedom residual references an unknown horizon")
    for horizon, value in record.residuals.items():
        if value:
            residual = residual.add_coordinate(
                f"future-freedom:{record.vector_id}:{horizon}",
                value,
                kind=CoordinateKind.RESIDUAL,
            )
    if record.order is not None:
        order_result = check_multi_horizon_order(record.order)
        reasons.extend(order_result.reasons)
        residual = residual.combine(order_result.residual_ledger)
    return _check_from_reasons(f"future-freedom:{record.vector_id}", reasons, residual)


def check_resource_calendar(record: ResourceCalendarRecord) -> CheckResult:
    """Check resource-calendar capacity and freshness constraints."""

    reasons: list[str] = []
    if not record.freshness_version:
        reasons.append("resource calendar freshness version is empty")
    if any(capacity < 0 for capacity in record.capacities.values()):
        reasons.append("resource calendar has negative capacity")
    usage: dict[tuple[str, int], float] = {}
    for reservation in record.reservations:
        if reservation.resource not in record.capacities:
            reasons.append(f"reservation uses unknown resource {reservation.resource}")
        if reservation.start_tick > reservation.end_tick:
            reasons.append("reservation starts after it ends")
        if reservation.amount < 0:
            reasons.append("reservation amount is negative")
        for tick in range(reservation.start_tick, reservation.end_tick + 1):
            key = (reservation.resource, tick)
            usage[key] = usage.get(key, 0.0) + reservation.amount
    for (resource, tick), amount in usage.items():
        if amount > record.capacities.get(resource, 0.0):
            reasons.append(f"resource calendar exceeds capacity for {resource} at tick {tick}")
    return _check_from_reasons(f"resource-calendar:{record.calendar_id}", reasons)


def check_tolerance_allocation_certificate(
    record: ToleranceAllocationCertificate,
) -> CheckResult:
    """Check a finite LP/MILP-style tolerance allocation certificate."""

    reasons: list[str] = []
    residual = Ledger()
    if not record.selected_items:
        reasons.append("tolerance allocation certificate has no selected items")
    if record.budget < 0:
        reasons.append("tolerance allocation budget is negative")
    if record.objective_value < 0:
        reasons.append("tolerance allocation objective is negative")
    if record.solver_gap < 0:
        reasons.append("tolerance allocation solver gap is negative")
    if record.residual_charge < 0:
        reasons.append("tolerance allocation residual charge is negative")
    if not record.integer_feasible:
        reasons.append("tolerance allocation is not integer feasible")
    if (
        record.dual_bound is not None
        and record.objective_value + record.solver_gap < record.dual_bound
    ):
        reasons.append("tolerance allocation violates the supplied dual bound")
    if record.residual_charge:
        residual = residual.add_coordinate(
            f"tolerance-allocation:{record.certificate_id}",
            record.residual_charge + record.solver_gap,
            kind=CoordinateKind.RESIDUAL,
        )
    return _check_from_reasons(f"tolerance-allocation:{record.certificate_id}", reasons, residual)


def check_lifecycle_dag(record: LifecycleDAGRecord, versions: list[str]) -> CheckResult:
    """Check lifecycle freshness for certificate versions used by a trace."""

    reasons: list[str] = []
    known_versions = set(record.certificate_versions) | set(record.certificate_versions.values())
    missing_versions = sorted(set(versions) - known_versions)
    if not record.accepts():
        reasons.append("lifecycle DAG has stale invalidations without recomputation routes")
    if missing_versions:
        reasons.append("trace references certificate versions absent from lifecycle DAG")
    residual = residual_from_reasons("lifecycle", reasons)
    if record.stale_residual:
        residual = residual.add_coordinate(
            "lifecycle:stale-residual",
            record.stale_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    return boolean_check_result(
        accepted=not reasons,
        obligation_id="lifecycle:fresh",
        failure_reason="; ".join(reasons) if reasons else "lifecycle DAG failed",
        residual_ledger=residual,
    )


def check_resource_escrow(record: ResourceEscrowRecord) -> CheckResult:
    """Check resource escrow feasibility and resolution."""

    reasons: list[str] = []
    if not record.accepts():
        reasons.append("resource escrow lacks commutation or capacity feasibility")
    if record.resolution_status != ClaimStatus.SETTLED:
        reasons.append("resource escrow is not resolved")
    return boolean_check_result(
        accepted=not reasons,
        obligation_id=f"escrow:{record.escrow_id}",
        failure_reason="; ".join(reasons) if reasons else "resource escrow failed",
        residual_ledger=residual_from_reasons(f"escrow:{record.escrow_id}", reasons),
    )


def check_trace_normal_form(trace: ExecutableTraceNormalForm) -> CheckResult:
    """Check the TRC tolerance-aware executable trace normal-form clauses."""

    reasons: list[str] = []
    residual = Ledger()
    if not trace.normalized_word:
        reasons.append("normalized trace word is empty")
    if len(trace.step_proofs) != len(trace.normalized_word):
        reasons.append("each normalized trace step must have one transition proof")
    if not all(trace.precondition.values()):
        reasons.append("trace precondition is false")
    if not all(trace.postcondition.values()):
        reasons.append("trace postcondition is false")
    if not trace.certificate_versions:
        reasons.append("certificate version ledger is empty")
    if not trace.tolerance_versions:
        reasons.append("tolerance version ledger is empty")
    if trace.error_budget < trace.trace_residual:
        reasons.append("trace residual exceeds error budget")
    if trace.normalization is None:
        reasons.append("trace normalization certificate is missing")
    else:
        normalization_result = check_trace_normalization(trace.normalization)
        residual = residual.combine(normalization_result.residual_ledger)
        reasons.extend(normalization_result.reasons)
        if trace.normalization.normalized_word != trace.normalized_word:
            reasons.append("trace normalization target differs from normalized word")
    if trace.causal_schedule is None:
        reasons.append("causal schedule is missing")
    else:
        causal_result = check_causal_event_poset(trace.causal_schedule)
        residual = residual.combine(causal_result.residual_ledger)
        reasons.extend(causal_result.reasons)
    if trace.lifecycle is None:
        reasons.append("lifecycle DAG is missing")
    else:
        lifecycle_result = check_lifecycle_dag(trace.lifecycle, trace.certificate_versions)
        residual = residual.combine(lifecycle_result.residual_ledger)
        reasons.extend(lifecycle_result.reasons)
    for step in trace.step_proofs:
        step_result = check_transition_proof(step)
        residual = residual.combine(step_result.residual_ledger)
        reasons.extend(step_result.reasons)
    for flow in trace.resource_flow_profile:
        flow_result = check_resource_flow(flow)
        residual = residual.combine(flow_result.residual_ledger)
        reasons.extend(flow_result.reasons)
    if trace.resource_flow_profile and trace.resource_calendar is None:
        reasons.append("resource calendar is missing for resource-flow trace")
    if trace.resource_calendar is not None:
        calendar_result = check_resource_calendar(trace.resource_calendar)
        residual = residual.combine(calendar_result.residual_ledger)
        reasons.extend(calendar_result.reasons)
    for escrow in trace.escrows:
        escrow_result = check_resource_escrow(escrow)
        residual = residual.combine(escrow_result.residual_ledger)
        reasons.extend(escrow_result.reasons)
    if trace.future_freedom is not None:
        future_result = check_future_freedom_vector(trace.future_freedom)
        residual = residual.combine(future_result.residual_ledger)
        reasons.extend(future_result.reasons)
    if trace.trace_residual:
        residual = residual.add_coordinate(
            f"trace:{trace.trace_id}:residual",
            trace.trace_residual,
            kind=CoordinateKind.RESIDUAL,
        )
    missing = [f"trace-normal-form:{trace.trace_id}"] if reasons else []
    return CheckResult(
        accepted=not reasons,
        status=ClaimStatus.SETTLED if not reasons else ClaimStatus.DIAGNOSTIC,
        reasons=sorted(set(reasons)),
        missing_obligations=missing,
        residual_ledger=residual.combine(residual_from_reasons("trace-normal-form", reasons)),
    )


def resource_efficiency_selection(records: list[FrontierRecord]) -> list[FrontierRecord]:
    """Pareto resource-efficiency selection within fixed strata."""

    return pareto_frontier(records)


def main_frontier_trace_accepts(record: FrontierRecord) -> bool:
    """Check the trace-normal-form gate for main frontier records."""

    trace_data = record.metadata.get("trace_normal_form")
    if isinstance(trace_data, dict):
        trace = ExecutableTraceNormalForm.model_validate(trace_data)
        return check_trace_normal_form(trace).accepted
    return False


def check_risk_gate(record: RiskGateRecord) -> CheckResult:
    """Check finite risk gate record."""

    return boolean_check_result(
        accepted=record.accepts(),
        obligation_id="risk-gate:dual-witness",
        failure_reason="risk gate requires nonnegative residuals and an accepted dual witness",
    )


def check_relaxation_schedule(record: RelaxationScheduleRecord) -> CheckResult:
    """Check finite lexicographic relaxation schedule."""

    return boolean_check_result(
        accepted=record.accepts(),
        obligation_id="relaxation-schedule:finite",
        failure_reason="relaxation schedule requires profiles and nonnegative residual",
    )


def check_boundary_script_automaton(record: BoundaryScriptAutomatonRecord) -> CheckResult:
    """Check finite boundary-script automaton shape."""

    return boolean_check_result(
        accepted=record.accepts(),
        obligation_id="boundary-script-automaton:finite",
        failure_reason="boundary script automaton has invalid bounds or residual",
    )


def compile_frontier(
    records: list[FrontierRecord],
    *,
    archive_cap: int = 64,
    epsilon: float = 0.0,
) -> TRCCompileResult:
    """Compile typed records into stratified frontiers and diagnostic archive."""

    invalid_main = [
        record.record_id
        for record in records
        if record.stratum == "main" and not main_frontier_trace_accepts(record)
    ]
    if invalid_main:
        raise ValueError(
            "main frontier records require accepted trace normal forms: "
            + ", ".join(sorted(invalid_main))
        )
    main = [record for record in records if record.stratum == "main"]
    risk = [record for record in records if record.stratum == "risk-provisional"]
    relaxed = [record for record in records if record.stratum == "relaxed"]
    partial = [record for record in records if record.stratum == "partial"]
    diagnostic = [record for record in records if record.stratum == "diagnostic"]
    efficiency = resource_efficiency_selection(main + risk + relaxed)
    archive = archive_with_truncation(efficiency, cap=archive_cap, epsilon=epsilon)
    if archive.truncated:
        diagnostic.extend(
            record.model_copy(update={"stratum": "diagnostic", "status": ClaimStatus.DIAGNOSTIC})
            for record in archive.truncated
        )
    return TRCCompileResult(
        main_frontier=pareto_frontier(main, epsilon=epsilon),
        risk_frontier=pareto_frontier(risk, epsilon=epsilon),
        relaxed_frontier=pareto_frontier(relaxed, epsilon=epsilon),
        partial_frontier=partial,
        diagnostic_archive=diagnostic,
        efficiency_archive=archive.retained,
        residual_ledger=archive.truncation_residual,
    )
