"""TRC record types."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus


class ObservationRecord(BaseModel):
    window_id: str
    sensor_fields: dict[str, float] = Field(default_factory=dict)
    abstraction_version: str = "v1"
    residual_fields: dict[str, float] = Field(default_factory=dict)


class ObservationWindow(BaseModel):
    window_id: str
    start_tick: int
    end_tick: int
    sample_period: int = 1
    sensor_ids: set[str] = Field(default_factory=set)
    refresh_obligation: str | None = None


class TypedGraphRecord(BaseModel):
    components: set[str] = Field(default_factory=set)
    typed_ports: dict[str, str] = Field(default_factory=dict)
    capacities: dict[str, float] = Field(default_factory=dict)
    observed_flows: dict[str, float] = Field(default_factory=dict)
    unit_tags: dict[str, str] = Field(default_factory=dict)


class TRCStateRecord(BaseModel):
    state_id: str
    observation_window: ObservationWindow
    infrastructure_graph: TypedGraphRecord
    active_components: set[str] = Field(default_factory=set)
    ledger_coordinates: set[str] = Field(default_factory=set)
    status: ClaimStatus = ClaimStatus.PROVISIONAL


class StatusAlgebraRecord(BaseModel):
    algebra_id: str
    allowed_transitions: dict[str, set[str]] = Field(default_factory=dict)
    settled_obligations: set[str] = Field(default_factory=set)
    non_promotion: bool = True


class EventContractRecord(BaseModel):
    contract_id: str
    arrival_curve: list[float]
    service_curve: list[float]
    drop_residual: float = 0.0
    event_check_cost: float = 0.0


class TransitionProofRecord(BaseModel):
    action_class: str
    precondition: dict[str, bool] = Field(default_factory=dict)
    postcondition: dict[str, bool] = Field(default_factory=dict)
    latency: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    cost: float = 0.0
    rollback_escrow: str | None = None


class ResourceFlowRecord(BaseModel):
    trace_id: str
    scenario_id: str
    reservation_interval: tuple[float, float]
    inflow_profile: list[float]
    service_profile: list[float]
    depletion_profile: list[float] = Field(default_factory=list)
    capacity: float
    conservation_residual: float = 0.0
    stale_calendar_residual: float = 0.0
    overlap_residual: float = 0.0


class ToleranceMenuItem(BaseModel):
    name: str
    fidelity_level: str
    computation_cost: float = 0.0
    latency_cost: float = 0.0
    resource_cost: float = 0.0
    recomputation_cost: float = 0.0
    residual_increment: float = 0.0

    @property
    def total_cost(self) -> float:
        return (
            self.computation_cost + self.latency_cost + self.resource_cost + self.recomputation_cost
        )


class ToleranceCostKernel(BaseModel):
    coordinate: str
    finite_menu: list[ToleranceMenuItem]
    selected_version: str | None = None
    validity_domain: str = "global"


class RiskGateRecord(BaseModel):
    finite_path_law_id: str
    script_ground_metric_id: str
    ambiguity_radius: float
    support_miss_residual: float = 0.0
    tail_residual: float = 0.0
    dual_witness_accepted: bool = False

    def accepts(self) -> bool:
        return (
            self.ambiguity_radius >= 0.0
            and self.support_miss_residual >= 0.0
            and self.tail_residual >= 0.0
            and self.dual_witness_accepted
        )


class RelaxationScheduleRecord(BaseModel):
    profiles: list[str]
    relaxed_coordinates: list[str]
    relaxation_residual: float = 0.0
    stratum_index: int = 0

    def accepts(self) -> bool:
        return bool(self.profiles) and self.relaxation_residual >= 0.0 and self.stratum_index >= 0


class BoundaryScriptAutomatonRecord(BaseModel):
    alphabet: set[str]
    prefix_bound: int
    branch_prefix_budget: int
    accepted_prefixes: set[str] = Field(default_factory=set)
    residual: float = 0.0

    def accepts(self) -> bool:
        return self.prefix_bound >= 0 and self.branch_prefix_budget >= 0 and self.residual >= 0.0


class BoundaryGeneratorRecord(BaseModel):
    generator_id: str
    alphabet: set[str] = Field(default_factory=set)
    allowed_edges: set[tuple[str, str]] = Field(default_factory=set)
    max_depth: int = 0
    generated_prefixes: set[str] = Field(default_factory=set)
    residual: float = 0.0


class BoundaryScriptRecord(BaseModel):
    script_id: str
    automaton_id: str
    tokens: list[str] = Field(default_factory=list)
    ground_metric_residual: float = 0.0


class ScriptGroundMetricCertificate(BaseModel):
    certificate_id: str
    source_script: list[str] = Field(default_factory=list)
    target_script: list[str] = Field(default_factory=list)
    distance: float = 0.0
    lower_bound: float = 0.0
    triangle_witness: bool = False
    residual: float = 0.0


class ProcessGrammarRecord(BaseModel):
    grammar_id: str
    action_classes: set[str] = Field(default_factory=set)
    start_actions: set[str] = Field(default_factory=set)
    terminal_actions: set[str] = Field(default_factory=set)
    transitions: dict[str, set[str]] = Field(default_factory=dict)
    forbidden_actions: set[str] = Field(default_factory=set)


class TraceNormalizationCertificate(BaseModel):
    trace_id: str
    source_word: list[str] = Field(default_factory=list)
    normalized_word: list[str] = Field(default_factory=list)
    commuting_pairs: set[tuple[str, str]] = Field(default_factory=set)
    rewrite_steps: list[tuple[str, str]] = Field(default_factory=list)
    confluence_witness: bool = False
    termination_witness: bool = False
    residual: float = 0.0


class TypedTraceTransducerRecord(BaseModel):
    transducer_id: str
    input_alphabet: set[str] = Field(default_factory=set)
    output_alphabet: set[str] = Field(default_factory=set)
    states: set[str] = Field(default_factory=set)
    initial_state: str
    accepting_states: set[str] = Field(default_factory=set)
    transitions: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


class ActionabilityVector(BaseModel):
    vector_id: str
    coordinates: dict[str, float] = Field(default_factory=dict)
    relaxed_coordinates: set[str] = Field(default_factory=set)
    residual: float = 0.0


class BudgetedToleranceScheduler(BaseModel):
    scheduler_id: str
    budget: float
    task_costs: dict[str, float] = Field(default_factory=dict)
    schedule: list[str] = Field(default_factory=list)
    dependency_edges: list[tuple[str, str]] = Field(default_factory=list)
    exhausted_budget_residual: float = 0.0
    partial_frontier_on_exhaustion: bool = True


class CascadeResidualPotential(BaseModel):
    potential_id: str
    component_potentials: dict[str, float] = Field(default_factory=dict)
    edge_couplings: dict[str, float] = Field(default_factory=dict)
    residual_floor: float = 0.0


class IndependenceCertificate(BaseModel):
    certificate_id: str
    variable_groups: dict[str, set[str]] = Field(default_factory=dict)
    separating_events: set[str] = Field(default_factory=set)
    dependence_residual: float = 0.0
    accepted: bool = False


class MultiHorizonOrder(BaseModel):
    order_id: str
    horizons: list[str] = Field(default_factory=list)
    precedence: list[tuple[str, str]] = Field(default_factory=list)


class FutureFreedomVector(BaseModel):
    vector_id: str
    horizons: list[str] = Field(default_factory=list)
    values: dict[str, float] = Field(default_factory=dict)
    residuals: dict[str, float] = Field(default_factory=dict)
    order: MultiHorizonOrder | None = None


class ResourceReservationRecord(BaseModel):
    reservation_id: str
    resource: str
    start_tick: int
    end_tick: int
    amount: float


class ResourceCalendarRecord(BaseModel):
    calendar_id: str
    capacities: dict[str, float] = Field(default_factory=dict)
    reservations: list[ResourceReservationRecord] = Field(default_factory=list)
    freshness_version: str = "v1"


class ToleranceAllocationCertificate(BaseModel):
    certificate_id: str
    selected_items: dict[str, str] = Field(default_factory=dict)
    budget: float
    objective_value: float
    solver: str = "finite-bruteforce"
    solver_gap: float = 0.0
    dual_bound: float | None = None
    integer_feasible: bool = True
    residual_charge: float = 0.0


class LifecycleDAGRecord(BaseModel):
    certificate_versions: dict[str, str] = Field(default_factory=dict)
    dependency_sets: dict[str, set[str]] = Field(default_factory=dict)
    invalidated_cells: set[str] = Field(default_factory=set)
    recomputation_routes: dict[str, str] = Field(default_factory=dict)
    stale_residual: float = 0.0

    def accepts(self) -> bool:
        return self.stale_residual >= 0.0 and self.invalidated_cells.issubset(
            set(self.recomputation_routes)
        )


class CausalEventPosetRecord(BaseModel):
    event_ids: set[str]
    happens_before: list[tuple[str, str]] = Field(default_factory=list)
    concurrency_residual: float = 0.0
    out_of_order_residual: float = 0.0
    missing_tick_residual: float = 0.0

    def accepts(self) -> bool:
        known = self.event_ids
        return (
            self.concurrency_residual >= 0.0
            and self.out_of_order_residual >= 0.0
            and self.missing_tick_residual >= 0.0
            and all(src in known and dst in known for src, dst in self.happens_before)
        )


class ResourceEscrowRecord(BaseModel):
    escrow_id: str
    dependency_class: str
    resource_use: dict[str, float] = Field(default_factory=dict)
    capacity_ledger: dict[str, float] = Field(default_factory=dict)
    commutation_certificate: bool = False
    resolution_status: ClaimStatus = ClaimStatus.PROVISIONAL

    def accepts(self) -> bool:
        return self.commutation_certificate and all(
            amount <= self.capacity_ledger.get(resource, 0.0)
            for resource, amount in self.resource_use.items()
        )


class ExecutableTraceNormalForm(BaseModel):
    trace_id: str
    normalized_word: list[str]
    normalization: TraceNormalizationCertificate | None = None
    step_proofs: list[TransitionProofRecord] = Field(default_factory=list)
    precondition: dict[str, bool] = Field(default_factory=dict)
    postcondition: dict[str, bool] = Field(default_factory=dict)
    causal_schedule: CausalEventPosetRecord | None = None
    latency_ledger: dict[str, float] = Field(default_factory=dict)
    resource_flow_profile: list[ResourceFlowRecord] = Field(default_factory=list)
    resource_calendar: ResourceCalendarRecord | None = None
    escrows: list[ResourceEscrowRecord] = Field(default_factory=list)
    lifecycle: LifecycleDAGRecord | None = None
    future_freedom: FutureFreedomVector | None = None
    rollback_obligations: list[str] = Field(default_factory=list)
    certificate_versions: list[str] = Field(default_factory=list)
    tolerance_versions: list[str] = Field(default_factory=list)
    error_budget: float = 0.0
    validity_domain: str = "global"
    trace_residual: float = 0.0


class ArchiveOutputRecord(FrontierRecord):
    horizon: str = "first"
    status_key: str = "provisional"
    latent_cell: str = "cell-0"
    epsilon_charge: float = 0.0
    truncation_residual: float = 0.0
    relaxation_residual: float = 0.0
    diagnostic_flag: bool = False


class TRCCompileResult(BaseModel):
    main_frontier: list[FrontierRecord] = Field(default_factory=list)
    risk_frontier: list[FrontierRecord] = Field(default_factory=list)
    relaxed_frontier: list[FrontierRecord] = Field(default_factory=list)
    partial_frontier: list[FrontierRecord] = Field(default_factory=list)
    diagnostic_archive: list[FrontierRecord] = Field(default_factory=list)
    efficiency_archive: list[FrontierRecord] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
