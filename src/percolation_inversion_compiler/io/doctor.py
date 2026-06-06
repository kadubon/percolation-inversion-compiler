"""Operational readiness diagnostics."""

from __future__ import annotations

import os
import sys
from importlib.util import find_spec
from pathlib import Path

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core.adapter_routes import list_adapter_route_specs
from percolation_inversion_compiler.core.operations import (
    OperationalCheck,
    OperationalReadinessReport,
    ProductionReadinessProfile,
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
) -> OperationalReadinessReport:
    """Build a deterministic readiness report without mutating local state."""

    policy = readiness_profile(profile)
    checks: list[OperationalCheck] = []
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
    route_ids = {spec.verifier_route for spec in route_specs}
    missing_routes: list[str] = []
    unavailable_routes = sorted(
        spec.verifier_route for spec in route_specs if spec.availability == "unavailable"
    )
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
            if missing_routes or (policy.require_available_external_routes and unavailable_routes)
            else "pass",
            "every external obligation route has an AdapterRouteSpec",
            route_count=len(route_specs),
            missing_routes=sorted(set(missing_routes)),
            unavailable_routes=unavailable_routes,
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
                "fail" if policy.require_canonical_or_signed_snapshot else "warn",
                "PIC_CANONICAL_TEX_DIR is not set; snapshot-only workflows remain available",
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

    manifest = canonical_manifest()
    checks.append(
        _check(
            "canonical-manifest",
            "pass",
            "canonical DOI manifest uses SHA-256 as primary integrity identity",
            schema_version=manifest.schema_version,
            record_count=len(manifest.records),
        )
    )

    security_files = {
        "SECURITY.md": Path("SECURITY.md").exists(),
        "LICENSE": Path("LICENSE").exists(),
        "NOTICE": Path("NOTICE").exists(),
        "THIRD_PARTY_LICENSES.md": Path("THIRD_PARTY_LICENSES.md").exists(),
        "CITATION.cff": Path("CITATION.cff").exists(),
    }
    checks.append(
        _check(
            "security-metadata",
            "fail"
            if policy.require_security_metadata and not all(security_files.values())
            else "pass",
            "security, citation, and license metadata are present",
            files=security_files,
        )
    )

    checks.append(
        _check(
            "schema-provenance",
            "fail" if policy.require_signed_schema_bundle else "warn",
            "schema bundle signing is not configured; JSON Schema output remains deterministic",
            signed=False,
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
            "external_obligation_totals": external_totals,
            "optional_dependency_status": dependency_status,
            "canonical_manifest_records": len(manifest.records),
        },
    )
