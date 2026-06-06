"""Theory audit composition for TeX artifacts."""

from __future__ import annotations

from pathlib import Path

from percolation_inversion_compiler.core.checker import (
    TheoryAuditReport,
    audit_registry_projection,
)
from percolation_inversion_compiler.core.coverage import (
    CoverageStatus,
    ExternalObligationCatalog,
    TheoryImplementationRecord,
    TheoryItem,
)
from percolation_inversion_compiler.io.snapshots import snapshot_delta
from percolation_inversion_compiler.io.tex import (
    count_mr_records_by_category,
    extract_artifact,
    extract_theory_coverage,
)
from percolation_inversion_compiler.io.zenodo import validate_canonical_source


def _implementation_record(item: TheoryItem) -> TheoryImplementationRecord:
    obligation_id = f"obligation:{item.item_id}"
    proof_obligations = item.proof_obligation_ids or (
        [obligation_id]
        if item.coverage_status
        in {
            CoverageStatus.EXTERNAL_OBLIGATION,
            CoverageStatus.UNSUPPORTED,
            CoverageStatus.PARTIAL,
        }
        else []
    )
    checker_refs = item.checker_refs or [
        ref
        for ref in item.implementation_refs
        if "check" in ref.lower() or "checker" in ref.lower()
    ]
    schema_refs = item.schema_refs
    return TheoryImplementationRecord(
        item_id=item.item_id,
        artifact=item.artifact,
        label=item.label,
        coverage_status=item.coverage_status,
        implementation_maturity=item.implementation_maturity,
        implementation_ref=item.implementation_refs[0] if item.implementation_refs else None,
        checker_ref=checker_refs[0] if checker_refs else None,
        schema_ref=schema_refs[0] if schema_refs else None,
        implementation_refs=item.implementation_refs,
        checker_refs=checker_refs,
        schema_refs=schema_refs,
        proof_obligation_ids=proof_obligations,
        residual_coordinates=item.residual_coordinates
        or ([f"residual:{item.item_id}"] if proof_obligations else []),
        external_failure_modes=item.external_failure_modes,
        obligation_category=item.obligation_category,
        verifier_route=item.verifier_route,
        verifier_contract=item.verifier_contract,
        accepted_evidence_kind=item.accepted_evidence_kind,
        residual_policy=item.residual_policy,
        safe_default=item.safe_default,
        failure_modes=item.failure_modes,
    )


def _unimplemented_by_section(items: list[TheoryItem]) -> dict[str, list[TheoryItem]]:
    grouped: dict[str, list[TheoryItem]] = {}
    for item in items:
        if item.coverage_status != CoverageStatus.UNSUPPORTED:
            continue
        grouped.setdefault(item.section or "unsectioned", []).append(item)
    return grouped


def _coverage_delta(counts: dict[str, int]) -> dict[str, int]:
    implemented_total = (
        counts.get(CoverageStatus.IMPLEMENTED_CONSTRUCTIVE.value, 0)
        + counts.get(CoverageStatus.IMPLEMENTED_CHECKER.value, 0)
        + counts.get(CoverageStatus.IMPLEMENTED_SCHEMA.value, 0)
    )
    unimplemented_total = (
        counts.get(CoverageStatus.PARTIAL.value, 0)
        + counts.get(CoverageStatus.EXTERNAL_OBLIGATION.value, 0)
        + counts.get(CoverageStatus.UNSUPPORTED.value, 0)
    )
    return {
        "implemented_total": implemented_total,
        "unimplemented_total": unimplemented_total,
        "unsupported_total": counts.get(CoverageStatus.UNSUPPORTED.value, 0),
        "external_obligation_total": counts.get(CoverageStatus.EXTERNAL_OBLIGATION.value, 0),
    }


def _count_by_field(
    records: list[TheoryImplementationRecord],
    field: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = getattr(record, field)
        if not isinstance(value, str) or not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _canonical_key_from_name(name: str) -> str | None:
    return {
        "Executable Capability Percolation Theory.tex": "ecpt",
        "Bottleneck Inversion Theory.tex": "bit",
        "Typed Reality Compilation.tex": "trc",
        "Salience-Queue Occupation Theory.tex": "sqot",
    }.get(name)


def _external_catalog_errors(records: list[TheoryImplementationRecord]) -> list[str]:
    errors: list[str] = []
    for record in records:
        missing: list[str] = []
        if not record.obligation_category:
            missing.append("obligation_category")
        if not record.verifier_route:
            missing.append("verifier_route")
        if not record.residual_policy:
            missing.append("residual_policy")
        if not record.safe_default:
            missing.append("safe_default")
        if not record.failure_modes:
            missing.append("failure_modes")
        if not record.residual_coordinates:
            missing.append("residual_coordinates")
        if missing:
            errors.append(f"{record.item_id}: missing {', '.join(missing)}")
    return errors


def audit_theory_source(
    source: str | Path,
    *,
    canonical_key: str | None = None,
    strict_projection: bool = True,
) -> TheoryAuditReport:
    """Build a deterministic audit report for one canonical TeX source."""

    path = Path(source)
    artifact = extract_artifact(path)
    coverage = extract_theory_coverage(path)
    extractor = artifact.extractor_output()
    projection_audits = [
        audit_registry_projection(
            extractor.claim_records(),
            registry,
            strict=strict_projection,
            extractor_artifact=extractor.artifact,
        )
        for registry in artifact.registries
    ]
    canonical = validate_canonical_source(path, canonical_key) if canonical_key else None
    unsupported = [
        item for item in coverage.items if item.coverage_status == CoverageStatus.UNSUPPORTED
    ]
    external = [
        item
        for item in coverage.items
        if item.coverage_status == CoverageStatus.EXTERNAL_OBLIGATION
    ]
    implementation_records = [_implementation_record(item) for item in coverage.items]
    finite_targets = [
        record
        for record in implementation_records
        if record.coverage_status in {CoverageStatus.PARTIAL, CoverageStatus.UNSUPPORTED}
    ]
    implemented_with_obligations = [
        record
        for record in implementation_records
        if record.coverage_status != CoverageStatus.UNSUPPORTED and record.proof_obligation_ids
    ]
    external_records = [
        record
        for record in implementation_records
        if record.coverage_status == CoverageStatus.EXTERNAL_OBLIGATION
    ]
    category_summary = _count_by_field(external_records, "obligation_category")
    route_summary = _count_by_field(external_records, "verifier_route")
    snapshot_key = canonical_key or _canonical_key_from_name(path.name)
    return TheoryAuditReport(
        source=str(path),
        artifact=path.name,
        canonical_key=canonical_key,
        canonical=canonical,
        coverage=coverage,
        projection_audits=projection_audits,
        bit_mr_counts=count_mr_records_by_category(artifact.mr_records),
        coverage_delta=_coverage_delta(coverage.counts_by_status()),
        snapshot_delta=snapshot_delta(
            artifact_key=snapshot_key,
            coverage_counts=coverage.counts_by_status(),
            external_category_summary=category_summary,
        ),
        unimplemented_by_section=_unimplemented_by_section(coverage.items),
        external_obligation_catalog=ExternalObligationCatalog(
            artifact=path.name,
            obligations=external_records,
            category_summary=category_summary,
            verifier_route_summary=route_summary,
        ),
        external_obligation_category_summary=category_summary,
        external_verifier_route_summary=route_summary,
        external_catalog_errors=_external_catalog_errors(external_records),
        finite_constructive_targets=finite_targets,
        implemented_with_obligations=implemented_with_obligations,
        unsupported_items=unsupported,
        external_obligation_items=external,
    )
