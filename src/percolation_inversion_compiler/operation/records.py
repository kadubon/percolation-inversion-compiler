"""Typed records for explicit, approval-bound real-world operations."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OperationAdapterKind(StrEnum):
    HTTPS = "https"
    PROCESS = "process"


class OperationRiskClass(StrEnum):
    READ_ONLY = "read_only"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_OR_PHYSICAL = "irreversible_or_physical"


class OperationAdapterManifest(BaseModel):
    manifest_id: str
    adapter_kind: OperationAdapterKind
    risk_class: OperationRiskClass
    version: str = "1"
    fixed_origin: str | None = None
    path_template: str | None = None
    method: str | None = None
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    executable_path: str | None = None
    executable_sha256_by_platform: dict[str, str] = Field(default_factory=dict)
    fixed_argv_prefix: list[str] = Field(default_factory=list)
    argv_patterns: list[str] = Field(default_factory=list)
    fixed_cwd: str | None = None
    environment_allowlist: list[str] = Field(default_factory=list)
    secret_env_names: list[str] = Field(default_factory=list)
    external_sandbox_attested: bool = False
    timeout_ms: int = 10_000
    max_request_bytes: int = 1_000_000
    max_response_bytes: int = 1_000_000
    rollback_contract_ref: str | None = None
    hazard_contract_ref: str | None = None
    verifier_contract_ref: str | None = None


class OperationPlan(BaseModel):
    plan_id: str
    adapter_manifest: OperationAdapterManifest
    adapter_digest: str
    arguments: list[str] = Field(default_factory=list)
    path_parameters: dict[str, str] = Field(default_factory=dict)
    body_sha256: str | None = None
    resource_limits: dict[str, int] = Field(default_factory=dict)
    scope: list[str] = Field(default_factory=list)
    risk_class: OperationRiskClass
    expires_at: str
    nonce: str
    idempotency_key: str
    rollback_contract_ref: str | None = None
    hazard_contract_ref: str | None = None
    verifier_contract_ref: str | None = None
    secret_env_names: list[str] = Field(default_factory=list)
    plan_digest: str = ""
    settled: bool = False


class OperationApproval(BaseModel):
    approval_id: str
    plan_digest: str
    key_id: str
    signer_id: str
    scope: list[str] = Field(default_factory=list)
    issued_at: str
    expires_at: str
    nonce: str
    max_uses: int = 1
    signature_b64: str


class OperationTrustPolicy(BaseModel):
    policy_id: str = "operation-trust-policy"
    public_keys_b64: dict[str, str] = Field(default_factory=dict)
    verifier_public_keys_b64: dict[str, str] = Field(default_factory=dict)
    read_only_enabled: bool = False
    allowed_adapter_ids: list[str] = Field(default_factory=list)


class OperationPreflightReport(BaseModel):
    report_id: str
    plan_id: str
    plan_digest: str
    effective_risk_class: OperationRiskClass
    required_approval_count: int = 0
    accepted_approval_ids: list[str] = Field(default_factory=list)
    accepted_key_ids: list[str] = Field(default_factory=list)
    accepted_signer_ids: list[str] = Field(default_factory=list)
    adapter_valid: bool = False
    plan_valid: bool = False
    approvals_valid: bool = False
    secrets_available: bool = False
    dispatch_ready: bool = False
    operation_ready: bool = False
    provider_dispatch_ready: bool = False
    physical_dispatch_ready: bool = False
    accepted: bool = False
    settled: bool = False
    blockers: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class OperationDispatchReceipt(BaseModel):
    receipt_id: str
    plan_id: str
    plan_digest: str
    adapter_id: str
    dispatch_status: str
    provider_called: bool = False
    response_status: int | None = None
    response_sha256: str | None = None
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    started_at: str
    completed_at: str | None = None
    idempotency_key: str
    nonce: str
    physical_outcome_proven: bool = False
    physical_outcome_verified: bool = False
    accepted: bool = False
    settled: bool = False
    blockers: list[str] = Field(default_factory=list)


class OperationVerifierReport(BaseModel):
    verifier_report_id: str
    receipt_id: str
    plan_digest: str
    verifier_key_id: str
    verifier_id: str
    scope: list[str] = Field(default_factory=list)
    observation_window_start: str
    observation_window_end: str
    outcome_digest: str
    outcome_accepted: bool = False
    signature_b64: str


class OperationVerificationReport(BaseModel):
    report_id: str
    receipt_id: str
    verifier_report_id: str
    signature_valid: bool = False
    scope_valid: bool = False
    observation_window_valid: bool = False
    physical_outcome_proven: bool = False
    physical_outcome_verified: bool = False
    accepted: bool = False
    settled: bool = False
    blockers: list[str] = Field(default_factory=list)


class OperationReplayLedger(BaseModel):
    ledger_id: str
    root: str
    nonce_digest: str
    status: str
    receipt_id: str | None = None
    dispatch_uncertain: bool = False
