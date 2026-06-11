# Provenance And SBOM

v0.3.4 uses deterministic provenance artifacts for release and downstream agent
deployment. The core uses SHA-256 manifests and does not store signing keys.
GitHub artifact attestations can be required as an additional production check.
These artifacts protect certificate schemas, snapshots, examples, SBOMs, and
release metadata from unnoticed drift.

## Schema Digest

`pic schema --all --output-dir schemas` writes individual JSON Schema files,
`bundle.schema.json`, and `schema-digest.json`. The digest file lets other
language implementations verify that their generated schema bundle matches the
release artifact.

## Provenance Manifest

Create and verify a release manifest:

```powershell
uv run pic provenance create --schema-dir schemas --output provenance.json
uv run pic provenance verify --manifest provenance.json
```

`ProvenanceManifest` records path, size, media type, and SHA-256 for release
metadata, examples, snapshots, and generated schemas. If any file changes,
verification fails and production doctor treats the provenance as invalid.
Release builds can add distributable artifacts explicitly:

```powershell
uv run pic provenance create --schema-dir schemas --sbom-ref dist\percolation-inversion-compiler-0.3.6.sbom.json --artifact-ref dist\percolation_inversion_compiler-0.3.6-py3-none-any.whl --artifact-ref dist\percolation_inversion_compiler-0.3.6.tar.gz --output provenance.json
```

For GitHub-attested release assets:

```powershell
uv run pic provenance verify --manifest release-provenance.json --require-attestation
```

`--require-attestation` checks attestation subject names, SHA-256 subject
digests, issuer, predicate type, bundle reference, and verified status in the
manifest. Full Sigstore verification is performed by the GitHub Actions release
workflow; the package core remains deterministic and keyless.

## SBOM

Generate a deterministic dependency inventory:

```powershell
uv run pic sbom create --format pic --output dist\percolation-inversion-compiler-0.3.6.sbom.json
uv run pic sbom create --format cyclonedx --output dist\percolation-inversion-compiler-0.3.6.cyclonedx.json
```

The PIC-SBOM format is retained for backward compatibility. CycloneDX JSON is
the standard release SBOM for v0.3.4. SBOM output is an audit input, not a
substitute for `pip-audit`, Bandit, Gitleaks, CodeQL, or Zizmor.

## Security Boundary

The provenance manifest is hash-based. It does not imply a cryptographic
signature unless attestation or signature fields are populated by the release
workflow or another external signing process. Private keys must not be stored in
this repository.
