"""Portable records for protocol-relative agent identity."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.ledger import Ledger


class SignatureSuite(StrEnum):
    """Registered signature suite identifiers."""

    ED25519 = "ed25519"


class AgentIdentityStrength(StrEnum):
    """Protocol-relative strength of an agent identity assertion."""

    DECLARED = "declared"
    PUBLIC_KEY_ATTESTED = "public-key-attested"
    HARDWARE_ATTESTED = "hardware-attested"
    INSTITUTIONALLY_ATTESTED = "institutionally-attested"
    REVOKED = "revoked"


class CryptographicAgentIdentity(BaseModel):
    """Public-key-backed identity for an agent inside a declared protocol."""

    agent_id: str
    public_key_id: str
    signature_suite: str = SignatureSuite.ED25519.value
    key_type: str = "ed25519-public"
    public_key_b64: str
    public_key_fingerprint: str
    signature_b64: str
    signature_payload_sha256: str
    identity_strength: AgentIdentityStrength = AgentIdentityStrength.PUBLIC_KEY_ATTESTED
    policy_digest: str
    model_digest: str | None = None
    tool_digest: str | None = None
    issuer_id: str | None = None
    credential_ref: str | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    revoked: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentIdentityAttestation(BaseModel):
    """Signed statement that binds an agent identity to finite evidence."""

    attestation_id: str
    agent_id: str
    public_key_id: str
    signature_suite: str = SignatureSuite.ED25519.value
    payload_digest: str
    signature_b64: str
    signature_payload_sha256: str
    evidence_refs: list[str] = Field(default_factory=list)
    issued_at: str | None = None
    expires_at: str | None = None
    revoked: bool = False
    nonce: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentIdentityCheckReport(BaseModel):
    """Fail-closed verification report for identity or attestation evidence."""

    report_id: str
    agent_id: str
    public_key_id: str | None = None
    signature_suite: str | None = None
    payload_digest: str | None = None
    fingerprint: str | None = None
    signature_valid: bool = False
    digest_valid: bool = False
    fingerprint_valid: bool = False
    key_valid: bool = False
    non_revoked: bool = False
    non_expired: bool = False
    policy_digest_present: bool = False
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    residual_ledger: Ledger = Field(default_factory=Ledger)
    reasons: list[str] = Field(default_factory=list)


class SybilResistancePolicy(BaseModel):
    """Population-level policy for protocol-relative Sybil resistance."""

    policy_id: str = "default-sybil-policy"
    minimum_identity_strength: AgentIdentityStrength = AgentIdentityStrength.PUBLIC_KEY_ATTESTED
    require_unique_agent_id: bool = True
    require_unique_public_key_id: bool = True
    require_unique_public_key_fingerprint: bool = True
    require_unique_credential_ref: bool = False
    reject_revoked: bool = True
    reject_expired: bool = True
    reject_failed_signatures: bool = True
    max_agents_per_issuer: int | None = None
    max_agents_per_policy_digest: int | None = None
    max_agents_per_model_digest: int | None = None
    max_clone_fanout: int | None = 1
    required_identity_evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class SybilResistanceLedger(BaseModel):
    """Population-level Sybil-resistance judgment and residual ledger."""

    ledger_id: str
    population_id: str
    policy_id: str
    identity_count: int
    accepted_agent_ids: list[str] = Field(default_factory=list)
    rejected_agent_ids: list[str] = Field(default_factory=list)
    duplicate_agent_ids: list[str] = Field(default_factory=list)
    duplicate_public_key_ids: list[str] = Field(default_factory=list)
    duplicate_public_key_fingerprints: list[str] = Field(default_factory=list)
    duplicate_credential_refs: list[str] = Field(default_factory=list)
    revoked_agent_ids: list[str] = Field(default_factory=list)
    expired_agent_ids: list[str] = Field(default_factory=list)
    failed_signature_agent_ids: list[str] = Field(default_factory=list)
    missing_evidence_refs: list[str] = Field(default_factory=list)
    issuer_overrepresented: list[str] = Field(default_factory=list)
    policy_overrepresented: list[str] = Field(default_factory=list)
    model_overrepresented: list[str] = Field(default_factory=list)
    clone_fanout_groups: list[str] = Field(default_factory=list)
    identity_check_reports: list[AgentIdentityCheckReport] = Field(default_factory=list)
    residual_ledger: Ledger = Field(default_factory=Ledger)
    accepted: bool = False
    finite_checks_passed: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
