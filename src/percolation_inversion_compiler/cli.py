"""Command-line interface for Percolation Inversion Compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core import (
    ExternalProofObligation,
    VerifierEvidenceEnvelope,
    binding_for_route,
    check_external_verifier_hook,
    list_adapter_route_specs,
    list_discharge_route_bindings,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.ecology import (
    PacketSourceKind,
    PsiDashboard,
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_registry,
    build_psi_dashboard,
    closed_loop_iteration,
    infer_live_kind,
    ingest_agent_output,
    ingest_live_source,
    ingest_local_file,
    registry_from_json,
)
from percolation_inversion_compiler.ecpt import (
    ASIProxyTargetContract,
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlState,
    build_phase_control_plan,
    reachable_mass,
)
from percolation_inversion_compiler.io import (
    audit_theory_source,
    build_operational_readiness_report,
    build_sbom_document,
    canonical_manifest,
    count_mr_records_by_category,
    create_provenance_manifest,
    extract_artifact,
    extract_theory_coverage,
    find_snapshot_item,
    list_theory_snapshots,
    load_theory_snapshot,
    registry_json_schema,
    schema_bundle,
    schema_bundle_digest,
    schema_by_type,
    strict_tex_parse_report,
    validate_canonical_source,
    validate_data,
    verify_provenance_manifest,
)
from percolation_inversion_compiler.io.provenance import ProvenanceManifest
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.sqot import (
    DiagnosticReservePolicy,
    SalienceQueueRecord,
    build_salience_schedule,
)
from percolation_inversion_compiler.trc import compile_frontier, datacenter_demo

app = typer.Typer(
    help="Finite certificate compiler toolkit for ECPT, BIT, TRC, and SQOT.",
    invoke_without_command=True,
)
demo_app = typer.Typer(help="Run bundled finite examples.")
audit_app = typer.Typer(help="Run source and theory audits.")
snapshot_app = typer.Typer(help="Inspect bundled derived theory snapshots.")
evidence_app = typer.Typer(help="Verify external evidence envelopes.")
routes_app = typer.Typer(help="Inspect verifier route bindings.")
provenance_app = typer.Typer(help="Create and verify release provenance manifests.")
sbom_app = typer.Typer(help="Create deterministic release SBOM documents.")
parse_app = typer.Typer(help="Run strict TeX parser diagnostics.")
ecpt_app = typer.Typer(help="Run ECPT active phase-control planning tools.")
sqot_app = typer.Typer(help="Run SQOT salience-queue scheduling tools.")
ecology_app = typer.Typer(help="Run ECPT capability packet ecology tools.")
app.add_typer(demo_app, name="demo")
app.add_typer(audit_app, name="audit")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(evidence_app, name="evidence")
app.add_typer(routes_app, name="routes")
app.add_typer(provenance_app, name="provenance")
app.add_typer(sbom_app, name="sbom")
app.add_typer(parse_app, name="parse")
app.add_typer(ecpt_app, name="ecpt")
app.add_typer(sqot_app, name="sqot")
app.add_typer(ecology_app, name="ecology")
console = Console()


def _dump(data: Any, output: Path | None = None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, default=str)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        console.print_json(text)


def _load_phase_state(path: Path) -> tuple[PhaseControlState, list[PhaseControlAction]]:
    data = load_data(path)
    raw_state = data.get("state", data)
    state = PhaseControlState.model_validate(raw_state)
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        raise typer.BadParameter("state file actions must be a list when present")
    actions = [PhaseControlAction.model_validate(item) for item in raw_actions]
    return state, actions


def _load_phase_actions(path: Path) -> list[PhaseControlAction]:
    data = load_data(path)
    raw_actions = data.get("actions", data.get("phase_control_actions"))
    if not isinstance(raw_actions, list):
        raise typer.BadParameter("actions file must contain an actions list")
    return [PhaseControlAction.model_validate(item) for item in raw_actions]


def _load_phase_objective(path: Path, budget_data: dict[str, Any]) -> PhaseControlObjective:
    data = load_data(path)
    if "objective" in data:
        raw_objective = data["objective"]
        if not isinstance(raw_objective, dict):
            raise typer.BadParameter("target file objective must be an object")
        merged = dict(raw_objective)
        for key in ["horizon", "residual_budget", "risk_tolerance", "route_preferences"]:
            if key in budget_data:
                merged[key] = budget_data[key]
        return PhaseControlObjective.model_validate(merged)
    raw_target = data.get("target", data)
    target = ASIProxyTargetContract.model_validate(raw_target)
    return PhaseControlObjective(
        objective_id=str(budget_data.get("objective_id", f"objective:{target.target_id}")),
        target=target,
        horizon=int(budget_data.get("horizon", 1)),
        residual_budget=float(budget_data.get("residual_budget", 0.0)),
        risk_tolerance=float(budget_data.get("risk_tolerance", 0.0)),
        route_preferences=list(budget_data.get("route_preferences", [])),
    )


def _load_salience_records(path: Path) -> list[SalienceQueueRecord]:
    data = load_data(path)
    raw_records = data.get("records", data.get("queue", data.get("packets", [])))
    if not isinstance(raw_records, list):
        raise typer.BadParameter("salience input must contain records, queue, or packets list")
    records: list[SalienceQueueRecord] = []
    for item in raw_records:
        if not isinstance(item, dict):
            raise typer.BadParameter("salience records must be JSON objects")
        if "record_id" in item:
            records.append(SalienceQueueRecord.model_validate(item))
            continue
        packet_id = str(item.get("packet_id", item.get("id", "packet")))
        records.append(
            SalienceQueueRecord(
                record_id=packet_id,
                item_type="packet",
                salience_class=str(item.get("salience_class", "packet")),
                expected_downstream_gain=float(item.get("expected_downstream_gain", 0.0)),
                residual_reduction=max(0.0, 1.0 - float(item.get("residual_charge", 1.0))),
                verification_cost=float(item.get("verification_cost", 0.0)),
                freshness=float(item.get("freshness", 1.0)),
                obligation_ids=[str(value) for value in item.get("obligation_ids", [])],
                verifier_routes=[str(value) for value in item.get("verifier_routes", [])],
            )
        )
    return records


def _threshold_from_file(path: Path) -> dict[str, float]:
    data = load_data(path)
    raw_threshold = data.get("threshold", data)
    if not isinstance(raw_threshold, dict):
        raise typer.BadParameter("threshold file must contain an object")
    return {str(key): float(value) for key, value in raw_threshold.items()}


def _read_text_or_literal(source: str) -> str:
    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return source


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show package version.", is_eager=True),
    ] = False,
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


@app.command()
def doctor(
    fail_on: Annotated[
        str,
        typer.Option(
            "--fail-on",
            help="Exit nonzero on: fail, warn, or never.",
        ),
    ] = "fail",
    profile: Annotated[
        str,
        typer.Option("--profile", help="Readiness profile: development, research, or production."),
    ] = "development",
    provenance: Annotated[
        Path | None,
        typer.Option("--provenance", help="Verified provenance manifest JSON."),
    ] = None,
    required_route: Annotated[
        list[str] | None,
        typer.Option(
            "--required-route",
            help="Route id or verifier_route that must be production-ready for this run.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report operational readiness for CI and autonomous-agent runners."""

    if fail_on not in {"fail", "warn", "never"}:
        console.print("Error: --fail-on must be one of: fail, warn, never")
        raise typer.Exit(2)
    report = build_operational_readiness_report(
        profile=profile,
        provenance=provenance,
        required_routes=required_route,
    )
    _dump(report.model_dump(mode="json"), output)
    if fail_on == "fail" and report.overall_status == "fail":
        raise typer.Exit(1)
    if fail_on == "warn" and report.overall_status in {"fail", "warn"}:
        raise typer.Exit(1)


@app.command()
def extract(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Extract filecontents JSON, BIT MR records, and claim registries."""

    artifact = extract_artifact(source)
    registries = [registry.model_dump(mode="json") for registry in artifact.registries]
    data = {
        "source": artifact.source,
        "filecontents": [block.name for block in artifact.filecontents],
        "json_blocks": sorted(artifact.json_blocks),
        "mr_record_count": len(artifact.mr_records),
        "mr_record_counts": count_mr_records_by_category(artifact.mr_records),
        "registry_count": len(artifact.registries),
        "claim_count": sum(len(registry.claims) for registry in artifact.registries),
        "registries": registries,
    }
    _dump(data, output)


@app.command()
def validate(
    registry: Annotated[Path, typer.Option("--registry", "-r", help="Registry JSON/YAML file.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Validate a registry-like JSON/YAML object against the public schema."""

    data = load_data(registry)
    errors = validate_data(data)
    result = {"registry": str(registry), "valid": not errors, "errors": errors}
    _dump(result, output)
    if errors:
        raise typer.Exit(1)


@app.command()
def schema(
    type_name: Annotated[
        str, typer.Option("--type", help="Public schema type to emit.")
    ] = "Registry",
    all_schemas: Annotated[
        bool,
        typer.Option("--all", help="Emit the full portability schema bundle."),
    ] = False,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Write one schema file per public type."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON Schema.")
    ] = None,
) -> None:
    """Emit a public JSON Schema."""

    try:
        if all_schemas:
            bundle = schema_bundle()
            if output_dir is not None:
                output_dir.mkdir(parents=True, exist_ok=True)
                for name, schema_data in bundle.schemas.items():
                    (output_dir / f"{name}.schema.json").write_text(
                        json.dumps(schema_data, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                (output_dir / "bundle.schema.json").write_text(
                    json.dumps(bundle.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                digest = schema_bundle_digest(output_dir, base_dir=output_dir.parent)
                (output_dir / "schema-digest.json").write_text(
                    json.dumps(digest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                return
            _dump(bundle.model_dump(mode="json"), output)
            return
        schema_data = (
            registry_json_schema() if type_name == "Registry" else schema_by_type(type_name)
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(schema_data, output)


@app.command()
def check(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    canonical_key: Annotated[
        str | None,
        typer.Option("--canonical-key", help="Canonical key: ecpt, bit, or trc."),
    ] = None,
    strict_projection: Annotated[
        bool,
        typer.Option(
            "--strict-projection",
            help="Compare stable registry fields against extractor judgments.",
        ),
    ] = False,
    derive_status: Annotated[
        bool,
        typer.Option("--derive-status", help="Include checker-derived status summary."),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run extraction, uniqueness, and optional canonical MD5 checks."""

    artifact = extract_artifact(source)
    results: dict[str, Any] = {
        "source": str(source),
        "registries": [],
        "valid": True,
        "errors": [],
    }
    if derive_status:
        derived: dict[str, int] = {}
        for judgment in artifact.extractor_output().judgments:
            key = judgment.derived_status.value
            derived[key] = derived.get(key, 0) + 1
        results["derived_status_summary"] = dict(sorted(derived.items()))
    for registry in artifact.registries:
        try:
            registry.require_unique_claim_ids()
            projection = artifact.extractor_output().check_registry_projection(
                registry,
                strict=strict_projection,
            )
            results["registries"].append(
                {
                    "artifact": registry.artifact,
                    "schema_version": registry.schema_version,
                    "claim_count": len(registry.claims),
                    "unique": True,
                    "projection_sound": projection.accepted,
                    "strict_projection": strict_projection,
                }
            )
            if not projection.accepted:
                results["valid"] = False
                results["errors"].extend(projection.reasons)
        except ValueError as exc:
            results["valid"] = False
            results["errors"].append(str(exc))
    if canonical_key is not None:
        canonical = validate_canonical_source(source, canonical_key)
        results["canonical"] = canonical
        if not canonical["matches"]:
            results["valid"] = False
            results["errors"].append("canonical checksum mismatch")
    _dump(results, output)
    if not results["valid"]:
        raise typer.Exit(1)


@app.command()
def coverage(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit definition, claim, and MRRecord coverage for a TeX artifact."""

    record = extract_theory_coverage(source)
    _dump(record.model_dump(mode="json"), output)


@audit_app.command("theory")
def audit_theory(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    canonical_key: Annotated[
        str | None,
        typer.Option("--canonical-key", help="Canonical key: ecpt, bit, or trc."),
    ] = None,
    strict_projection: Annotated[
        bool,
        typer.Option(
            "--strict-projection/--no-strict-projection",
            help="Compare stable registry fields against extractor judgments.",
        ),
    ] = True,
    strict_maturity: Annotated[
        bool,
        typer.Option(
            "--strict-maturity/--no-strict-maturity",
            help="Treat maturity/provenance downgrades as audit-relevant metadata.",
        ),
    ] = False,
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Diagnose unsupported theorem-like or MRRecord source syntax.",
        ),
    ] = False,
    fail_on: Annotated[
        list[str] | None,
        typer.Option(
            "--fail-on",
            help=(
                "Fail when audit contains: unsupported, external, projection, canonical, "
                "or snapshot."
            ),
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Emit a JSON-first theory, coverage, projection, and obligation audit."""

    report = audit_theory_source(
        source,
        canonical_key=canonical_key,
        strict_projection=strict_projection,
    )
    data = report.model_dump(mode="json")
    data["strict_maturity"] = strict_maturity
    grammar_report = strict_tex_parse_report(source) if strict_grammar else None
    if grammar_report is not None:
        data["strict_grammar"] = grammar_report.model_dump(mode="json")
    _dump(data, output)
    fail_reasons = set(fail_on or [])
    fail = not report.accepted
    if "projection" in fail_reasons and any(
        not audit.accepted for audit in report.projection_audits
    ):
        fail = True
    if (
        "canonical" in fail_reasons
        and report.canonical is not None
        and not report.canonical.get("matches")
    ):
        fail = True
    if "unsupported" in fail_reasons and report.unsupported_items:
        fail = True
    if "external" in fail_reasons and report.external_obligation_items:
        fail = True
    if "snapshot" in fail_reasons and report.snapshot_delta:
        counts_match = bool(report.snapshot_delta.get("coverage_counts_match", True))
        external_match = bool(report.snapshot_delta.get("external_category_summary_match", True))
        if not counts_match or not external_match:
            fail = True
    if "provenance" in fail_reasons and (
        report.canonical is None or not bool(report.canonical.get("matches", False))
    ):
        fail = True
    if grammar_report is not None and not grammar_report.accepted:
        fail = True
    if fail:
        raise typer.Exit(1)


@snapshot_app.command("list")
def snapshot_list(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """List bundled derived snapshots without requiring canonical TeX files."""

    snapshots = list_theory_snapshots()
    data = {
        "snapshots": [
            {
                "artifact_key": snapshot.artifact_key,
                "artifact": snapshot.artifact,
                "doi": snapshot.attribution.doi,
                "coverage_counts": snapshot.coverage_counts,
                "external_obligation_category_summary": (
                    snapshot.external_obligation_category_summary
                ),
            }
            for snapshot in snapshots
        ]
    }
    _dump(data, output)


@snapshot_app.command("show")
def snapshot_show(
    artifact: Annotated[
        str,
        typer.Option("--artifact", "-a", help="Snapshot artifact key: ecpt, bit, trc, or sqot."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show one bundled derived theory snapshot."""

    try:
        snapshot = load_theory_snapshot(artifact)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"unknown snapshot artifact {artifact!r}") from exc
    _dump(snapshot.model_dump(mode="json"), output)


@snapshot_app.command("routes")
def snapshot_routes(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show adapter route specs for external verifier obligations."""

    _dump(
        {"routes": [spec.model_dump(mode="json") for spec in list_adapter_route_specs()]},
        output,
    )


@routes_app.command("bindings")
def route_bindings(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Show reviewed canonical-to-implementation discharge route bindings."""

    _dump(
        {
            "bindings": [
                binding.model_dump(mode="json") for binding in list_discharge_route_bindings()
            ]
        },
        output,
    )


@routes_app.command("explain")
def route_explain(
    route: Annotated[
        str,
        typer.Option("--route", help="Route id or verifier_route to explain."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Explain one verifier route binding and its settlement scope."""

    specs = {
        key: spec
        for spec in list_adapter_route_specs()
        for key in {spec.route_id, spec.verifier_route}
    }
    spec = specs.get(route)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {route!r}")
    binding = binding_for_route(spec.route_id)
    data = {
        "route": spec.model_dump(mode="json"),
        "binding": None if binding is None else binding.model_dump(mode="json"),
        "settled_scope": [] if binding is None else binding.settlement_scope,
        "finite_scope_usable": (
            spec.discharge_level.value != "external_domain_required"
            if binding is None
            else binding.discharge_level.value != "external_domain_required"
        ),
        "residual_external_obligations": []
        if binding is None
        else binding.residual_external_obligation_refs,
        "required_evidence_kind": spec.required_evidence_kind,
    }
    _dump(data, output)


@provenance_app.command("create")
def provenance_create(
    schema_dir: Annotated[
        Path | None,
        typer.Option("--schema-dir", help="Directory containing generated schema JSON files."),
    ] = None,
    sbom_ref: Annotated[
        str | None,
        typer.Option("--sbom-ref", help="Optional SBOM release-asset reference."),
    ] = None,
    artifact_ref: Annotated[
        list[str] | None,
        typer.Option(
            "--artifact-ref",
            help="Additional release artifact path to include in the manifest.",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write provenance manifest JSON.")
    ] = None,
) -> None:
    """Create a deterministic SHA-256 provenance manifest."""

    manifest = create_provenance_manifest(
        schema_dir=schema_dir,
        sbom_ref=sbom_ref,
        artifact_refs=artifact_ref,
    )
    _dump(manifest.model_dump(mode="json"), output)


@provenance_app.command("verify")
def provenance_verify(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", "-m", help="Provenance manifest JSON."),
    ],
    require_attestation: Annotated[
        bool,
        typer.Option(
            "--require-attestation/--no-require-attestation",
            help="Require attestation metadata in addition to local SHA-256 checks.",
        ),
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write verification JSON.")
    ] = None,
) -> None:
    """Verify a deterministic provenance manifest against local files."""

    data = load_data(manifest)
    parsed = ProvenanceManifest.model_validate(data)
    valid, reasons = verify_provenance_manifest(
        parsed,
        require_attestation=require_attestation,
    )
    _dump(
        {
            "manifest": str(manifest),
            "require_attestation": require_attestation,
            "valid": valid,
            "reasons": reasons,
        },
        output,
    )
    if not valid:
        raise typer.Exit(1)


@snapshot_app.command("verify")
def snapshot_verify(
    artifact: Annotated[
        str,
        typer.Option("--artifact", "-a", help="Snapshot artifact key: ecpt, bit, trc, or sqot."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify derived snapshot attribution against the canonical manifest metadata."""

    snapshot = load_theory_snapshot(artifact)
    manifest = canonical_manifest()
    record = manifest.records.get(snapshot.artifact_key)
    valid = record is not None and snapshot.attribution.doi == record.doi
    data = {
        "artifact_key": snapshot.artifact_key,
        "valid": valid,
        "snapshot_schema_version": snapshot.schema_version,
        "canonical_manifest_schema_version": manifest.schema_version,
        "doi_matches": bool(record and snapshot.attribution.doi == record.doi),
        "legacy_md5_matches": bool(
            record and snapshot.attribution.source_tex_md5 == record.tex_md5_legacy
        ),
        "canonical_sha256": None if record is None else record.tex_sha256,
        "snapshot_is_derived_metadata": True,
    }
    _dump(data, output)
    if not valid:
        raise typer.Exit(1)


@sbom_app.command("create")
def sbom_create(
    format_name: Annotated[
        str,
        typer.Option("--format", help="SBOM format: pic or cyclonedx."),
    ] = "pic",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write SBOM JSON output.")
    ] = None,
) -> None:
    """Create a deterministic SBOM document."""

    try:
        document = build_sbom_document(format_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(document, output)


@parse_app.command("audit")
def parse_audit(
    source: Annotated[Path, typer.Option("--source", "-s", help="TeX source artifact.")],
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Exit nonzero on strict grammar diagnostics.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run strict TeX parser diagnostics."""

    report = strict_tex_parse_report(source)
    _dump(report.model_dump(mode="json"), output)
    if strict_grammar and not report.accepted:
        raise typer.Exit(1)


@sqot_app.command("audit")
def sqot_audit(
    source: Annotated[Path, typer.Option("--source", "-s", help="SQOT TeX source artifact.")],
    strict_grammar: Annotated[
        bool,
        typer.Option(
            "--strict-grammar/--no-strict-grammar",
            help="Exit nonzero on strict grammar diagnostics.",
        ),
    ] = True,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Audit SQOT source coverage and strict parser compatibility."""

    grammar = strict_tex_parse_report(source)
    coverage_record = extract_theory_coverage(source)
    canonical_key = "sqot" if source.name == "Salience-Queue Occupation Theory.tex" else None
    audit = audit_theory_source(source, canonical_key=canonical_key, strict_projection=True)
    data = {
        "source": str(source),
        "strict_grammar": grammar.model_dump(mode="json"),
        "coverage": coverage_record.model_dump(mode="json"),
        "coverage_counts": coverage_record.counts_by_status(),
        "audit": audit.model_dump(mode="json"),
    }
    _dump(data, output)
    if strict_grammar and not grammar.accepted:
        raise typer.Exit(1)


@sqot_app.command("schedule")
def sqot_schedule(
    packets: Annotated[
        Path,
        typer.Option("--packets", help="JSON/YAML queue records or packet candidates."),
    ],
    obligations: Annotated[
        Path | None,
        typer.Option("--obligations", help="Optional JSON/YAML obligations list."),
    ] = None,
    profile: Annotated[
        str,
        typer.Option("--profile", help="Scheduler profile: development, research, or production."),
    ] = "development",
    attention_budget: Annotated[
        float,
        typer.Option("--attention-budget", help="Finite attention budget for this queue run."),
    ] = 1.0,
    risk_budget: Annotated[
        float,
        typer.Option("--risk-budget", help="Finite risk budget for this queue run."),
    ] = 1.0,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Schedule packet, obligation, and verifier tasks with SQOT reserve rules."""

    records = _load_salience_records(packets)
    if obligations is not None:
        obligation_data = load_data(obligations)
        raw_obligations = obligation_data.get("obligations", [])
        if isinstance(raw_obligations, list):
            for obligation in raw_obligations:
                if not isinstance(obligation, dict):
                    continue
                records.append(
                    SalienceQueueRecord(
                        record_id=str(obligation.get("obligation_id", obligation.get("item_id"))),
                        item_type="obligation",
                        salience_class="diagnostic",
                        expected_downstream_gain=0.1,
                        residual_reduction=1.0,
                        verification_cost=0.1,
                        obligation_ids=[str(obligation.get("obligation_id", ""))],
                        verifier_routes=[str(obligation.get("verifier_hint", ""))],
                    )
                )
    report = build_salience_schedule(
        records,
        attention_budget=attention_budget,
        diagnostic_reserve=DiagnosticReservePolicy(),
        risk_budget=risk_budget,
        profile=profile,
    )
    _dump(report.model_dump(mode="json"), output)


@ecology_app.command("ingest")
def ecology_ingest(
    source: Annotated[
        str,
        typer.Option("--source", help="Local path, URL, repo slug, or literal agent output."),
    ],
    kind: Annotated[
        str,
        typer.Option("--kind", help="local, github, zenodo, arxiv, agent-output, or auto."),
    ] = "auto",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Ingest a source into capability packet candidates."""

    packet_kind = PacketSourceKind(kind)
    if packet_kind == PacketSourceKind.AUTO:
        packet_kind = infer_live_kind(source)
    if packet_kind == PacketSourceKind.LOCAL:
        report = ingest_local_file(Path(source))
    elif packet_kind == PacketSourceKind.AGENT_OUTPUT:
        report = ingest_agent_output(_read_text_or_literal(source))
    else:
        token = os.environ.get("GITHUB_TOKEN") if packet_kind == PacketSourceKind.GITHUB else None
        report = ingest_live_source(
            source,
            kind=packet_kind,
            token=token,
        )
    _dump(report.model_dump(mode="json"), output)
    if not report.accepted:
        raise typer.Exit(1)


@ecology_app.command("build-edges")
def ecology_build_edges(
    packets: Annotated[
        Path,
        typer.Option("--packets", help="JSON/YAML packet list or registry."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build finite packet edge witnesses and return a registry."""

    data = load_data(packets)
    registry = registry_from_json(data)
    edges = build_edge_witnesses(registry.packets)
    updated = build_packet_registry(registry.packets, edges, registry_id=registry.registry_id)
    _dump(updated.model_dump(mode="json"), output)


@ecology_app.command("psi")
def ecology_psi(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    threshold: Annotated[
        Path | None,
        typer.Option("--threshold", help="Optional Psi threshold JSON/YAML."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compute a finite ASI-proxy Psi dashboard."""

    parsed = registry_from_json(load_data(registry))
    thresholds = _threshold_from_file(threshold) if threshold is not None else None
    dashboard = build_psi_dashboard(parsed, threshold=thresholds)
    _dump(dashboard.model_dump(mode="json"), output)


@ecology_app.command("plan")
def ecology_plan(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="CapabilityPacketRegistry JSON/YAML."),
    ],
    psi: Annotated[
        Path,
        typer.Option("--psi", help="PsiDashboard JSON/YAML."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Planner profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Rank bottleneck-inversion interventions from a Psi dashboard."""

    parsed_registry = registry_from_json(load_data(registry))
    dashboard = PsiDashboard.model_validate(load_data(psi))
    plan = build_bottleneck_plan(parsed_registry, dashboard, profile=profile)
    _dump(plan.model_dump(mode="json"), output)


@ecology_app.command("loop")
def ecology_loop(
    state: Annotated[
        Path,
        typer.Option("--state", help="JSON/YAML state with optional threshold object."),
    ],
    agent_output: Annotated[
        str,
        typer.Option("--agent-output", help="Path or literal output from an agent."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run one deterministic agent-output to packet-ecology planning loop."""

    state_data = load_data(state)
    threshold = state_data.get("threshold")
    thresholds = (
        {str(key): float(value) for key, value in threshold.items()}
        if isinstance(threshold, dict)
        else None
    )
    iteration = closed_loop_iteration(
        state_id=str(state_data.get("state_id", "ecology-state")),
        agent_output=_read_text_or_literal(agent_output),
        threshold=thresholds,
    )
    _dump(iteration.model_dump(mode="json"), output)


@ecpt_app.command("plan")
def ecpt_plan(
    state: Annotated[
        Path,
        typer.Option("--state", help="PhaseControlState JSON/YAML, optionally with actions."),
    ],
    target: Annotated[
        Path,
        typer.Option("--target", help="ASIProxyTargetContract or PhaseControlObjective JSON/YAML."),
    ],
    budget: Annotated[
        Path,
        typer.Option("--budget", help="Budget/objective JSON/YAML, optionally with actions."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Planner profile: development, research, or production."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Build a deterministic ECPT ASI-proxy phase-control plan."""

    phase_state, state_actions = _load_phase_state(state)
    budget_data = load_data(budget)
    raw_budgets = budget_data.get("budgets")
    if isinstance(raw_budgets, dict):
        phase_state = phase_state.model_copy(update={"budgets": raw_budgets})
    objective = _load_phase_objective(target, budget_data)
    actions = state_actions
    if "actions" in budget_data:
        raw_actions = budget_data["actions"]
        if not isinstance(raw_actions, list):
            raise typer.BadParameter("budget file actions must be a list when present")
        actions.extend(PhaseControlAction.model_validate(item) for item in raw_actions)
    if not actions:
        raise typer.BadParameter("phase-control planning requires at least one action")
    report = build_phase_control_plan(phase_state, objective, actions, profile=profile)
    _dump(report.model_dump(mode="json"), output)


@ecpt_app.command("simulate")
def ecpt_simulate(
    state: Annotated[
        Path,
        typer.Option("--state", help="PhaseControlState JSON/YAML."),
    ],
    actions: Annotated[
        Path,
        typer.Option("--actions", help="JSON/YAML object containing an actions list."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Simulate finite ECPT reachable-mass response for proposed actions."""

    phase_state, _ = _load_phase_state(state)
    parsed_actions = _load_phase_actions(actions)
    target_nodes = sorted({action.target_node for action in parsed_actions})
    objective = PhaseControlObjective(
        objective_id="simulate-finite-reachable-mass",
        target=ASIProxyTargetContract(
            target_id="simulation-target",
            target_nodes=target_nodes,
        ),
        residual_budget=1.0,
        risk_tolerance=1.0,
    )
    report = build_phase_control_plan(phase_state, objective, parsed_actions)
    _dump(
        {
            "state_id": phase_state.state_id,
            "baseline_reachable_mass": dict(sorted(reachable_mass(phase_state.graph).items())),
            "controlled_reachable_mass": report.controlled_reachable_mass,
            "candidates": [
                candidate.model_dump(mode="json") for candidate in report.plan.candidates
            ],
            "safety_invariants": report.safety_invariants,
        },
        output,
    )


@ecpt_app.command("route-obligations")
def ecpt_route_obligations(
    audit: Annotated[
        Path,
        typer.Option("--audit", help="pic audit theory JSON output with ECPT external items."),
    ],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Map ECPT external obligations to verifier route bindings."""

    data = load_data(audit)
    external_items = data.get("external_obligation_items", [])
    catalog = data.get("external_obligation_catalog")
    if isinstance(catalog, dict) and not external_items:
        external_items = catalog.get("obligations", [])
    if not isinstance(external_items, list):
        raise typer.BadParameter("audit JSON external obligations must be a list")
    specs = {
        key: spec
        for spec in list_adapter_route_specs()
        for key in {spec.route_id, spec.verifier_route}
    }
    routed: list[dict[str, Any]] = []
    for item in external_items:
        if not isinstance(item, dict):
            continue
        route_id = item.get("verifier_route") or item.get("route_id")
        spec = specs.get(str(route_id)) if route_id is not None else None
        binding = binding_for_route(spec.route_id) if spec is not None else None
        routed.append(
            {
                "item_id": item.get("item_id"),
                "label": item.get("label"),
                "obligation_category": item.get("obligation_category"),
                "verifier_route": route_id,
                "route_known": spec is not None,
                "required_evidence_kind": [] if spec is None else spec.required_evidence_kind,
                "binding": None if binding is None else binding.model_dump(mode="json"),
                "safe_default": item.get("safe_default") if spec is None else spec.safe_default,
                "residual_coordinates": item.get("residual_coordinates", []),
            }
        )
    _dump({"routed_obligations": routed}, output)


@app.command(name="compile")
def compile_command(
    records: Annotated[
        Path,
        typer.Option("--records", "-r", help="JSON/YAML file with a top-level records list."),
    ],
    archive_cap: Annotated[
        int, typer.Option("--archive-cap", help="Returned efficiency archive cap.")
    ] = 64,
    fail_on: Annotated[
        list[str] | None,
        typer.Option("--fail-on", help="Fail on invalid-main-trace."),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Compile typed frontier records into TRC strata."""

    data = load_data(records)
    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        raise typer.BadParameter("records file must contain a top-level 'records' list")
    frontier_records = [FrontierRecord.model_validate(item) for item in raw_records]
    try:
        fail_reasons = set(fail_on or [])
        result = compile_frontier(
            frontier_records,
            archive_cap=archive_cap,
            fail_on_invalid_main_trace="invalid-main-trace" in fail_reasons,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(result.model_dump(mode="json"), output)


@evidence_app.command("verify")
def evidence_verify(
    envelope: Annotated[
        Path,
        typer.Option("--envelope", "-e", help="VerifierEvidenceEnvelope JSON/YAML file."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Evidence verification profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify a finite evidence envelope against its adapter route contract."""

    data = load_data(envelope)
    evidence = VerifierEvidenceEnvelope.model_validate(data)
    specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
    spec = specs.get(evidence.route_id)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {evidence.route_id!r}")
    result = resolve_adapter_route(spec, evidence, base_dir=envelope.parent, profile=profile)
    _dump(result.model_dump(mode="json"), output)
    if not result.accepted:
        raise typer.Exit(1)


@evidence_app.command("discharge")
def evidence_discharge(
    envelope: Annotated[
        Path,
        typer.Option("--envelope", "-e", help="VerifierEvidenceEnvelope JSON/YAML file."),
    ],
    obligations: Annotated[
        Path,
        typer.Option("--obligations", help="JSON/YAML object with an obligations list."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", help="Evidence verification profile."),
    ] = "development",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Verify evidence and emit a provenance-bound ExternalVerifierHook."""

    evidence = VerifierEvidenceEnvelope.model_validate(load_data(envelope))
    obligation_data = load_data(obligations)
    raw_obligations = obligation_data.get("obligations")
    if not isinstance(raw_obligations, list):
        raise typer.BadParameter("obligations file must contain a top-level 'obligations' list")
    parsed_obligations = [ExternalProofObligation.model_validate(item) for item in raw_obligations]
    specs = {spec.route_id: spec for spec in list_adapter_route_specs()}
    spec = specs.get(evidence.route_id)
    if spec is None:
        raise typer.BadParameter(f"unknown adapter route {evidence.route_id!r}")
    resolution = resolve_adapter_route(spec, evidence, base_dir=envelope.parent, profile=profile)
    hook = resolution.to_external_verifier_hook()
    check = check_external_verifier_hook(hook, parsed_obligations)
    data = {
        "resolution": resolution.model_dump(mode="json"),
        "hook": hook.model_dump(mode="json"),
        "check": check.model_dump(mode="json"),
    }
    _dump(data, output)
    if not resolution.accepted or not check.accepted:
        raise typer.Exit(1)


@demo_app.command("datacenter")
def demo_datacenter(
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Run the TRC AI datacenter cooling and management-link example."""

    result = datacenter_demo()
    _dump(result.model_dump(mode="json"), output)


@app.command()
def explain(
    topic: Annotated[
        str,
        typer.Argument(help="Topic: ecpt, bit, trc, status, license, coverage, or external."),
    ],
    item_id: Annotated[
        str | None,
        typer.Argument(help="Optional item id for 'coverage' or 'external'."),
    ] = None,
    from_snapshot: Annotated[
        bool,
        typer.Option(
            "--from-snapshot",
            help="Explain coverage/external items from bundled derived snapshots.",
        ),
    ] = False,
    artifact: Annotated[
        str | None,
        typer.Option("--artifact", help="Snapshot artifact key when using --from-snapshot."),
    ] = None,
) -> None:
    """Print concise scientific framing for a subsystem."""

    if topic.lower() in {"coverage", "external"}:
        if item_id is None:
            raise typer.BadParameter(f"{topic.lower()} explanation requires an item id")
        if from_snapshot:
            snapshot_record = find_snapshot_item(
                item_id,
                artifact_key=artifact,
                external_only=topic.lower() == "external",
            )
            if snapshot_record is None:
                raise typer.BadParameter(f"snapshot {topic.lower()} item {item_id!r} was not found")
            _dump(snapshot_record.model_dump(mode="json"))
            return
        canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
        if not canonical_dir:
            raise typer.BadParameter(f"set PIC_CANONICAL_TEX_DIR to explain {topic.lower()} items")
        for filename in [
            "Executable Capability Percolation Theory.tex",
            "Bottleneck Inversion Theory.tex",
            "Typed Reality Compilation.tex",
        ]:
            source = Path(canonical_dir) / filename
            if not source.exists():
                continue
            if topic.lower() == "external":
                audit = audit_theory_source(source, strict_projection=True)
                catalog = audit.external_obligation_catalog
                if catalog is None:
                    continue
                for obligation in catalog.obligations:
                    if obligation.item_id == item_id:
                        _dump(obligation.model_dump(mode="json"))
                        return
                continue
            coverage_record = extract_theory_coverage(source)
            for coverage_item in coverage_record.items:
                if coverage_item.item_id == item_id:
                    _dump(coverage_item.model_dump(mode="json"))
                    return
        raise typer.BadParameter(f"{topic.lower()} item {item_id!r} was not found")

    explanations = {
        "ecpt": (
            "ECPT models protocol-relative capability propagation through finite "
            "hypergraphs, activation laws, queue/capacity ledgers, and checker output."
        ),
        "bit": (
            "BIT reports only unit-compatible, intervention-backed potential coordinates "
            "with finite witnesses and explicit selection/resource charges."
        ),
        "trc": (
            "TRC compiles observed cyber-physical infrastructure into typed process "
            "frontiers with residual, tolerance, resource, and trace-normal-form ledgers."
        ),
        "status": (
            "Status labels are not scalar confidence scores. Settled claims require all "
            "settled obligations; provisional, speculative, risk, relaxed, and diagnostic "
            "records do not silently promote."
        ),
        "license": (
            "Repository code is Apache-2.0. Cited Zenodo papers are CC-BY-4.0 and are "
            "not vendored by this package."
        ),
    }
    key = topic.lower()
    if key not in explanations:
        raise typer.BadParameter(f"unknown topic {topic!r}")
    console.print(explanations[key])
