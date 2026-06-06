"""ECPT record types."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.order import FiniteOrder
from percolation_inversion_compiler.core.status import ClaimStatus


class ObservationProtocol(BaseModel):
    time_index: str
    window_family: list[str] = Field(default_factory=list)
    receiver_contexts: list[str] = Field(default_factory=list)
    validity_domains: list[str] = Field(default_factory=list)


class ProtocolFunctorCertificate(BaseModel):
    certificate_id: str
    source_protocol: ObservationProtocol
    target_protocol: ObservationProtocol
    object_map: dict[str, str] = Field(default_factory=dict)
    obligation_map: dict[str, str] = Field(default_factory=dict)
    ontology_extension_obligations: set[str] = Field(default_factory=set)
    accepted_extension: bool = False
    residual: float = 0.0


class PhaseControlEnvelope(BaseModel):
    envelope_id: str
    finite_state_space: set[str] = Field(default_factory=set)
    control_surface: dict[str, float] = Field(default_factory=dict)
    phase_response: dict[str, float] = Field(default_factory=dict)
    finite_horizon: int = 0
    thermodynamic_obligation_ids: set[str] = Field(default_factory=set)
    residual: float = 0.0


class FinitePhaseControlCertificate(BaseModel):
    certificate_id: str
    envelope: PhaseControlEnvelope
    baseline_response: float = 0.0
    controlled_response: float = 0.0
    minimum_improvement: float = 0.0
    thermodynamic_obligation_ids: set[str] = Field(default_factory=set)
    residual: float = 0.0


class ConstraintFrame(BaseModel):
    hard_gates: dict[str, bool] = Field(default_factory=dict)
    hazards: Ledger = Field(default_factory=Ledger)
    capacity: Ledger = Field(default_factory=Ledger)
    queue: Ledger = Field(default_factory=Ledger)
    expires: set[str] = Field(default_factory=set)

    def hard_domain_live(self) -> bool:
        return all(self.hard_gates.values())


class DiagnosticOrder(BaseModel):
    positive_order: FiniteOrder
    burden_order: FiniteOrder


class AdmissibilityGrade(BaseModel):
    grade_id: str
    hard_indicator: bool
    activation_weight: float
    burden: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL


class TargetValidityStatus(BaseModel):
    domain: str
    receiver_family: set[str] = Field(default_factory=set)
    target_basis: str = "default"
    mandatory_obligations: set[str] = Field(default_factory=set)
    refresh_obligations: set[str] = Field(default_factory=set)
    stop_obligations: set[str] = Field(default_factory=set)


class CapabilityEdge(BaseModel):
    edge_id: str
    sources: tuple[str, ...]
    target: str
    activation_weight: float = 1.0
    burden: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    required_capacity: dict[str, float] = Field(default_factory=dict)


class CapabilityPacket(BaseModel):
    packet_id: str
    coordinates: dict[str, float] = Field(default_factory=dict)
    validity_domain: str = "global"
    duplicate_mass: float = 0.0
    burden: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL

    def effective_mass(self, coordinate: str) -> float:
        return max(0.0, self.coordinates.get(coordinate, 0.0) - self.duplicate_mass - self.burden)


class CapabilityStateVector(BaseModel):
    packets: list[CapabilityPacket] = Field(default_factory=list)
    burden_ledger: Ledger = Field(default_factory=Ledger)
    validity_domain: str = "global"


class FiniteTraceLaw(BaseModel):
    law_id: str
    traces: dict[str, float] = Field(default_factory=dict)
    normalized: bool = False
    support_residual: float = 0.0


class PacketAtlas(BaseModel):
    atlas_id: str
    strata: dict[str, set[str]] = Field(default_factory=dict)
    transition_kernel: dict[str, dict[str, float]] = Field(default_factory=dict)
    boundary_residual: float = 0.0


class InformationProjectionQuotient(BaseModel):
    quotient_id: str
    chart_id: str
    distortion: float = 0.0
    chart_validity_radius: float = 0.0


class CapabilityHypergraph(BaseModel):
    nodes: set[str] = Field(default_factory=set)
    edges: list[CapabilityEdge] = Field(default_factory=list)
    seed_mass: dict[str, float] = Field(default_factory=dict)

    def all_nodes(self) -> set[str]:
        nodes = set(self.nodes) | set(self.seed_mass)
        for edge in self.edges:
            nodes.add(edge.target)
            nodes.update(edge.sources)
        return nodes


class ActionGrammar(BaseModel):
    actions: set[str] = Field(default_factory=set)
    preconditions: dict[str, set[str]] = Field(default_factory=dict)
    postconditions: dict[str, set[str]] = Field(default_factory=dict)


class PostconditionObligation(BaseModel):
    action_id: str
    required_postconditions: set[str] = Field(default_factory=set)
    satisfied_postconditions: set[str] = Field(default_factory=set)


class ControlledTransition(BaseModel):
    transition_id: str
    action_id: str
    preconditions_met: bool = False
    postcondition_obligation: PostconditionObligation | None = None
    status: ClaimStatus = ClaimStatus.PROVISIONAL
    residual: float = 0.0


class InnerViabilityKernel(BaseModel):
    kernel_id: str
    states: set[str] = Field(default_factory=set)
    inner_states: set[str] = Field(default_factory=set)
    transition_map: dict[str, set[str]] = Field(default_factory=dict)
    residual: float = 0.0


class QueueCertificate(BaseModel):
    queue_id: str
    arrivals: list[float]
    service: list[float]
    reserve: float
    accepted_latency: float | None = None

    def accepts(self) -> bool:
        return len(self.arrivals) == len(self.service) and self.reserve >= 0


class CapacityCertificate(BaseModel):
    capacity_id: str
    available: dict[str, float] = Field(default_factory=dict)
    required: dict[str, float] = Field(default_factory=dict)
    debt: dict[str, float] = Field(default_factory=dict)

    def accepts(self) -> bool:
        return all(
            self.available.get(resource, 0.0) >= amount + self.debt.get(resource, 0.0)
            for resource, amount in self.required.items()
        )


class ActivationConstructionCertificate(BaseModel):
    construction_id: str
    configuration_space_size: int
    energy_ledger_present: bool = False
    sampler_residual: float = 0.0
    exact: bool = False

    def accepts(self) -> bool:
        return (
            self.configuration_space_size > 0
            and self.energy_ledger_present
            and (self.exact or self.sampler_residual >= 0.0)
        )


class PathLawResponsePolicyCertificate(BaseModel):
    policy_id: str
    baseline_law_id: str
    candidate_law_id: str
    overlap: float
    effective_sample_size: float
    residual: float = 0.0

    def accepts(self) -> bool:
        return self.overlap > 0.0 and self.effective_sample_size > 0.0 and self.residual >= 0.0


class SettlementEventAlgebra(BaseModel):
    algebra_id: str
    settled_events: set[str] = Field(default_factory=set)
    ruin_events: set[str] = Field(default_factory=set)
    expiration_events: set[str] = Field(default_factory=set)

    def settles(self, event_id: str) -> bool:
        return event_id in self.settled_events and event_id not in (
            self.ruin_events | self.expiration_events
        )


class RAFSettlementCertificate(BaseModel):
    certificate_id: str
    event_algebra: SettlementEventAlgebra
    event_id: str
    transition_ledger_present: bool = False
    debt_ledger_present: bool = False
    risk_ledger_present: bool = False


class SettlementReturnRAFCertificate(BaseModel):
    certificate_id: str
    raf_certificate: RAFSettlementCertificate
    required_ledger_obligations: set[str] = Field(default_factory=set)
    present_ledger_obligations: set[str] = Field(default_factory=set)
    external_settlement_obligations: set[str] = Field(default_factory=set)
    residual: float = 0.0


class CycleMonitorCertificate(BaseModel):
    monitor_id: str
    cycle_ids: set[str] = Field(default_factory=set)
    stopped_cycles: set[str] = Field(default_factory=set)
    runtime_bound: int = 0


class ResourceNormalizedCut(BaseModel):
    cut_id: str
    release_delta: float
    resource_cost: float
    normalization_unit: str = "dimensionless"


class ReachableMassRecursionCertificate(BaseModel):
    certificate_id: str
    graph: CapabilityHypergraph
    target_nodes: set[str] = Field(default_factory=set)
    lower_bounds: dict[str, float] = Field(default_factory=dict)
    status_floor: ClaimStatus = ClaimStatus.SPECULATIVE


class ActivationThresholdCertificate(BaseModel):
    certificate_id: str
    activation: ActivationConstructionCertificate
    graph: CapabilityHypergraph
    target_nodes: set[str] = Field(default_factory=set)
    lower_bounds: dict[str, float] = Field(default_factory=dict)
    threshold: float = 0.0
    finite_size: int = 0
    thermodynamic_obligation_ids: set[str] = Field(default_factory=set)
    residual: float = 0.0


class MeanFieldEnvelopeCertificate(BaseModel):
    envelope_id: str
    chart_id: str
    finite_horizon: int
    generator_identified: bool = False
    coupling_residual: float = 0.0
    reachable_mass_residual: float = 0.0

    def accepts(self) -> bool:
        return (
            self.finite_horizon >= 0
            and self.generator_identified
            and self.coupling_residual >= 0.0
            and self.reachable_mass_residual >= 0.0
        )
