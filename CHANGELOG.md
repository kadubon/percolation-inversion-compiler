# Changelog

## v0.2.2 - 2026-06-06

- Adds settlement scope semantics to verifier resolutions and route bindings so finite replay/contract scope is separated from residual physical, oracle, policy, or domain obligations.
- Adds route-scoped production doctor checks and `pic routes explain` for agent-selected verifier route sets.
- Adds GitHub artifact-attestation metadata support in provenance manifests and `pic provenance verify --require-attestation`.
- Adds CycloneDX SBOM generation through `pic sbom create --format cyclonedx`.
- Adds strict TeX grammar diagnostics and `pic parse audit` so unknown theorem-like shapes and malformed MR macros are not silently ignored.

## v0.2.1 - 2026-06-06

- Adds canonical-to-implementation discharge route bindings for external verifier routes.
- Adds production evidence policy checks for replayable content hashes and provenance-bound hooks.
- Adds deterministic provenance manifests, schema digest output, SBOM generation, and production doctor provenance support.
- Expands verifier SDK docs for agent-facing ASI-proxy phase-control workflows without claiming unobserved physical or ASI proof.

## v0.2.0 - 2026-06-06

- Adds fail-closed status, ledger, frontier, and TRC compile behavior for agent-facing use.
- Adds evidence provenance records and deterministic external-verifier envelope checks.
- Adds production readiness profiles, SHA-256 canonical manifests, and hardened citation validation.
- Keeps ASI language protocol-relative: the project accelerates ASI-proxy phase-control workflows without claiming to prove unobserved ASI or physical claims.

## v0.1.0 - 2026-06-06

- Initial Apache-2.0 public release with ECPT/BIT/TRC finite certificate tooling, derived snapshots, schemas, CLI, CI, and security workflow.
