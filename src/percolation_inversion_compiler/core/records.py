"""Pydantic records shared by the finite compiler subsystems."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.graph import DependencyDAG
from percolation_inversion_compiler.core.ledger import Ledger
from percolation_inversion_compiler.core.status import ClaimStatus, StatusDecision, StatusRule


def _coerce_status(value: object) -> ClaimStatus | None:
    if value is None:
        return None
    normalized = str(value).lower().replace(" ", "-")
    try:
        return ClaimStatus(normalized)
    except ValueError:
        return None


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value]
    return [str(value)]


def _coerce_domain(value: object) -> ValidityDomain | None:
    if value is None:
        return None
    if isinstance(value, ValidityDomain):
        return value
    if isinstance(value, dict):
        return ValidityDomain.model_validate(value)
    return ValidityDomain(identifier=str(value))


class ValidityDomain(BaseModel):
    """A declared finite domain for one extracted claim."""

    identifier: str
    observation_window: str | None = None
    receiver_family: str | None = None
    target_basis: str | None = None
    protocol_scope: str | None = None
    notes: list[str] = Field(default_factory=list)


class ClaimRecord(BaseModel):
    """Machine-readable claim projection."""

    claim_id: str
    kind: str
    label: str
    declared_status: ClaimStatus | None = None
    derived_status: ClaimStatus | None = None
    status: ClaimStatus | None = None
    status_outputs: list[ClaimStatus] = Field(default_factory=list)
    dependency_labels: list[str] = Field(default_factory=list)
    ledger_coordinates: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    artifact: str | None = None
    domain: ValidityDomain | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, object], *, artifact: str | None = None) -> ClaimRecord:
        status_outputs: list[ClaimStatus] = []
        for item in _string_list(raw.get("status_outputs")):
            coerced = _coerce_status(item)
            if coerced is not None:
                status_outputs.append(coerced)
        raw_status = raw.get("status")
        derived_status = _coerce_status(raw.get("derived_status"))
        return cls(
            claim_id=str(raw.get("claim_id") or raw.get("id") or raw.get("ClaimID")),
            kind=str(raw.get("kind", "claim")),
            label=str(raw.get("label", raw.get("claim_id", ""))),
            declared_status=_coerce_status(raw_status),
            derived_status=derived_status,
            status=None,
            status_outputs=status_outputs,
            dependency_labels=_string_list(raw.get("dependency_labels")),
            ledger_coordinates=_string_list(raw.get("ledger_coordinates")),
            citation_keys=_string_list(raw.get("citation_keys")),
            artifact=artifact,
            domain=_coerce_domain(raw.get("domain") or raw.get("validity_domain")),
        )

    def with_derived_status(self, status: ClaimStatus) -> ClaimRecord:
        """Return a copy whose checker-derived status is explicit."""

        return self.model_copy(update={"derived_status": status, "status": status})


class ExternalProofObligation(BaseModel):
    """A non-finite or domain-specific proof obligation exposed to callers."""

    obligation_id: str
    description: str
    obligation_category: str | None = None
    verifier_hint: str | None = None
    verifier_contract: dict[str, object] = Field(default_factory=dict)
    accepted_evidence_kind: list[str] = Field(default_factory=list)
    residual_policy: str = "charge-residual-until-verified"
    safe_default: str = "diagnostic-with-proof-obligation"
    residual_charge: Ledger = Field(default_factory=Ledger)
    failure_mode: str = "proof-obligation-unmet"
    failure_modes: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    required_for_status: ClaimStatus = ClaimStatus.SETTLED


class ExternalVerifierHook(BaseModel):
    """Portable result channel for domain-specific obligation verifiers."""

    hook_id: str
    verifier_route: str
    obligation_ids: set[str] = Field(default_factory=set)
    obligation_categories: dict[str, str] = Field(default_factory=dict)
    verifier_contract: dict[str, object] = Field(default_factory=dict)
    accepted_evidence_kind: list[str] = Field(default_factory=list)
    residual_policy: str = "charge-residual-until-verified"
    safe_default: str = "return-diagnostic-with-unresolved-obligations"
    accepted_obligation_ids: set[str] = Field(default_factory=set)
    rejected_obligation_ids: set[str] = Field(default_factory=set)
    failure_modes: dict[str, str] = Field(default_factory=dict)
    residual_coordinates: dict[str, float] = Field(default_factory=dict)
    resolution_id: str | None = None
    resolution_digest: str | None = None
    evidence_envelope_id: str | None = None
    evidence_artifact_ids: set[str] = Field(default_factory=set)
    provenance_policy: str = "legacy-hook-no-resolution-provenance"
    schema_refs: list[str] = Field(default_factory=list)
    deterministic: bool = True
    notes: list[str] = Field(default_factory=list)


class CertificateShell(BaseModel):
    """Finite construction/verification shell for one certificate component."""

    identifier: str
    assert_label: str
    construct_route: str | None = None
    verify_route: str | None = None
    cost: Ledger = Field(default_factory=Ledger)
    fail_policy: str = "diagnostic"
    domain: ValidityDomain | None = None
    expires_at: str | None = None
    status: ClaimStatus = ClaimStatus.SPECULATIVE

    @property
    def has_construction(self) -> bool:
        return bool(self.construct_route)

    @property
    def has_verification(self) -> bool:
        return bool(self.verify_route)


class CheckResult(BaseModel):
    """Result of a finite checker call."""

    accepted: bool
    status: ClaimStatus
    schema_valid: bool = True
    finite_checks_passed: bool | None = None
    operationally_usable: bool | None = None
    settled: bool | None = None
    claims: list[ClaimRecord] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    missing_obligations: list[str] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)

    def model_post_init(self, __context: object) -> None:
        if self.finite_checks_passed is None:
            self.finite_checks_passed = self.accepted
        if self.settled is None:
            self.settled = self.status == ClaimStatus.SETTLED and self.accepted
        if self.operationally_usable is None:
            self.operationally_usable = (
                self.schema_valid
                and bool(self.finite_checks_passed)
                and not self.missing_obligations
                and bool(self.settled)
            )


class Registry(BaseModel):
    """Finite claim registry extracted from a source artifact."""

    schema_version: str = "registry-1.0"
    artifact: str | None = None
    claims: list[ClaimRecord] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)

    def claim_ids(self) -> set[str]:
        return {claim.claim_id for claim in self.claims}

    def require_unique_claim_ids(self) -> None:
        ids = [claim.claim_id for claim in self.claims]
        duplicates = sorted({claim_id for claim_id in ids if ids.count(claim_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate claim ids: {duplicates}")


class Certificate(BaseModel):
    """A finite protocol-relative certificate bundle."""

    certificate_id: str
    shells: dict[str, CertificateShell] = Field(default_factory=dict)
    dependency_dag: DependencyDAG = Field(default_factory=DependencyDAG)
    claims: list[ClaimRecord] = Field(default_factory=list)
    proof_obligations: list[ExternalProofObligation] = Field(default_factory=list)
    present_obligations: set[str] = Field(default_factory=set)
    expired_obligations: set[str] = Field(default_factory=set)
    residual_ledger: Ledger = Field(default_factory=Ledger)

    def check_status(self, rule: StatusRule) -> StatusDecision:
        return rule.decide(self.present_obligations, self.expired_obligations)

    def extract_claims(self, accepted_ids: set[str] | None = None) -> list[ClaimRecord]:
        """Return only claims whose dependency labels are available."""

        accepted_ids = accepted_ids or self.present_obligations
        extracted: list[ClaimRecord] = []
        for claim in self.claims:
            if set(claim.dependency_labels).issubset(accepted_ids):
                extracted.append(claim)
        return extracted

    def check_registry_projection(self, registry: Registry) -> CheckResult:
        """Check that a registry is only a projection of extracted claims."""

        extracted = {claim.claim_id for claim in self.extract_claims()}
        registry_ids = registry.claim_ids()
        missing = sorted(registry_ids - extracted)
        if missing:
            return CheckResult(
                accepted=False,
                status=ClaimStatus.DIAGNOSTIC,
                reasons=["registry contains claims absent from extractor output"],
                missing_obligations=missing,
                residual_ledger=self.residual_ledger,
            )
        return CheckResult(
            accepted=True,
            status=ClaimStatus.SETTLED,
            claims=[claim for claim in registry.claims if claim.claim_id in extracted],
            residual_ledger=self.residual_ledger,
        )
