# Production Readiness

`pic doctor` is the operational readiness interface for CI systems and
autonomous agents. It reports whether the installed package or source checkout
has the schema registry, snapshots, route bindings, optional adapters,
provenance, security metadata, and status policy needed for fail-closed use.

For a PyPI-installed package, start with commands that do not require repository
fixtures:

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
pic agent intake --text "Candidate packet: preserve residuals." --profile development
pic snapshot list
pic schema --type AgentIntakeReport
```

Commands that read `examples/...`, canonical TeX files, or release artifacts
require a source checkout. For full practical use, install `uv`, clone the
repository, and sync all extras:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

## Profiles

```powershell
uv run pic doctor --profile development --fail-on never
uv run pic doctor --profile research --fail-on never
uv run pic doctor --profile production --fail-on never
uv run pic doctor --profile production --required-route adapters.domain.verify_trc_telemetry_calibration --fail-on never
uv run pic doctor --profile production --required-route ecpt.adapters.proxy.verify_target_contract --fail-on never
```

`development` accepts metadata-only evidence for local experimentation.
`research` keeps warnings visible. `controlled` and `federated` are useful for
signed internal or multi-issuer fleets. `production` and `adversarial` require
deterministic provenance or canonical source checks, available route bindings,
optional adapter visibility, security metadata, and identity-ready runtime
context before signed packet issuers can become verified packet capital.

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

## Identity Readiness

For production runtime steps, derive accepted identity context from a signed
population and pass it into the runtime:

```powershell
uv run pic identity explain-profile --profile production
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic runtime health --state examples/runtime_state.json --profile production
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production --identity-context identity-context.json
```

`RuntimeHealthReport` includes `accepted_agent_context_present`,
`accepted_public_key_context_present`, `cryptographic_identity_required`,
`can_promote_unsigned_packets`, and `production_identity_ready`. If production
identity context is missing, packets remain diagnostic or rejected with residual
coordinates rather than being silently promoted.
