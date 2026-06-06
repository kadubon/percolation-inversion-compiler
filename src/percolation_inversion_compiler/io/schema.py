"""JSON Schema and data validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from percolation_inversion_compiler.bit.records import (
    CertificateCompilerRecord,
    FusedGeometricComparisonCertificate,
    MartingaleDeficiencyCertificate,
    MechanismCubeCertificate,
    OrderedPotentialCone,
    ProtocolObject,
    PullbackGluingWitness,
    SelectiveCUPCertificate,
    SinkhornCertificate,
    StoppedEvidenceSheafCertificate,
    VectorCompatibleFamily,
)
from percolation_inversion_compiler.core.adapter_routes import (
    AdapterRouteSpec,
    DischargeRouteBinding,
    EvidenceArtifact,
    EvidencePolicy,
    EvidenceVerificationProfileRecord,
    VerifierEvidenceEnvelope,
    VerifierResolution,
)
from percolation_inversion_compiler.core.algebra import (
    AlgebraLawCertificate,
    DomainTypedSemiring,
    FunctorLawCertificate,
    MonoidRecord,
    ReconstructionResidual,
)
from percolation_inversion_compiler.core.calibration import (
    CalibrationCertificate,
    ConfidenceLedger,
    DKWCertificate,
    EProcessCertificate,
    GoodTuringCertificate,
    MartingaleBlockResidual,
    SplitCertificate,
)
from percolation_inversion_compiler.core.certificates import (
    CertificateFamily,
    CertificateRoute,
    NonPromotionPolicy,
    RefreshRule,
)
from percolation_inversion_compiler.core.checker import (
    CheckerContext,
    ObligationRule,
    ObligationTrace,
    ProjectionAudit,
    TheoryAuditReport,
)
from percolation_inversion_compiler.core.coverage import (
    ExternalObligationCatalog,
    ImplementationMaturityRecord,
    TheoryImplementationRecord,
)
from percolation_inversion_compiler.core.judgment import (
    AgentConnectorSpec,
    Judgment,
    ObligationSet,
)
from percolation_inversion_compiler.core.ledger import LedgerCoordinate
from percolation_inversion_compiler.core.operations import (
    OperationalCheck,
    OperationalReadinessReport,
    ProductionReadinessProfile,
)
from percolation_inversion_compiler.core.order import (
    DominanceWitness,
    FiniteOrder,
    LatticeWitness,
    MonotoneMap,
    ProductOrder,
)
from percolation_inversion_compiler.core.records import (
    CheckResult,
    ExternalProofObligation,
    ExternalVerifierHook,
    Registry,
)
from percolation_inversion_compiler.ecology.records import (
    BottleneckIntervention,
    BottleneckInversionPlan,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    ClosedLoopAgentIteration,
    EdgeWitness,
    PacketIngestionReport,
    PsiDashboard,
    VerificationThroughputReport,
)
from percolation_inversion_compiler.ecpt.records import (
    ActionGrammar,
    ActivationThresholdCertificate,
    ASIProxyTargetContract,
    CapabilityStateVector,
    ControlledTransition,
    FinitePhaseControlCertificate,
    FiniteTraceLaw,
    InnerViabilityKernel,
    InterventionCandidate,
    PhaseControlAction,
    PhaseControlEnvelope,
    PhaseControlObjective,
    PhaseControlPlan,
    PhaseControlRunReport,
    PhaseControlState,
    ProtocolFunctorCertificate,
    ReachableMassRecursionCertificate,
    SettlementReturnRAFCertificate,
)
from percolation_inversion_compiler.io.provenance import (
    AttestationRecord,
    ProvenanceManifest,
    ProvenanceManifestEntry,
    ReleaseArtifactManifest,
    SchemaBundleDigest,
)
from percolation_inversion_compiler.io.sbom import SBOMManifest
from percolation_inversion_compiler.io.snapshots import (
    SnapshotAttribution,
    SnapshotCatalog,
    TheorySnapshot,
    TheorySnapshotItem,
)
from percolation_inversion_compiler.io.tex import StrictTexParseReport, TexGrammarDiagnostic
from percolation_inversion_compiler.io.zenodo import CanonicalManifest, CanonicalManifestRecord
from percolation_inversion_compiler.sqot.records import (
    DiagnosticReservePolicy,
    OccupationLedger,
    QuarantineLedger,
    RiskBudgetLedger,
    SalienceQueueRecord,
    SalienceScheduleReport,
    SalienceSchedulingDecision,
    SQOTTheorySnapshot,
)
from percolation_inversion_compiler.trc.records import (
    ActionabilityVector,
    BoundaryGeneratorRecord,
    BoundaryScriptRecord,
    BudgetedToleranceScheduler,
    CascadeResidualPotential,
    ExecutableTraceNormalForm,
    FutureFreedomVector,
    IndependenceCertificate,
    ObservationWindow,
    ProcessGrammarRecord,
    ResourceCalendarRecord,
    ScriptGroundMetricCertificate,
    StatusAlgebraRecord,
    ToleranceAllocationCertificate,
    TraceNormalizationCertificate,
    TRCCompileResult,
    TRCStateRecord,
    TypedTraceTransducerRecord,
)


class PortabilitySchemaBundle(BaseModel):
    """Named JSON Schema bundle for other implementations and agents."""

    bundle_id: str = "percolation-inversion-compiler-portability"
    schemas: dict[str, dict[str, Any]]


def load_data(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if source.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("top-level registry data must be an object")
    return data


def registry_json_schema() -> dict[str, Any]:
    return Registry.model_json_schema()


def schema_model_map() -> dict[str, type[BaseModel]]:
    """Return stable public schema model names."""

    return {
        "AgentConnectorSpec": AgentConnectorSpec,
        "AdapterRouteSpec": AdapterRouteSpec,
        "AlgebraLawCertificate": AlgebraLawCertificate,
        "ActionGrammar": ActionGrammar,
        "ActionabilityVector": ActionabilityVector,
        "ActivationThresholdCertificate": ActivationThresholdCertificate,
        "ASIProxyTargetContract": ASIProxyTargetContract,
        "AttestationRecord": AttestationRecord,
        "BottleneckIntervention": BottleneckIntervention,
        "BottleneckInversionPlan": BottleneckInversionPlan,
        "BoundaryGeneratorRecord": BoundaryGeneratorRecord,
        "BoundaryScriptRecord": BoundaryScriptRecord,
        "BudgetedToleranceScheduler": BudgetedToleranceScheduler,
        "CalibrationCertificate": CalibrationCertificate,
        "CapabilityPacketCandidate": CapabilityPacketCandidate,
        "CapabilityPacketRegistry": CapabilityPacketRegistry,
        "CapabilityStateVector": CapabilityStateVector,
        "CascadeResidualPotential": CascadeResidualPotential,
        "CertificateCompilerRecord": CertificateCompilerRecord,
        "CertificateFamily": CertificateFamily,
        "CertificateRoute": CertificateRoute,
        "CheckResult": CheckResult,
        "CheckerContext": CheckerContext,
        "ClosedLoopAgentIteration": ClosedLoopAgentIteration,
        "ConfidenceLedger": ConfidenceLedger,
        "ControlledTransition": ControlledTransition,
        "DKWCertificate": DKWCertificate,
        "DiagnosticReservePolicy": DiagnosticReservePolicy,
        "DischargeRouteBinding": DischargeRouteBinding,
        "DomainTypedSemiring": DomainTypedSemiring,
        "DominanceWitness": DominanceWitness,
        "EProcessCertificate": EProcessCertificate,
        "EdgeWitness": EdgeWitness,
        "EvidenceArtifact": EvidenceArtifact,
        "EvidencePolicy": EvidencePolicy,
        "EvidenceVerificationProfile": EvidenceVerificationProfileRecord,
        "ExecutableTraceNormalForm": ExecutableTraceNormalForm,
        "ExternalObligationCatalog": ExternalObligationCatalog,
        "ExternalVerifierHook": ExternalVerifierHook,
        "FinitePhaseControlCertificate": FinitePhaseControlCertificate,
        "FiniteOrder": FiniteOrder,
        "FiniteTraceLaw": FiniteTraceLaw,
        "FusedGeometricComparisonCertificate": FusedGeometricComparisonCertificate,
        "FutureFreedomVector": FutureFreedomVector,
        "FunctorLawCertificate": FunctorLawCertificate,
        "GoodTuringCertificate": GoodTuringCertificate,
        "IndependenceCertificate": IndependenceCertificate,
        "ImplementationMaturity": ImplementationMaturityRecord,
        "InnerViabilityKernel": InnerViabilityKernel,
        "InterventionCandidate": InterventionCandidate,
        "Judgment": Judgment,
        "LatticeWitness": LatticeWitness,
        "LedgerCoordinate": LedgerCoordinate,
        "MartingaleDeficiencyCertificate": MartingaleDeficiencyCertificate,
        "MartingaleBlockResidual": MartingaleBlockResidual,
        "MechanismCubeCertificate": MechanismCubeCertificate,
        "MonoidRecord": MonoidRecord,
        "MonotoneMap": MonotoneMap,
        "NonPromotionPolicy": NonPromotionPolicy,
        "ObligationRule": ObligationRule,
        "ObligationSet": ObligationSet,
        "ObligationTrace": ObligationTrace,
        "ObservationWindow": ObservationWindow,
        "OccupationLedger": OccupationLedger,
        "OperationalCheck": OperationalCheck,
        "OperationalReadinessReport": OperationalReadinessReport,
        "OrderedPotentialCone": OrderedPotentialCone,
        "PhaseControlAction": PhaseControlAction,
        "PhaseControlEnvelope": PhaseControlEnvelope,
        "PhaseControlObjective": PhaseControlObjective,
        "PhaseControlPlan": PhaseControlPlan,
        "PhaseControlRunReport": PhaseControlRunReport,
        "PhaseControlState": PhaseControlState,
        "PacketIngestionReport": PacketIngestionReport,
        "PortabilitySchemaBundle": PortabilitySchemaBundle,
        "ProvenanceManifest": ProvenanceManifest,
        "ProvenanceManifestEntry": ProvenanceManifestEntry,
        "ReleaseArtifactManifest": ReleaseArtifactManifest,
        "ProductOrder": ProductOrder,
        "ProductionReadinessProfile": ProductionReadinessProfile,
        "ProcessGrammarRecord": ProcessGrammarRecord,
        "ProtocolObject": ProtocolObject,
        "ProtocolFunctorCertificate": ProtocolFunctorCertificate,
        "ProjectionAudit": ProjectionAudit,
        "ProofObligation": ExternalProofObligation,
        "PsiDashboard": PsiDashboard,
        "PullbackGluingWitness": PullbackGluingWitness,
        "QuarantineLedger": QuarantineLedger,
        "ReachableMassRecursionCertificate": ReachableMassRecursionCertificate,
        "ReconstructionResidual": ReconstructionResidual,
        "RefreshRule": RefreshRule,
        "Registry": Registry,
        "ResourceCalendarRecord": ResourceCalendarRecord,
        "RiskBudgetLedger": RiskBudgetLedger,
        "SQOTTheorySnapshot": SQOTTheorySnapshot,
        "ScriptGroundMetricCertificate": ScriptGroundMetricCertificate,
        "SchemaBundleDigest": SchemaBundleDigest,
        "SelectiveCUPCertificate": SelectiveCUPCertificate,
        "SettlementReturnRAFCertificate": SettlementReturnRAFCertificate,
        "SinkhornCertificate": SinkhornCertificate,
        "SBOMManifest": SBOMManifest,
        "SalienceQueueRecord": SalienceQueueRecord,
        "SalienceScheduleReport": SalienceScheduleReport,
        "SalienceSchedulingDecision": SalienceSchedulingDecision,
        "SplitCertificate": SplitCertificate,
        "StatusAlgebraRecord": StatusAlgebraRecord,
        "StoppedEvidenceSheafCertificate": StoppedEvidenceSheafCertificate,
        "StrictTexParseReport": StrictTexParseReport,
        "TRCStateRecord": TRCStateRecord,
        "TRCCompileResult": TRCCompileResult,
        "ToleranceAllocationCertificate": ToleranceAllocationCertificate,
        "TheoryAuditReport": TheoryAuditReport,
        "TheoryImplementationRecord": TheoryImplementationRecord,
        "TheorySnapshot": TheorySnapshot,
        "TheorySnapshotItem": TheorySnapshotItem,
        "TexGrammarDiagnostic": TexGrammarDiagnostic,
        "TraceNormalizationCertificate": TraceNormalizationCertificate,
        "TypedTraceTransducerRecord": TypedTraceTransducerRecord,
        "VectorCompatibleFamily": VectorCompatibleFamily,
        "SnapshotAttribution": SnapshotAttribution,
        "SnapshotCatalog": SnapshotCatalog,
        "VerifierEvidenceEnvelope": VerifierEvidenceEnvelope,
        "VerifierResolution": VerifierResolution,
        "VerificationThroughputReport": VerificationThroughputReport,
        "CanonicalManifest": CanonicalManifest,
        "CanonicalManifestRecord": CanonicalManifestRecord,
    }


def schema_by_type(type_name: str = "Registry") -> dict[str, Any]:
    """Return a stable public JSON Schema by type name."""

    schemas = schema_model_map()
    try:
        return schemas[type_name].model_json_schema()
    except KeyError as exc:
        available = ", ".join(sorted(schemas))
        raise ValueError(f"unknown schema type {type_name!r}; available: {available}") from exc


def schema_bundle() -> PortabilitySchemaBundle:
    return PortabilitySchemaBundle(
        schemas={name: model.model_json_schema() for name, model in schema_model_map().items()}
    )


def validate_data(data: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    validator = Draft202012Validator(schema or registry_json_schema())
    return [error.message for error in sorted(validator.iter_errors(data), key=str)]
