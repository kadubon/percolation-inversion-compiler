from __future__ import annotations

import hashlib
import json
from pathlib import Path

from percolation_inversion_compiler.core import (
    EvidenceArtifact,
    VerifierEvidenceEnvelope,
    check_external_verifier_hook,
    list_adapter_route_specs,
    list_discharge_route_bindings,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.adapter_routes import (
    DischargeLevel,
    EvidenceVerificationProfile,
)
from percolation_inversion_compiler.core.coverage import external_route_specs_data
from percolation_inversion_compiler.core.records import (
    ExternalProofObligation,
    ExternalVerifierHook,
)
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.io.provenance import (
    create_provenance_manifest,
    verify_provenance_manifest,
)


def _telemetry_spec():
    return next(
        route
        for route in list_adapter_route_specs()
        if route.route_id == "adapters.domain.verify_trc_telemetry_calibration"
    )


def _artifact(*, content_ref: str | None = None, sha256: str | None = None) -> EvidenceArtifact:
    return EvidenceArtifact(
        artifact_id="artifact",
        evidence_kind="finite-telemetry-calibration",
        sha256=sha256 or "a" * 64,
        media_type="application/json",
        schema_uri="https://example.invalid/schema",
        schema_sha256="0" * 64,
        producer_id="producer",
        produced_at="2026-06-06T00:00:00Z",
        verifier_id="verifier",
        verifier_version="0.2.1",
        content_ref=content_ref,
    )


def test_every_canonical_external_route_has_discharge_binding() -> None:
    external_route_ids = {
        str(data["route_id"])
        for data in external_route_specs_data()
        if data.get("availability") == "unavailable"
    }
    binding_route_ids = {binding.canonical_route_id for binding in list_discharge_route_bindings()}
    assert external_route_ids <= binding_route_ids
    assert all(
        binding.discharge_level
        in {
            DischargeLevel.FINITE_VALUE_CHECK,
            DischargeLevel.REPLAY_CHECK,
            DischargeLevel.CONTRACT_ENFORCED,
            DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        }
        for binding in list_discharge_route_bindings()
    )


def test_production_evidence_rejects_metadata_only_artifact() -> None:
    spec = _telemetry_spec()
    development = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="metadata-only",
            route_id=spec.route_id,
            obligation_ids=["obligation:telemetry"],
            evidence_kind=["finite-telemetry-calibration"],
            evidence_artifacts=[_artifact()],
        ),
        profile=EvidenceVerificationProfile.DEVELOPMENT,
    )
    assert development.accepted

    production = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="metadata-only",
            route_id=spec.route_id,
            obligation_ids=["obligation:telemetry"],
            evidence_kind=["finite-telemetry-calibration"],
            evidence_artifacts=[_artifact()],
        ),
        profile=EvidenceVerificationProfile.PRODUCTION,
    )
    assert not production.accepted
    assert production.status == ClaimStatus.DIAGNOSTIC
    assert "production evidence requires content_ref" in " ".join(production.reasons)


def test_production_evidence_accepts_replayable_content(tmp_path: Path) -> None:
    evidence_file = tmp_path / "telemetry.json"
    evidence_file.write_text('{"calibration_error": 0.01}', encoding="utf-8")
    digest = hashlib.sha256(evidence_file.read_bytes()).hexdigest()
    spec = _telemetry_spec()
    resolution = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="replayable",
            route_id=spec.route_id,
            obligation_ids=["obligation:telemetry"],
            evidence_kind=["finite-telemetry-calibration"],
            evidence_artifacts=[_artifact(content_ref=evidence_file.name, sha256=digest)],
        ),
        base_dir=tmp_path,
        profile=EvidenceVerificationProfile.PRODUCTION,
    )
    assert resolution.accepted
    assert resolution.operationally_usable
    assert resolution.settled
    assert resolution.evidence_artifact_ids == ["artifact"]
    assert resolution.resolution_digest


def test_legacy_external_hook_cannot_discharge_without_resolution_provenance() -> None:
    obligation = ExternalProofObligation(
        obligation_id="obligation:telemetry",
        description="telemetry calibration",
        obligation_category="telemetry-calibration",
    )
    hook = ExternalVerifierHook(
        hook_id="legacy",
        verifier_route="adapters.domain.verify_trc_telemetry_calibration",
        obligation_ids={"obligation:telemetry"},
        accepted_obligation_ids={"obligation:telemetry"},
    )
    result = check_external_verifier_hook(hook, [obligation])
    assert not result.accepted
    assert "accepted external verifier hook requires resolution provenance" in result.reasons


def test_provenance_manifest_is_deterministic_and_detects_mutation(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    schema_file = schema_dir / "Example.schema.json"
    schema_file.write_text('{"title":"Example"}\n', encoding="utf-8")
    first = create_provenance_manifest(schema_dir=schema_dir)
    second = create_provenance_manifest(schema_dir=schema_dir)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    valid, reasons = verify_provenance_manifest(first)
    assert valid, reasons

    schema_file.write_text('{"title":"Modified"}\n', encoding="utf-8")
    valid_after_mutation, reasons_after_mutation = verify_provenance_manifest(first)
    assert not valid_after_mutation
    assert "sha256 mismatch" in " ".join(reasons_after_mutation)


def test_example_evidence_envelope_content_hash_matches() -> None:
    envelope = VerifierEvidenceEnvelope.model_validate_json(
        Path("examples/evidence_envelope.json").read_text(encoding="utf-8")
    )
    artifact = envelope.evidence_artifacts[0]
    content = Path("examples") / str(artifact.content_ref)
    assert hashlib.sha256(content.read_bytes()).hexdigest() == artifact.sha256
    payload = json.loads(content.read_text(encoding="utf-8"))
    assert payload["tolerance"] == 0.1
