# Identity and Sybil Resistance

v0.4.1 keeps the practical cryptographic identity layer for adversarial protocol settings and connects it to external packet intake and ALT abstraction-liquidity admission. It is designed for ECPT collective phase runtime users who need stronger evidence than a declared `agent_id` before accepting packet capital, population steps, abstraction capital, or collective phase certificates, while still preserving diagnostic packet candidates in less strict profiles.

## Boundary

The identity layer proves protocol-relative key control. It does not prove legal identity, real-world personhood, institutional authority, or world-global uniqueness. Sybil resistance proves compliance with the declared population policy, not uniqueness across all possible agents.

`CollectivePhaseCertificate.settled` remains `false` unless the existing scoped finite verifier settlement rules discharge the complete finite route. Signed identities and Sybil ledgers can make a population acceptable for production routing, but they do not settle physical, simulator, oracle, policy, or real-ASI obligations.

## Choosing A Trust Profile

Use `pic identity explain-profile --profile <name>` to inspect the exact policy before an agent run.

- `development`: local examples and unsigned diagnostic packets. It keeps workflows usable but does not provide production identity readiness.
- `research`: signed public-key identities for experiments. It keeps repeated model/policy/tool digests visible without treating them as production Sybil proof.
- `controlled`: internal lab or trusted cluster. It requires unique public keys and allows homogeneous fleets when `fleet_id` is declared and the fleet quota is respected.
- `federated`: multi-issuer deployment. It requires issuer identity and enforces issuer quotas.
- `production`: public-key-attested population, unique keys, signed packet issuers, non-revoked/non-expired credentials, and bounded fleet membership.
- `adversarial`: strict population policy. It requires unique credentials, issuer evidence, signed packet issuers, and clone-fanout rejection unless an explicit policy overrides it.

Production and adversarial profiles fail closed, but they should not fail dead: rejected packets remain visible as diagnostic or quarantined records with residual coordinates and repair routes.

## Why Homogeneous Fleets Are Not Automatically Sybil

A real deployment may run many agents with the same model digest, tool digest, and policy digest. That alone is not a Sybil proof. In `controlled` and `production` profiles, homogeneous fleets can contribute when each worker has a distinct public key, declared `fleet_id`, bounded fleet quota, and residual accounting. Duplicate keys, duplicate fingerprints, missing issuer evidence, and unbounded clone fanout still fail closed.

## Contribution Statuses

Packet identity evidence is downgraded instead of being silently dropped:

- `verified`: issuer identity, public key, attestation, signature ref, and Sybil ledger context match the selected profile.
- `provisional`: useful in research or partial runs, but not production packet capital.
- `diagnostic`: preserved for repair tasks and residual accounting.
- `quarantined`: unsafe for runtime contribution until evidence is repaired.
- `rejected`: cannot contribute under the selected profile.

Queue priority, signed identity, declared status, and registry metadata cannot promote a packet to `settled`.

## Records

- `CryptographicAgentIdentity`: agent id, public key id, signature suite, public key, fingerprint, policy digest, model/tool digests, revocation/expiry flags, and identity signature.
- `AgentIdentityAttestation`: signed statement that binds an identity to finite evidence references.
- `AgentIdentityCheckReport`: fail-closed signature, digest, fingerprint, revocation, expiry, and policy-digest report.
- `SybilResistancePolicy`: trust profile, uniqueness, revocation, expiry, issuer/fleet quotas, required evidence, and clone-fanout policy.
- `SybilResistanceLedger`: accepted/rejected agent ids, accepted public-key ids, duplicate keys, failed signatures, fleet overrepresentation, missing evidence, clone groups, and residual ledger.

## Signature Suite Boundary

Ed25519 is the first implemented suite. Runtime and certificate logic depends only on explicit suite names and verifier-provider outputs, so future providers such as post-quantum signatures can be added without changing ECPT semantics.

Canonical signed payload serialization is:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
```

The core package does not import `cryptography` at import time. Verification returns a diagnostic, fail-closed report when the optional `[identity]` extra is unavailable.

## CLI

```powershell
uv run pic identity explain-profile --profile production
uv run pic identity verify --identity examples/identity/agent_identity_alice.json
uv run pic identity verify-attestation --attestation examples/identity/packet_attestation.json --identities examples/identity/agent_identities.json
uv run pic identity sybil-check --population examples/agent_population_signed.json
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production --identity-context identity-context.json
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

Development mode remains backward-compatible with unsigned examples. Production mode is intentionally stricter, but it emits deterministic diagnostics and residual ledgers rather than crashing.

## What Cryptographic Identity Proves

Cryptographic identity proves protocol-relative control of a signing key. It does not prove legal identity, real-world personhood, organizational authority, or global uniqueness.
