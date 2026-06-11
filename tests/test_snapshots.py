from __future__ import annotations

import os
from pathlib import Path

import pytest

from percolation_inversion_compiler.core import (
    AdapterRouteSpec,
    DischargeLevel,
    EvidenceArtifact,
    VerifierEvidenceEnvelope,
    list_adapter_route_specs,
    list_discharge_route_bindings,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.coverage import TheoryImplementationRecord
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.io import audit_theory_source
from percolation_inversion_compiler.io.snapshots import (
    find_snapshot_item,
    list_theory_snapshots,
    load_theory_snapshot,
)


def test_snapshot_catalog_is_available_without_tex() -> None:
    snapshots = list_theory_snapshots()
    assert [snapshot.artifact_key for snapshot in snapshots] == [
        "ecpt",
        "bit",
        "trc",
        "sqot",
        "alt",
    ]
    assert snapshots[0].attribution.license_id == "cc-by-4.0"
    assert all(snapshot.coverage_counts["unsupported"] == 0 for snapshot in snapshots)


def test_snapshot_external_lookup() -> None:
    item = find_snapshot_item("def:null-channel-routing", external_only=True)
    assert isinstance(item, TheoryImplementationRecord)
    assert item.obligation_category == "physical-hybrid-system"
    assert item.safe_default == "diagnostic-with-physical-obligation"


@pytest.mark.parametrize(
    ("key", "filename"),
    [
        ("ecpt", "Executable Capability Percolation Theory.tex"),
        ("bit", "Bottleneck Inversion Theory.tex"),
        ("trc", "Typed Reality Compilation.tex"),
        ("sqot", "Salience-Queue Occupation Theory.tex"),
        ("alt", "Abstraction Liquidity Theory.tex"),
    ],
)
def test_canonical_snapshot_regression_when_present(key: str, filename: str) -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    report = audit_theory_source(Path(canonical_dir) / filename, canonical_key=key)
    snapshot = load_theory_snapshot(key)
    assert report.snapshot_delta["coverage_counts_match"]
    assert report.snapshot_delta["external_category_summary_match"]
    assert snapshot.coverage_counts == report.coverage.counts_by_status()
    assert {item.item_id: item.coverage_status.value for item in report.coverage.items} == {
        item.item_id: item.coverage_status for item in snapshot.item_mappings
    }


def test_adapter_route_catalog_covers_external_snapshot_routes() -> None:
    known_routes = {spec.verifier_route for spec in list_adapter_route_specs()}
    bound_route_ids = {binding.canonical_route_id for binding in list_discharge_route_bindings()}
    for snapshot in list_theory_snapshots():
        catalog = snapshot.external_obligation_catalog
        if catalog is None:
            continue
        for obligation in catalog.obligations:
            assert obligation.verifier_route in known_routes
            spec = next(
                route
                for route in list_adapter_route_specs()
                if route.verifier_route == obligation.verifier_route
            )
            assert spec.route_id in bound_route_ids


def test_contract_adapter_route_returns_diagnostic_without_evidence() -> None:
    spec = next(
        route
        for route in list_adapter_route_specs()
        if route.verifier_route == "trc.adapters.physical_hybrid.verify_envelope"
    )
    binding = next(
        route
        for route in list_discharge_route_bindings()
        if route.canonical_route_id == spec.route_id
    )
    assert spec.availability == "contract"
    assert binding.discharge_level == DischargeLevel.REPLAY_CHECK
    assert binding.unresolved_domain_obligations
    result = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="missing",
            route_id=spec.route_id,
            obligation_ids=["obligation:def:null-channel-routing"],
            evidence_kind=[],
            residual_coordinates={"null-channel-unverified": 1.0},
        ),
    )
    assert not result.accepted
    assert result.status == ClaimStatus.DIAGNOSTIC
    assert result.safe_default == "diagnostic-with-physical-obligation"
    assert "evidence artifacts are missing" in result.reasons


def test_evidence_artifact_provenance_accepts_attested_digest() -> None:
    spec = next(
        route
        for route in list_adapter_route_specs()
        if route.route_id == "adapters.domain.verify_trc_telemetry_calibration"
    )
    result = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="telemetry",
            route_id=spec.route_id,
            obligation_ids=["obligation:telemetry"],
            evidence_kind=["finite-telemetry-calibration"],
            evidence_artifacts=[
                EvidenceArtifact(
                    artifact_id="artifact",
                    evidence_kind="finite-telemetry-calibration",
                    sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
                    media_type="application/json",
                    schema_uri="https://example.invalid/schema",
                    schema_sha256=(
                        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    ),
                    producer_id="producer",
                    produced_at="2026-06-06T00:00:00Z",
                    verifier_id="verifier",
                    verifier_version="0.2.2",
                )
            ],
        ),
    )
    assert result.accepted
    assert result.status == ClaimStatus.SETTLED


def test_evidence_artifact_hash_mismatch_is_diagnostic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text("{}", encoding="utf-8")
    spec = next(
        route
        for route in list_adapter_route_specs()
        if route.route_id == "adapters.domain.verify_trc_telemetry_calibration"
    )
    result = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="telemetry",
            route_id=spec.route_id,
            obligation_ids=["obligation:telemetry"],
            evidence_kind=["finite-telemetry-calibration"],
            evidence_artifacts=[
                EvidenceArtifact(
                    artifact_id="artifact",
                    evidence_kind="finite-telemetry-calibration",
                    sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
                    media_type="application/json",
                    schema_uri="https://example.invalid/schema",
                    schema_sha256=(
                        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    ),
                    producer_id="producer",
                    produced_at="2026-06-06T00:00:00Z",
                    verifier_id="verifier",
                    verifier_version="0.2.2",
                    content_ref=str(evidence_file),
                )
            ],
        ),
    )
    assert not result.accepted
    assert "sha256 mismatch" in " ".join(result.reasons)


def test_missing_optional_adapter_dependency_returns_diagnostic_resolution() -> None:
    spec = AdapterRouteSpec(
        route_id="example.optional.missing",
        verifier_route="example.optional.missing",
        obligation_category="test-optional",
        availability="optional",
        optional_dependency="definitely_missing_pic_dependency",
        license_note="test-only",
        required_evidence_kind=["finite-witness"],
        residual_policy="charge-test-residual",
        safe_default="diagnostic-with-missing-optional-dependency",
    )
    result = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="witness",
            route_id=spec.route_id,
            obligation_ids=["obligation:test"],
            evidence_kind=["finite-witness"],
        ),
    )
    assert not result.accepted
    assert result.status == ClaimStatus.DIAGNOSTIC
    assert "optional dependency 'definitely_missing_pic_dependency' is not installed" in (
        result.reasons
    )
