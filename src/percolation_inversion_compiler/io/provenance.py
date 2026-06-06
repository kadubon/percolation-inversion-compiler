"""Deterministic SHA-256 provenance manifests for release and schema artifacts."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from percolation_inversion_compiler import __version__


class ProvenanceManifestEntry(BaseModel):
    """One file entry in a deterministic provenance manifest."""

    path: str
    sha256: str
    size_bytes: int
    media_type: str = "application/octet-stream"


class SchemaBundleDigest(BaseModel):
    """Digest summary for a generated schema bundle."""

    schema_dir: str
    entries: list[ProvenanceManifestEntry] = Field(default_factory=list)
    aggregate_sha256: str


class AttestationRecord(BaseModel):
    """GitHub/Sigstore-style artifact attestation metadata.

    The core package verifies local SHA-256 subject consistency. Full signature
    and transparency-log validation stays behind the release workflow and
    optional external tooling.
    """

    attestation_id: str
    subject_name: str
    subject_sha256: str
    issuer: str
    predicate_type: str
    bundle_ref: str | None = None
    verified: bool = False
    verified_at: str | None = None


class ReleaseArtifactManifest(BaseModel):
    """Release-asset manifest with deterministic local digests."""

    manifest_id: str = "percolation-inversion-compiler-release-artifacts"
    package_version: str = __version__
    entries: list[ProvenanceManifestEntry] = Field(default_factory=list)
    aggregate_sha256: str


class ProvenanceManifest(BaseModel):
    """Release provenance manifest for agents and downstream implementers."""

    manifest_id: str = "percolation-inversion-compiler-provenance"
    schema_version: str = "provenance-manifest-1.1"
    package_version: str = __version__
    entries: list[ProvenanceManifestEntry] = Field(default_factory=list)
    aggregate_sha256: str
    signed: bool = False
    signature_ref: str | None = None
    sbom_ref: str | None = None
    attestations: list[AttestationRecord] = Field(default_factory=list)
    attestation_subjects: list[str] = Field(default_factory=list)
    issuer: str | None = None
    predicate_type: str | None = None
    bundle_ref: str | None = None
    verified_at: str | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix in {".md", ".txt"}:
        return "text/plain"
    if suffix in {".toml", ".cff", ".yml", ".yaml"}:
        return "text/plain"
    if suffix == ".whl":
        return "application/zip"
    if suffix == ".gz":
        return "application/gzip"
    return "application/octet-stream"


def file_entry(path: Path, *, base_dir: Path = Path(".")) -> ProvenanceManifestEntry:
    data = path.read_bytes()
    try:
        display_path = path.relative_to(base_dir).as_posix()
    except ValueError:
        display_path = path.as_posix()
    return ProvenanceManifestEntry(
        path=display_path,
        sha256=sha256_bytes(data),
        size_bytes=len(data),
        media_type=_media_type(path),
    )


def aggregate_digest(entries: list[ProvenanceManifestEntry]) -> str:
    joined = "\n".join(f"{entry.path}:{entry.sha256}:{entry.size_bytes}" for entry in entries)
    return sha256_bytes(joined.encode("utf-8"))


def schema_bundle_digest(schema_dir: Path, *, base_dir: Path = Path(".")) -> SchemaBundleDigest:
    entries = [
        file_entry(path, base_dir=base_dir)
        for path in sorted(schema_dir.glob("*.json"))
        if path.is_file()
    ]
    try:
        schema_dir_display = schema_dir.relative_to(base_dir).as_posix()
    except ValueError:
        schema_dir_display = schema_dir.as_posix()
    return SchemaBundleDigest(
        schema_dir=schema_dir_display,
        entries=entries,
        aggregate_sha256=aggregate_digest(entries),
    )


def default_provenance_paths(*, schema_dir: Path | None = None) -> list[Path]:
    paths = [
        Path("pyproject.toml"),
        Path("CITATION.cff"),
        Path("README.md"),
        Path("LICENSE"),
        Path("NOTICE"),
        Path("SECURITY.md"),
        Path("THIRD_PARTY_LICENSES.md"),
        Path("CHANGELOG.md"),
        Path("examples/evidence_artifact_content.json"),
        Path("examples/evidence_envelope.json"),
        Path("examples/external_obligations.json"),
        Path("examples/minimal_invalid_main_frontier.json"),
        Path("src/percolation_inversion_compiler/data/snapshots/ecpt.json"),
        Path("src/percolation_inversion_compiler/data/snapshots/bit.json"),
        Path("src/percolation_inversion_compiler/data/snapshots/trc.json"),
    ]
    if schema_dir is not None:
        paths.extend(sorted(schema_dir.glob("*.json")))
    return [path for path in paths if path.exists() and path.is_file()]


def create_provenance_manifest(
    *,
    schema_dir: Path | None = None,
    base_dir: Path = Path("."),
    sbom_ref: str | None = None,
    artifact_refs: Sequence[str | Path] | None = None,
) -> ProvenanceManifest:
    paths = default_provenance_paths(schema_dir=schema_dir)
    if sbom_ref is not None:
        sbom_path = Path(sbom_ref)
        if sbom_path.exists() and sbom_path.is_file():
            paths.append(sbom_path)
    for artifact_ref in artifact_refs or []:
        artifact_path = Path(artifact_ref)
        if artifact_path.exists() and artifact_path.is_file():
            paths.append(artifact_path)
    entries = [file_entry(path, base_dir=base_dir) for path in sorted(paths)]
    return ProvenanceManifest(
        entries=entries,
        aggregate_sha256=aggregate_digest(entries),
        sbom_ref=sbom_ref,
        attestation_subjects=[entry.path for entry in entries],
    )


def verify_provenance_manifest(
    manifest: ProvenanceManifest,
    *,
    base_dir: Path = Path("."),
    require_attestation: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    entries: list[ProvenanceManifestEntry] = []
    manifest_entry_by_path = {entry.path: entry for entry in manifest.entries}
    for entry in manifest.entries:
        path = base_dir / entry.path
        if not path.exists() or not path.is_file():
            reasons.append(f"provenance entry is missing: {entry.path}")
            continue
        current = file_entry(path, base_dir=base_dir)
        entries.append(current)
        if current.sha256 != entry.sha256:
            reasons.append(f"sha256 mismatch for {entry.path}")
        if current.size_bytes != entry.size_bytes:
            reasons.append(f"size mismatch for {entry.path}")
    if aggregate_digest(entries) != manifest.aggregate_sha256:
        reasons.append("provenance aggregate digest mismatch")
    if require_attestation:
        if not manifest.attestations:
            reasons.append("attestation is required but manifest has no attestations")
        for subject in manifest.attestation_subjects:
            if subject not in manifest_entry_by_path:
                reasons.append(f"attestation subject has no provenance entry: {subject}")
        for attestation in manifest.attestations:
            subject_entry = manifest_entry_by_path.get(attestation.subject_name)
            if subject_entry is None:
                reasons.append(
                    f"attestation subject is absent from manifest entries: "
                    f"{attestation.subject_name}"
                )
                continue
            if attestation.subject_sha256.lower() != subject_entry.sha256:
                reasons.append(f"attestation subject digest mismatch: {attestation.subject_name}")
            if not attestation.issuer:
                reasons.append(f"attestation issuer is missing: {attestation.subject_name}")
            if not attestation.predicate_type:
                reasons.append(f"attestation predicate_type is missing: {attestation.subject_name}")
            if not attestation.bundle_ref:
                reasons.append(f"attestation bundle_ref is missing: {attestation.subject_name}")
            if not attestation.verified:
                reasons.append(f"attestation is not marked verified: {attestation.subject_name}")
    return not reasons, sorted(set(reasons))
