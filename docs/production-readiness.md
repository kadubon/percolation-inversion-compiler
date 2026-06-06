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
```

`development` accepts metadata-only evidence for local experimentation.
`research` keeps warnings visible. `production` requires deterministic
provenance or canonical source checks, available route bindings, optional
adapter visibility, and security metadata.

## Provenance-Backed Production

For TeX-free deployment, generate schemas and a provenance manifest:

```powershell
uv run pic schema --all --output-dir schemas
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
uv run pic doctor --profile production --provenance provenance.json --fail-on fail
```

A valid provenance manifest can substitute for local canonical TeX in production
doctor checks. It does not prove new mathematical claims; it proves that the
schema bundle, snapshots, examples, and release metadata match the manifest.

## Interpreting Production Output

Production readiness means the SDK can be used as a finite certificate and
obligation ledger compiler. It does not mean external physical, oracle,
simulator, or ASI-proxy claims are settled. Routes with
`external_domain_required` remain explicit `ExternalProofObligation` boundaries
until a domain verifier supplies accepted replayable evidence.
