"""Core certificate, ledger, registry, and frontier primitives."""

from __future__ import annotations

from percolation_inversion_compiler.core.adapter_routes import (
    AdapterRouteSpec,
    VerifierEvidenceEnvelope,
    VerifierResolution,
    list_adapter_route_specs,
    resolve_adapter_route,
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
    audit_registry_projection,
)
from percolation_inversion_compiler.core.coverage import (
    CoverageStatus,
    ExternalObligationCatalog,
    TheoryCoverageRecord,
    TheoryImplementationRecord,
    TheoryItem,
)
from percolation_inversion_compiler.core.frontier import (
    FrontierRecord,
    archive_with_truncation,
    dominates,
    pareto_frontier,
)
from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.judgment import (
    AgentConnectorSpec,
    CertificateDAG,
    ExtractorOutput,
    Judgment,
    ObligationSet,
    ProofObligationVerifier,
    check_external_verifier_hook,
)
from percolation_inversion_compiler.core.ledger import Ledger, LedgerCoordinate
from percolation_inversion_compiler.core.operations import (
    OperationalCheck,
    OperationalReadinessReport,
)
from percolation_inversion_compiler.core.order import (
    DominanceWitness,
    FiniteOrder,
    LatticeWitness,
    MonotoneMap,
    ProductOrder,
)
from percolation_inversion_compiler.core.records import (
    Certificate,
    CertificateShell,
    CheckResult,
    ClaimRecord,
    ExternalProofObligation,
    ExternalVerifierHook,
    Registry,
    ValidityDomain,
)
from percolation_inversion_compiler.core.status import ClaimStatus, StatusDecision, StatusRule

__all__ = [
    "AdapterRouteSpec",
    "AgentConnectorSpec",
    "AlgebraLawCertificate",
    "CalibrationCertificate",
    "Certificate",
    "CertificateDAG",
    "CertificateFamily",
    "CertificateRoute",
    "CertificateShell",
    "CheckResult",
    "CheckerContext",
    "ClaimRecord",
    "ClaimStatus",
    "ConfidenceLedger",
    "CoverageStatus",
    "DKWCertificate",
    "DependencyDAG",
    "DomainTypedSemiring",
    "DominanceWitness",
    "EProcessCertificate",
    "ExternalObligationCatalog",
    "ExternalProofObligation",
    "ExternalVerifierHook",
    "ExtractorOutput",
    "FiniteOrder",
    "FrontierRecord",
    "FunctorLawCertificate",
    "GoodTuringCertificate",
    "Judgment",
    "LatticeWitness",
    "Ledger",
    "LedgerCoordinate",
    "MartingaleBlockResidual",
    "MonoidRecord",
    "MonotoneMap",
    "NonPromotionPolicy",
    "ObligationRule",
    "ObligationSet",
    "ObligationTrace",
    "OperationalCheck",
    "OperationalReadinessReport",
    "ProductOrder",
    "ProjectionAudit",
    "ProofObligationVerifier",
    "ReconstructionResidual",
    "RefreshRule",
    "Registry",
    "SplitCertificate",
    "StatusDecision",
    "StatusRule",
    "TheoryAuditReport",
    "TheoryCoverageRecord",
    "TheoryImplementationRecord",
    "TheoryItem",
    "ValidityDomain",
    "VerifierEvidenceEnvelope",
    "VerifierResolution",
    "archive_with_truncation",
    "audit_registry_projection",
    "check_external_verifier_hook",
    "dominates",
    "list_adapter_route_specs",
    "pareto_frontier",
    "resolve_adapter_route",
]
