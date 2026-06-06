"""Validate the project CITATION.cff fields used by CI."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOIS = {
    "10.5281/zenodo.20535654",
    "10.5281/zenodo.20545356",
    "10.5281/zenodo.20554083",
}


def main() -> int:
    data = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    required_fields = ["cff-version", "message", "title", "authors", "license", "references"]
    missing = [field for field in required_fields if field not in data]
    references = data.get("references", [])
    dois = {reference.get("doi") for reference in references if isinstance(reference, dict)}
    missing_dois = sorted(REQUIRED_DOIS - dois)
    failures = [f"missing field: {field}" for field in missing]
    failures.extend(f"missing DOI reference: {doi}" for doi in missing_dois)
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
