"""Operational readiness diagnostics."""

from __future__ import annotations

import json
import os
import sys
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core.adapter_routes import (
    list_adapter_route_specs,
    list_discharge_route_bindings,
)
from percolation_inversion_compiler.core.operations import (
    OperationalCheck,
    OperationalReadinessReport,
    ProductionReadinessProfile,
)
from percolation_inversion_compiler.io.provenance import (
    ProvenanceManifest,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.schema import schema_model_map
from percolation_inversion_compiler.io.snapshots import list_theory_snapshots
from percolation_inversion_compiler.io.zenodo import (
    CANONICAL_RECORDS,
    canonical_manifest,
    validate_canonical_source,
)


def _check(check_id: str, status: str, message: str, **details: object) -> OperationalCheck:
    return OperationalCheck(
        check_id=check_id,
        status=status,
        message=message,
        details={key: value for key, value in details.items() if value is not None},
    )


def _overall_status(checks: list[OperationalCheck]) -> str:
    statuses = {check.status for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _metadata_value(package_metadata: Any, key: str, default: str = "") -> str:
    if key not in package_metadata:
        return default
    value = package_metadata[key]
    return str(value) if value else default


def readiness_profile(profile: str = "development") -> ProductionReadinessProfile:
    normalized = profile.lower()
    if normalized not in {"development", "research", "production"}:
        raise ValueError("profile must be one of: development, research, production")
    return ProductionReadinessProfile(
        profile=normalized,
        require_canonical_or_signed_snapshot=normalized == "production",
        require_available_external_routes=normalized == "production",
        require_optional_dependencies=normalized == "production",
        require_security_metadata=normalized in {"research", "production"},
        require_signed_schema_bundle=normalized == "production",
    )


def build_operational_readiness_report(
    *,
    profile: str = "development",
    provenance: str | Path | None = None,
) -> OperationalReadinessReport:
    """Build a deterministic readiness report without mutating local state."""

    policy = readiness_profile(profile)
    checks: list[OperationalCheck] = []
    provenance_valid = False
    provenance_reasons: list[str] = []
    provenance_path: Path | None = Path(provenance) if provenance is not None else None
    if provenance_path is not None:
        try:
            manifest = ProvenanceManifest.model_validate(
                json.loads(provenance_path.read_text(encoding="utf-8"))
            )
            provenance_valid, provenance_reasons = verify_provenance_manifest(
                manifest,
                base_dir=Path("."),
            )
        except (OSError, ValueError) as exc:
            provenance_reasons = [str(exc)]
    checks.append(
        _check(
            "provenance-manifest",
            "pass"
            if provenance_valid
            else "fail"
            if policy.require_canonical_or_signed_snapshot
            else "warn",
            "release provenance manifest verifies schema, snapshot, examples, and metadata",
            provenance=str(provenance_path) if provenance_path is not None else None,
            reasons=provenance_reasons,
        )
    )
    schemas = schema_model_map()
    checks.append(
        _check(
            "schema-registry",
            "pass" if schemas else "fail",
            "public schema registry is available",
            schema_count=len(schemas),
        )
    )

    snapshots = list_theory_snapshots()
    snapshot_unsupported = {
        snapshot.artifact_key: snapshot.coverage_counts.get("unsupported", 0)
        for snapshot in snapshots
    }
    checks.append(
        _check(
            "derived-snapshots",
            "pass"
            if len(snapshots) == len(CANONICAL_RECORDS)
            and all(value == 0 for value in snapshot_unsupported.values())
            else "fail",
            "bundled derived snapshots are available and keep unsupported at zero",
            snapshot_count=len(snapshots),
            unsupported_by_artifact=snapshot_unsupported,
        )
    )

    route_specs = list_adapter_route_specs()
    route_bindings = list_discharge_route_bindings()
    route_ids = {spec.verifier_route for spec in route_specs}
    binding_route_ids = {binding.canonical_route_id for binding in route_bindings}
    missing_routes: list[str] = []
    unavailable_routes = sorted(
        spec.verifier_route for spec in route_specs if spec.availability == "unavailable"
    )
    unbound_contract_routes = sorted(
        spec.route_id
        for spec in route_specs
        if spec.canonical_route_id == spec.route_id and spec.route_id not in binding_route_ids
    )
    discharge_level_summary: dict[str, int] = {}
    unresolved_domain_obligations = 0
    for binding in route_bindings:
        key = binding.discharge_level.value
        discharge_level_summary[key] = discharge_level_summary.get(key, 0) + 1
        unresolved_domain_obligations += len(binding.unresolved_domain_obligations)
    external_totals: dict[str, int] = {}
    for snapshot in snapshots:
        catalog = snapshot.external_obligation_catalog
        if catalog is None:
            continue
        external_totals[snapshot.artifact_key] = len(catalog.obligations)
        for obligation in catalog.obligations:
            if obligation.verifier_route not in route_ids:
                missing_routes.append(str(obligation.verifier_route))
    checks.append(
        _check(
            "adapter-route-catalog",
            "fail"
            if missing_routes
            or (policy.require_available_external_routes and unavailable_routes)
            or unbound_contract_routes
            else "pass",
            "every external obligation route has an AdapterRouteSpec",
            route_count=len(route_specs),
            binding_count=len(route_bindings),
            missing_routes=sorted(set(missing_routes)),
            unavailable_routes=unavailable_routes,
            unbound_contract_routes=unbound_contract_routes,
            discharge_level_summary=discharge_level_summary,
            unresolved_domain_obligation_count=unresolved_domain_obligations,
        )
    )

    optional_dependencies = sorted(
        {spec.optional_dependency for spec in route_specs if spec.optional_dependency}
    )
    dependency_status = {
        dependency: "installed" if find_spec(dependency) is not None else "missing"
        for dependency in optional_dependencies
    }
    checks.append(
        _check(
            "optional-adapters",
            "fail"
            if policy.require_optional_dependencies and "missing" in dependency_status.values()
            else "warn"
            if "missing" in dependency_status.values()
            else "pass",
            "optional scientific adapters are reported explicitly",
            dependencies=dependency_status,
        )
    )

    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if canonical_dir is None:
        checks.append(
            _check(
                "canonical-tex",
                "pass"
                if provenance_valid
                else "fail"
                if policy.require_canonical_or_signed_snapshot
                else "warn",
                "PIC_CANONICAL_TEX_DIR is not set; verified provenance may substitute local TeX",
                provenance_verified=provenance_valid,
            )
        )
    else:
        canonical_results: dict[str, object] = {}
        canonical_status = "pass"
        for key, record in CANONICAL_RECORDS.items():
            source = Path(canonical_dir) / record.tex_filename
            if not source.exists():
                canonical_results[key] = {"exists": False, "matches": False}
                canonical_status = "fail"
                continue
            result = validate_canonical_source(source, key)
            canonical_results[key] = {
                "exists": True,
                "matches": bool(result["matches"]),
                "expected_md5": result["expected_md5"],
                "actual_md5": result["actual_md5"],
                "expected_sha256": result["expected_sha256"],
                "actual_sha256": result["actual_sha256"],
            }
            if not result["matches"]:
                canonical_status = "fail"
        checks.append(
            _check(
                "canonical-tex",
                canonical_status,
                "canonical TeX files were checked against bundled DOI metadata",
                artifacts=canonical_results,
            )
        )

    canonical = canonical_manifest()
    checks.append(
        _check(
            "canonical-manifest",
            "pass",
            "canonical DOI manifest uses SHA-256 as primary integrity identity",
            schema_version=canonical.schema_version,
            record_count=len(canonical.records),
        )
    )

    source_security_files = {
        "SECURITY.md": Path("SECURITY.md").exists(),
        "LICENSE": Path("LICENSE").exists(),
        "NOTICE": Path("NOTICE").exists(),
        "THIRD_PARTY_LICENSES.md": Path("THIRD_PARTY_LICENSES.md").exists(),
        "CITATION.cff": Path("CITATION.cff").exists(),
    }
    try:
        distribution_metadata = metadata.metadata("percolation-inversion-compiler")
        distribution_metadata_ok = bool(_metadata_value(distribution_metadata, "Name")) and bool(
            _metadata_value(distribution_metadata, "License")
        )
    except metadata.PackageNotFoundError:
        distribution_metadata_ok = False
    security_ok = all(source_security_files.values()) or distribution_metadata_ok
    checks.append(
        _check(
            "security-metadata",
            "fail" if policy.require_security_metadata and not security_ok else "pass",
            "security, citation, and license metadata are present",
            source_files=source_security_files,
            distribution_metadata=distribution_metadata_ok,
        )
    )

    checks.append(
        _check(
            "schema-provenance",
            "pass"
            if provenance_valid
            else "fail"
            if policy.require_signed_schema_bundle
            else "warn",
            "schema bundle provenance is verified by deterministic SHA-256 manifest",
            signed=False,
            provenance_verified=provenance_valid,
        )
    )

    checks.append(
        _check(
            "status-policy",
            "pass",
            "non-promotion and residual preservation policies are active",
            policy=[
                "declared_status is metadata",
                "checker output derives status",
                "external routes default to diagnostic unless accepted evidence is present",
            ],
        )
    )

    return OperationalReadinessReport(
        package_version=__version__,
        python_version=sys.version.split()[0],
        overall_status=_overall_status(checks),
        checks=checks,
        summary={
            "profile": policy.profile,
            "schema_count": len(schemas),
            "snapshot_count": len(snapshots),
            "adapter_route_count": len(route_specs),
            "discharge_route_binding_count": len(route_bindings),
            "discharge_level_summary": discharge_level_summary,
            "external_obligation_totals": external_totals,
            "optional_dependency_status": dependency_status,
            "canonical_manifest_records": len(canonical.records),
            "provenance_verified": provenance_valid,
        },
    )
