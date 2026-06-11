"""Validate the project CITATION.cff fields used by CI."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOIS = {
    "10.5281/zenodo.20535654",
    "10.5281/zenodo.20545356",
    "10.5281/zenodo.20554083",
    "10.5281/zenodo.20526451",
    "10.5281/zenodo.20476200",
}
EXPECTED_REPOSITORY = "https://github.com/kadubon/percolation-inversion-compiler"
EXPECTED_VERSION = "0.4.1"
EXPECTED_DATE_RELEASED = "2026-06-11"
EXPECTED_CONCEPT_DOI = "10.5281/zenodo.20569166"


def main() -> int:
    data = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    required_fields = ["cff-version", "message", "title", "authors", "license", "references"]
    missing = [field for field in required_fields if field not in data]
    references = data.get("references", [])
    dois = {reference.get("doi") for reference in references if isinstance(reference, dict)}
    missing_dois = sorted(REQUIRED_DOIS - dois)
    failures = [f"missing field: {field}" for field in missing]
    failures.extend(f"missing DOI reference: {doi}" for doi in missing_dois)
    if data.get("repository-code") != EXPECTED_REPOSITORY:
        failures.append("repository-code must be the public GitHub repository URL")
    if "OWNER/" in str(data.get("repository-code", "")):
        failures.append("repository-code still contains a placeholder owner")
    if str(data.get("version")) != EXPECTED_VERSION:
        failures.append(f"version must be {EXPECTED_VERSION}")
    if data.get("doi") != EXPECTED_CONCEPT_DOI:
        failures.append(f"top-level doi must be {EXPECTED_CONCEPT_DOI}")
    if data.get("license") != "Apache-2.0":
        failures.append("license must be Apache-2.0")
    if data.get("date-released") != EXPECTED_DATE_RELEASED:
        failures.append(f"date-released must be {EXPECTED_DATE_RELEASED}")
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
