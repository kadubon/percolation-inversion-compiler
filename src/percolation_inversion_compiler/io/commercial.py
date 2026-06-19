"""Commercial and OSS onboarding readiness helpers."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core.live_policy import (
    default_allow_live_connectors,
    live_default_mode,
)
from percolation_inversion_compiler.core.operations import CommercialReadinessSummary
from percolation_inversion_compiler.io.zenodo import CANONICAL_RECORDS


def curated_demo_available() -> bool:
    """Return true when the installed curated demo bundle is available."""

    try:
        demo_root = files("percolation_inversion_compiler.data.demo")
    except ModuleNotFoundError:
        return False
    return all(
        demo_root.joinpath(name).is_file()
        for name in [
            "manifest.json",
            "runtime_state.json",
            "runtime_step_input.json",
            "agent_output.txt",
            "alt_admission_packet.json",
            "agent_message.json",
            "agent_inbox.json",
        ]
    )


def install_mode() -> str:
    """Classify the current runtime as source checkout or installed package."""

    if Path("pyproject.toml").exists() and Path("src/percolation_inversion_compiler").exists():
        return "source-checkout"
    return "installed-package"


def build_commercial_readiness_summary(
    *,
    profile: str = "development",
    schema_count: int = 0,
    snapshot_count: int = 0,
    provenance_verified: bool = False,
    security_metadata_present: bool = False,
    identity_ready: bool | None = None,
    package_version: str = __version__,
) -> CommercialReadinessSummary:
    """Build an onboarding-focused readiness summary without mutating state."""

    profile_lower = profile.lower()
    production_identity_required = profile_lower in {"production", "adversarial"}
    resolved_identity_ready = (
        not production_identity_required if identity_ready is None else identity_ready
    )
    curated_demo = curated_demo_available()
    schema_ready = schema_count > 0
    snapshots_ready = snapshot_count == len(CANONICAL_RECORDS)
    live_default_enabled = default_allow_live_connectors()
    live_default_off = not live_default_enabled
    connector_dependency_ready = True
    token_ready = bool(not production_identity_required or resolved_identity_ready)
    checks = {
        "install_mode": install_mode(),
        "schema_registry": "ready" if schema_ready else "fail",
        "snapshots": "ready" if snapshots_ready else "fail",
        "provenance": "ready" if provenance_verified else "diagnostic",
        "curated_demo": "ready" if curated_demo else "fail",
        "identity": (
            "ready"
            if resolved_identity_ready
            else "diagnostic"
            if production_identity_required
            else "ready"
        ),
        "security_metadata": "ready" if security_metadata_present else "fail",
        "live_connectors": "bounded-default-on" if live_default_enabled else "fail",
        "live_connector_opt_out": "ready",
        "bounded_candidate_intake": "ready" if live_default_enabled else "fail",
        "connector_dependency": "ready" if connector_dependency_ready else "diagnostic",
        "token_readiness": "ready" if token_ready else "diagnostic",
    }
    hard_fail = (
        any(
            checks[key] == "fail"
            for key in ["schema_registry", "snapshots", "curated_demo", "security_metadata"]
        )
        or not live_default_enabled
    )
    diagnostic = (production_identity_required and not resolved_identity_ready) or (
        not provenance_verified
    )
    reasons: list[str] = []
    if not provenance_verified:
        reasons.append("release or schema provenance is not verified in this environment")
    if production_identity_required and not resolved_identity_ready:
        reasons.append("production/adversarial use requires accepted identity context")
    if not curated_demo:
        reasons.append("curated installed-demo resources are unavailable")
    if not security_metadata_present:
        reasons.append("security, citation, or license metadata is incomplete")
    onboarding_status = "fail" if hard_fail else "diagnostic" if diagnostic else "pass"
    accepted = not hard_fail
    return CommercialReadinessSummary(
        install_mode=checks["install_mode"],
        onboarding_status=onboarding_status,
        package_version=package_version,
        schema_registry_ready=schema_ready,
        schema_count=schema_count,
        snapshot_bundle_ready=snapshots_ready,
        snapshot_count=snapshot_count,
        provenance_verified=provenance_verified,
        curated_demo_available=curated_demo,
        identity_ready=resolved_identity_ready,
        production_identity_required=production_identity_required,
        security_metadata_present=security_metadata_present,
        live_connectors_default_off=live_default_off,
        live_connectors_default_enabled=live_default_enabled,
        live_default_mode=live_default_mode(),
        live_connector_opt_out_available=True,
        bounded_intake_default=True,
        connector_dependency_ready=connector_dependency_ready,
        token_ready=token_ready,
        checks=checks,
        reasons=sorted(set(reasons)),
        accepted=accepted,
        operationally_usable=accepted and not diagnostic,
        settled=False,
    )
