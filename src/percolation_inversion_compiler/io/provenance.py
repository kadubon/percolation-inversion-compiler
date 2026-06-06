"""Deterministic SHA-256 provenance manifests for release and schema artifacts."""

from __future__ import annotations

import hashlib
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


class ProvenanceManifest(BaseModel):
    """Release provenance manifest for agents and downstream implementers."""

    manifest_id: str = "percolation-inversion-compiler-provenance"
    schema_version: str = "provenance-manifest-1.0"
    package_version: str = __version__
    entries: list[ProvenanceManifestEntry] = Field(default_factory=list)
    aggregate_sha256: str
    signed: bool = False
    signature_ref: str | None = None
    sbom_ref: str | None = None


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
) -> ProvenanceManifest:
    paths = default_provenance_paths(schema_dir=schema_dir)
    if sbom_ref is not None:
        sbom_path = Path(sbom_ref)
        if sbom_path.exists() and sbom_path.is_file():
            paths.append(sbom_path)
    entries = [file_entry(path, base_dir=base_dir) for path in sorted(paths)]
    return ProvenanceManifest(
        entries=entries,
        aggregate_sha256=aggregate_digest(entries),
        sbom_ref=sbom_ref,
    )


def verify_provenance_manifest(
    manifest: ProvenanceManifest,
    *,
    base_dir: Path = Path("."),
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    entries: list[ProvenanceManifestEntry] = []
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
    return not reasons, sorted(set(reasons))
