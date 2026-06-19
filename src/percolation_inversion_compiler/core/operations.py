"""Operational readiness records for production and agent runners."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.live_policy import (
    default_allow_live_connectors,
    live_default_mode,
)


class OperationalCheck(BaseModel):
    """One deterministic operational readiness check."""

    check_id: str
    status: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class CommercialReadinessSummary(BaseModel):
    """Practical onboarding readiness summary for commercial and OSS users."""

    summary_id: str = "pic-commercial-readiness"
    install_mode: str = "unknown"
    onboarding_status: str = "diagnostic"
    package_version: str = ""
    schema_registry_ready: bool = False
    schema_count: int = 0
    snapshot_bundle_ready: bool = False
    snapshot_count: int = 0
    provenance_verified: bool = False
    curated_demo_available: bool = False
    identity_ready: bool = False
    production_identity_required: bool = False
    security_metadata_present: bool = False
    live_connectors_default_off: bool = False
    live_connectors_default_enabled: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    live_connector_opt_out_available: bool = True
    bounded_intake_default: bool = True
    connector_dependency_ready: bool = False
    token_ready: bool = False
    checks: dict[str, str] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False


class PortabilityConformanceReport(BaseModel):
    """Schema-first conformance report for language ports and bundled examples."""

    report_id: str = "pic-portability-conformance"
    manifest_path: str = ""
    checked_examples: dict[str, str] = Field(default_factory=dict)
    checked_negative_examples: dict[str, str] = Field(default_factory=dict)
    schema_names: dict[str, str] = Field(default_factory=dict)
    sha256: dict[str, str] = Field(default_factory=dict)
    schema_digest: str = ""
    positive_example_count: int = 0
    negative_example_count: int = 0
    expected_failure_count: int = 0
    unexpected_failure_count: int = 0
    semantic_invariants: list[str] = Field(default_factory=list)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class OperationalReadinessReport(BaseModel):
    """Machine-readable environment report for CI and autonomous agents."""

    report_id: str = "pic-operational-readiness"
    package_version: str
    python_version: str
    overall_status: str
    checks: list[OperationalCheck] = Field(default_factory=list)
    summary: dict[str, object] = Field(default_factory=dict)
    commercial_readiness: CommercialReadinessSummary = Field(
        default_factory=lambda: CommercialReadinessSummary()
    )
    safety_invariants: list[str] = Field(
        default_factory=lambda: [
            "registry entries are metadata, not evidence",
            "derived_status is checker-derived",
            "unresolved external obligations do not promote to settled",
            "snapshots are derived metadata and do not vendor TeX/PDF sources",
        ]
    )


class ProductionReadinessProfile(BaseModel):
    """Production policy knobs for fail-closed operational readiness."""

    profile: str = "development"
    require_canonical_or_signed_snapshot: bool = False
    require_available_external_routes: bool = False
    require_optional_dependencies: bool = False
    require_security_metadata: bool = False
    require_signed_schema_bundle: bool = False
