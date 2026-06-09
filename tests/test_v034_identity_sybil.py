from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitnessCertificate,
    PacketPromotionPolicy,
    ProtocolFrameDigest,
    check_no_hidden_capability_injection,
)
from percolation_inversion_compiler.identity import (
    AgentIdentityAttestation,
    AgentIdentityStrength,
    CryptographicAgentIdentity,
    SybilResistanceLedger,
    SybilResistancePolicy,
    check_sybil_resistance,
    identity_contribution_status_for_packet,
    normalize_identity_profile,
    sybil_policy_for_profile,
    verify_agent_attestation,
    verify_agent_identity,
)
from percolation_inversion_compiler.identity import algorithms as identity_algorithms
from percolation_inversion_compiler.runtime import (
    AgentPopulationState,
    AgentRuntimeConfig,
    RuntimeRunReport,
    RuntimeState,
    RuntimeStepInput,
    build_runtime_step,
    certify_collective_phase,
    promote_packet_candidate,
    runtime_health,
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


def test_sybil_policy_for_profile_defaults_are_deterministic() -> None:
    development = sybil_policy_for_profile("development")
    controlled = sybil_policy_for_profile("controlled")
    adversarial = sybil_policy_for_profile("adversarial")
    assert development.minimum_identity_strength == AgentIdentityStrength.DECLARED
    assert not development.reject_failed_signatures
    assert controlled.max_agents_per_fleet == 8
    assert controlled.allow_homogeneous_fleet_with_unique_keys
    assert adversarial.require_unique_credential_ref
    assert adversarial.max_clone_fanout == 1
    assert normalize_identity_profile("unknown").value == "production"


def test_identity_contribution_status_profiles() -> None:
    unsigned = CapabilityPacketCandidate(
        packet_id="packet:unsigned-status",
        source_ref="packet.json",
        content_sha256="a" * 64,
        claim="unsigned",
    )
    partial = unsigned.model_copy(update={"issuer_agent_id": "agent:alice"})
    signed = _signed_packet("packet:signed-status", "agent:alice", "key:alice:ed25519")
    ledger = SybilResistanceLedger(
        ledger_id="ledger:status",
        population_id="population:status",
        policy_id="policy:status",
        identity_count=1,
        accepted_agent_ids=["agent:alice"],
        accepted_public_key_ids=["key:alice:ed25519"],
        accepted=True,
    )
    assert identity_contribution_status_for_packet(unsigned, None, "development") == "diagnostic"
    assert identity_contribution_status_for_packet(unsigned, None, "production") == "rejected"
    assert identity_contribution_status_for_packet(partial, None, "research") == "diagnostic"
    assert identity_contribution_status_for_packet(partial, None, "production") == "quarantined"
    assert identity_contribution_status_for_packet(signed, None, "production") == "quarantined"
    assert identity_contribution_status_for_packet(signed, ledger, "production") == "verified"
    rejected_ledger = ledger.model_copy(update={"accepted": False})
    assert (
        identity_contribution_status_for_packet(signed, rejected_ledger, "production") == "rejected"
    )
    assert (
        identity_contribution_status_for_packet(signed, rejected_ledger, "research") == "diagnostic"
    )


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
    assert "Sybil-resistance ledger rejected under selected profile" in certificate.reasons


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
        profile="production",
    )
    assert not report.accepted
    assert report.rejected_agent_ids == ["agent:mallory"]
    assert report.unsigned_packet_ids == ["packet:unsigned"]


def test_hidden_injection_profile_sensitive_unsigned_packets() -> None:
    packet = CapabilityPacketCandidate(
        packet_id="packet:unsigned-dev",
        source_ref="packet.json",
        content_sha256="a" * 64,
        claim="unsigned packet",
    )
    registry = CapabilityPacketRegistry(registry_id="registry:dev", packets=[packet])
    protocol = ProtocolFrameDigest(protocol_id="protocol:dev", sha256="1" * 64)
    development = check_no_hidden_capability_injection(
        registry,
        protocol,
        profile="development",
    )
    production = check_no_hidden_capability_injection(
        registry,
        protocol,
        profile="production",
    )
    assert development.accepted
    assert not production.accepted
    assert production.unsigned_packet_ids == ["packet:unsigned-dev"]


def test_runtime_step_passes_accepted_identity_context_to_packet_promotion() -> None:
    state = _minimal_runtime_state().model_copy(
        update={
            "accepted_agent_ids": ["agent:alice"],
            "accepted_public_key_ids": ["key:alice:ed25519"],
            "identity_mode": "cryptographic",
        }
    )
    packet = _signed_packet("packet:alice-runtime", "agent:alice", "key:alice:ed25519")
    report = build_runtime_step(
        state,
        RuntimeStepInput(
            input_id="identity-runtime-step",
            packets=[packet],
            edge_certificates=[_accepted_edge_certificate(packet.packet_id)],
        ),
        AgentRuntimeConfig(profile="production"),
    )
    assert report.promotion_report.verified_packets
    assert any(
        packet.source_candidate_id == "packet:alice-runtime"
        for packet in report.promotion_report.verified_packets
    )


def test_runtime_step_rejects_packet_issuer_outside_context_in_production() -> None:
    state = _minimal_runtime_state().model_copy(
        update={
            "accepted_agent_ids": ["agent:alice"],
            "accepted_public_key_ids": ["key:alice:ed25519"],
            "identity_mode": "cryptographic",
        }
    )
    packet = _signed_packet("packet:mallory-runtime", "agent:mallory", "key:mallory")
    report = build_runtime_step(
        state,
        RuntimeStepInput(
            input_id="identity-runtime-step-reject",
            packets=[packet],
            edge_certificates=[_accepted_edge_certificate(packet.packet_id)],
        ),
        AgentRuntimeConfig(profile="production"),
    )
    assert report.promotion_report.rejected_packets
    rejection_reasons = report.promotion_report.rejected_packets[0].reasons
    assert "packet issuer is outside accepted population" in rejection_reasons


def test_runtime_step_missing_identity_context_has_runtime_residual() -> None:
    packet = _signed_packet("packet:no-context", "agent:alice", "key:alice:ed25519")
    report = build_runtime_step(
        _minimal_runtime_state(),
        RuntimeStepInput(
            input_id="identity-runtime-step-no-context",
            packets=[packet],
            edge_certificates=[_accepted_edge_certificate(packet.packet_id)],
        ),
        AgentRuntimeConfig(profile="production"),
    )
    assert not report.promotion_report.verified_packets
    assert any(
        coordinate.startswith("runtime-identity:")
        for coordinate in report.residual_ledger.coordinates
    )


def test_controlled_profile_allows_homogeneous_fleet_with_unique_keys() -> None:
    identities = [
        _generated_identity("agent:fleet:0", "key:fleet:0", fleet_id="fleet:alpha"),
        _generated_identity("agent:fleet:1", "key:fleet:1", fleet_id="fleet:alpha"),
    ]
    ledger = check_sybil_resistance(
        "population:controlled-fleet",
        identities,
        sybil_policy_for_profile("controlled"),
    )
    assert ledger.accepted
    assert ledger.accepted_public_key_ids == ["key:fleet:0", "key:fleet:1"]


def test_duplicate_key_rejected_even_when_homogeneous_fleet_allowed() -> None:
    alice = _generated_identity("agent:fleet:0", "key:fleet:0", fleet_id="fleet:alpha")
    duplicate = alice.model_copy(update={"agent_id": "agent:fleet:1"})
    ledger = check_sybil_resistance(
        "population:controlled-duplicate-key",
        [alice, duplicate],
        sybil_policy_for_profile("controlled"),
    )
    assert not ledger.accepted
    assert ledger.duplicate_public_key_ids == ["key:fleet:0"]


def test_adversarial_profile_rejects_homogeneous_fleet_without_explicit_policy() -> None:
    identities = [
        _generated_identity("agent:adv:0", "key:adv:0"),
        _generated_identity("agent:adv:1", "key:adv:1"),
    ]
    ledger = check_sybil_resistance(
        "population:adversarial-clone",
        identities,
        sybil_policy_for_profile("adversarial"),
    )
    assert not ledger.accepted
    assert ledger.clone_fanout_groups


def test_fleet_and_issuer_profile_bounds_are_reported() -> None:
    identities = [
        _generated_identity("agent:fleet-bound:0", "key:fleet-bound:0", fleet_id="fleet:bounded"),
        _generated_identity("agent:fleet-bound:1", "key:fleet-bound:1", fleet_id="fleet:bounded"),
    ]
    policy = sybil_policy_for_profile("federated").model_copy(
        update={"max_agents_per_fleet": 1, "max_agents_per_issuer": 1}
    )
    ledger = check_sybil_resistance("population:fleet-bound", identities, policy)
    assert not ledger.accepted
    assert ledger.fleet_overrepresented == ["fleet:bounded"]
    assert ledger.issuer_overrepresented == ["issuer:fleet"]


def test_runtime_health_reports_identity_readiness() -> None:
    state = _minimal_runtime_state()
    health = runtime_health(state, AgentRuntimeConfig(profile="production"))
    assert health.cryptographic_identity_required
    assert not health.accepted_agent_context_present
    assert not health.production_identity_ready


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

    explain = runner.invoke(app, ["identity", "explain-profile", "--profile", "production"])
    assert explain.exit_code == 0
    assert "packet_promotion_policy" in explain.stdout

    context = runner.invoke(
        app,
        [
            "identity",
            "derive-context",
            "--population",
            "examples/agent_population_signed.json",
            "--profile",
            "production",
        ],
    )
    assert context.exit_code == 0
    assert "accepted_agent_ids" in context.stdout


def _minimal_runtime_state():
    import json

    raw = json.loads(Path("examples/runtime_state.json").read_text(encoding="utf-8"))
    return RuntimeState.model_validate(raw)


def _signed_packet(
    packet_id: str,
    issuer_agent_id: str,
    issuer_public_key_id: str,
) -> CapabilityPacketCandidate:
    return CapabilityPacketCandidate(
        packet_id=packet_id,
        source_ref=f"{packet_id}.json",
        content_sha256="a" * 64,
        claim="signed runtime packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "a" * 64],
        expected_downstream_gain=2.0,
        verification_cost=0.1,
        verifier_routes=[],
        rollback_available=True,
        issuer_agent_id=issuer_agent_id,
        issuer_public_key_id=issuer_public_key_id,
        issuer_attestation_id=f"attestation:{issuer_agent_id}",
        issuer_signature_ref="sha256:" + "b" * 64,
    )


def _accepted_edge_certificate(packet_id: str) -> EdgeWitnessCertificate:
    return EdgeWitnessCertificate(
        certificate_id=f"edge-certificate:{packet_id}",
        edge_id=f"edge:{packet_id}",
        relation_type="semantic-dependency",
        source_packet_ids=[packet_id],
        target_packet_id=packet_id,
        evidence_refs=["sha256:" + "a" * 64],
        confidence_lower_bound=0.9,
        false_edge_residual=0.0,
        accepted=True,
    )


def _generated_identity(
    agent_id: str,
    public_key_id: str,
    *,
    fleet_id: str | None = None,
) -> CryptographicAgentIdentity:
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    signing_key = ed25519.Ed25519PrivateKey.generate()
    public_key = signing_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    import base64
    import hashlib
    import json

    identity = CryptographicAgentIdentity(
        agent_id=agent_id,
        public_key_id=public_key_id,
        public_key_b64=base64.b64encode(public_key_bytes).decode("ascii"),
        public_key_fingerprint=hashlib.sha256(public_key_bytes).hexdigest(),
        signature_b64="",
        signature_payload_sha256="",
        policy_digest="policy:homogeneous:v1",
        model_digest="model:homogeneous:v1",
        tool_digest="tool:homogeneous:v1",
        fleet_id=fleet_id,
        role_id=agent_id.rsplit(":", maxsplit=1)[-1],
        worker_index=agent_id.rsplit(":", maxsplit=1)[-1],
        issuer_id="issuer:fleet",
        credential_ref=f"credential:{agent_id}",
    )
    payload = identity.model_dump(
        mode="json",
        exclude={"signature_b64", "signature_payload_sha256"},
        exclude_none=True,
    )
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = signing_key.sign(payload_bytes)
    return identity.model_copy(
        update={
            "signature_b64": base64.b64encode(signature).decode("ascii"),
            "signature_payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        }
    )
