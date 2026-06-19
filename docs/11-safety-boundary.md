# Safety Boundary

This repository is intentionally useful for agents, but it is fail-closed. It helps agents route finite evidence and obligations; it does not grant authority to perform unsafe execution or claim unverified outcomes.

## Non-Claims

- No package-level proof of real ASI.
- No proof of unobserved physical, simulator, oracle, or policy outcomes.
- No requirement for self-rewrite, fine-tuning, or model-weight changes.
- No claim that a declared `agent_id` proves legal identity, real-world personhood, or world-global uniqueness.
- No promotion from declared status, registry metadata, snapshot metadata, queue priority, or agent text.
- No implicit settlement of external obligations.

## Execution Boundary

The standard runtime executor is allowlist-based. It supports finite verification tasks such as evidence verification, schema validation, snapshot verification, parse audit, local packet ingestion, route execution, runtime step/apply/compare/certify, and store operations. Arbitrary shell commands and repository mutation are never granted by intake. Live connectors are bounded and candidate-only by default when an explicit source is supplied; use `--no-allow-live-connectors` for local-only runs.

Production service defaults:

- bind to loopback unless configured otherwise;
- require bearer authentication;
- allow bounded explicit-source live intake only as candidate packet input;
- avoid returning stack traces, secrets, private keys, or local absolute paths;
- preserve residual ledgers rather than hiding unresolved obligations.

Default-live communication does not grant background crawling, autonomous polling, shell
execution, repository mutation, unsafe tool use, or hidden promotion from `accepted` or
`workflow_usable` to `settled`.

ASI-proxy phase-control is an operational coordination target: agents can use
PIC to exchange bounded candidate work, route verifier obligations, and build
auditable reusable packets. The package does not certify that the network has
produced real ASI, an unobserved physical transition, or oracle truth.

## Status Discipline

Use `workflow_usable` for beginner/onboarding checks such as `pic agent check`.
`pic agent check --compact` is a short routing contract for humans, CI, and
agents; it intentionally omits nested runtime detail but does not loosen status
semantics. `pic agent runbook` gives commands, schemas, and fields to inspect;
it is not an execution grant.
Use `operationally_usable` for stricter profile-aware routing decisions. Use
`settled` only for scoped finite obligations actually discharged by verifier
rules. A useful recommendation may still have `settled=false`.

## Identity Boundary

Production collective certificates should require cryptographic agent identities and a `SybilResistanceLedger`. Cryptographic identity proves protocol-relative control of a signing key. It does not prove legal identity, real-world personhood, organizational authority, or global uniqueness.

Sybil resistance is also protocol-relative. It rejects duplicate `agent_id` values, duplicate public-key IDs, duplicate public-key fingerprints, revoked or expired identities, failed signatures, issuer overrepresentation, fleet overrepresentation, and clone fanout according to the selected profile and declared policy. Homogeneous fleets are allowed only when distinct public keys, declared fleet membership, bounded quotas, and residual accounting satisfy the profile. A rejected identity remains visible in reasons and residual ledgers.

## Residual Ledgers

Residual coordinates are part of the result, not an error to suppress. They carry missing evidence, external-domain limits, fallback proxy use, stale evidence, hidden-injection rejection, verification backlog, or resource mismatch.

## Recommended Agent Policy

1. Ingest packet candidates.
2. Verify evidence and semantic edges.
3. Promote only packets that pass the production promotion policy.
4. Schedule with SQOT while preserving diagnostic reserve.
5. Execute only allowlisted finite tasks.
6. Apply results into the runtime store.
7. Certify only resource-matched protocol-relative improvements.
