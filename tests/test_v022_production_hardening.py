from __future__ import annotations

import hashlib
import json
from pathlib import Path

from percolation_inversion_compiler.adapters.domain import (
    replay_trc_physical_trace,
    verify_archive_domain_evidence,
    verify_ecpt_generator_limit,
    verify_ecpt_numerical_envelope,
    verify_trc_telemetry_calibration,
)
from percolation_inversion_compiler.adapters.transport import sinkhorn_transport
from percolation_inversion_compiler.core import (
    Certificate,
    ClaimRecord,
    EvidenceArtifact,
    ExternalProofObligation,
    ExternalVerifierHook,
    Registry,
    VerifierEvidenceEnvelope,
    check_external_verifier_hook,
    evidence_policy,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.adapter_routes import EvidenceVerificationProfile
from percolation_inversion_compiler.core.status import ClaimStatus
from percolation_inversion_compiler.io.doctor import build_operational_readiness_report
from percolation_inversion_compiler.io.provenance import (
    AttestationRecord,
    create_provenance_manifest,
    file_entry,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.sbom import (
    build_cyclonedx_sbom,
    build_pic_sbom,
    build_sbom_document,
)
from percolation_inversion_compiler.io.schema import schema_by_type, validate_data
from percolation_inversion_compiler.io.tex import (
    ExtractedFile,
    MRRecord,
    extract_mr_records,
    registry_from_json_block,
    registry_from_mr_records,
    strict_tex_parse_report,
)


def _spec(route_id: str):
    return next(route for route in list_adapter_route_specs() if route.route_id == route_id)


def _artifact(
    *,
    evidence_kind: str,
    path: Path,
    artifact_id: str = "artifact",
) -> EvidenceArtifact:
    return EvidenceArtifact(
        artifact_id=artifact_id,
        evidence_kind=evidence_kind,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        media_type="application/json",
        schema_uri="https://example.invalid/schema",
        schema_sha256="1" * 64,
        producer_id="producer",
        produced_at="2026-06-06T00:00:00Z",
        verifier_id="verifier",
        verifier_version="0.2.2",
        content_ref=path.name,
    )


def test_replay_check_preserves_external_residual_scope(tmp_path: Path) -> None:
    evidence_path = tmp_path / "trace.json"
    evidence_path.write_text('{"events": ["a", "b"]}', encoding="utf-8")
    spec = _spec("adapters.domain.replay_trc_physical_trace")
    resolution = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="physical-replay",
            route_id=spec.route_id,
            obligation_ids=["obligation:physical"],
            evidence_kind=["finite-physical-trace"],
            evidence_artifacts=[
                _artifact(evidence_kind="finite-physical-trace", path=evidence_path),
            ],
        ),
        base_dir=tmp_path,
        profile=EvidenceVerificationProfile.PRODUCTION,
    )
    assert resolution.accepted
    assert resolution.finite_scope_usable
    assert not resolution.settled
    assert not resolution.operationally_usable
    assert resolution.status == ClaimStatus.PROVISIONAL
    assert resolution.settled_scope == ["finite-replay:adapters.domain.replay_trc_physical_trace"]
    assert "continuous-physics-envelope" in resolution.residual_external_obligations
    assert resolution.domain_witness_required

    hook = resolution.to_external_verifier_hook()
    obligation = ExternalProofObligation(
        obligation_id="obligation:physical",
        description="physical replay residual",
        obligation_category="physical-hybrid-system",
    )
    check = check_external_verifier_hook(hook, [obligation])
    assert not check.accepted
    assert "obligation:physical" in check.missing_obligations


def test_finite_value_check_can_settle_when_no_external_residuals(tmp_path: Path) -> None:
    evidence_path = tmp_path / "archive.json"
    evidence_path.write_text('{"archive": true}', encoding="utf-8")
    spec = _spec("adapters.domain.verify_archive_domain_evidence")
    resolution = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="archive",
            route_id=spec.route_id,
            obligation_ids=["obligation:archive"],
            evidence_kind=["finite-archive-domain"],
            evidence_artifacts=[
                _artifact(evidence_kind="finite-archive-domain", path=evidence_path),
            ],
        ),
        base_dir=tmp_path,
        profile=EvidenceVerificationProfile.PRODUCTION,
    )
    assert resolution.accepted
    assert resolution.finite_scope_usable
    assert resolution.settled
    assert resolution.operationally_usable
    assert resolution.residual_external_obligations == []
    assert resolution.accepted_obligation_ids == ["obligation:archive"]


def test_inconsistent_accepted_hook_cannot_exceed_settled_scope() -> None:
    obligation = ExternalProofObligation(
        obligation_id="obligation:domain",
        description="domain witness",
    )
    hook = ExternalVerifierHook(
        hook_id="hook",
        verifier_route="route",
        obligation_ids={"obligation:domain"},
        accepted_obligation_ids={"obligation:domain"},
        resolution_id="resolution:id",
        resolution_digest="a" * 64,
        evidence_envelope_id="envelope",
        evidence_artifact_ids={"artifact"},
        settled_scope=["finite-replay:route"],
        residual_external_obligations={"oracle-witness"},
        domain_witness_required=True,
    )
    result = check_external_verifier_hook(hook, [obligation])
    assert not result.accepted
    assert "accepted external verifier hook exceeds settled scope" in result.reasons


def test_required_route_doctor_scopes_optional_dependencies(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "Example.schema.json").write_text('{"title":"Example"}\n', encoding="utf-8")
    manifest = create_provenance_manifest(schema_dir=schema_dir)
    manifest_path = tmp_path / "provenance.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = build_operational_readiness_report(
        profile="production",
        provenance=manifest_path,
        required_routes=["adapters.domain.verify_trc_telemetry_calibration"],
    )
    assert report.overall_status == "pass"
    assert report.summary["required_routes"] == ["adapters.domain.verify_trc_telemetry_calibration"]
    assert report.summary["optional_dependency_status"] == {}

    missing = build_operational_readiness_report(
        profile="production",
        provenance=manifest_path,
        required_routes=["route.does.not.exist"],
    )
    assert missing.overall_status == "fail"
    route_check = next(
        check for check in missing.checks if check.check_id == "adapter-route-catalog"
    )
    assert route_check.details["missing_required_routes"] == ["route.does.not.exist"]


def test_provenance_require_attestation(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "Example.schema.json").write_text('{"title":"Example"}\n', encoding="utf-8")
    manifest = create_provenance_manifest(schema_dir=schema_dir)
    valid_without, _ = verify_provenance_manifest(manifest)
    assert valid_without

    valid_required, reasons_required = verify_provenance_manifest(
        manifest,
        require_attestation=True,
    )
    assert not valid_required
    assert "attestation is required but manifest has no attestations" in reasons_required

    entry = manifest.entries[0]
    attested = manifest.model_copy(
        update={
            "attestations": [
                AttestationRecord(
                    attestation_id="attestation",
                    subject_name=entry.path,
                    subject_sha256=entry.sha256,
                    issuer="https://token.actions.githubusercontent.com",
                    predicate_type="https://slsa.dev/provenance/v1",
                    bundle_ref="gh-attestation://example",
                    verified=True,
                    verified_at="2026-06-06T00:00:00Z",
                )
            ],
            "attestation_subjects": [entry.path],
            "issuer": "https://token.actions.githubusercontent.com",
            "predicate_type": "https://slsa.dev/provenance/v1",
            "bundle_ref": "gh-attestation://example",
            "verified_at": "2026-06-06T00:00:00Z",
        }
    )
    valid_attested, reasons_attested = verify_provenance_manifest(
        attested,
        require_attestation=True,
    )
    assert valid_attested, reasons_attested

    bad_attested = attested.model_copy(
        update={
            "attestation_subjects": ["missing.json"],
            "attestations": [
                AttestationRecord(
                    attestation_id="bad",
                    subject_name="missing.json",
                    subject_sha256="f" * 64,
                    issuer="",
                    predicate_type="",
                    bundle_ref=None,
                    verified=False,
                )
            ],
        }
    )
    invalid_attested, invalid_reasons = verify_provenance_manifest(
        bad_attested,
        require_attestation=True,
    )
    assert not invalid_attested
    assert "attestation subject has no provenance entry: missing.json" in invalid_reasons
    assert "attestation subject is absent from manifest entries: missing.json" in invalid_reasons

    schema_file = schema_dir / "Example.schema.json"
    schema_entry = file_entry(schema_file, base_dir=schema_dir)
    assert schema_entry.path == "Example.schema.json"
    schema_file.unlink()
    missing_valid, missing_reasons = verify_provenance_manifest(manifest)
    assert not missing_valid
    assert "provenance entry is missing" in " ".join(missing_reasons)


def test_cyclonedx_and_pic_sbom_are_deterministic() -> None:
    pic = build_pic_sbom()
    cyclonedx = build_cyclonedx_sbom()
    assert pic.bomFormat == "PIC-SBOM"
    assert pic.components
    assert cyclonedx["bomFormat"] == "CycloneDX"
    assert cyclonedx["specVersion"] == "1.6"
    assert cyclonedx["components"]
    assert build_cyclonedx_sbom() == cyclonedx
    try:
        build_sbom_document("spdx")
    except ValueError as exc:
        assert "pic, cyclonedx" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("unknown SBOM format must fail")


def test_strict_tex_parse_flags_unsupported_shapes(tmp_path: Path) -> None:
    source = tmp_path / "bad.tex"
    source.write_text(
        r"""
\begin{claim}[Unsupported]\label{claim:x}
\end{claim}
\begin{definition}[Broken header]
\label{def:broken}
\end{definition}
\begin{theorem}
\end{theorem}
\begin{theorem}[Duplicate]\label{thm:dup}
\end{theorem}
\begin{lemma}[Duplicate again]\label{thm:dup}
\end{lemma}
\MRClaim{missing-fields}
""",
        encoding="utf-8",
    )
    report = strict_tex_parse_report(source)
    kinds = {diagnostic.kind for diagnostic in report.diagnostics}
    assert not report.accepted
    assert "unknown-theorem-environment" in kinds
    assert "unparsed-claim-like-line" in kinds
    assert "multi-line-label-parse-failure" in kinds
    assert "orphan-label" in kinds
    assert "duplicate-item-id" in kinds
    assert "mr-macro-arity-mismatch" in kinds


def test_tex_extractors_cover_json_and_mr_edges() -> None:
    assert ExtractedFile(name="notes.txt", text="plain").json_data() is None
    try:
        ExtractedFile(name="bad.json", text="[1, 2]").json_data()
    except ValueError as exc:
        assert "does not contain a JSON object" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("non-object JSON must fail")

    source = r"""
\MRRecord{metadata}{m1}{kind=demo;tags=a,b}
\MRClaim{claim:a}{guarantee=G;inputs=x,y;proof=p}
\MRWitness{wit:a}{value=1}
\MRDepends{claim:a}{claim:b,claim:c}
\MRCitation{cite:a}{10.0000/example}{Example source}
"""
    records = extract_mr_records(source)
    assert [record.record_type for record in records] == [
        "metadata",
        "claim",
        "witness",
        "depends",
        "citation",
    ]
    registry = registry_from_mr_records("bit.tex", records)
    assert registry is not None
    claim = registry.claims[0]
    assert claim.dependency_labels == ["claim:b", "claim:c"]
    assert claim.citation_keys == ["cite:a"]
    assert "inputs" in claim.ledger_coordinates

    depends_as_string = MRRecord(
        record_type="depends",
        identifier="claim:a",
        fields={"depends_on": "claim:d"},
        raw="",
        line_number=1,
    )
    string_registry = registry_from_mr_records(
        "bit.tex",
        [records[1], depends_as_string],
    )
    assert string_registry is not None
    assert string_registry.claims[0].dependency_labels == ["claim:d"]
    assert registry_from_mr_records("empty.tex", [depends_as_string]) is None
    assert registry_from_json_block("data.json", {"metadata": True}) is None


def test_domain_adapters_negative_and_success_paths() -> None:
    numerical = verify_ecpt_numerical_envelope(
        residual=2.0,
        residual_bound=1.0,
        finite_horizon=-1,
    )
    assert not numerical.accepted
    assert numerical.residual_ledger.value("ecpt:numerical-envelope:gap") == 1.0

    generator = verify_ecpt_generator_limit(
        observed_generation=5.0,
        certified_limit=3.0,
        residual_allowance=0.5,
    )
    assert not generator.accepted
    assert generator.residual_ledger.value("ecpt:generator-limit:excess") == 1.5

    telemetry_mismatch = verify_trc_telemetry_calibration(
        [1.0],
        [1.0, 2.0],
        tolerance=-1.0,
    )
    assert not telemetry_mismatch.accepted
    assert "telemetry samples and references must have equal length" in telemetry_mismatch.reasons

    telemetry_gap = verify_trc_telemetry_calibration([1.0], [2.0], tolerance=0.1)
    assert not telemetry_gap.accepted
    assert telemetry_gap.residual_ledger.value("trc:telemetry-calibration:error-gap") == 0.9

    assert replay_trc_physical_trace(["a"], ["a", "b"], allow_prefix=True).accepted
    replay_failed = replay_trc_physical_trace(["a"], [], allow_prefix=False)
    assert not replay_failed.accepted
    assert "expected physical trace is empty" in replay_failed.reasons

    archive = verify_archive_domain_evidence({"r1": "outside"}, {"inside"})
    assert not archive.accepted
    assert archive.residual_ledger.value("trc:archive-domain:r1") == 1.0


def test_sinkhorn_transport_adapter_returns_plan() -> None:
    plan = sinkhorn_transport(
        [0.5, 0.5],
        [0.5, 0.5],
        [[0.0, 1.0], [1.0, 0.0]],
        regularization=1.0,
    )
    assert len(plan) == 2
    assert len(plan[0]) == 2
    assert abs(sum(sum(row) for row in plan) - 1.0) < 1e-6


def test_record_coercion_and_certificate_projection() -> None:
    claim = ClaimRecord.from_raw(
        {
            "id": "claim:a",
            "kind": "theorem",
            "label": "A",
            "status": "invalid-status",
            "derived_status": "settled",
            "status_outputs": ["settled", "bad"],
            "dependency_labels": "dep:a",
            "ledger_coordinates": ("l1", "l2"),
            "citation_keys": {"cite:a"},
            "domain": {"identifier": "domain:a"},
        },
        artifact="artifact",
    )
    assert claim.declared_status is None
    assert claim.derived_status == ClaimStatus.SETTLED
    assert claim.status_outputs == [ClaimStatus.SETTLED]
    assert claim.dependency_labels == ["dep:a"]
    assert sorted(claim.ledger_coordinates) == ["l1", "l2"]
    assert claim.domain is not None
    assert claim.domain.identifier == "domain:a"

    string_domain = ClaimRecord.from_raw(
        {"claim_id": "claim:b", "label": "B", "domain": "domain:b"}
    )
    assert string_domain.domain is not None
    assert string_domain.domain.identifier == "domain:b"
    settled_claim = string_domain.with_derived_status(ClaimStatus.SETTLED)
    assert settled_claim.status == ClaimStatus.SETTLED

    certificate = Certificate(
        certificate_id="certificate",
        claims=[claim],
        present_obligations={"dep:a"},
    )
    accepted = certificate.check_registry_projection(Registry(claims=[claim], artifact="artifact"))
    assert accepted.accepted
    missing = certificate.check_registry_projection(
        Registry(
            claims=[claim.model_copy(update={"claim_id": "claim:missing"})],
            artifact="artifact",
        )
    )
    assert not missing.accepted
    assert "claim:missing" in missing.missing_obligations


def test_schema_and_evidence_policy_error_paths(tmp_path: Path) -> None:
    try:
        schema_by_type("NoSuchSchema")
    except ValueError as exc:
        assert "unknown schema type" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("unknown schema type must fail")

    errors = validate_data({"claims": "not-a-list"})
    assert errors

    try:
        evidence_policy("unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("unknown evidence profile must fail")

    artifact = EvidenceArtifact(
        artifact_id="attested",
        evidence_kind="finite-telemetry-calibration",
        sha256="a" * 64,
        media_type="application/json",
        schema_uri="https://example.invalid/schema",
        schema_sha256="b" * 64,
        producer_id="producer",
        produced_at="2026-06-06T00:00:00Z",
        verifier_id="verifier",
        verifier_version="0.2.2",
        attestation_ref="gh-attestation://example",
        attestation_verified=True,
    )
    assert artifact.has_replayable_content_or_verified_attestation()
    assert artifact.content_hash_matches(base_dir=tmp_path)

    missing_content = artifact.model_copy(update={"content_ref": "missing.json"})
    assert not missing_content.content_hash_matches(base_dir=tmp_path)
