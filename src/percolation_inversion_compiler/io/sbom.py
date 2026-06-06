"""Deterministic SBOM builders for release and production readiness."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from pydantic import BaseModel, Field

from percolation_inversion_compiler import __version__


def _metadata_value(package_metadata: Any, key: str, default: str = "UNKNOWN") -> str:
    if key not in package_metadata:
        return default
    value = package_metadata[key]
    return str(value) if value else default


def _normalized_name(name: str) -> str:
    return name.lower().replace("_", "-")


class SBOMComponent(BaseModel):
    """One Python distribution component in a deterministic SBOM."""

    name: str
    version: str
    license: str = "UNKNOWN"
    purl: str | None = None


class SBOMManifest(BaseModel):
    """Backward-compatible PIC SBOM manifest."""

    bomFormat: str = "PIC-SBOM"
    schemaVersion: str = "1.1"
    packageVersion: str = __version__
    components: list[SBOMComponent] = Field(default_factory=list)


def installed_components() -> list[SBOMComponent]:
    """Return installed Python distributions as deterministic SBOM components."""

    components: list[SBOMComponent] = []
    distributions = sorted(
        metadata.distributions(),
        key=lambda item: _metadata_value(item.metadata, "Name").lower(),
    )
    for distribution in distributions:
        name = _metadata_value(distribution.metadata, "Name")
        version = distribution.version
        components.append(
            SBOMComponent(
                name=name,
                version=version,
                license=_metadata_value(distribution.metadata, "License"),
                purl=f"pkg:pypi/{_normalized_name(name)}@{version}",
            )
        )
    return components


def build_pic_sbom() -> SBOMManifest:
    """Build the legacy PIC-SBOM manifest."""

    return SBOMManifest(components=installed_components())


def build_cyclonedx_sbom() -> dict[str, object]:
    """Build a CycloneDX 1.6 JSON document without adding runtime dependencies."""

    components = []
    for component in installed_components():
        components.append(
            {
                "type": "library",
                "name": component.name,
                "version": component.version,
                "licenses": [{"license": {"name": component.license}}],
                "purl": component.purl,
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:00000000-0000-0000-0000-000000000000",
        "version": 1,
        "metadata": {
            "component": {
                "type": "library",
                "name": "percolation-inversion-compiler",
                "version": __version__,
                "licenses": [{"license": {"id": "Apache-2.0"}}],
            }
        },
        "components": components,
    }


def build_sbom_document(format_name: str = "pic") -> dict[str, object]:
    """Build a deterministic SBOM document in PIC or CycloneDX JSON format."""

    normalized = format_name.lower()
    if normalized == "pic":
        return build_pic_sbom().model_dump(mode="json")
    if normalized == "cyclonedx":
        return build_cyclonedx_sbom()
    raise ValueError("SBOM format must be one of: pic, cyclonedx")
