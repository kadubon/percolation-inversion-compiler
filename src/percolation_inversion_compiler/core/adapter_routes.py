"""Portable external-verifier adapter route contracts."""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.core.records import CheckResult
from percolation_inversion_compiler.core.status import ClaimStatus

if TYPE_CHECKING:
    from percolation_inversion_compiler.core.records import ExternalVerifierHook


class EvidenceVerificationProfile(StrEnum):
    DEVELOPMENT = "development"
    RESEARCH = "research"
    PRODUCTION = "production"


class DischargeLevel(StrEnum):
    FINITE_VALUE_CHECK = "finite_value_check"
    REPLAY_CHECK = "replay_check"
    CONTRACT_ENFORCED = "contract_enforced"
    EXTERNAL_DOMAIN_REQUIRED = "external_domain_required"


class EvidencePolicy(BaseModel):
    """Profile-specific evidence hardening policy for verifier envelopes."""

    profile: EvidenceVerificationProfile = EvidenceVerificationProfile.DEVELOPMENT
    require_content_ref: bool = False
    require_signature: bool = False
    require_attestation_ref: bool = False
    allow_verified_attestation_without_content: bool = False
    require_schema_digest: bool = True
    require_verifier_identity: bool = True
    require_deterministic: bool = True


class EvidenceVerificationProfileRecord(BaseModel):
    """Portable profile record for JSON Schema consumers."""

    profile: EvidenceVerificationProfile
    policy: EvidencePolicy


def evidence_policy(profile: str | EvidenceVerificationProfile = "development") -> EvidencePolicy:
    """Return the fail-closed evidence policy for a named execution profile."""

    normalized = EvidenceVerificationProfile(str(profile).lower())
    if normalized == EvidenceVerificationProfile.PRODUCTION:
        return EvidencePolicy(
            profile=normalized,
            require_content_ref=True,
            require_signature=False,
            require_attestation_ref=False,
            allow_verified_attestation_without_content=False,
        )
    if normalized == EvidenceVerificationProfile.RESEARCH:
        return EvidencePolicy(
            profile=normalized,
            require_content_ref=False,
            require_signature=False,
            require_attestation_ref=False,
        )
    return EvidencePolicy(profile=normalized)


class AdapterRouteSpec(BaseModel):
    """Language-neutral adapter boundary for an external proof obligation."""

    route_id: str
    verifier_route: str
    obligation_category: str
    availability: str = "contract"
    discharge_level: DischargeLevel = DischargeLevel.EXTERNAL_DOMAIN_REQUIRED
    canonical_route_id: str | None = None
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
    attestation_verified: bool = False

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

    def has_replayable_content_or_verified_attestation(self) -> bool:
        return self.content_ref is not None or (
            self.attestation_ref is not None and self.attestation_verified
        )


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

    resolution_id: str
    route_id: str
    accepted: bool
    status: ClaimStatus
    availability: str
    profile: EvidenceVerificationProfile = EvidenceVerificationProfile.DEVELOPMENT
    discharge_level: DischargeLevel = DischargeLevel.EXTERNAL_DOMAIN_REQUIRED
    binding_id: str | None = None
    evidence_envelope_id: str | None = None
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    resolution_digest: str
    settled_scope: list[str] = Field(default_factory=list)
    finite_scope_usable: bool = False
    residual_external_obligations: list[str] = Field(default_factory=list)
    domain_witness_required: bool = False
    operationally_usable: bool = False
    settled: bool = False
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
            finite_checks_passed=self.accepted,
            operationally_usable=self.operationally_usable,
            settled=self.settled,
            reasons=self.reasons,
            missing_obligations=self.missing_evidence_kind,
            residual_ledger=self.residual_ledger,
        )

    def to_external_verifier_hook(self) -> ExternalVerifierHook:
        from percolation_inversion_compiler.core.records import ExternalVerifierHook

        return ExternalVerifierHook(
            hook_id=f"hook:{self.resolution_id}",
            verifier_route=self.route_id,
            obligation_ids=set(self.accepted_obligation_ids + self.rejected_obligation_ids),
            accepted_obligation_ids=set(self.accepted_obligation_ids if self.settled else []),
            rejected_obligation_ids=set(self.rejected_obligation_ids if not self.settled else []),
            residual_policy=self.safe_default,
            safe_default=self.safe_default,
            settled_scope=self.settled_scope,
            residual_external_obligations=set(self.residual_external_obligations),
            domain_witness_required=self.domain_witness_required,
            resolution_id=self.resolution_id,
            resolution_digest=self.resolution_digest,
            evidence_envelope_id=self.evidence_envelope_id,
            evidence_artifact_ids=set(self.evidence_artifact_ids),
            provenance_policy=f"evidence-policy:{self.profile.value}",
            deterministic=True,
        )


class DischargeRouteBinding(BaseModel):
    """Reviewed binding from a canonical external route to an implementation route."""

    binding_id: str
    canonical_route_id: str
    implemented_route_id: str
    canonical_verifier_route: str
    implemented_verifier_route: str
    obligation_category: str
    discharge_level: DischargeLevel
    settlement_scope: list[str] = Field(default_factory=list)
    evidence_kind_map: dict[str, str] = Field(default_factory=dict)
    unresolved_domain_obligations: list[str] = Field(default_factory=list)
    residual_external_obligation_refs: list[str] = Field(default_factory=list)
    residual_policy: str
    safe_default: str


_OPTIONAL_ROUTE_SPECS: tuple[AdapterRouteSpec, ...] = (
    AdapterRouteSpec(
        route_id="adapters.graphs.shortest_path_lengths",
        verifier_route="percolation_inversion_compiler.adapters.graphs.shortest_path_lengths",
        obligation_category="finite-graph-adapter",
        availability="optional",
        discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
        discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
        discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
        discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
            discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
            discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-generator-limit"],
            residual_policy="charge-generator-residual-until-limit-certificate-is-validated",
            safe_default="diagnostic-with-generator-limit-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_bridge_reserve",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_bridge_reserve"
            ),
            obligation_category="ecpt-bridge-reserve",
            availability="implemented",
            discharge_level=DischargeLevel.CONTRACT_ENFORCED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-bridge-reserve"],
            residual_policy="charge-cross-theory-residual-until-bridge-relations-are-validated",
            safe_default="diagnostic-with-bridge-reserve-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_trace_diagnostic_projection",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain."
                "verify_ecpt_trace_diagnostic_projection"
            ),
            obligation_category="ecpt-trace-diagnostic",
            availability="implemented",
            discharge_level=DischargeLevel.CONTRACT_ENFORCED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-trace-diagnostic-projection"],
            residual_policy="charge-trace-complex-residual-until-projection-is-validated",
            safe_default="diagnostic-with-trace-diagnostic-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_domain_abstraction",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_domain_abstraction"
            ),
            obligation_category="ecpt-ecology-ontology",
            availability="implemented",
            discharge_level=DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-domain-abstraction"],
            residual_policy="charge-ontology-residual-until-domain-abstraction-is-validated",
            safe_default="diagnostic-with-ecology-ontology-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_execution_policy",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_execution_policy"
            ),
            obligation_category="ecpt-economics-policy",
            availability="implemented",
            discharge_level=DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-execution-policy-envelope"],
            residual_policy="charge-policy-residual-until-counterfactual-envelope-is-validated",
            safe_default="diagnostic-with-economics-policy-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_proxy_target_contract",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_ecpt_proxy_target_contract"
            ),
            obligation_category="ecpt-proxy-target",
            availability="implemented",
            discharge_level=DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-proxy-target-contract"],
            residual_policy="charge-proxy-grounding-residual-until-target-contract-is-validated",
            safe_default="diagnostic-with-proxy-target-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_ecpt_speculative_channel_repair",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain."
                "verify_ecpt_speculative_channel_repair"
            ),
            obligation_category="ecpt-speculative-channel",
            availability="implemented",
            discharge_level=DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-speculative-channel-repair"],
            residual_policy="charge-speculative-channel-residual-until-repair-envelope-is-validated",
            safe_default="diagnostic-with-speculative-channel-obligation",
        ),
        AdapterRouteSpec(
            route_id="adapters.domain.verify_trc_telemetry_calibration",
            verifier_route=(
                "percolation_inversion_compiler.adapters.domain.verify_trc_telemetry_calibration"
            ),
            obligation_category="telemetry-calibration",
            availability="implemented",
            discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
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
            discharge_level=DischargeLevel.REPLAY_CHECK,
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
            discharge_level=DischargeLevel.FINITE_VALUE_CHECK,
            license_note="core deterministic implementation, Apache-2.0",
            required_evidence_kind=["finite-archive-domain"],
            residual_policy="charge-archive-domain-residual-until-domain-membership-is-checked",
            safe_default="diagnostic-with-archive-domain-obligation",
        ),
    )


_CATEGORY_IMPLEMENTATION_BINDINGS: dict[str, tuple[str, DischargeLevel, tuple[str, ...]]] = {
    "numerical-envelope": (
        "adapters.domain.verify_ecpt_numerical_envelope",
        DischargeLevel.FINITE_VALUE_CHECK,
        (),
    ),
    "ecpt-generator-limit": (
        "adapters.domain.verify_ecpt_generator_limit",
        DischargeLevel.FINITE_VALUE_CHECK,
        (),
    ),
    "telemetry-calibration": (
        "adapters.domain.verify_trc_telemetry_calibration",
        DischargeLevel.FINITE_VALUE_CHECK,
        (),
    ),
    "physical-hybrid-system": (
        "adapters.domain.replay_trc_physical_trace",
        DischargeLevel.REPLAY_CHECK,
        ("continuous-physics-envelope", "resource-calendar-domain-witness"),
    ),
    "archive-domain-cover": (
        "adapters.domain.verify_archive_domain_evidence",
        DischargeLevel.FINITE_VALUE_CHECK,
        (),
    ),
    "observation-partition": (
        "trc.adapters.observation.verify_partition_cover",
        DischargeLevel.CONTRACT_ENFORCED,
        ("partition-cover-domain-proof",),
    ),
    "distributionally-robust-metric": (
        "trc.adapters.metric.verify_distributionally_robust_dual",
        DischargeLevel.CONTRACT_ENFORCED,
        ("dual-risk-domain-witness",),
    ),
    "assume-guarantee-contract": (
        "trc.adapters.contracts.verify_assume_guarantee_library",
        DischargeLevel.CONTRACT_ENFORCED,
        ("contract-library-domain-witness",),
    ),
    "latent-oracle-model": (
        "trc.adapters.latent_oracle.verify_model_witness",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("oracle-witness", "latent-model-replay"),
    ),
    "redesign-response": (
        "trc.adapters.redesign.verify_response_interval",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("redesign-domain-oracle",),
    ),
    "ecpt-trace-diagnostic": (
        "adapters.domain.verify_ecpt_trace_diagnostic_projection",
        DischargeLevel.CONTRACT_ENFORCED,
        ("trace-complex-domain-witness",),
    ),
    "ecpt-bridge-reserve": (
        "adapters.domain.verify_ecpt_bridge_reserve",
        DischargeLevel.CONTRACT_ENFORCED,
        ("cross-theory-bridge-proof",),
    ),
    "ecpt-ecology-ontology": (
        "adapters.domain.verify_ecpt_domain_abstraction",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("ontology-extension-domain-proof",),
    ),
    "ecpt-economics-policy": (
        "adapters.domain.verify_ecpt_execution_policy",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("policy-counterfactual-domain-proof",),
    ),
    "ecpt-proxy-target": (
        "adapters.domain.verify_ecpt_proxy_target_contract",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("proxy-target-grounding-proof",),
    ),
    "ecpt-speculative-channel": (
        "adapters.domain.verify_ecpt_speculative_channel_repair",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED,
        ("speculative-channel-repair-proof",),
    ),
}


def _binding_for_contract_spec(
    spec: AdapterRouteSpec,
    specs: dict[str, AdapterRouteSpec],
) -> DischargeRouteBinding:
    implemented_route_id, discharge_level, unresolved = _CATEGORY_IMPLEMENTATION_BINDINGS.get(
        spec.obligation_category,
        (spec.route_id, DischargeLevel.EXTERNAL_DOMAIN_REQUIRED, ("domain-specific-proof",)),
    )
    implemented = specs.get(implemented_route_id, spec)
    evidence_kind_map = {
        kind: implemented.required_evidence_kind[index]
        if index < len(implemented.required_evidence_kind)
        else kind
        for index, kind in enumerate(spec.required_evidence_kind)
    }
    scope_prefix = {
        DischargeLevel.FINITE_VALUE_CHECK: "finite-value",
        DischargeLevel.REPLAY_CHECK: "finite-replay",
        DischargeLevel.CONTRACT_ENFORCED: "contract-envelope",
        DischargeLevel.EXTERNAL_DOMAIN_REQUIRED: "routing-contract",
    }[discharge_level]
    settlement_scope = [f"{scope_prefix}:{implemented_route_id}"]
    return DischargeRouteBinding(
        binding_id=f"binding:{spec.route_id}->{implemented_route_id}",
        canonical_route_id=spec.route_id,
        implemented_route_id=implemented_route_id,
        canonical_verifier_route=spec.verifier_route,
        implemented_verifier_route=implemented.verifier_route,
        obligation_category=spec.obligation_category,
        discharge_level=discharge_level,
        settlement_scope=settlement_scope,
        evidence_kind_map=evidence_kind_map,
        unresolved_domain_obligations=sorted(unresolved),
        residual_external_obligation_refs=sorted(unresolved),
        residual_policy=spec.residual_policy,
        safe_default=spec.safe_default,
    )


def route_specs_from_external_metadata() -> dict[str, AdapterRouteSpec]:
    """Build route specs from coverage metadata without importing adapter code."""

    from percolation_inversion_compiler.core.coverage import external_route_specs_data

    specs: dict[str, AdapterRouteSpec] = {}
    for data in external_route_specs_data():
        spec = AdapterRouteSpec.model_validate(data)
        if spec.availability == "unavailable":
            spec = spec.model_copy(
                update={
                    "availability": "contract",
                    "canonical_route_id": spec.route_id,
                    "discharge_level": DischargeLevel.CONTRACT_ENFORCED,
                }
            )
        specs[spec.route_id] = spec
    for spec in _OPTIONAL_ROUTE_SPECS:
        specs[spec.route_id] = spec
    for spec in _implemented_domain_route_specs():
        specs[spec.route_id] = spec
    return dict(sorted(specs.items()))


def list_adapter_route_specs() -> list[AdapterRouteSpec]:
    return list(route_specs_from_external_metadata().values())


def list_discharge_route_bindings() -> list[DischargeRouteBinding]:
    specs = route_specs_from_external_metadata()
    bindings = [
        _binding_for_contract_spec(spec, specs)
        for spec in specs.values()
        if spec.canonical_route_id == spec.route_id and spec.availability == "contract"
    ]
    return sorted(bindings, key=lambda binding: binding.binding_id)


def binding_for_route(route_id: str) -> DischargeRouteBinding | None:
    for binding in list_discharge_route_bindings():
        if binding.canonical_route_id == route_id or binding.implemented_route_id == route_id:
            return binding
    return None


def _resolution_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def resolve_adapter_route(
    spec: AdapterRouteSpec,
    evidence: VerifierEvidenceEnvelope,
    *,
    base_dir: Path | None = None,
    profile: str | EvidenceVerificationProfile = EvidenceVerificationProfile.DEVELOPMENT,
    policy: EvidencePolicy | None = None,
    binding: DischargeRouteBinding | None = None,
) -> VerifierResolution:
    """Resolve an adapter route conservatively without promoting external claims."""

    active_policy = policy or evidence_policy(profile)
    active_binding = binding or binding_for_route(spec.route_id)
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
        if (
            active_policy.require_content_ref
            and not artifact.has_replayable_content_or_verified_attestation()
        ):
            reasons.append(
                "production evidence requires content_ref with matching sha256 "
                "or verified attestation"
            )
        if active_policy.require_signature and not artifact.signature:
            reasons.append("evidence artifact signature is missing")
        if active_policy.require_attestation_ref and not artifact.attestation_ref:
            reasons.append("evidence artifact attestation_ref is missing")
        if not artifact.producer_id:
            reasons.append("evidence artifact producer_id is missing")
        if not artifact.verifier_id:
            reasons.append("evidence artifact verifier_id is missing")
        if not artifact.verifier_version:
            reasons.append("evidence artifact verifier_version is missing")
        if not artifact.content_hash_matches(base_dir=base_dir):
            reasons.append(f"evidence artifact {artifact.artifact_id!r} sha256 mismatch")
    accepted = not reasons and (evidence.deterministic or not active_policy.require_deterministic)
    if not evidence.deterministic:
        reasons.append("evidence envelope is not deterministic")
    discharge_level = (
        active_binding.discharge_level if active_binding is not None else spec.discharge_level
    )
    residual_external_obligations = (
        active_binding.residual_external_obligation_refs if active_binding is not None else []
    )
    if (
        discharge_level == DischargeLevel.EXTERNAL_DOMAIN_REQUIRED
        and not residual_external_obligations
    ):
        residual_external_obligations = ["external-domain-witness"]
    settled_scope = (
        active_binding.settlement_scope
        if active_binding is not None
        else [f"{discharge_level.value}:{spec.route_id}"]
    )
    finite_scope_usable = accepted and bool(settled_scope)
    domain_witness_required = bool(residual_external_obligations) or (
        discharge_level == DischargeLevel.EXTERNAL_DOMAIN_REQUIRED
    )
    settled = accepted and not domain_witness_required
    accepted_obligation_ids = evidence.obligation_ids if settled else []
    rejected_obligation_ids = [] if settled else evidence.obligation_ids
    resolution_payload = {
        "accepted": accepted,
        "accepted_obligation_ids": accepted_obligation_ids,
        "artifact_ids": [artifact.artifact_id for artifact in evidence.evidence_artifacts],
        "binding_id": None if active_binding is None else active_binding.binding_id,
        "domain_witness_required": domain_witness_required,
        "discharge_level": discharge_level.value,
        "envelope_id": evidence.envelope_id,
        "finite_scope_usable": finite_scope_usable,
        "profile": active_policy.profile.value,
        "reasons": sorted(set(reasons)),
        "rejected_obligation_ids": rejected_obligation_ids,
        "residual_external_obligations": residual_external_obligations,
        "route_id": spec.route_id,
        "settled_scope": settled_scope if accepted else [],
        "settled": settled,
    }
    digest = _resolution_digest(resolution_payload)
    return VerifierResolution(
        resolution_id=f"resolution:{digest[:16]}",
        route_id=spec.route_id,
        accepted=accepted,
        status=ClaimStatus.SETTLED
        if settled
        else ClaimStatus.PROVISIONAL
        if accepted
        else ClaimStatus.DIAGNOSTIC,
        availability=spec.availability,
        profile=active_policy.profile,
        discharge_level=discharge_level,
        binding_id=None if active_binding is None else active_binding.binding_id,
        evidence_envelope_id=evidence.envelope_id,
        evidence_artifact_ids=[artifact.artifact_id for artifact in evidence.evidence_artifacts],
        resolution_digest=digest,
        settled_scope=settled_scope if accepted else [],
        finite_scope_usable=finite_scope_usable,
        residual_external_obligations=residual_external_obligations,
        domain_witness_required=domain_witness_required,
        operationally_usable=settled,
        settled=settled,
        accepted_obligation_ids=accepted_obligation_ids,
        rejected_obligation_ids=rejected_obligation_ids,
        missing_evidence_kind=missing,
        reasons=sorted(set(reasons)),
        residual_ledger=residual,
        safe_default=spec.safe_default,
    )
