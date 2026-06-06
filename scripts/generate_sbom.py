"""Generate a small deterministic SBOM-style dependency inventory."""

from __future__ import annotations

import argparse
import json
from importlib import metadata
from pathlib import Path
from typing import Any


def _metadata_value(package_metadata: Any, key: str, default: str = "UNKNOWN") -> str:
    if key not in package_metadata:
        return default
    value = package_metadata[key]
    return str(value) if value else default


def build_sbom() -> dict[str, object]:
    components: list[dict[str, str]] = []
    distributions = sorted(
        metadata.distributions(),
        key=lambda item: _metadata_value(item.metadata, "Name").lower(),
    )
    for distribution in distributions:
        components.append(
            {
                "name": _metadata_value(distribution.metadata, "Name"),
                "version": distribution.version,
                "license": _metadata_value(distribution.metadata, "License"),
            }
        )
    return {
        "bomFormat": "PIC-SBOM",
        "schemaVersion": "1.0",
        "components": components,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(build_sbom(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
