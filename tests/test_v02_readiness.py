from __future__ import annotations

import hashlib

import pytest

from percolation_inversion_compiler.core.adapter_routes import (
    EvidenceArtifact,
    VerifierEvidenceEnvelope,
    list_adapter_route_specs,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.algorithms import (
    empirical_bernstein_radius,
    expected_value,
    finite_difference_interval,
    gibbs_distribution,
    split_lower_confidence_bound,
    trapezoid_integral,
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
from percolation_inversion_compiler.io.doctor import (
    build_operational_readiness_report,
    readiness_profile,
)
from percolation_inversion_compiler.io.zenodo import (
    CANONICAL_RECORDS,
    canonical_manifest,
    sha256_file,
    validate_canonical_source,
)


def test_v02_calibration_certificate_success_and_residuals() -> None:
    certificate = CalibrationCertificate(
        split=SplitCertificate(
            certificate_id="split",
            train_size=10,
            holdout_size=5,
            selected_on_train=True,
            checked_on_holdout=True,
            selection_residual=0.1,
        ),
        dkw=DKWCertificate(sample_size=20, alpha=0.05),
        good_turing=GoodTuringCertificate(species_counts=[1, 1, 2]),
        e_process=EProcessCertificate(e_values=[1.0, 20.0], alpha=0.1),
        martingale=MartingaleBlockResidual(
            block_bounds=[0.1, 0.2],
            quadratic_variation=0.5,
            alpha=0.1,
            drift_charge=0.01,
        ),
        confidence=ConfidenceLedger(
            alpha=0.05,
            sample_size=20,
            residual_coordinates={"confidence:tail": 0.2},
        ),
    )
    result = certificate.check()
    assert result.accepted
    assert result.settled
    assert result.residual_ledger.value("confidence:tail") == 0.2
    assert result.residual_ledger.burden_sum() > 0.0


def test_v02_calibration_certificate_fail_closed_cases() -> None:
    empty = CalibrationCertificate().check()
    assert not empty.accepted
    assert "calibration:component" in empty.missing_obligations

    split = SplitCertificate(certificate_id="bad", train_size=0, holdout_size=0).check()
    assert not split.accepted
    assert "split:bad" in split.missing_obligations

    dkw = DKWCertificate(sample_size=-1, alpha=2.0, observed_radius=-0.1).check()
    assert not dkw.accepted
    assert dkw.residual_ledger.value("dkw:radius") == 0.0

    gt = GoodTuringCertificate(species_counts=[-1], duplicate_rate=-0.1).check()
    assert not gt.accepted

    e_process = EProcessCertificate(e_values=[1.0], alpha=0.05).check()
    assert not e_process.accepted
    assert "e-process:boundary" in e_process.missing_obligations

    martingale = MartingaleBlockResidual(
        block_bounds=[],
        quadratic_variation=-1.0,
        alpha=2.0,
    ).check()
    assert not martingale.accepted
    assert "martingale:block-certificate" in martingale.missing_obligations


def test_v02_core_algorithm_edges() -> None:
    assert empirical_bernstein_radius([0.0, 1.0, 0.5], 0.05) > 0.0
    assert split_lower_confidence_bound([0.4, 0.6, 0.8], 0.1) >= 0.0
    assert finite_difference_interval(1.0, 1.2, 0.1, residual=0.02) == pytest.approx((1.8, 2.2))
    distribution = gibbs_distribution({"a": 0.0, "b": 1.0}, beta=1.0)
    assert abs(sum(distribution.values()) - 1.0) < 1e-12
    assert expected_value(distribution, lambda state: 1.0 if state == "a" else 0.0) > 0.5
    assert trapezoid_integral([0.0, 1.0, 2.0], [0.0, 1.0, 0.0]) == 1.0

    with pytest.raises(ValueError, match="at least two observations"):
        empirical_bernstein_radius([1.0], 0.05)
    with pytest.raises(ValueError, match="epsilon must be positive"):
        finite_difference_interval(1.0, 2.0, 0.0)
    with pytest.raises(ValueError, match="energies must not be empty"):
        gibbs_distribution({})
    with pytest.raises(ValueError, match="xs and ys must have the same length"):
        trapezoid_integral([0.0], [0.0])
    with pytest.raises(ValueError, match="xs must be sorted"):
        trapezoid_integral([1.0, 0.0], [0.0, 1.0])


def test_v02_doctor_profiles_and_canonical_manifest(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assert readiness_profile("development").profile == "development"
    assert readiness_profile("research").require_security_metadata
    assert readiness_profile("production").require_signed_schema_bundle
    with pytest.raises(ValueError, match="profile must be one of"):
        readiness_profile("invalid")

    monkeypatch.delenv("PIC_CANONICAL_TEX_DIR", raising=False)
    development = build_operational_readiness_report(profile="development")
    assert development.summary["profile"] == "development"
    assert development.overall_status in {"pass", "warn", "fail"}

    production = build_operational_readiness_report(profile="production")
    assert production.overall_status == "fail"
    failed = {check.check_id for check in production.checks if check.status == "fail"}
    assert {"canonical-tex", "schema-provenance"}.issubset(failed)

    manifest = canonical_manifest()
    assert manifest.schema_version == "canonical-manifest-2.0"
    assert set(manifest.records) == set(CANONICAL_RECORDS)
    assert all(record.tex_sha256 for record in manifest.records.values())


def test_v02_zenodo_sha256_validation_is_primary(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "Executable Capability Percolation Theory.tex"
    source.write_text("not the canonical source", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert sha256_file(source) == digest

    result = validate_canonical_source(source, key="ecpt")
    assert result["integrity_algorithm"] == "sha256"
    assert result["actual_sha256"] == digest
    assert not result["matches"]

    with pytest.raises(ValueError, match="no canonical record matches"):
        validate_canonical_source(tmp_path / "unknown.tex")


def test_v02_evidence_route_negative_contracts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    spec = next(
        route
        for route in list_adapter_route_specs()
        if route.route_id == "adapters.domain.verify_ecpt_numerical_envelope"
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text('{"finite": true}', encoding="utf-8")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    artifact = EvidenceArtifact(
        artifact_id="artifact",
        evidence_kind="finite-numerical-envelope",
        sha256=digest,
        media_type="application/json",
        schema_uri="https://example.invalid/schema",
        schema_sha256="0" * 64,
        producer_id="producer",
        produced_at="2026-06-06T00:00:00Z",
        verifier_id="verifier",
        verifier_version="0.2.2",
        content_ref=evidence_path.name,
    )
    accepted = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="ok",
            route_id=spec.route_id,
            obligation_ids=["obligation:numerical"],
            evidence_kind=["finite-numerical-envelope"],
            evidence_artifacts=[artifact],
        ),
        base_dir=tmp_path,
    )
    assert accepted.accepted

    wrong_route = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="wrong-route",
            route_id="other",
            obligation_ids=["obligation:numerical"],
            evidence_kind=["finite-numerical-envelope"],
            evidence_artifacts=[artifact],
        ),
        base_dir=tmp_path,
    )
    assert not wrong_route.accepted
    assert "evidence envelope route_id does not match adapter route" in wrong_route.reasons

    missing_artifact_kind = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="missing-kind",
            route_id=spec.route_id,
            obligation_ids=["obligation:numerical"],
            evidence_kind=["finite-numerical-envelope"],
            evidence_artifacts=[
                artifact.model_copy(update={"evidence_kind": "wrong-kind"}),
            ],
        ),
        base_dir=tmp_path,
    )
    assert not missing_artifact_kind.accepted
    assert "required evidence artifact kind is missing" in missing_artifact_kind.reasons

    nondeterministic = resolve_adapter_route(
        spec,
        VerifierEvidenceEnvelope(
            envelope_id="nondeterministic",
            route_id=spec.route_id,
            obligation_ids=["obligation:numerical"],
            evidence_kind=["finite-numerical-envelope"],
            evidence_artifacts=[artifact],
            deterministic=False,
        ),
        base_dir=tmp_path,
    )
    assert not nondeterministic.accepted
    assert "evidence envelope is not deterministic" in nondeterministic.reasons
