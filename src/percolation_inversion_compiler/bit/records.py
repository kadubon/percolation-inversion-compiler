"""BIT record types."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.order import FiniteOrder
from percolation_inversion_compiler.core.status import ClaimStatus


class ProtocolObject(BaseModel):
    protocol_id: str
    candidate_universe: set[str] = Field(default_factory=set)
    law_labels: set[str] = Field(default_factory=set)
    observation_sigma: set[str] = Field(default_factory=set)
    validity_domains: set[str] = Field(default_factory=set)


class InterventionLaw(BaseModel):
    law_id: str
    support: set[str] = Field(default_factory=set)
    probabilities: dict[str, float] = Field(default_factory=dict)
    normalized: bool = False


class StoppedEvidenceWitness(BaseModel):
    probability_space: str
    stopping_time: str
    ledger_id: str
    evidence_ids: set[str] = Field(default_factory=set)


class PullbackGluingWitness(BaseModel):
    witness_id: str
    local_sections: dict[str, set[str]] = Field(default_factory=dict)
    overlaps: dict[str, set[str]] = Field(default_factory=dict)
    glued_section: set[str] = Field(default_factory=set)


class StoppedEvidenceSheafCertificate(BaseModel):
    certificate_id: str
    witnesses: list[StoppedEvidenceWitness] = Field(default_factory=list)
    gluing_witness: PullbackGluingWitness | None = None
    missing_sections: set[str] = Field(default_factory=set)
    residual: float = 0.0


class SelectivePotentialResult(BaseModel):
    reported: dict[str, float]
    unreported: dict[str, str] = Field(default_factory=dict)
    charges: Ledger = Field(default_factory=Ledger)


class MechanismCube(BaseModel):
    path_channel: str
    log_channel: str
    observation_channel: str
    factorization_rank: int
    negative_control_rank: int
    proximal_bridge: bool = False
    triangular_commutator_zero: bool = False


class MechanismCubeCertificate(BaseModel):
    certificate_id: str
    cube: MechanismCube
    release_channel: str
    negative_control_channels: set[str] = Field(default_factory=set)
    paired_null_witnesses: dict[str, str] = Field(default_factory=dict)
    non_substitution_residual: float = 0.0
    accepted: bool = False


class UnitConversion(BaseModel):
    source_unit: str
    target_unit: str
    factor: float
    audit_id: str


class UnitFunctorCertificate(BaseModel):
    ordered_units: set[str] = Field(default_factory=set)
    conversions: list[UnitConversion] = Field(default_factory=list)
    monotone: bool = False

    def accepts(self) -> bool:
        return self.monotone and all(conversion.factor > 0 for conversion in self.conversions)


class OrderedPotentialCone(BaseModel):
    cone_id: str
    coordinate_kinds: dict[str, str] = Field(default_factory=dict)
    product_order: FiniteOrder
    unit_functor: UnitFunctorCertificate | None = None


class VectorCompatibleFamily(BaseModel):
    family_id: str
    protocol: ProtocolObject
    laws: list[InterventionLaw] = Field(default_factory=list)
    potential_cone: OrderedPotentialCone
    report_mask: set[str] = Field(default_factory=set)
    dependency_graph: DependencyDAG = Field(default_factory=DependencyDAG)
    resource_ledger: Ledger = Field(default_factory=Ledger)


class SelectiveCUPCertificate(BaseModel):
    certificate_id: str
    family: VectorCompatibleFamily
    lower_process: dict[str, float] = Field(default_factory=dict)
    selection_charge: dict[str, float] = Field(default_factory=dict)
    report_mask: set[str] = Field(default_factory=set)
    unit_audit: set[str] = Field(default_factory=set)
    required_reported: set[str] = Field(default_factory=set)
    residual: float = 0.0


class MartingalePartitionAudit(BaseModel):
    block_bounds: list[float]
    boundary_drift: float = 0.0
    selection_charge: float = 0.0
    confidence_radius: float = 0.0
    carved_splits: set[str] = Field(default_factory=set)
    uncarved_splits: set[str] = Field(default_factory=set)

    def accepts(self) -> bool:
        return bool(self.block_bounds) and not self.uncarved_splits


class MartingaleDeficiencyCertificate(BaseModel):
    certificate_id: str
    audit: MartingalePartitionAudit
    lower_mass_floor: float = 0.0
    residual_tolerance: float = 0.0


class EpigraphReleaseProgram(BaseModel):
    inner_primal_value: float
    outer_dual_value: float
    slater_witness: bool = False
    unit_ledger_accepted: bool = False
    exactness_residual: float = 0.0

    def accepts(self) -> bool:
        return (
            self.slater_witness
            and self.unit_ledger_accepted
            and self.inner_primal_value <= self.outer_dual_value
        )


class CEGARRefinementTrace(BaseModel):
    trace_id: str
    abstraction_id: str
    contraction: float
    barrier_floor: float = 0.0
    counterexamples: list[str] = Field(default_factory=list)
    refinements: list[str] = Field(default_factory=list)

    def accepts(self) -> bool:
        return 0.0 <= self.contraction <= 1.0 and not self.counterexamples


class MECRecord(FrontierRecord):
    positive_release: bool = False
    mechanism_factorized_non_substitution: bool = False
    cost: float = 0.0
    load: float = 0.0
    friction: float = 0.0
    status: ClaimStatus = ClaimStatus.PROVISIONAL


class SinkhornCertificate(BaseModel):
    source: list[float]
    target: list[float]
    plan: list[list[float]]
    marginal_tolerance: float = 1e-6
    duality_gap: float = 0.0
    solver_gap: float = 0.0
    unit_ledger_charge: float = 0.0


class FusedGeometricComparisonCertificate(BaseModel):
    certificate_id: str
    source_nodes: set[str] = Field(default_factory=set)
    target_nodes: set[str] = Field(default_factory=set)
    coupling: list[tuple[str, str, float]] = Field(default_factory=list)
    geometry_distortion: float = 0.0
    feature_distortion: float = 0.0
    marginal_residual: float = 0.0
    solver_gap: float = 0.0
    distortion_upper_bound: float = 0.0
    accepted: bool = False


class CertificateCompilerRecord(BaseModel):
    compiler_id: str
    dependency_graph: DependencyDAG = Field(default_factory=DependencyDAG)
    witness_nodes: set[str] = Field(default_factory=set)
    coordinate_nodes: set[str] = Field(default_factory=set)
    law_labels: dict[str, str] = Field(default_factory=dict)
    unit_labels: dict[str, str] = Field(default_factory=dict)
    resource_labels: dict[str, str] = Field(default_factory=dict)
    accepted_nodes: set[str] = Field(default_factory=set)
