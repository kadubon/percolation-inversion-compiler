"""Portable external-verifier adapter route contracts."""

from __future__ import annotations

import hashlib
import re
from importlib.util import find_spec
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus


class AdapterRouteSpec(BaseModel):
    """Language-neutral adapter boundary for an external proof obligation."""

    route_id: str
    verifier_route: str
    obligation_category: str
    availability: str = "unavailable"
    optional_dependency: str | None = None
    license_note: str | None = None
    required_evidence_kind: list[str] = Field(default_factory=list)
    residual_policy: str
    safe_default: str
    status_non_promotion_rule: str = (
        "adapter output may discharge listed obligations but cannot bypass checker-derived status"
    )
    notes: list[str] = Field(default_factory=list)


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class EvidenceArtifact(BaseModel):
    """Replayable evidence metadata for an external verifier route."""

    artifact_id: str
    evidence_kind: str
    sha256: str
    media_type: str
    schema_uri: str
    schema_sha256: str
    producer_id: str
    produced_at: str
    verifier_id: str
    verifier_version: str
    content_ref: str | None = None
    signature: str | None = None
    signature_algorithm: str | None = None
    attestation_ref: str | None = None

    @field_validator("sha256", "schema_sha256")
    @classmethod
    def valid_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("sha256 digests must be 64 hexadecimal characters")
        return value.lower()

    def content_hash_matches(self, *, base_dir: Path | None = None) -> bool:
        if self.content_ref is None:
            return True
        path = Path(self.content_ref)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        if not path.exists() or not path.is_file():
            return False
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == self.sha256


class VerifierEvidenceEnvelope(BaseModel):
    """Finite evidence envelope supplied to an adapter route."""

    envelope_id: str
    route_id: str
    obligation_ids: list[str] = Field(default_factory=list)
    evidence_kind: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_artifacts: list[EvidenceArtifact] = Field(default_factory=list)
    residual_coordinates: dict[str, float] = Field(default_factory=dict)
    deterministic: bool = True
    envelope_schema_version: str = "verifier-evidence-envelope-2.0"


class VerifierResolution(BaseModel):
    """Adapter-route resolution result that preserves safe failure behavior."""

    route_id: str
    accepted: bool
    status: ClaimStatus
    availability: str
    accepted_obligation_ids: list[str] = Field(default_factory=list)
    rejected_obligation_ids: list[str] = Field(default_factory=list)
    missing_evidence_kind: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    safe_default: str = "diagnostic-with-unresolved-obligations"

    def to_check_result(self) -> CheckResult:
        return CheckResult(
            accepted=self.accepted,
            status=self.status,
            reasons=self.reasons,
            missing_obligations=self.missing_evidence_kind,
            residual_ledger=self.residual_ledger,
        )


_OPTIONAL_ROUTE_SPECS: tuple[AdapterRouteSpec, ...] = (
    AdapterRouteSpec(
        route_id="adapters.graphs.shortest_path_lengths",
        verifier_route="percolation_inversion_compiler.adapters.graphs.shortest_path_lengths",
        obligation_category="finite-graph-adapter",
        availability="optional",
        optional_dependency="networkx",
        license_note="NetworkX BSD-3-Clause",
        required_evidence_kind=["finite-edge-list"],
        residual_policy="no-external-residual-when-finite-graph-input-is-validated",
        safe_default="diagnostic-with-missing-networkx",
    ),
    AdapterRouteSpec(
        route_id="adapters.units.assert_compatible_units",
        verifier_route="percolation_inversion_compiler.adapters.units.assert_compatible_units",
        obligation_category="unit-validation-adapter",
        availability="optional",
        optional_dependency="pint",
        license_note="Pint BSD-3-Clause",
        required_evidence_kind=["unit-tags"],
        residual_policy="charge-unit-ledger-until-compatible-units-are-validated",
        safe_default="diagnostic-with-missing-pint",
    ),
    AdapterRouteSpec(
        route_id="adapters.transport.sinkhorn_transport",
        verifier_route="percolation_inversion_compiler.adapters.transport.sinkhorn_transport",
        obligation_category="transport-adapter",
        availability="optional",
        optional_dependency="ot",
        license_note="POT MIT",
        required_evidence_kind=["finite-marginals", "finite-cost-matrix"],
        residual_policy="charge-sinkhorn-residual-until-plan-gap-is-certified",
        safe_default="diagnostic-with-missing-pot",
    ),
    AdapterRouteSpec(
        route_id="adapters.optimization.solve_linear_release",
        verifier_route="percolation_inversion_compiler.adapters.optimization.solve_linear_release",
        obligation_category="linear-optimization-adapter",
        availability="implemented",
        optional_dependency=None,
        license_note="core deterministic implementation, Apache-2.0",
        required_evidence_kind=["bounded-linear-release-program"],
        residual_policy="no-external-residual-for-validated-bounded-separable-lp",
        safe_default="diagnostic-with-invalid-linear-program",
    ),
)


def _implemented_domain_route_specs() -> tuple[AdapterRouteSpec, ...]:
    return (
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_numerical_envelope",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_numerical_envelope"
            ),
            obligation_category="numerical-envelope",
            availability="implemented",
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-numerical-envelope"],
            residual_policy="charge-numerical-residual-until-envelope-bound-is-certified",
            safe_default="diagnostic-with-numerical-envelope-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_generator_limit",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_generator_limit"
            ),
            obligation_category="generator-limit",
            availability="implemented",
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-generator-limit"],
            residual_policy="charge-generator-residual-until-limit-certificate-is-validated",
            safe_default="diagnostic-with-generator-limit-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_trc_telemetry_calibration",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_trc_telemetry_calibration"
            ),
            obligation_category="telemetry-calibration",
            availability="implemented",
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-telemetry-calibration"],
            residual_policy="charge-telemetry-residual-until-calibration-error-is-bounded",
            safe_default="diagnostic-with-telemetry-calibration-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.replay_trc_physical_trace",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.replay_trc_physical_trace"
            ),
            obligation_category="physical-trace-replay",
            availability="implemented",
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-physical-trace"],
            residual_policy="charge-physical-residual-until-replay-matches-transition-log",
            safe_default="diagnostic-with-physical-trace-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_archive_domain_evidence",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_archive_domain_evidence"
            ),
            obligation_category="archive-domain-evidence",
            availability="implemented",
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-archive-domain"],
            residual_policy="charge-archive-domain-residual-until-domain-membership-is-checked",
            safe_default="diagnostic-with-archive-domain-obligation",
        ),
    )


def route_specs_from_external_metadata() -> dict[str, AdapterRouteSpec]:
    """Build route specs from coverage metadata without importing adapter code."""

    from percolation_inversion_compiler.core.coverage import external_route_specs_data

    specs: dict[str, AdapterRouteSpec] = {}
    for data in external_route_specs_data():
        spec = AdapterRouteSpec.model_validate(data)
        specs[spec.route_id] = spec
    for spec in _OPTIONAL_ROUTE_SPECS:
        specs[spec.route_id] = spec
    for spec in _implemented_domain_route_specs():
        specs[spec.route_id] = spec
    return dict(sorted(specs.items()))


def list_adapter_route_specs() -> list[AdapterRouteSpec]:
    return list(route_specs_from_external_metadata().values())


def resolve_adapter_route(
    spec: AdapterRouteSpec,
    evidence: VerifierEvidenceEnvelope,
    *,
    base_dir: Path | None = None,
) -> VerifierResolution:
    """Resolve an adapter route conservatively without promoting external claims."""

    residual = Ledger()
    for name, value in evidence.residual_coordinates.items():
        residual = residual.add_coordinate(
            f"adapter-route:{name}",
            value,
            kind=CoordinateKind.RESIDUAL,
        )
    missing = sorted(set(spec.required_evidence_kind) - set(evidence.evidence_kind))
    reasons: list[str] = []
    if spec.route_id != evidence.route_id:
        reasons.append("evidence envelope route_id does not match adapter route")
    if spec.availability == "unavailable":
        reasons.append("adapter route is declared unavailable")
    if spec.optional_dependency and find_spec(spec.optional_dependency) is None:
        reasons.append(f"optional dependency {spec.optional_dependency!r} is not installed")
    if missing:
        reasons.append("required evidence kind is missing")
    if not evidence.evidence_artifacts:
        reasons.append("evidence artifacts are missing")
    artifact_kinds = {artifact.evidence_kind for artifact in evidence.evidence_artifacts}
    missing_artifact_kinds = sorted(set(spec.required_evidence_kind) - artifact_kinds)
    if evidence.evidence_artifacts and missing_artifact_kinds:
        reasons.append("required evidence artifact kind is missing")
        missing.extend(missing_artifact_kinds)
    for artifact in evidence.evidence_artifacts:
        if not artifact.producer_id:
            reasons.append("evidence artifact producer_id is missing")
        if not artifact.verifier_id:
            reasons.append("evidence artifact verifier_id is missing")
        if not artifact.verifier_version:
            reasons.append("evidence artifact verifier_version is missing")
        if not artifact.content_hash_matches(base_dir=base_dir):
            reasons.append(f"evidence artifact {artifact.artifact_id!r} sha256 mismatch")
    accepted = not reasons and evidence.deterministic
    if not evidence.deterministic:
        reasons.append("evidence envelope is not deterministic")
    return VerifierResolution(
        route_id=spec.route_id,
        accepted=accepted,
        status=ClaimStatus.SETTLED if accepted else ClaimStatus.DIAGNOSTIC,
        availability=spec.availability,
        accepted_obligation_ids=evidence.obligation_ids if accepted else [],
        rejected_obligation_ids=[] if accepted else evidence.obligation_ids,
        missing_evidence_kind=missing,
        reasons=sorted(set(reasons)),
        residual_ledger=residual,
        safe_default=spec.safe_default,
    )
