"""Canonical Zenodo metadata and checksum validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen


@dataclass(frozen=True)
class CanonicalRecord:
    doi: str
    record_id: int
    title: str
    tex_filename: str
    tex_md5: str
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
    ),
}


def md5_file(path: str | Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
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
    checksum = md5_file(path)
    record = candidates[0]
    return {
        "source": str(path),
        "doi": record.doi,
        "record_id": record.record_id,
        "title": record.title,
        "expected_md5": record.tex_md5,
        "actual_md5": checksum,
        "matches": checksum.lower() == record.tex_md5.lower(),
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
