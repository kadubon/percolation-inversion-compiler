# Production Readiness

`pic doctor` is the operational readiness interface for CI systems and
autonomous agents. It reports whether the installed package or source checkout
has the schema registry, snapshots, route bindings, optional adapters,
provenance, security metadata, and status policy needed for fail-closed use.

## Profiles

```powershell
uv run pic doctor --profile development --fail-on never
uv run pic doctor --profile research --fail-on never
uv run pic doctor --profile production --fail-on never
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --fail-on never
uv run pic doctor --profile production --required-route ecpt.adapters.proxy.verify_target_contract --fail-on never
```

`development` accepts metadata-only evidence for local experimentation.
`research` keeps warnings visible. `production` requires deterministic
provenance or canonical source checks, available route bindings, optional
adapter visibility, and security metadata.

`--required-route` scopes production checks to the adapter routes an agent is
actually about to use. Missing optional dependencies for unused routes are
reported but do not fail the route-scoped readiness decision. The doctor summary
also returns `external_domain_required_routes`, `contract_enforced_routes`,
`replay_residual_routes`, and `residual_external_obligation_count`.

## Provenance-Backed Production

For TeX-free deployment, generate schemas and a provenance manifest:

```powershell
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic doctor --profile production --provenance provenance.json --fail-on fail
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --provenance provenance.json --fail-on fail
uv run pic doctor --profile production --required-route ecpt.adapters.proxy.verify_target_contract --provenance provenance.json --fail-on fail
```

A valid provenance manifest can substitute for local canonical TeX in production
doctor checks. It does not prove new mathematical claims; it proves that the
schema bundle, snapshots, examples, and release metadata match the manifest.

GitHub release attestations can be required separately:

```powershell
uv run pic provenance verify --manifest release-provenance.json --require-attestation
```

This mode is intended for release artifacts built and attested by GitHub
Actions. A locally generated manifest without attestation metadata remains valid
for deterministic hash checking but fails the attestation-required check.

## Interpreting Production Output

Production readiness means the SDK can be used as a finite certificate and
obligation ledger compiler. It does not mean external physical, oracle,
simulator, or ASI-proxy claims are settled. Routes with
`external_domain_required` remain explicit `ExternalProofObligation` boundaries
until a domain verifier supplies accepted replayable evidence.
