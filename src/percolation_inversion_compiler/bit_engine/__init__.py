"""Practical BIT bottleneck inversion engine."""

from __future__ import annotations

from percolation_inversion_compiler.bit_engine.algorithms import (
    build_inversion_certificate,
    compare_observation_baseline,
    diagnose_bottlenecks,
    invert_bottlenecks,
    minimal_enabling_conditions_for_bottleneck,
)
from percolation_inversion_compiler.bit_engine.records import (
    ActivationGainEstimate,
    BottleneckClassDiagnosis,
    BottleneckInversionCandidate,
    BottleneckInversionReport,
    CapabilityExpressionPath,
    InversionCertificate,
    MinimalEnablingCondition,
    PostInversionAuditPlan,
    RollbackOrDeactivationPlan,
)

__all__ = [
    "ActivationGainEstimate",
    "BottleneckClassDiagnosis",
    "BottleneckInversionCandidate",
    "BottleneckInversionReport",
    "CapabilityExpressionPath",
    "InversionCertificate",
    "MinimalEnablingCondition",
    "PostInversionAuditPlan",
    "RollbackOrDeactivationPlan",
    "build_inversion_certificate",
    "compare_observation_baseline",
    "diagnose_bottlenecks",
    "invert_bottlenecks",
    "minimal_enabling_conditions_for_bottleneck",
]
