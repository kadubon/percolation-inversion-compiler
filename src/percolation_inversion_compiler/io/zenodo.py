"""Canonical Zenodo metadata and checksum validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class CanonicalRecord:
    doi: str
    record_id: int
    title: str
    tex_filename: str
    tex_md5: str
    tex_sha256: str
    license_id: str = "cc-by-4.0"

    @property
    def api_url(self) -> str:
        return f"https://zenodo.org/api/records/{self.record_id}"


CANONICAL_RECORDS: dict[str, CanonicalRecord] = {
    "ecpt": CanonicalRecord(
        doi="10.5281/zenodo.20535654",
        record_id=20535654,
        title="Executable Capability Percolation Theory",
        tex_filename="Executable Capability Percolation Theory.tex",
        tex_md5="c4614418ce96155c605a5b0337b3e99c",
        tex_sha256="0a45e52c65112a93086b302e3642c85f24ca65b2f5638a1a66eac68afd4d3c7b",
    ),
    "bit": CanonicalRecord(
        doi="10.5281/zenodo.20545356",
        record_id=20545356,
        title=(
            "Bottleneck Inversion Theory: Machine-Readable Witness Calculus "
            "for Unlockable Potential"
        ),
        tex_filename="Bottleneck Inversion Theory.tex",
        tex_md5="20d11630520de9ea81f886b8b731772e",
        tex_sha256="078a4c55eb51bd7b2a4c07533bdff3ba9ed94ae604e2985ea81a26662a005ac2",
    ),
    "trc": CanonicalRecord(
        doi="10.5281/zenodo.20554083",
        record_id=20554083,
        title=(
            "Typed Reality Compilation: Operational Tolerance Allocation for "
            "Resource-Efficient Cyber-Physical Frontier Compilation"
        ),
        tex_filename="Typed Reality Compilation.tex",
        tex_md5="dfd71f38380e0db87f5537f65f035c32",
        tex_sha256="cd236045dd7d6608bbf031878d6c4083c8209ebdba60916ec6d550858f6bf79e",
    ),
}


class CanonicalManifestRecord(BaseModel):
    """Release-stable canonical artifact identity metadata."""

    artifact_key: str
    doi: str
    record_id: int
    title: str
    tex_filename: str
    tex_sha256: str
    tex_md5_legacy: str
    license_id: str = "cc-by-4.0"
    provenance_policy: str = "sha256-primary-md5-legacy-identity"


class CanonicalManifest(BaseModel):
    """Small derived manifest for canonical source integrity checks."""

    manifest_id: str = "percolation-inversion-compiler-canonical-manifest"
    schema_version: str = "canonical-manifest-2.0"
    records: dict[str, CanonicalManifestRecord] = Field(default_factory=dict)


def canonical_manifest() -> CanonicalManifest:
    return CanonicalManifest(
        records={
            key: CanonicalManifestRecord(
                artifact_key=key,
                doi=record.doi,
                record_id=record.record_id,
                title=record.title,
                tex_filename=record.tex_filename,
                tex_sha256=record.tex_sha256,
                tex_md5_legacy=record.tex_md5,
                license_id=record.license_id,
            )
            for key, record in CANONICAL_RECORDS.items()
        }
    )


def md5_file(path: str | Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_canonical_source(source: str | Path, key: str | None = None) -> dict[str, Any]:
    path = Path(source)
    candidates = (
        [CANONICAL_RECORDS[key]]
        if key is not None
        else [record for record in CANONICAL_RECORDS.values() if record.tex_filename == path.name]
    )
    if not candidates:
        raise ValueError(f"no canonical record matches {path.name!r}")
    md5_checksum = md5_file(path)
    sha256_checksum = sha256_file(path)
    record = candidates[0]
    return {
        "source": str(path),
        "doi": record.doi,
        "record_id": record.record_id,
        "title": record.title,
        "expected_md5": record.tex_md5,
        "actual_md5": md5_checksum,
        "expected_sha256": record.tex_sha256,
        "actual_sha256": sha256_checksum,
        "matches": sha256_checksum.lower() == record.tex_sha256.lower(),
        "md5_legacy_matches": md5_checksum.lower() == record.tex_md5.lower(),
        "integrity_algorithm": "sha256",
        "license": record.license_id,
    }


def fetch_zenodo_metadata(record: CanonicalRecord, timeout: float = 20.0) -> dict[str, Any]:
    parsed = urlparse(record.api_url)
    if parsed.scheme != "https" or parsed.netloc != "zenodo.org":
        raise ValueError("canonical metadata fetch only supports https://zenodo.org")
    with urlopen(record.api_url, timeout=timeout) as response:  # nosec B310
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Zenodo response was not a JSON object")
    return data
