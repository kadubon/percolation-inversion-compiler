# Identity and Sybil Resistance

v0.3.4 adds an optional cryptographic identity layer for adversarial protocol settings. It is designed for ECPT collective phase runtime users who need stronger evidence than a declared `agent_id` before accepting packet capital, population steps, or collective phase certificates.

## Boundary

The identity layer proves protocol-relative key control. It does not prove legal identity, real-world personhood, institutional authority, or world-global uniqueness. Sybil resistance proves compliance with the declared population policy, not uniqueness across all possible agents.

`CollectivePhaseCertificate.settled` remains `false` unless the existing scoped finite verifier settlement rules discharge the complete finite route. Signed identities and Sybil ledgers can make a population acceptable for production routing, but they do not settle physical, simulator, oracle, policy, or real-ASI obligations.

## Records

- `CryptographicAgentIdentity`: agent id, public key id, signature suite, public key, fingerprint, policy digest, model/tool digests, revocation/expiry flags, and identity signature.
- `AgentIdentityAttestation`: signed statement that binds an identity to finite evidence references.
- `AgentIdentityCheckReport`: fail-closed signature, digest, fingerprint, revocation, expiry, and policy-digest report.
- `SybilResistancePolicy`: uniqueness, revocation, expiry, overrepresentation, required evidence, and clone-fanout policy.
- `SybilResistanceLedger`: accepted/rejected agent ids, duplicate keys, failed signatures, missing evidence, clone groups, and residual ledger.

## Signature Suite Boundary

Ed25519 is the first implemented suite. Runtime and certificate logic depends only on explicit suite names and verifier-provider outputs, so future providers such as post-quantum signatures can be added without changing ECPT semantics.

Canonical signed payload serialization is:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
```

The core package does not import `cryptography` at import time. Verification returns a diagnostic, fail-closed report when the optional `[identity]` extra is unavailable.

## CLI

```powershell
uv run pic identity verify --identity examples/identity/agent_identity_alice.json
uv run pic identity verify-attestation --attestation examples/identity/packet_attestation.json --identities examples/identity/agent_identities.json
uv run pic identity sybil-check --population examples/agent_population_signed.json
```

Negative fixtures:

```powershell
uv run pic identity sybil-check --population examples/identity/sybil_population_duplicate_key.json
uv run pic identity sybil-check --population examples/identity/sybil_population_clone_fanout.json
```

These commands should fail closed and emit machine-readable reasons.

## Agent Policy

For production collective phase workflows, configure agents to require:

1. signed cryptographic identities for every population member;
2. non-revoked and non-expired credentials;
3. unique agent ids, public-key ids, and public-key fingerprints;
4. acceptable issuer, policy, model, and clone-fanout bounds;
5. packet issuer identity refs before candidate promotion;
6. hidden-injection rejection for packets/events outside accepted agent ids or trusted public keys.

Development mode remains backward-compatible with unsigned v0.3.4 examples. Production mode is intentionally stricter.
