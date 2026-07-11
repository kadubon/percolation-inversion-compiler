"""JSON Schema and data validation helpers."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel
from yaml.events import AliasEvent

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
from percolation_inversion_compiler.adoption.records import (
    AdoptionFirstRunCommand,
    AdoptionReviewChecklist,
    AdoptionSafetyBoundary,
    AgentToOperatorRequest,
    OperatorAdoptionPacket,
)
from percolation_inversion_compiler.afst.records import (
    AFSTFluxStabilizationReport,
    AFSTProfilePolicy,
    AuthorityEnvelope,
    BoundedFrictionHandover,
    BufferComponent,
    CandidateFlux,
    CertifiedAbundanceCoordinate,
    ConsentChannel,
    NonMarketLiquidityCertificate,
    RawInputAudit,
    RefusalChannel,
    ResourceBalanceWitness,
    SatisfactionCoordinate,
    SatisfactionDeficit,
    SatisfactionEffectWitness,
    SatisfactionFluxRecord,
    ShockEnvelope,
    StabilizationBuffer,
    UnitFrame,
)
from percolation_inversion_compiler.agent.records import (
    AgentAutonomyAuditReport,
    AgentCheckReport,
    AgentCommandInvocation,
    AgentCommunicationGuide,
    AgentCommunicationPolicy,
    AgentCommunicationStep,
    AgentFeatureReadinessReport,
    AgentIntakeReport,
    AgentIntakeRequest,
    AgentNetworkReadinessReport,
    AgentNextActionReport,
    AgentRunbookReport,
    AgentWorkflowGuide,
    AgentWorkflowStep,
)
from percolation_inversion_compiler.alt.records import (
    AbstractionToken,
    ALTAccelerationCertificate,
    ALTAdmissionDecision,
    ALTCARACertificate,
    ALTDeprecationRecord,
    AltEcptLiftReport,
    ALTKernelTransitionReport,
    AltLiftBlocker,
    ALTResurrectionRecord,
    BaselineRefreshCertificate,
    CapitalToPathContribution,
    CertifiedAbstractionCapital,
    CrossContextTransferWitness,
    DownstreamSearchCostDelta,
    ExecutableALTCertificatePacket,
    FormationCostLedger,
    FoundryControlDashboard,
    FoundryState,
    HazardEnvelopeCertificate,
    LifecycleCostBounds,
    LiquidityCertificate,
    LiquidityToClosureContribution,
    MissionValidityCertificate,
    NegativeLiquidityCertificate,
    ObservedTraceProjection,
    OpportunityMeasureContract,
    ProblemSolvingTrace,
    ReceiverLiquidityLift,
    ReproductionMatrixCertificate,
    RootFinalityCertificate,
    TelemetryCostCertificate,
    TokenLineage,
    TraceSufficiencyCertificate,
    TransportCertificate,
    ValueBridgeReport,
)
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
from percolation_inversion_compiler.bit_engine.records import (
    ActivationGainEstimate,
    BottleneckClassDiagnosis,
    BottleneckInversionCandidate,
    BottleneckInversionReport,
    CapabilityExpressionPath,
    InterventionWitness,
    InversionCertificate,
    MinimalEnablingCondition,
    PostInversionAuditPlan,
    RollbackOrDeactivationPlan,
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
    CanonicalImplementationReadinessReport,
    CanonicalTheorySnapshotSummary,
    CheckerContext,
    ObligationRule,
    ObligationTrace,
    ProjectionAudit,
    TheoryAuditReport,
    TheoryAuditSuiteReport,
    TheoryFidelityReport,
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
    CommercialReadinessSummary,
    OperationalCheck,
    OperationalReadinessReport,
    PortabilityConformanceReport,
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
    AgentInboxRecord,
    AgentMessageContractReport,
    AgentMessageDeliveryReport,
    AgentMessageEnvelope,
    AgentMessageNonceLedger,
    AgentMessageVerificationContext,
    AgentPacketExchangeReport,
    AgentPeerRecord,
    AgentRelayReadinessReport,
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
    ExternalCandidateClassification,
    GeneralIntakePolicy,
    GeneralIntakePolicyDecision,
    GeneralIntakeProfile,
    GeneralIntakeReport,
    GeneralIntakeRuntimeBridgeReport,
    GeneralIntakeSource,
    HiddenCapabilityInjectionReport,
    IntakeProvenanceRecord,
    PacketCapitalLineage,
    PacketIngestionReport,
    PacketPromotionPolicy,
    PacketPromotionReport,
    PacketRejection,
    ProtocolFrameDigest,
    PsiDashboard,
    RobotsDecision,
    VerificationThroughputReport,
    VerifiedCapabilityPacket,
    WebDiscoveryReport,
    WebFetchPolicy,
    WebFetchReport,
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
from percolation_inversion_compiler.operation.records import (
    OperationAdapterManifest,
    OperationApproval,
    OperationDispatchReceipt,
    OperationPlan,
    OperationPreflightReport,
    OperationReplayLedger,
    OperationTrustPolicy,
    OperationVerificationReport,
    OperationVerifierReport,
)
from percolation_inversion_compiler.packet_exchange.records import (
    PacketExchangeEnvelope,
    PacketImportInspectionReport,
    PacketLineageDigest,
    PacketMergeReport,
    ResidualCarryForwardReport,
)
from percolation_inversion_compiler.phase_lab.records import (
    ActionBoundaryRequirement,
    ASIProxyThresholdSpec,
    ASIProxyThresholdStatus,
    AutocatalyticClosureReport,
    BasinReachabilityProxy,
    ClosureAbstentionReason,
    ClosureCertificateCandidate,
    ClosureDefect,
    ClosureSupportHyperpath,
    CollectivePhaseAbstentionReport,
    CollectivePhaseCertificateCandidate,
    EffectiveGraphResidualSummary,
    EffectivePacketEdge,
    EffectivePacketEligibility,
    EffectivePacketGraph,
    EffectivePacketGraphBuildReport,
    EffectivePacketNode,
    ExecutableClosureWitness,
    ExecutablePathDensityReport,
    ExecutionAuthorityStatus,
    ExecutionAvailableHyperpath,
    ExecutionPathDefect,
    ExecutionPathWitness,
    FalseLiquidityLoad,
    PacketContributionStatus,
    PhaseCertificateDefect,
    PhaseComponentObservation,
    PhaseLabEvent,
    PhaseLabExportManifest,
    PhaseLabIngestReport,
    PhaseLabStoreManifest,
    PhaseLabWindowIndex,
    PhaseMetricObservation,
    PhaseThresholdStatus,
    PhaseWindow,
    PhaseWindowComparison,
    PhaseWindowObservation,
    ProductiveClosureWitness,
    ReceiverContextSupport,
    SalienceObstructionLoad,
    SemanticEdgeEvidence,
    VerificationThroughputWindow,
    WasteLoad,
)
from percolation_inversion_compiler.phase_lab.records import (
    AutocatalyticClosureWitness as PhaseLabAutocatalyticClosureWitness,
)
from percolation_inversion_compiler.runtime.records import (
    AccelerationCertificate,
    AccelerationExperimentSuite,
    AccelerationMeasurementMetrics,
    AccelerationMetricComparison,
    ActionCommit,
    AgentPolicyIdentity,
    AgentPopulationState,
    AgentRuntimeConfig,
    AgentTask,
    BottleneckWitnessReport,
    CollectivePhaseCertificate,
    ContentAddressedEvidenceRef,
    EvidenceEnvelopeStoreRecord,
    EvidenceResolutionBatch,
    FixedPopulationLedger,
    FrontierDebtReport,
    PhaseAccelerationScore,
    PhaseControlAuditSummary,
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
from percolation_inversion_compiler.sqot_controller.records import (
    AttentionBudgetLedger,
    DiagnosticReserveReport,
    PacketQuarantineDecision,
    QueueItemCost,
    QueueOccupationReport,
    QueueRebalancePlan,
    ReversibleSalienceSovereigntyCertificate,
    SalienceObstructionDiagnosis,
    VerificationQueuePressure,
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
    TraceAdapterReport,
    TraceFrontierDebt,
    TraceNormalForm,
    TraceNormalizationCertificate,
    TraceToleranceLedger,
    TRCCompileResult,
    TRCStateRecord,
    TypedActionBoundary,
    TypedAgentTrace,
    TypedToolCallTrace,
    TypedTraceTransducerRecord,
)


class PortabilitySchemaBundle(BaseModel):
    """Named JSON Schema bundle for other implementations and agents."""

    bundle_id: str = "percolation-inversion-compiler-portability"
    schemas: dict[str, dict[str, Any]]


MAX_PUBLIC_INPUT_BYTES = 4_000_000
MAX_PUBLIC_INPUT_DEPTH = 64
MAX_PUBLIC_INPUT_ITEMS = 50_000
MAX_PUBLIC_JSONL_LINES = 50_000


def read_bounded_bytes(
    path: str | Path,
    *,
    max_bytes: int = MAX_PUBLIC_INPUT_BYTES,
) -> bytes:
    source = Path(path)
    size = source.stat().st_size
    if size > max_bytes:
        raise ValueError(f"input exceeds byte limit ({size} > {max_bytes})")
    data = source.read_bytes()
    if len(data) > max_bytes:
        raise ValueError(f"input exceeds byte limit ({len(data)} > {max_bytes})")
    return data


def read_bounded_text(
    path: str | Path,
    *,
    max_bytes: int = MAX_PUBLIC_INPUT_BYTES,
) -> str:
    return read_bounded_bytes(path, max_bytes=max_bytes).decode("utf-8")


class _NoAliasSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases before expansion."""

    max_depth = MAX_PUBLIC_INPUT_DEPTH
    max_items = MAX_PUBLIC_INPUT_ITEMS

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._compose_depth = 0
        self._compose_items = 0

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):  # type: ignore[no-untyped-call]
            raise ValueError("YAML aliases are not allowed in public inputs")
        self._compose_depth += 1
        self._compose_items += 1
        if self._compose_depth > self.max_depth + 1:
            raise ValueError(f"input exceeds nesting depth limit ({self.max_depth})")
        if self._compose_items > self.max_items:
            raise ValueError(f"input exceeds item limit ({self.max_items})")
        try:
            return super().compose_node(parent, index)
        finally:
            self._compose_depth -= 1


def _construct_bounded_yaml_int(loader: _NoAliasSafeLoader, node: Any) -> int:
    value = yaml.SafeLoader.construct_yaml_int(loader, node)
    if value == 0 and str(node.value).strip().startswith("-"):
        raise ValueError("negative zero is not allowed in public inputs")
    return value


def _construct_bounded_yaml_float(loader: _NoAliasSafeLoader, node: Any) -> float:
    value = yaml.SafeLoader.construct_yaml_float(loader, node)
    if value == 0.0 and str(node.value).strip().startswith("-"):
        raise ValueError("negative zero is not allowed in public inputs")
    return value


_NoAliasSafeLoader.add_constructor(
    "tag:yaml.org,2002:int",
    _construct_bounded_yaml_int,
)
_NoAliasSafeLoader.add_constructor(
    "tag:yaml.org,2002:float",
    _construct_bounded_yaml_float,
)


def load_data(
    path: str | Path,
    *,
    max_bytes: int = MAX_PUBLIC_INPUT_BYTES,
    max_depth: int = MAX_PUBLIC_INPUT_DEPTH,
    max_items: int = MAX_PUBLIC_INPUT_ITEMS,
) -> dict[str, Any]:
    """Load one bounded I-JSON-compatible object from JSON or YAML."""

    source = Path(path)
    text = read_bounded_text(source, max_bytes=max_bytes)
    # This loader subclasses SafeLoader and additionally rejects aliases.
    if source.suffix.lower() in {".yaml", ".yml"}:
        loader = _NoAliasSafeLoader(text)
        loader.max_depth = max_depth
        loader.max_items = max_items
        try:
            data = loader.get_single_data()
        finally:
            loader.dispose()  # type: ignore[no-untyped-call]
    else:
        _precheck_json_structure(text, max_depth=max_depth)
        data = json.loads(text, parse_constant=_reject_json_constant)
    if not isinstance(data, dict):
        raise ValueError("top-level registry data must be an object")
    _validate_public_value(data, max_depth=max_depth, max_items=max_items)
    return data


def load_jsonl_records(
    path: str | Path,
    *,
    max_bytes: int = MAX_PUBLIC_INPUT_BYTES,
    max_lines: int = MAX_PUBLIC_JSONL_LINES,
    max_depth: int = MAX_PUBLIC_INPUT_DEPTH,
    max_items: int = MAX_PUBLIC_INPUT_ITEMS,
) -> list[dict[str, Any]]:
    """Load bounded JSONL object records without scalar coercion."""

    source = Path(path)
    size = source.stat().st_size
    if size > max_bytes:
        raise ValueError(f"input exceeds byte limit ({size} > {max_bytes})")
    records: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line_number > max_lines:
                raise ValueError(f"JSONL exceeds line limit ({max_lines})")
            stripped = line.strip()
            if not stripped:
                continue
            _precheck_json_structure(stripped, max_depth=max_depth)
            item = json.loads(stripped, parse_constant=_reject_json_constant)
            if not isinstance(item, dict):
                raise ValueError(f"JSONL line {line_number} must be an object")
            _validate_public_value(item, max_depth=max_depth, max_items=max_items)
            records.append(item)
    return records


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _precheck_json_structure(text: str, *, max_depth: int) -> None:
    """Reject excessive JSON nesting before the recursive parser allocates it."""

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > max_depth + 1:
                raise ValueError(f"input exceeds nesting depth limit ({max_depth})")
        elif character in "]}":
            depth -= 1


def _validate_public_value(value: Any, *, max_depth: int, max_items: int) -> None:
    count = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(f"input exceeds nesting depth limit ({max_depth})")
        count += 1
        if count > max_items:
            raise ValueError(f"input exceeds item limit ({max_items})")
        if isinstance(current, dict):
            if any(not isinstance(key, str) for key in current):
                raise ValueError("public input object keys must be strings")
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, float):
            if not math.isfinite(current):
                raise ValueError("non-finite JSON numbers are not allowed")
            if current == 0.0 and math.copysign(1.0, current) < 0.0:
                raise ValueError("negative zero is not allowed in public inputs")
        elif current is not None and not isinstance(current, str | int | bool):
            raise ValueError(f"unsupported public input type: {type(current).__name__}")


def registry_json_schema() -> dict[str, Any]:
    return Registry.model_json_schema()


def schema_model_map() -> dict[str, type[Any]]:
    """Return stable public schema model names."""

    return {
        "AcceptedPacketPath": AcceptedPacketPath,
        "ActionBoundaryRequirement": ActionBoundaryRequirement,
        "ActionCommit": ActionCommit,
        "AccelerationCertificate": AccelerationCertificate,
        "AccelerationMetricComparison": AccelerationMetricComparison,
        "AccelerationMeasurementMetrics": AccelerationMeasurementMetrics,
        "AccelerationExperimentSuite": AccelerationExperimentSuite,
        "AFSTFluxStabilizationReport": AFSTFluxStabilizationReport,
        "AFSTProfilePolicy": AFSTProfilePolicy,
        "AFSTRawInputAudit": RawInputAudit,
        "AFSTUnitFrame": UnitFrame,
        "AFSTSatisfactionCoordinate": SatisfactionCoordinate,
        "AFSTSatisfactionDeficit": SatisfactionDeficit,
        "AFSTCertifiedAbundanceCoordinate": CertifiedAbundanceCoordinate,
        "AFSTCandidateFlux": CandidateFlux,
        "AFSTAuthorityEnvelope": AuthorityEnvelope,
        "AFSTConsentChannel": ConsentChannel,
        "AFSTRefusalChannel": RefusalChannel,
        "AFSTResourceBalanceWitness": ResourceBalanceWitness,
        "AFSTBufferComponent": BufferComponent,
        "AFSTShockEnvelope": ShockEnvelope,
        "AFSTStabilizationBuffer": StabilizationBuffer,
        "AFSTBoundedFrictionHandover": BoundedFrictionHandover,
        "AFSTSatisfactionEffectWitness": SatisfactionEffectWitness,
        "AFSTNonMarketLiquidityCertificate": NonMarketLiquidityCertificate,
        "AFSTSatisfactionFluxRecord": SatisfactionFluxRecord,
        "ALTAccelerationCertificate": ALTAccelerationCertificate,
        "ALTCARACertificate": ALTCARACertificate,
        "ALTAdmissionDecision": ALTAdmissionDecision,
        "ALTDeprecationRecord": ALTDeprecationRecord,
        "AltEcptLiftReport": AltEcptLiftReport,
        "AltLiftBlocker": AltLiftBlocker,
        "ALTKernelTransitionReport": ALTKernelTransitionReport,
        "ALTResurrectionRecord": ALTResurrectionRecord,
        "AbstractionToken": AbstractionToken,
        "ActivationGainEstimate": ActivationGainEstimate,
        "AdoptionFirstRunCommand": AdoptionFirstRunCommand,
        "AdoptionReviewChecklist": AdoptionReviewChecklist,
        "AdoptionSafetyBoundary": AdoptionSafetyBoundary,
        "AgentAutonomyAuditReport": AgentAutonomyAuditReport,
        "AgentCheckReport": AgentCheckReport,
        "AgentCommandInvocation": AgentCommandInvocation,
        "AgentCommunicationGuide": AgentCommunicationGuide,
        "AgentCommunicationPolicy": AgentCommunicationPolicy,
        "AgentCommunicationStep": AgentCommunicationStep,
        "AgentInboxRecord": AgentInboxRecord,
        "AgentConnectorSpec": AgentConnectorSpec,
        "AgentFeatureReadinessReport": AgentFeatureReadinessReport,
        "AgentIdentityAttestation": AgentIdentityAttestation,
        "AgentIdentityCheckReport": AgentIdentityCheckReport,
        "AgentIntakeReport": AgentIntakeReport,
        "AgentIntakeRequest": AgentIntakeRequest,
        "AgentMessageEnvelope": AgentMessageEnvelope,
        "AgentMessageContractReport": AgentMessageContractReport,
        "AgentMessageDeliveryReport": AgentMessageDeliveryReport,
        "AgentMessageNonceLedger": AgentMessageNonceLedger,
        "AgentMessageVerificationContext": AgentMessageVerificationContext,
        "AgentNetworkReadinessReport": AgentNetworkReadinessReport,
        "AgentNextActionReport": AgentNextActionReport,
        "AgentToOperatorRequest": AgentToOperatorRequest,
        "AgentPacketExchangeReport": AgentPacketExchangeReport,
        "AgentPeerRecord": AgentPeerRecord,
        "AgentRelayReadinessReport": AgentRelayReadinessReport,
        "AgentPolicyIdentity": AgentPolicyIdentity,
        "AgentPopulationState": AgentPopulationState,
        "AgentRuntimeConfig": AgentRuntimeConfig,
        "AgentRunbookReport": AgentRunbookReport,
        "AgentTask": AgentTask,
        "AgentWorkflowGuide": AgentWorkflowGuide,
        "AgentWorkflowStep": AgentWorkflowStep,
        "AdapterRouteSpec": AdapterRouteSpec,
        "AlgebraLawCertificate": AlgebraLawCertificate,
        "ActionGrammar": ActionGrammar,
        "ActionabilityVector": ActionabilityVector,
        "ActivationThresholdCertificate": ActivationThresholdCertificate,
        "ASIProxyThresholdSpec": ASIProxyThresholdSpec,
        "ASIProxyThresholdStatus": ASIProxyThresholdStatus,
        "ASIProxyTargetContract": ASIProxyTargetContract,
        "AttentionBudgetLedger": AttentionBudgetLedger,
        "AttestationRecord": AttestationRecord,
        "AutocatalyticClosureReport": AutocatalyticClosureReport,
        "AutocatalyticClosureWitness": PhaseLabAutocatalyticClosureWitness,
        "BaselineRefreshCertificate": BaselineRefreshCertificate,
        "BasinReachabilityProxy": BasinReachabilityProxy,
        "BasinReachabilityReport": BasinReachabilityReport,
        "BottleneckClassDiagnosis": BottleneckClassDiagnosis,
        "BottleneckInversionCandidate": BottleneckInversionCandidate,
        "BottleneckInversionReport": BottleneckInversionReport,
        "BottleneckIntervention": BottleneckIntervention,
        "BottleneckInversionPlan": BottleneckInversionPlan,
        "BottleneckCandidate": BottleneckCandidate,
        "BottleneckWitnessReport": BottleneckWitnessReport,
        "BoundaryGeneratorRecord": BoundaryGeneratorRecord,
        "BoundaryScriptRecord": BoundaryScriptRecord,
        "BudgetedToleranceScheduler": BudgetedToleranceScheduler,
        "CalibrationCertificate": CalibrationCertificate,
        "CanonicalImplementationReadinessReport": CanonicalImplementationReadinessReport,
        "CanonicalTheorySnapshotSummary": CanonicalTheorySnapshotSummary,
        "CapabilityExpressionPath": CapabilityExpressionPath,
        "CapabilityBasinContract": CapabilityBasinContract,
        "CapabilityPacketCandidate": CapabilityPacketCandidate,
        "CapabilityPacketRegistry": CapabilityPacketRegistry,
        "CapabilityStateVector": CapabilityStateVector,
        "CapitalToPathContribution": CapitalToPathContribution,
        "CascadeResidualPotential": CascadeResidualPotential,
        "CertificateCompilerRecord": CertificateCompilerRecord,
        "CertificateFamily": CertificateFamily,
        "CertificateRoute": CertificateRoute,
        "CertifiedAbstractionCapital": CertifiedAbstractionCapital,
        "CheckResult": CheckResult,
        "CheckerContext": CheckerContext,
        "ClosureAbstentionReason": ClosureAbstentionReason,
        "ClosureCertificateCandidate": ClosureCertificateCandidate,
        "ClosureDefect": ClosureDefect,
        "ClosureSupportHyperpath": ClosureSupportHyperpath,
        "ClosedLoopAgentIteration": ClosedLoopAgentIteration,
        "CollectivePhaseAbstentionReport": CollectivePhaseAbstentionReport,
        "CollectivePhaseCertificate": CollectivePhaseCertificate,
        "CollectivePhaseCertificateCandidate": CollectivePhaseCertificateCandidate,
        "ConfidenceLedger": ConfidenceLedger,
        "CommercialReadinessSummary": CommercialReadinessSummary,
        "ControlledTransition": ControlledTransition,
        "CrossContextTransferWitness": CrossContextTransferWitness,
        "CryptographicAgentIdentity": CryptographicAgentIdentity,
        "IdentityContributionStatus": IdentityContributionStatus,
        "IdentityTrustProfile": IdentityTrustProfile,
        "DKWCertificate": DKWCertificate,
        "DiagnosticReservePolicy": DiagnosticReservePolicy,
        "DiagnosticReserveReport": DiagnosticReserveReport,
        "DischargeRouteBinding": DischargeRouteBinding,
        "DownstreamSearchCostDelta": DownstreamSearchCostDelta,
        "DomainTypedSemiring": DomainTypedSemiring,
        "DominanceWitness": DominanceWitness,
        "EProcessCertificate": EProcessCertificate,
        "EcologyAutocatalyticClosureWitness": AutocatalyticClosureWitness,
        "EdgeWitness": EdgeWitness,
        "EdgeWitnessCertificate": EdgeWitnessCertificate,
        "EdgeRelationVerificationReport": EdgeRelationVerificationReport,
        "EdgeRelationVerifierSpec": EdgeRelationVerifierSpec,
        "EffectiveGraphResidualSummary": EffectiveGraphResidualSummary,
        "EffectivePacketEdge": EffectivePacketEdge,
        "EffectivePacketEligibility": EffectivePacketEligibility,
        "EffectivePacketGraph": EffectivePacketGraph,
        "EffectivePacketGraphBuildReport": EffectivePacketGraphBuildReport,
        "EffectivePacketNode": EffectivePacketNode,
        "ExecutableClosureWitness": ExecutableClosureWitness,
        "ExecutionAvailablePathCertificate": ExecutionAvailablePathCertificate,
        "ExecutionAvailableHyperpath": ExecutionAvailableHyperpath,
        "ExecutionAuthorityStatus": ExecutionAuthorityStatus,
        "ExecutionPathDefect": ExecutionPathDefect,
        "ExecutionPathWitness": ExecutionPathWitness,
        "ExecutablePathDensityReport": ExecutablePathDensityReport,
        "ExternalCandidateClassification": ExternalCandidateClassification,
        "ContentAddressedEvidenceRef": ContentAddressedEvidenceRef,
        "EvidenceEnvelopeStoreRecord": EvidenceEnvelopeStoreRecord,
        "EvidenceResolutionBatch": EvidenceResolutionBatch,
        "EvidenceArtifact": EvidenceArtifact,
        "EvidencePolicy": EvidencePolicy,
        "EvidenceVerificationProfile": EvidenceVerificationProfileRecord,
        "ExecutableALTCertificatePacket": ExecutableALTCertificatePacket,
        "ExecutableTraceNormalForm": ExecutableTraceNormalForm,
        "ExternalObligationCatalog": ExternalObligationCatalog,
        "ExternalVerifierHook": ExternalVerifierHook,
        "FixedPopulationLedger": FixedPopulationLedger,
        "FinitePhaseControlCertificate": FinitePhaseControlCertificate,
        "FiniteOrder": FiniteOrder,
        "FiniteTraceLaw": FiniteTraceLaw,
        "FalseLiquidityLoad": FalseLiquidityLoad,
        "FusedGeometricComparisonCertificate": FusedGeometricComparisonCertificate,
        "FutureFreedomVector": FutureFreedomVector,
        "FunctorLawCertificate": FunctorLawCertificate,
        "FormationCostLedger": FormationCostLedger,
        "FrontierDebtReport": FrontierDebtReport,
        "FoundryControlDashboard": FoundryControlDashboard,
        "FoundryState": FoundryState,
        "GeneralIntakeProfile": GeneralIntakeProfile,
        "GeneralIntakePolicy": GeneralIntakePolicy,
        "GeneralIntakePolicyDecision": GeneralIntakePolicyDecision,
        "GeneralIntakeReport": GeneralIntakeReport,
        "GeneralIntakeRuntimeBridgeReport": GeneralIntakeRuntimeBridgeReport,
        "GeneralIntakeSource": GeneralIntakeSource,
        "GoodTuringCertificate": GoodTuringCertificate,
        "HiddenCapabilityInjectionReport": HiddenCapabilityInjectionReport,
        "HazardEnvelopeCertificate": HazardEnvelopeCertificate,
        "IndependenceCertificate": IndependenceCertificate,
        "ImplementationMaturity": ImplementationMaturityRecord,
        "InnerViabilityKernel": InnerViabilityKernel,
        "InterventionCandidate": InterventionCandidate,
        "IntakeProvenanceRecord": IntakeProvenanceRecord,
        "InversionCertificate": InversionCertificate,
        "InterventionWitness": InterventionWitness,
        "Judgment": Judgment,
        "LatticeWitness": LatticeWitness,
        "LedgerCoordinate": LedgerCoordinate,
        "LifecycleCostBounds": LifecycleCostBounds,
        "LiquidityCertificate": LiquidityCertificate,
        "LiquidityToClosureContribution": LiquidityToClosureContribution,
        "MartingaleDeficiencyCertificate": MartingaleDeficiencyCertificate,
        "MartingaleBlockResidual": MartingaleBlockResidual,
        "MechanismCubeCertificate": MechanismCubeCertificate,
        "MinimalEnablingCondition": MinimalEnablingCondition,
        "MonoidRecord": MonoidRecord,
        "MonotoneMap": MonotoneMap,
        "MissionValidityCertificate": MissionValidityCertificate,
        "NegativeLiquidityCertificate": NegativeLiquidityCertificate,
        "NonPromotionPolicy": NonPromotionPolicy,
        "ObligationRule": ObligationRule,
        "ObligationSet": ObligationSet,
        "ObligationTrace": ObligationTrace,
        "ObservationWindow": ObservationWindow,
        "ObservedTraceProjection": ObservedTraceProjection,
        "OccupationLedger": OccupationLedger,
        "OpportunityMeasureContract": OpportunityMeasureContract,
        "OperationalCheck": OperationalCheck,
        "OperationalReadinessReport": OperationalReadinessReport,
        "OperationAdapterManifest": OperationAdapterManifest,
        "OperationApproval": OperationApproval,
        "OperationDispatchReceipt": OperationDispatchReceipt,
        "OperationPlan": OperationPlan,
        "OperationPreflightReport": OperationPreflightReport,
        "OperationReplayLedger": OperationReplayLedger,
        "OperationTrustPolicy": OperationTrustPolicy,
        "OperationVerificationReport": OperationVerificationReport,
        "OperationVerifierReport": OperationVerifierReport,
        "OperatorAdoptionPacket": OperatorAdoptionPacket,
        "OrderedPotentialCone": OrderedPotentialCone,
        "PacketQuarantineDecision": PacketQuarantineDecision,
        "PacketContributionStatus": PacketContributionStatus,
        "PhaseAccelerationBenchmarkReport": PhaseAccelerationBenchmarkReport,
        "PhaseAccelerationPlan": PhaseAccelerationPlan,
        "PhaseAccelerationRequest": PhaseAccelerationRequest,
        "PhaseAccelerationScore": PhaseAccelerationScore,
        "PhaseBenchmarkCaseResult": PhaseBenchmarkCaseResult,
        "PhaseBenchmarkSuiteReport": PhaseBenchmarkSuiteReport,
        "PhaseBenchmarkTask": PhaseBenchmarkTask,
        "PhaseCertificateDefect": PhaseCertificateDefect,
        "PhaseComponentObservation": PhaseComponentObservation,
        "PhaseComponentGap": PhaseComponentGap,
        "PhaseDashboardReport": PhaseDashboardReport,
        "PhaseControlAuditSummary": PhaseControlAuditSummary,
        "PhaseControlAction": PhaseControlAction,
        "PhaseControlEnvelope": PhaseControlEnvelope,
        "PhaseControlObjective": PhaseControlObjective,
        "PhaseControlPlan": PhaseControlPlan,
        "PhaseControlRunReport": PhaseControlRunReport,
        "PhaseControlState": PhaseControlState,
        "PhaseGapVector": PhaseGapVector,
        "PhaseLabEvent": PhaseLabEvent,
        "PhaseLabExportManifest": PhaseLabExportManifest,
        "PhaseLabIngestReport": PhaseLabIngestReport,
        "PhaseLabStoreManifest": PhaseLabStoreManifest,
        "PhaseLabWindowIndex": PhaseLabWindowIndex,
        "PhaseObservationReport": PhaseObservationReport,
        "PhaseThresholdStatus": PhaseThresholdStatus,
        "PhaseTrajectoryReport": PhaseTrajectoryReport,
        "PhaseWindow": PhaseWindow,
        "PhaseWindowComparison": PhaseWindowComparison,
        "PhaseWindowObservation": PhaseWindowObservation,
        "PhaseMetricObservation": PhaseMetricObservation,
        "ProtocolRelativeBenchmarkMetric": ProtocolRelativeBenchmarkMetric,
        "PacketExchangeEnvelope": PacketExchangeEnvelope,
        "PacketIngestionReport": PacketIngestionReport,
        "PacketImportInspectionReport": PacketImportInspectionReport,
        "PacketLineageDigest": PacketLineageDigest,
        "PacketCapitalLineage": PacketCapitalLineage,
        "PacketMergeReport": PacketMergeReport,
        "PacketPromotionPolicy": PacketPromotionPolicy,
        "PacketPromotionReport": PacketPromotionReport,
        "PacketRejection": PacketRejection,
        "PortabilitySchemaBundle": PortabilitySchemaBundle,
        "PortabilityConformanceReport": PortabilityConformanceReport,
        "PopulationRuntimeStepReport": PopulationRuntimeStepReport,
        "ProvenanceManifest": ProvenanceManifest,
        "ProvenanceManifestEntry": ProvenanceManifestEntry,
        "ReleaseArtifactManifest": ReleaseArtifactManifest,
        "ProductOrder": ProductOrder,
        "ProductionReadinessProfile": ProductionReadinessProfile,
        "PostInversionAuditPlan": PostInversionAuditPlan,
        "ProductiveClosureWitness": ProductiveClosureWitness,
        "ProcessGrammarRecord": ProcessGrammarRecord,
        "ProtocolObject": ProtocolObject,
        "ProtocolFunctorCertificate": ProtocolFunctorCertificate,
        "ProtocolFrameDigest": ProtocolFrameDigest,
        "ProblemSolvingTrace": ProblemSolvingTrace,
        "ProjectionAudit": ProjectionAudit,
        "ProofObligation": ExternalProofObligation,
        "PsiDashboard": PsiDashboard,
        "PullbackGluingWitness": PullbackGluingWitness,
        "QuarantineLedger": QuarantineLedger,
        "QueueOccupationReport": QueueOccupationReport,
        "QueueItemCost": QueueItemCost,
        "QueueRebalancePlan": QueueRebalancePlan,
        "ReachableMassRecursionCertificate": ReachableMassRecursionCertificate,
        "ReconstructionResidual": ReconstructionResidual,
        "ReproductionMatrixCertificate": ReproductionMatrixCertificate,
        "RefreshRule": RefreshRule,
        "Registry": Registry,
        "ResourceCalendarRecord": ResourceCalendarRecord,
        "ResidualCarryForwardReport": ResidualCarryForwardReport,
        "RiskBudgetLedger": RiskBudgetLedger,
        "RootFinalityCertificate": RootFinalityCertificate,
        "RouteExecutionRequest": RouteExecutionRequest,
        "RouteExecutionBatch": RouteExecutionBatch,
        "ResourceEnvelope": ResourceEnvelope,
        "ResourceMatchedBaselineConfig": ResourceMatchedBaselineConfig,
        "ReceiverLiquidityLift": ReceiverLiquidityLift,
        "ReceiverContextSupport": ReceiverContextSupport,
        "ReversibleSalienceSovereigntyCertificate": ReversibleSalienceSovereigntyCertificate,
        "RobotsDecision": RobotsDecision,
        "RollbackOrDeactivationPlan": RollbackOrDeactivationPlan,
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
        "SafePhaseAction": SafePhaseAction,
        "SQOTTheorySnapshot": SQOTTheorySnapshot,
        "ScriptGroundMetricCertificate": ScriptGroundMetricCertificate,
        "SchemaBundleDigest": SchemaBundleDigest,
        "SelectiveCUPCertificate": SelectiveCUPCertificate,
        "SemanticEdgeEvidence": SemanticEdgeEvidence,
        "SettlementReturnRAFCertificate": SettlementReturnRAFCertificate,
        "SinkhornCertificate": SinkhornCertificate,
        "SBOMManifest": SBOMManifest,
        "SalienceQueueRecord": SalienceQueueRecord,
        "SalienceObstructionLoad": SalienceObstructionLoad,
        "SalienceObstructionDiagnosis": SalienceObstructionDiagnosis,
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
        "TheoryAuditSuiteReport": TheoryAuditSuiteReport,
        "TheoryFidelityReport": TheoryFidelityReport,
        "TheoryImplementationRecord": TheoryImplementationRecord,
        "TheorySnapshot": TheorySnapshot,
        "TheorySnapshotItem": TheorySnapshotItem,
        "TexGrammarDiagnostic": TexGrammarDiagnostic,
        "TelemetryCostCertificate": TelemetryCostCertificate,
        "TokenLineage": TokenLineage,
        "TraceAdapterReport": TraceAdapterReport,
        "TraceFrontierDebt": TraceFrontierDebt,
        "TraceNormalForm": TraceNormalForm,
        "TraceSufficiencyCertificate": TraceSufficiencyCertificate,
        "TraceNormalizationCertificate": TraceNormalizationCertificate,
        "TraceToleranceLedger": TraceToleranceLedger,
        "TransportCertificate": TransportCertificate,
        "TypedActionBoundary": TypedActionBoundary,
        "TypedAgentTrace": TypedAgentTrace,
        "TypedToolCallTrace": TypedToolCallTrace,
        "TypedTraceTransducerRecord": TypedTraceTransducerRecord,
        "ValueBridgeReport": ValueBridgeReport,
        "VectorCompatibleFamily": VectorCompatibleFamily,
        "SnapshotAttribution": SnapshotAttribution,
        "SnapshotCatalog": SnapshotCatalog,
        "VerifierEvidenceEnvelope": VerifierEvidenceEnvelope,
        "VerifierResolution": VerifierResolution,
        "VerifiedCapabilityPacket": VerifiedCapabilityPacket,
        "VerificationThroughputWindow": VerificationThroughputWindow,
        "VerificationThroughputReport": VerificationThroughputReport,
        "VerificationQueuePressure": VerificationQueuePressure,
        "WasteLoad": WasteLoad,
        "WebDiscoveryReport": WebDiscoveryReport,
        "WebFetchReport": WebFetchReport,
        "WebFetchPolicy": WebFetchPolicy,
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
