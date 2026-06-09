"""JSON Schema and data validation helpers."""

from __future__ import annotations

import json
from enum import StrEnum
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
    AcceptedPacketPath,
    AutocatalyticClosureWitness,
    BasinReachabilityReport,
    BottleneckIntervention,
    BottleneckInversionPlan,
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    ClosedLoopAgentIteration,
    EdgeRelationVerificationReport,
    EdgeRelationVerifierSpec,
    EdgeWitness,
    EdgeWitnessCertificate,
    ExecutionAvailablePathCertificate,
    HiddenCapabilityInjectionReport,
    PacketCapitalLineage,
    PacketIngestionReport,
    PacketPromotionPolicy,
    PacketPromotionReport,
    PacketRejection,
    ProtocolFrameDigest,
    PsiDashboard,
    VerificationThroughputReport,
    VerifiedCapabilityPacket,
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
from percolation_inversion_compiler.identity.records import (
    AgentIdentityAttestation,
    AgentIdentityCheckReport,
    CryptographicAgentIdentity,
    IdentityContributionStatus,
    IdentityTrustProfile,
    SybilResistanceLedger,
    SybilResistancePolicy,
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
from percolation_inversion_compiler.runtime.records import (
    AccelerationCertificate,
    AccelerationExperimentSuite,
    ActionCommit,
    AgentPolicyIdentity,
    AgentPopulationState,
    AgentRuntimeConfig,
    AgentTask,
    CollectivePhaseCertificate,
    ContentAddressedEvidenceRef,
    EvidenceEnvelopeStoreRecord,
    EvidenceResolutionBatch,
    FixedPopulationLedger,
    PhaseAccelerationScore,
    PopulationRuntimeStepReport,
    ResourceEnvelope,
    ResourceMatchedBaselineConfig,
    RouteExecutionBatch,
    RouteExecutionRequest,
    RuntimeActionResult,
    RuntimeComparisonReport,
    RuntimeEvent,
    RuntimeEventLog,
    RuntimeExecutionReport,
    RuntimeExecutorPolicy,
    RuntimeHealthReport,
    RuntimeIdentityContext,
    RuntimeRunReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
    RuntimeStoreRecord,
    RuntimeStoreSnapshot,
)
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


def schema_model_map() -> dict[str, type[Any]]:
    """Return stable public schema model names."""

    return {
        "AcceptedPacketPath": AcceptedPacketPath,
        "ActionCommit": ActionCommit,
        "AccelerationCertificate": AccelerationCertificate,
        "AccelerationExperimentSuite": AccelerationExperimentSuite,
        "AgentConnectorSpec": AgentConnectorSpec,
        "AgentIdentityAttestation": AgentIdentityAttestation,
        "AgentIdentityCheckReport": AgentIdentityCheckReport,
        "AgentPolicyIdentity": AgentPolicyIdentity,
        "AgentPopulationState": AgentPopulationState,
        "AgentRuntimeConfig": AgentRuntimeConfig,
        "AgentTask": AgentTask,
        "AdapterRouteSpec": AdapterRouteSpec,
        "AlgebraLawCertificate": AlgebraLawCertificate,
        "ActionGrammar": ActionGrammar,
        "ActionabilityVector": ActionabilityVector,
        "ActivationThresholdCertificate": ActivationThresholdCertificate,
        "ASIProxyTargetContract": ASIProxyTargetContract,
        "AttestationRecord": AttestationRecord,
        "AutocatalyticClosureWitness": AutocatalyticClosureWitness,
        "BasinReachabilityReport": BasinReachabilityReport,
        "BottleneckIntervention": BottleneckIntervention,
        "BottleneckInversionPlan": BottleneckInversionPlan,
        "BoundaryGeneratorRecord": BoundaryGeneratorRecord,
        "BoundaryScriptRecord": BoundaryScriptRecord,
        "BudgetedToleranceScheduler": BudgetedToleranceScheduler,
        "CalibrationCertificate": CalibrationCertificate,
        "CapabilityBasinContract": CapabilityBasinContract,
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
        "CollectivePhaseCertificate": CollectivePhaseCertificate,
        "ConfidenceLedger": ConfidenceLedger,
        "ControlledTransition": ControlledTransition,
        "CryptographicAgentIdentity": CryptographicAgentIdentity,
        "IdentityContributionStatus": IdentityContributionStatus,
        "IdentityTrustProfile": IdentityTrustProfile,
        "DKWCertificate": DKWCertificate,
        "DiagnosticReservePolicy": DiagnosticReservePolicy,
        "DischargeRouteBinding": DischargeRouteBinding,
        "DomainTypedSemiring": DomainTypedSemiring,
        "DominanceWitness": DominanceWitness,
        "EProcessCertificate": EProcessCertificate,
        "EdgeWitness": EdgeWitness,
        "EdgeWitnessCertificate": EdgeWitnessCertificate,
        "EdgeRelationVerificationReport": EdgeRelationVerificationReport,
        "EdgeRelationVerifierSpec": EdgeRelationVerifierSpec,
        "ExecutionAvailablePathCertificate": ExecutionAvailablePathCertificate,
        "ContentAddressedEvidenceRef": ContentAddressedEvidenceRef,
        "EvidenceEnvelopeStoreRecord": EvidenceEnvelopeStoreRecord,
        "EvidenceResolutionBatch": EvidenceResolutionBatch,
        "EvidenceArtifact": EvidenceArtifact,
        "EvidencePolicy": EvidencePolicy,
        "EvidenceVerificationProfile": EvidenceVerificationProfileRecord,
        "ExecutableTraceNormalForm": ExecutableTraceNormalForm,
        "ExternalObligationCatalog": ExternalObligationCatalog,
        "ExternalVerifierHook": ExternalVerifierHook,
        "FixedPopulationLedger": FixedPopulationLedger,
        "FinitePhaseControlCertificate": FinitePhaseControlCertificate,
        "FiniteOrder": FiniteOrder,
        "FiniteTraceLaw": FiniteTraceLaw,
        "FusedGeometricComparisonCertificate": FusedGeometricComparisonCertificate,
        "FutureFreedomVector": FutureFreedomVector,
        "FunctorLawCertificate": FunctorLawCertificate,
        "GoodTuringCertificate": GoodTuringCertificate,
        "HiddenCapabilityInjectionReport": HiddenCapabilityInjectionReport,
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
        "PhaseAccelerationScore": PhaseAccelerationScore,
        "PhaseControlAction": PhaseControlAction,
        "PhaseControlEnvelope": PhaseControlEnvelope,
        "PhaseControlObjective": PhaseControlObjective,
        "PhaseControlPlan": PhaseControlPlan,
        "PhaseControlRunReport": PhaseControlRunReport,
        "PhaseControlState": PhaseControlState,
        "PacketIngestionReport": PacketIngestionReport,
        "PacketCapitalLineage": PacketCapitalLineage,
        "PacketPromotionPolicy": PacketPromotionPolicy,
        "PacketPromotionReport": PacketPromotionReport,
        "PacketRejection": PacketRejection,
        "PortabilitySchemaBundle": PortabilitySchemaBundle,
        "PopulationRuntimeStepReport": PopulationRuntimeStepReport,
        "ProvenanceManifest": ProvenanceManifest,
        "ProvenanceManifestEntry": ProvenanceManifestEntry,
        "ReleaseArtifactManifest": ReleaseArtifactManifest,
        "ProductOrder": ProductOrder,
        "ProductionReadinessProfile": ProductionReadinessProfile,
        "ProcessGrammarRecord": ProcessGrammarRecord,
        "ProtocolObject": ProtocolObject,
        "ProtocolFunctorCertificate": ProtocolFunctorCertificate,
        "ProtocolFrameDigest": ProtocolFrameDigest,
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
        "RouteExecutionRequest": RouteExecutionRequest,
        "RouteExecutionBatch": RouteExecutionBatch,
        "ResourceEnvelope": ResourceEnvelope,
        "ResourceMatchedBaselineConfig": ResourceMatchedBaselineConfig,
        "RuntimeActionResult": RuntimeActionResult,
        "RuntimeComparisonReport": RuntimeComparisonReport,
        "RuntimeEvent": RuntimeEvent,
        "RuntimeEventLog": RuntimeEventLog,
        "RuntimeExecutionReport": RuntimeExecutionReport,
        "RuntimeExecutorPolicy": RuntimeExecutorPolicy,
        "RuntimeHealthReport": RuntimeHealthReport,
        "RuntimeIdentityContext": RuntimeIdentityContext,
        "RuntimeRunReport": RuntimeRunReport,
        "RuntimeServiceSettings": RuntimeServiceSettings,
        "RuntimeState": RuntimeState,
        "RuntimeStoreRecord": RuntimeStoreRecord,
        "RuntimeStoreSnapshot": RuntimeStoreSnapshot,
        "RuntimeStepInput": RuntimeStepInput,
        "RuntimeStepReport": RuntimeStepReport,
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
        "SybilResistanceLedger": SybilResistanceLedger,
        "SybilResistancePolicy": SybilResistancePolicy,
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
        "VerifiedCapabilityPacket": VerifiedCapabilityPacket,
        "VerificationThroughputReport": VerificationThroughputReport,
        "CanonicalManifest": CanonicalManifest,
        "CanonicalManifestRecord": CanonicalManifestRecord,
    }


def schema_by_type(type_name: str = "Registry") -> dict[str, Any]:
    """Return a stable public JSON Schema by type name."""

    schemas = schema_model_map()
    try:
        return _schema_for_type(type_name, schemas[type_name])
    except KeyError as exc:
        available = ", ".join(sorted(schemas))
        raise ValueError(f"unknown schema type {type_name!r}; available: {available}") from exc


def schema_bundle() -> PortabilitySchemaBundle:
    return PortabilitySchemaBundle(
        schemas={name: _schema_for_type(name, model) for name, model in schema_model_map().items()}
    )


def _schema_for_type(name: str, model: type[Any]) -> dict[str, Any]:
    if issubclass(model, BaseModel):
        return model.model_json_schema()
    if issubclass(model, StrEnum):
        return {
            "enum": [item.value for item in model],
            "title": name,
            "type": "string",
        }
    raise TypeError(f"unsupported schema type for {name}: {model!r}")


def validate_data(data: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    validator = Draft202012Validator(schema or registry_json_schema())
    return [error.message for error in sorted(validator.iter_errors(data), key=str)]
