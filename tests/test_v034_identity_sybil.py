from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    PacketPromotionPolicy,
    ProtocolFrameDigest,
    check_no_hidden_capability_injection,
)
from percolation_inversion_compiler.identity import (
    AgentIdentityAttestation,
    AgentIdentityStrength,
    CryptographicAgentIdentity,
    SybilResistancePolicy,
    check_sybil_resistance,
    verify_agent_attestation,
    verify_agent_identity,
)
from percolation_inversion_compiler.identity import algorithms as identity_algorithms
from percolation_inversion_compiler.runtime import (
    AgentPopulationState,
    RuntimeRunReport,
    RuntimeState,
    certify_collective_phase,
    promote_packet_candidate,
)

runner = CliRunner()


def _load_identity(name: str) -> CryptographicAgentIdentity:
    import json

    raw = json.loads(Path(f"examples/identity/agent_identity_{name}.json").read_text())
    return CryptographicAgentIdentity.model_validate(raw["identity"])


def _load_population(path: str) -> AgentPopulationState:
    import json

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return AgentPopulationState.model_validate(raw["population"])


def _load_attestation() -> AgentIdentityAttestation:
    import json

    raw = json.loads(Path("examples/identity/packet_attestation.json").read_text())
    return AgentIdentityAttestation.model_validate(raw["attestation"])


def test_valid_ed25519_identity_fixture_is_accepted() -> None:
    report = verify_agent_identity(_load_identity("alice"))
    assert report.accepted
    assert report.signature_valid
    assert report.fingerprint_valid
    assert not report.settled


def test_bad_signature_and_digest_mismatch_rejected() -> None:
    identity = _load_identity("alice")
    bad_signature = identity.model_copy(update={"signature_b64": "A" * 88})
    assert not verify_agent_identity(bad_signature).accepted

    bad_digest = identity.model_copy(update={"signature_payload_sha256": "0" * 64})
    report = verify_agent_identity(bad_digest)
    assert not report.accepted
    assert "payload digest mismatch" in report.reasons


def test_identity_attestation_success_and_failures() -> None:
    alice = _load_identity("alice")
    attestation = _load_attestation()
    report = verify_agent_attestation(attestation, [alice])
    assert report.accepted
    assert report.signature_valid

    unknown = verify_agent_attestation(attestation, [])
    assert not unknown.accepted
    assert "unknown identity" in unknown.reasons

    bad_digest = attestation.model_copy(update={"payload_digest": "0" * 64})
    digest_report = verify_agent_attestation(bad_digest, [alice])
    assert not digest_report.accepted
    assert "payload digest mismatch" in digest_report.reasons

    revoked = attestation.model_copy(update={"revoked": True})
    revoked_report = verify_agent_attestation(revoked, [alice])
    assert not revoked_report.accepted
    assert "revoked credential" in revoked_report.reasons


def test_missing_crypto_dependency_returns_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableProvider:
        def verify(self, public_key_b64: str, signature_b64: str, payload: bytes) -> bool:
            del public_key_b64, signature_b64, payload
            raise identity_algorithms.IdentityCryptoUnavailable("missing crypto")

    monkeypatch.setitem(identity_algorithms._SIGNATURE_PROVIDERS, "ed25519", UnavailableProvider())
    report = verify_agent_identity(_load_identity("alice"))
    assert not report.accepted
    assert "missing crypto dependency" in report.reasons


def test_sybil_duplicate_ids_keys_revoked_expired_and_clone_fanout_reject() -> None:
    alice = _load_identity("alice")
    bob = _load_identity("bob")
    duplicate_agent = bob.model_copy(update={"agent_id": alice.agent_id})
    ledger = check_sybil_resistance(
        "population:duplicate-agent",
        [alice, duplicate_agent],
        SybilResistancePolicy(max_clone_fanout=2),
    )
    assert not ledger.accepted
    assert ledger.duplicate_agent_ids == ["agent:alice"]

    duplicate_key_population = _load_population(
        "examples/identity/sybil_population_duplicate_key.json"
    )
    duplicate_key = check_sybil_resistance(
        duplicate_key_population.population_id,
        duplicate_key_population.cryptographic_identities,
        duplicate_key_population.sybil_resistance_policy,
    )
    assert not duplicate_key.accepted
    assert duplicate_key.duplicate_public_key_ids
    assert duplicate_key.duplicate_public_key_fingerprints

    revoked = alice.model_copy(update={"revoked": True})
    expired = bob.model_copy(update={"expires_at": "expired"})
    ledger = check_sybil_resistance(
        "population:revoked-expired",
        [revoked, expired],
        SybilResistancePolicy(max_clone_fanout=2),
    )
    assert not ledger.accepted
    assert ledger.revoked_agent_ids == ["agent:alice"]
    assert ledger.expired_agent_ids == ["agent:bob"]

    clone_population = _load_population("examples/identity/sybil_population_clone_fanout.json")
    clone_ledger = check_sybil_resistance(
        clone_population.population_id,
        clone_population.cryptographic_identities,
        clone_population.sybil_resistance_policy,
    )
    assert not clone_ledger.accepted
    assert clone_ledger.clone_fanout_groups


def test_sybil_policy_overrepresentation_and_missing_evidence_reject() -> None:
    alice = _load_identity("alice")
    bob = _load_identity("bob")
    weak = bob.model_copy(
        update={
            "identity_strength": AgentIdentityStrength.DECLARED,
            "credential_ref": alice.credential_ref,
            "model_digest": alice.model_digest,
        }
    )
    ledger = check_sybil_resistance(
        "population:policy-bounds",
        [alice, weak],
        SybilResistancePolicy(
            require_unique_credential_ref=True,
            max_agents_per_issuer=1,
            max_agents_per_policy_digest=1,
            max_agents_per_model_digest=1,
            required_identity_evidence_refs=["attestation:required"],
        ),
        [],
    )
    assert not ledger.accepted
    assert ledger.duplicate_credential_refs
    assert ledger.issuer_overrepresented
    assert ledger.policy_overrepresented
    assert ledger.model_overrepresented
    assert ledger.missing_evidence_refs == ["attestation:required"]
    assert "insufficient identity strength" in ledger.reasons


def test_signed_population_sybil_check_accepts_protocol_relative_key_control() -> None:
    population = _load_population("examples/identity/sybil_population_signed.json")
    ledger = check_sybil_resistance(
        population.population_id,
        population.cryptographic_identities,
        population.sybil_resistance_policy,
        [attestation.attestation_id for attestation in population.identity_attestations],
    )
    assert ledger.accepted
    assert sorted(ledger.accepted_agent_ids) == ["agent:alice", "agent:bob"]
    assert not ledger.settled


def test_production_collective_phase_rejects_missing_crypto_identities() -> None:
    population = AgentPopulationState.model_validate(
        _load_population("examples/identity/sybil_population_signed.json").model_dump(
            mode="json",
            exclude={"cryptographic_identities", "identity_attestations"},
        )
    )
    state = population.runtime_states[0] if population.runtime_states else _minimal_runtime_state()
    certificate = certify_collective_phase(
        population,
        state,
        CapabilityBasinContract(basin_id="identity-basin"),
        RuntimeRunReport(run_id="baseline:identity", initial_state_id=state.state_id),
        {},
        profile="production",
    )
    assert not certificate.accepted
    assert certificate.sybil_resistance_ledger is not None
    assert "Sybil-resistance ledger rejected" in certificate.reasons


def test_production_packet_promotion_rejects_missing_issuer_attestation() -> None:
    packet = CapabilityPacketCandidate(
        packet_id="packet:unsigned",
        source_ref="packet.json",
        content_sha256="a" * 64,
        claim="unsigned packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "a" * 64],
        verifier_routes=[],
        rollback_available=True,
    )
    result = promote_packet_candidate(
        packet,
        [],
        [],
        PacketPromotionPolicy.for_profile("production"),
    )
    assert "packet issuer identity attestation is missing" in result.reasons


def test_hidden_injection_rejects_untrusted_or_unsigned_packet_issuer() -> None:
    packet = CapabilityPacketCandidate(
        packet_id="packet:unsigned",
        source_ref="packet.json",
        content_sha256="a" * 64,
        claim="unsigned packet",
        issuer_agent_id="agent:mallory",
        issuer_public_key_id="key:mallory",
    )
    registry = CapabilityPacketRegistry(registry_id="registry:identity", packets=[packet])
    protocol = ProtocolFrameDigest(protocol_id="protocol:identity", sha256="1" * 64)
    report = check_no_hidden_capability_injection(
        registry,
        protocol,
        accepted_agent_ids=["agent:alice"],
        trusted_public_key_ids=["key:alice:ed25519"],
    )
    assert not report.accepted
    assert report.rejected_agent_ids == ["agent:mallory"]
    assert report.unsigned_packet_ids == ["packet:unsigned"]


def test_identity_cli_smoke() -> None:
    result = runner.invoke(
        app,
        ["identity", "verify", "--identity", "examples/identity/agent_identity_alice.json"],
    )
    assert result.exit_code == 0

    sybil = runner.invoke(
        app,
        [
            "identity",
            "sybil-check",
            "--population",
            "examples/identity/sybil_population_duplicate_key.json",
        ],
    )
    assert sybil.exit_code != 0


def _minimal_runtime_state():
    import json

    raw = json.loads(Path("examples/runtime_state.json").read_text(encoding="utf-8"))
    return RuntimeState.model_validate(raw)
