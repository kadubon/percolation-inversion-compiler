from __future__ import annotations

import os
from pathlib import Path

import pytest

from percolation_inversion_compiler.io import (
    audit_theory_source,
    count_mr_records_by_category,
    extract_artifact,
    extract_filecontents,
    extract_mr_records,
    extract_theory_coverage,
    validate_canonical_source,
)


def test_filecontents_extraction_from_minimal_tex() -> None:
    tex = r"""
\begin{filecontents*}[overwrite]{claims.json}
{"schema_version":"x","artifact":"a","claims":[{"claim_id":"c","kind":"theorem","label":"C"}]}
\end{filecontents*}
"""
    blocks = extract_filecontents(tex)
    assert blocks[0].name == "claims.json"
    assert blocks[0].json_data()["claims"][0]["claim_id"] == "c"


def test_mr_extraction_from_minimal_bit_tex() -> None:
    tex = r"""
\MRClaim{THM-X}{inputs=a;witness=b;guarantee=c}
\MRDepends{THM-X}{WIT-A,WIT-B}
\MRCitation{ref}{10.1/example}{doi}
"""
    records = extract_mr_records(tex)
    assert [record.record_type for record in records] == ["claim", "depends", "citation"]
    assert records[1].fields["depends_on"] == ["WIT-A", "WIT-B"]


@pytest.mark.parametrize(
    ("key", "filename", "claim_count"),
    [
        ("ecpt", "Executable Capability Percolation Theory.tex", 9),
        ("bit", "Bottleneck Inversion Theory.tex", 18),
        ("trc", "Typed Reality Compilation.tex", 46),
        ("sqot", "Salience-Queue Occupation Theory.tex", 0),
    ],
)
def test_canonical_sources_when_present(key: str, filename: str, claim_count: int) -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    source = Path(canonical_dir) / filename
    canonical = validate_canonical_source(source, key)
    assert canonical["matches"]
    artifact = extract_artifact(source)
    assert sum(len(registry.claims) for registry in artifact.registries) == claim_count


@pytest.mark.parametrize(
    ("filename", "definitions", "claims"),
    [
        ("Executable Capability Percolation Theory.tex", 79, 35),
        ("Bottleneck Inversion Theory.tex", 22, 20),
        ("Typed Reality Compilation.tex", 70, 46),
        ("Salience-Queue Occupation Theory.tex", 59, 74),
    ],
)
def test_theory_coverage_counts_when_present(filename: str, definitions: int, claims: int) -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    coverage = extract_theory_coverage(Path(canonical_dir) / filename)
    assert coverage.definitions == definitions
    assert coverage.claims == claims
    assert coverage.items


@pytest.mark.parametrize(
    ("filename", "counts"),
    [
        (
            "Executable Capability Percolation Theory.tex",
            {
                "implemented_constructive": 18,
                "implemented_checker": 48,
                "implemented_schema": 18,
                "partial": 0,
                "external_obligation": 30,
                "unsupported": 0,
            },
        ),
        (
            "Bottleneck Inversion Theory.tex",
            {
                "implemented_constructive": 15,
                "implemented_checker": 24,
                "implemented_schema": 3,
                "partial": 0,
                "external_obligation": 0,
                "unsupported": 0,
            },
        ),
        (
            "Typed Reality Compilation.tex",
            {
                "implemented_constructive": 20,
                "implemented_checker": 52,
                "implemented_schema": 12,
                "partial": 0,
                "external_obligation": 32,
                "unsupported": 0,
            },
        ),
        (
            "Salience-Queue Occupation Theory.tex",
            {
                "implemented_constructive": 22,
                "implemented_checker": 78,
                "implemented_schema": 18,
                "partial": 0,
                "external_obligation": 15,
                "unsupported": 0,
            },
        ),
    ],
)
def test_theory_coverage_status_counts_when_present(
    filename: str,
    counts: dict[str, int],
) -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    coverage = extract_theory_coverage(Path(canonical_dir) / filename)
    assert coverage.counts_by_status() == counts


def test_bit_mr_record_category_counts_when_present() -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    source = Path(canonical_dir) / "Bottleneck Inversion Theory.tex"
    records = extract_mr_records(source.read_text(encoding="utf-8"))
    assert count_mr_records_by_category(records) == {
        "total": 92,
        "claims": 18,
        "witnesses": 9,
        "depends": 8,
        "citations": 53,
        "metadata": 4,
    }


@pytest.mark.parametrize(
    ("key", "filename", "external_count"),
    [
        ("ecpt", "Executable Capability Percolation Theory.tex", 30),
        ("trc", "Typed Reality Compilation.tex", 32),
        ("sqot", "Salience-Queue Occupation Theory.tex", 15),
    ],
)
def test_external_obligation_catalog_is_concrete_when_present(
    key: str,
    filename: str,
    external_count: int,
) -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    report = audit_theory_source(
        Path(canonical_dir) / filename,
        canonical_key=key,
        strict_projection=True,
    )
    catalog = report.external_obligation_catalog
    assert catalog is not None
    assert len(catalog.obligations) == external_count
    assert sum(catalog.category_summary.values()) == external_count
    assert sum(catalog.verifier_route_summary.values()) == external_count
    for obligation in catalog.obligations:
        assert obligation.obligation_category
        assert obligation.verifier_route
        assert obligation.verifier_contract
        assert obligation.accepted_evidence_kind
        assert obligation.residual_policy
        assert obligation.safe_default
        assert obligation.residual_coordinates
        assert obligation.failure_modes
        assert "non-finite-domain-claim" not in obligation.failure_modes
        assert "external-verifier-hook-required" in obligation.external_failure_modes
