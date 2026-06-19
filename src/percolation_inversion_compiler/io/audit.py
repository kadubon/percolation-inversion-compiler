"""Theory audit composition for TeX artifacts."""

from __future__ import annotations

from pathlib import Path

from percolation_inversion_compiler.core.checker import (
    TheoryAuditReport,
    TheoryAuditSuiteReport,
    TheoryFidelityReport,
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
    strict_tex_parse_report,
)
from percolation_inversion_compiler.io.zenodo import CANONICAL_RECORDS, validate_canonical_source


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
        "Abstraction Liquidity Theory.tex": "alt",
    }.get(name)


def canonical_suite_sources(canonical_dir: str | Path) -> dict[str, Path]:
    """Return the exact canonical-suite source paths, excluding non-suite papers."""

    root = Path(canonical_dir)
    return {key: root / record.tex_filename for key, record in CANONICAL_RECORDS.items()}


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


def theory_audit_cli_payload(
    source: str | Path,
    *,
    canonical_key: str | None,
    safety_invariants: list[str] | None = None,
) -> dict[str, object]:
    """Build the repeated specialized audit CLI payload used by ALT and SQOT."""

    path = Path(source)
    grammar = strict_tex_parse_report(path)
    coverage_record = extract_theory_coverage(path)
    audit = audit_theory_source(path, canonical_key=canonical_key, strict_projection=True)
    data: dict[str, object] = {
        "source": str(path),
        "strict_grammar": grammar.model_dump(mode="json"),
        "coverage": coverage_record.model_dump(mode="json"),
        "coverage_counts": coverage_record.counts_by_status(),
        "audit": audit.model_dump(mode="json"),
    }
    if safety_invariants is not None:
        data["safety_invariants"] = safety_invariants
    return data


def audit_canonical_suite(canonical_dir: str | Path) -> TheoryAuditSuiteReport:
    """Audit ECPT/BIT/TRC/SQOT/ALT canonical TeX as one reproducibility unit."""

    sources = canonical_suite_sources(canonical_dir)
    reasons: list[str] = []
    audits: dict[str, TheoryAuditReport] = {}
    canonical_results: dict[str, dict[str, object]] = {}
    strict_grammar: dict[str, dict[str, object]] = {}
    snapshot_deltas: dict[str, dict[str, object]] = {}
    coverage_counts: dict[str, dict[str, int]] = {}
    external_categories: dict[str, dict[str, int]] = {}
    unsupported_total = 0
    partial_total = 0
    coverage_match = True
    external_match = True

    for key, source in sources.items():
        if not source.exists():
            reasons.append(f"{key}: canonical source is missing: {source.name}")
            canonical_results[key] = {
                "source": str(source),
                "matches": False,
                "exists": False,
            }
            coverage_match = False
            external_match = False
            continue

        report = audit_theory_source(source, canonical_key=key, strict_projection=True)
        audits[key] = report
        if report.canonical is not None:
            canonical_results[key] = dict(report.canonical)
        grammar = strict_tex_parse_report(source)
        strict_grammar[key] = grammar.model_dump(mode="json")
        snapshot_deltas[key] = dict(report.snapshot_delta)
        counts = report.coverage.counts_by_status()
        coverage_counts[key] = counts
        external_categories[key] = dict(report.external_obligation_category_summary)
        unsupported_total += counts.get(CoverageStatus.UNSUPPORTED.value, 0)
        partial_total += counts.get(CoverageStatus.PARTIAL.value, 0)

        if report.canonical is None or not bool(report.canonical.get("matches", False)):
            reasons.append(f"{key}: canonical SHA-256 mismatch")
        if not grammar.accepted:
            reasons.append(f"{key}: strict TeX grammar diagnostics are present")
        if report.unsupported_items:
            reasons.append(f"{key}: unsupported coverage items remain")
        if counts.get(CoverageStatus.PARTIAL.value, 0):
            reasons.append(f"{key}: partial coverage items remain")
        if not report.snapshot_delta.get("coverage_counts_match", False):
            coverage_match = False
            reasons.append(f"{key}: snapshot coverage counts differ from canonical audit")
        if not report.snapshot_delta.get("external_category_summary_match", False):
            external_match = False
            reasons.append(f"{key}: snapshot external-obligation categories differ")
        if report.external_catalog_errors:
            reasons.append(f"{key}: external obligation catalog metadata is incomplete")
        if not report.accepted:
            reasons.append(f"{key}: projection or canonical audit did not accept")

    accepted = not reasons and len(audits) == len(sources)
    return TheoryAuditSuiteReport(
        canonical_dir=str(Path(canonical_dir)),
        expected_artifacts=[record.tex_filename for record in CANONICAL_RECORDS.values()],
        audits=audits,
        canonical_results=canonical_results,
        strict_grammar=strict_grammar,
        snapshot_delta=snapshot_deltas,
        coverage_counts=coverage_counts,
        external_obligation_category_summary=external_categories,
        unsupported_total=unsupported_total,
        partial_total=partial_total,
        coverage_counts_match=coverage_match,
        external_category_summary_match=external_match,
        accepted=accepted,
        overall_status="pass" if accepted else "fail",
        reasons=sorted(set(reasons)),
    )


def build_theory_fidelity_report(canonical_dir: str | Path) -> TheoryFidelityReport:
    """Build a v0.4.2 theory-fidelity summary from the canonical suite audit."""

    suite = audit_canonical_suite(canonical_dir)
    theory_summaries: dict[str, dict[str, object]] = {}
    external_totals: dict[str, int] = {}
    finite_upgrade_candidates: dict[str, list[str]] = {}
    strict_grammar_accepted: dict[str, bool] = {}
    snapshot_health: dict[str, bool] = {}
    for key, audit in sorted(suite.audits.items()):
        counts = audit.coverage.counts_by_status()
        external_total = int(counts.get(CoverageStatus.EXTERNAL_OBLIGATION.value, 0))
        external_totals[key] = external_total
        catalog = audit.external_obligation_catalog
        external_records = catalog.obligations if catalog is not None else []
        finite_upgrade_candidates[key] = [
            record.item_id
            for record in external_records
            if record.verifier_route or record.checker_refs or record.checker_ref
        ]
        grammar = suite.strict_grammar.get(key, {})
        strict_grammar_accepted[key] = bool(grammar.get("accepted", False))
        delta = suite.snapshot_delta.get(key, {})
        snapshot_health[key] = bool(
            delta.get("coverage_counts_match", False)
            and delta.get("external_category_summary_match", False)
        )
        theory_summaries[key] = {
            "artifact": audit.artifact,
            "implemented_total": audit.coverage_delta.get("implemented_total", 0),
            "external_obligation_total": external_total,
            "unsupported_total": counts.get(CoverageStatus.UNSUPPORTED.value, 0),
            "partial_total": counts.get(CoverageStatus.PARTIAL.value, 0),
            "finite_upgrade_candidate_count": len(finite_upgrade_candidates[key]),
            "strict_grammar_accepted": strict_grammar_accepted[key],
            "snapshot_healthy": snapshot_health[key],
        }
    accepted = bool(suite.accepted and all(strict_grammar_accepted.values()))
    return TheoryFidelityReport(
        canonical_dir=str(Path(canonical_dir)),
        suite_status=suite.overall_status,
        theory_summaries=theory_summaries,
        unsupported_total=suite.unsupported_total,
        partial_total=suite.partial_total,
        external_obligation_totals=dict(sorted(external_totals.items())),
        finite_upgrade_candidates={
            key: sorted(values) for key, values in sorted(finite_upgrade_candidates.items())
        },
        strict_grammar_accepted=dict(sorted(strict_grammar_accepted.items())),
        snapshot_health=dict(sorted(snapshot_health.items())),
        accepted=accepted,
        operationally_usable=accepted,
        settled=False,
        reasons=list(suite.reasons),
    )
