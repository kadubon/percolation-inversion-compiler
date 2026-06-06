# Provenance And SBOM

v0.2.1 adds deterministic provenance artifacts for release and downstream agent
deployment. The core uses SHA-256 manifests and does not store signing keys.
These artifacts protect certificate schemas, snapshots, examples, and release
metadata from unnoticed drift.

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

## SBOM

Generate a deterministic dependency inventory:

```powershell
uv run python scripts\generate_sbom.py --output dist\percolation-inversion-compiler-0.2.1.sbom.json
```

The SBOM is intended as a release asset and audit input. It is not a substitute
for `pip-audit`, Bandit, Gitleaks, CodeQL, or Zizmor.

## Security Boundary

The provenance manifest is hash-based. It does not imply a cryptographic
signature unless `signed` and `signature_ref` are populated by an external
signing process. Private keys must not be stored in this repository.
