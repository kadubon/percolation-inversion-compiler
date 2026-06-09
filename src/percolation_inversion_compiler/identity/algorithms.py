"""Fail-closed identity and Sybil-resistance algorithms."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Protocol

from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.identity.records import (
    AgentIdentityAttestation,
    AgentIdentityCheckReport,
    AgentIdentityStrength,
    CryptographicAgentIdentity,
    SignatureSuite,
    SybilResistanceLedger,
    SybilResistancePolicy,
)


class SignatureVerifier(Protocol):
    """Provider boundary for signature suites."""

    suite: SignatureSuite

    def verify(self, public_key_b64: str, signature_b64: str, payload: bytes) -> bool:
        """Return whether the signature validates for the payload."""


class IdentityCryptoUnavailable(RuntimeError):
    """Raised when an optional crypto provider is not installed."""


class Ed25519SignatureVerifier:
    """Ed25519 verifier loaded lazily from the optional identity extra."""

    suite = SignatureSuite.ED25519

    def verify(self, public_key_b64: str, signature_b64: str, payload: bytes) -> bool:
        public_key_bytes = _decode_b64(public_key_b64)
        signature_bytes = _decode_b64(signature_b64)
        if public_key_bytes is None or signature_bytes is None:
            return False
        if len(public_key_bytes) != 32 or len(signature_bytes) != 64:
            return False
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
        except ModuleNotFoundError as exc:  # pragma: no cover - monkeypatched in tests.
            raise IdentityCryptoUnavailable(
                "cryptography is required for ed25519 identity verification"
            ) from exc
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature_bytes, payload)
        except (InvalidSignature, ValueError):
            return False
        return True


_SIGNATURE_PROVIDERS: dict[str, SignatureVerifier] = {
    SignatureSuite.ED25519.value: Ed25519SignatureVerifier(),
}

_STRENGTH_RANK: dict[AgentIdentityStrength, int] = {
    AgentIdentityStrength.REVOKED: -1,
    AgentIdentityStrength.DECLARED: 0,
    AgentIdentityStrength.PUBLIC_KEY_ATTESTED: 1,
    AgentIdentityStrength.HARDWARE_ATTESTED: 2,
    AgentIdentityStrength.INSTITUTIONALLY_ATTESTED: 3,
}


def stable_digest(payload: bytes | str | dict[str, Any] | list[Any]) -> str:
    """Return a SHA-256 digest for bytes, text, or stable JSON payloads."""

    if isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = _canonical_json_bytes(payload)
    return hashlib.sha256(raw).hexdigest()


def stable_identity_payload(identity: CryptographicAgentIdentity) -> dict[str, Any]:
    """Return the canonical identity payload covered by the identity signature."""

    return identity.model_dump(
        mode="json",
        exclude={"signature_b64", "signature_payload_sha256"},
        exclude_none=True,
    )


def stable_attestation_payload(attestation: AgentIdentityAttestation) -> dict[str, Any]:
    """Return the canonical attestation payload covered by the attestation signature."""

    return attestation.model_dump(
        mode="json",
        exclude={"payload_digest", "signature_b64", "signature_payload_sha256"},
        exclude_none=True,
    )


def verify_agent_identity(
    identity: CryptographicAgentIdentity,
) -> AgentIdentityCheckReport:
    """Verify one cryptographic agent identity without asserting real-world identity."""

    residual = Ledger()
    reasons: list[str] = []
    payload = stable_identity_payload(identity)
    payload_bytes = _canonical_json_bytes(payload)
    payload_digest = stable_digest(payload_bytes)
    digest_valid = payload_digest == identity.signature_payload_sha256
    key_bytes = _decode_b64(identity.public_key_b64)
    signature_bytes = _decode_b64(identity.signature_b64)
    key_valid = key_bytes is not None and len(key_bytes) == 32
    signature_shape_valid = signature_bytes is not None and len(signature_bytes) == 64
    fingerprint = hashlib.sha256(key_bytes).hexdigest() if key_bytes is not None else None
    fingerprint_valid = fingerprint == identity.public_key_fingerprint
    non_revoked = (
        not identity.revoked and identity.identity_strength != AgentIdentityStrength.REVOKED
    )
    non_expired = not _is_expired(identity.expires_at)
    policy_digest_present = bool(identity.policy_digest)
    signature_valid = False

    if identity.signature_suite not in _SIGNATURE_PROVIDERS:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:unsupported-signature-suite",
            "unsupported signature suite",
        )
    if not digest_valid:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:payload-digest-mismatch",
            "payload digest mismatch",
        )
    if not key_valid:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:invalid-public-key",
            "invalid public key",
        )
    if not signature_shape_valid:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:invalid-signature",
            "invalid signature",
        )
    if key_valid and not fingerprint_valid:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:public-key-fingerprint-mismatch",
            "public key fingerprint mismatch",
        )
    if not non_revoked:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:revoked-credential",
            "revoked credential",
        )
    if not non_expired:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:expired-credential",
            "expired credential",
        )
    if not policy_digest_present:
        _append_failure(
            residual,
            reasons,
            f"identity:{identity.agent_id}:missing-policy-digest",
            "missing policy digest",
        )

    provider = _SIGNATURE_PROVIDERS.get(identity.signature_suite)
    if provider is not None and key_valid and signature_shape_valid:
        try:
            signature_valid = provider.verify(
                identity.public_key_b64,
                identity.signature_b64,
                payload_bytes,
            )
        except IdentityCryptoUnavailable:
            _append_failure(
                residual,
                reasons,
                f"identity:{identity.agent_id}:missing-crypto-dependency",
                "missing crypto dependency",
            )
        else:
            if not signature_valid:
                _append_failure(
                    residual,
                    reasons,
                    f"identity:{identity.agent_id}:invalid-signature",
                    "invalid signature",
                )

    accepted = (
        digest_valid
        and key_valid
        and fingerprint_valid
        and signature_valid
        and non_revoked
        and non_expired
        and policy_digest_present
        and not reasons
    )
    return AgentIdentityCheckReport(
        report_id=f"identity-check:{identity.agent_id}",
        agent_id=identity.agent_id,
        public_key_id=identity.public_key_id,
        signature_suite=identity.signature_suite,
        payload_digest=payload_digest,
        fingerprint=fingerprint,
        signature_valid=signature_valid,
        digest_valid=digest_valid,
        fingerprint_valid=fingerprint_valid,
        key_valid=key_valid,
        non_revoked=non_revoked,
        non_expired=non_expired,
        policy_digest_present=policy_digest_present,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        residual_ledger=residual,
        reasons=sorted(set(reasons)),
    )


def verify_agent_attestation(
    attestation: AgentIdentityAttestation,
    identities: list[CryptographicAgentIdentity],
) -> AgentIdentityCheckReport:
    """Verify an identity attestation against known public identities."""

    residual = Ledger()
    reasons: list[str] = []
    identity = {(item.agent_id, item.public_key_id): item for item in identities}.get(
        (attestation.agent_id, attestation.public_key_id)
    )
    if identity is None:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:unknown-identity",
            "unknown identity",
        )
        return AgentIdentityCheckReport(
            report_id=f"attestation-check:{attestation.attestation_id}",
            agent_id=attestation.agent_id,
            public_key_id=attestation.public_key_id,
            signature_suite=attestation.signature_suite,
            accepted=False,
            finite_checks_passed=False,
            operationally_usable=False,
            settled=False,
            residual_ledger=residual,
            reasons=sorted(set(reasons)),
        )

    identity_report = verify_agent_identity(identity)
    residual = residual.combine(identity_report.residual_ledger)
    if not identity_report.accepted:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:identity-not-accepted",
            "identity verification failed",
        )

    payload = stable_attestation_payload(attestation)
    payload_bytes = _canonical_json_bytes(payload)
    payload_digest = stable_digest(payload_bytes)
    digest_valid = payload_digest == attestation.signature_payload_sha256
    non_revoked = not attestation.revoked
    non_expired = not _is_expired(attestation.expires_at)
    signature_valid = False

    if payload_digest != attestation.payload_digest:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:payload-digest-mismatch",
            "payload digest mismatch",
        )
    if not digest_valid:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:signature-payload-digest-mismatch",
            "signature payload digest mismatch",
        )
    if not non_revoked:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:revoked-credential",
            "revoked credential",
        )
    if not non_expired:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:expired-credential",
            "expired credential",
        )
    provider = _SIGNATURE_PROVIDERS.get(attestation.signature_suite)
    if provider is None:
        _append_failure(
            residual,
            reasons,
            f"attestation:{attestation.attestation_id}:unsupported-signature-suite",
            "unsupported signature suite",
        )
    else:
        try:
            signature_valid = provider.verify(
                identity.public_key_b64,
                attestation.signature_b64,
                payload_bytes,
            )
        except IdentityCryptoUnavailable:
            _append_failure(
                residual,
                reasons,
                f"attestation:{attestation.attestation_id}:missing-crypto-dependency",
                "missing crypto dependency",
            )
        else:
            if not signature_valid:
                _append_failure(
                    residual,
                    reasons,
                    f"attestation:{attestation.attestation_id}:invalid-signature",
                    "invalid signature",
                )

    accepted = (
        identity_report.accepted
        and digest_valid
        and payload_digest == attestation.payload_digest
        and signature_valid
        and non_revoked
        and non_expired
        and not reasons
    )
    return AgentIdentityCheckReport(
        report_id=f"attestation-check:{attestation.attestation_id}",
        agent_id=attestation.agent_id,
        public_key_id=attestation.public_key_id,
        signature_suite=attestation.signature_suite,
        payload_digest=payload_digest,
        fingerprint=identity_report.fingerprint,
        signature_valid=signature_valid,
        digest_valid=digest_valid,
        fingerprint_valid=identity_report.fingerprint_valid,
        key_valid=identity_report.key_valid,
        non_revoked=non_revoked,
        non_expired=non_expired,
        policy_digest_present=identity_report.policy_digest_present,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        residual_ledger=residual,
        reasons=sorted(set(reasons + identity_report.reasons)),
    )


def check_sybil_resistance(
    population_id: str,
    identities: list[CryptographicAgentIdentity],
    policy: SybilResistancePolicy | None = None,
    identity_attestation_refs: list[str] | None = None,
) -> SybilResistanceLedger:
    """Check protocol-relative Sybil resistance for a declared population."""

    active_policy = policy or SybilResistancePolicy()
    residual = Ledger()
    reasons: list[str] = []
    attestation_refs = sorted(identity_attestation_refs or [])
    reports = [verify_agent_identity(identity) for identity in identities]
    report_by_agent = {report.agent_id: report for report in reports}
    rejected: set[str] = set()

    duplicate_agent_ids = _duplicates([identity.agent_id for identity in identities])
    duplicate_public_key_ids = _duplicates([identity.public_key_id for identity in identities])
    duplicate_fingerprints = _duplicates(
        [identity.public_key_fingerprint for identity in identities]
    )
    credential_refs = [
        identity.credential_ref for identity in identities if identity.credential_ref
    ]
    duplicate_credentials = _duplicates(credential_refs)

    if not identities:
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:missing-identities",
            "missing required identity evidence",
        )
    if active_policy.require_unique_agent_id and duplicate_agent_ids:
        rejected.update(_agents_with_values(identities, "agent_id", duplicate_agent_ids))
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:duplicate-agent-id",
            "duplicate agent id",
            value=len(duplicate_agent_ids),
        )
    if active_policy.require_unique_public_key_id and duplicate_public_key_ids:
        rejected.update(_agents_with_values(identities, "public_key_id", duplicate_public_key_ids))
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:duplicate-public-key-id",
            "duplicate public key id",
            value=len(duplicate_public_key_ids),
        )
    if active_policy.require_unique_public_key_fingerprint and duplicate_fingerprints:
        rejected.update(
            _agents_with_values(identities, "public_key_fingerprint", duplicate_fingerprints)
        )
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:duplicate-public-key-fingerprint",
            "duplicate public key fingerprint",
            value=len(duplicate_fingerprints),
        )
    if active_policy.require_unique_credential_ref and duplicate_credentials:
        rejected.update(_agents_with_values(identities, "credential_ref", duplicate_credentials))
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:duplicate-credential-ref",
            "duplicate credential ref",
            value=len(duplicate_credentials),
        )

    revoked_agent_ids = sorted(
        identity.agent_id
        for identity in identities
        if identity.revoked or identity.identity_strength == AgentIdentityStrength.REVOKED
    )
    expired_agent_ids = sorted(
        identity.agent_id for identity in identities if _is_expired(identity.expires_at)
    )
    failed_signature_agent_ids = sorted(
        report.agent_id for report in reports if not report.accepted
    )
    missing_evidence = sorted(
        ref for ref in active_policy.required_identity_evidence_refs if ref not in attestation_refs
    )
    if active_policy.reject_revoked and revoked_agent_ids:
        rejected.update(revoked_agent_ids)
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:revoked-credential",
            "revoked credential",
            value=len(revoked_agent_ids),
        )
    if active_policy.reject_expired and expired_agent_ids:
        rejected.update(expired_agent_ids)
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:expired-credential",
            "expired credential",
            value=len(expired_agent_ids),
        )
    if active_policy.reject_failed_signatures and failed_signature_agent_ids:
        rejected.update(failed_signature_agent_ids)
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:failed-signature",
            "failed signature",
            value=len(failed_signature_agent_ids),
        )
    if missing_evidence:
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:missing-identity-evidence",
            "missing required identity evidence",
            value=len(missing_evidence),
        )

    for identity in identities:
        if _strength_rank(identity.identity_strength) < _strength_rank(
            active_policy.minimum_identity_strength
        ):
            rejected.add(identity.agent_id)
            _append_failure(
                residual,
                reasons,
                f"sybil:{population_id}:insufficient-identity-strength",
                "insufficient identity strength",
            )

    issuer_overrepresented = _overrepresented(
        [identity.issuer_id for identity in identities if identity.issuer_id],
        active_policy.max_agents_per_issuer,
    )
    policy_overrepresented = _overrepresented(
        [identity.policy_digest for identity in identities],
        active_policy.max_agents_per_policy_digest,
    )
    model_overrepresented = _overrepresented(
        [identity.model_digest for identity in identities if identity.model_digest],
        active_policy.max_agents_per_model_digest,
    )
    clone_fanout_groups = _clone_fanout_groups(identities, active_policy.max_clone_fanout)
    for value in issuer_overrepresented:
        rejected.update(identity.agent_id for identity in identities if identity.issuer_id == value)
    for value in policy_overrepresented:
        rejected.update(
            identity.agent_id for identity in identities if identity.policy_digest == value
        )
    for value in model_overrepresented:
        rejected.update(
            identity.agent_id for identity in identities if identity.model_digest == value
        )
    if issuer_overrepresented:
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:issuer-overrepresentation",
            "issuer overrepresentation",
            value=len(issuer_overrepresented),
        )
    if policy_overrepresented:
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:policy-overrepresentation",
            "policy overrepresentation",
            value=len(policy_overrepresented),
        )
    if model_overrepresented:
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:model-overrepresentation",
            "model overrepresentation",
            value=len(model_overrepresented),
        )
    if clone_fanout_groups:
        for group in clone_fanout_groups:
            policy_digest, model_digest, tool_digest = group.split("|", maxsplit=2)
            rejected.update(
                identity.agent_id
                for identity in identities
                if identity.policy_digest == policy_digest
                and (identity.model_digest or "") == model_digest
                and (identity.tool_digest or "") == tool_digest
            )
        _append_failure(
            residual,
            reasons,
            f"sybil:{population_id}:clone-fanout",
            "clone fanout",
            value=len(clone_fanout_groups),
        )

    accepted_agent_ids = sorted(
        identity.agent_id
        for identity in identities
        if identity.agent_id not in rejected
        and report_by_agent.get(identity.agent_id, _empty_report(identity.agent_id)).accepted
    )
    accepted = bool(identities) and not reasons and len(accepted_agent_ids) == len(identities)
    return SybilResistanceLedger(
        ledger_id=(
            f"sybil:{population_id}:"
            f"{stable_digest(_sybil_digest_payload(active_policy, identities))[:16]}"
        ),
        population_id=population_id,
        policy_id=active_policy.policy_id,
        identity_count=len(identities),
        accepted_agent_ids=accepted_agent_ids,
        rejected_agent_ids=sorted(rejected),
        duplicate_agent_ids=duplicate_agent_ids,
        duplicate_public_key_ids=duplicate_public_key_ids,
        duplicate_public_key_fingerprints=duplicate_fingerprints,
        duplicate_credential_refs=duplicate_credentials,
        revoked_agent_ids=revoked_agent_ids,
        expired_agent_ids=expired_agent_ids,
        failed_signature_agent_ids=failed_signature_agent_ids,
        missing_evidence_refs=missing_evidence,
        issuer_overrepresented=issuer_overrepresented,
        policy_overrepresented=policy_overrepresented,
        model_overrepresented=model_overrepresented,
        clone_fanout_groups=clone_fanout_groups,
        identity_check_reports=reports,
        residual_ledger=residual,
        accepted=accepted,
        finite_checks_passed=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=sorted(set(reasons)),
    )


def _canonical_json_bytes(payload: dict[str, Any] | list[Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _decode_b64(value: str) -> bytes | None:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError):
        return None


def _append_failure(
    residual: Ledger,
    reasons: list[str],
    coordinate: str,
    reason: str,
    *,
    value: float = 1.0,
) -> None:
    residual.add_coordinate(coordinate, value, kind=CoordinateKind.RESIDUAL)
    reasons.append(reason)


def _is_expired(expires_at: str | None) -> bool:
    return bool(expires_at and expires_at.strip().lower() == "expired")


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _overrepresented(values: list[str], limit: int | None) -> list[str]:
    if limit is None:
        return []
    return sorted(value for value, count in Counter(values).items() if count > limit)


def _clone_fanout_groups(
    identities: list[CryptographicAgentIdentity],
    max_clone_fanout: int | None,
) -> list[str]:
    if max_clone_fanout is None:
        return []
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for identity in identities:
        groups[
            (
                identity.policy_digest,
                identity.model_digest or "",
                identity.tool_digest or "",
            )
        ].append(identity.agent_id)
    return sorted(
        "|".join(key) for key, agent_ids in groups.items() if len(agent_ids) > max_clone_fanout
    )


def _sybil_digest_payload(
    policy: SybilResistancePolicy,
    identities: list[CryptographicAgentIdentity],
) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "identities": [
            {
                "agent_id": identity.agent_id,
                "public_key_id": identity.public_key_id,
                "public_key_fingerprint": identity.public_key_fingerprint,
            }
            for identity in sorted(
                identities,
                key=lambda item: (item.agent_id, item.public_key_id),
            )
        ],
    }


def _agents_with_values(
    identities: list[CryptographicAgentIdentity],
    field_name: str,
    values: list[str],
) -> list[str]:
    value_set = set(values)
    matched: list[str] = []
    for identity in identities:
        value = getattr(identity, field_name)
        if value in value_set:
            matched.append(identity.agent_id)
    return sorted(matched)


def _strength_rank(strength: AgentIdentityStrength) -> int:
    return _STRENGTH_RANK[strength]


def _empty_report(agent_id: str) -> AgentIdentityCheckReport:
    return AgentIdentityCheckReport(report_id=f"identity-check:{agent_id}", agent_id=agent_id)
