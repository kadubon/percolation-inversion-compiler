"""Command-line interface for Percolation Inversion Compiler."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.core import list_adapter_route_specs
from percolation_inversion_compiler.core.frontier import FrontierRecord
from percolation_inversion_compiler.io import (
    audit_theory_source,
    build_operational_readiness_report,
    count_mr_records_by_category,
    extract_artifact,
    extract_theory_coverage,
    find_snapshot_item,
    list_theory_snapshots,
    load_theory_snapshot,
    registry_json_schema,
    schema_bundle,
    schema_by_type,
    validate_canonical_source,
    validate_data,
)
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.trc import compile_frontier, datacenter_demo

app = typer.Typer(
    help="Finite certificate compiler toolkit for ECPT, BIT, and TRC.",
    invoke_without_command=True,
)
demo_app = typer.Typer(help="Run bundled finite examples.")
audit_app = typer.Typer(help="Run source and theory audits.")
snapshot_app = typer.Typer(help="Inspect bundled derived theory snapshots.")
app.add_typer(demo_app, name="demo")
app.add_typer(audit_app, name="audit")
app.add_typer(snapshot_app, name="snapshot")
console = Console()


def _dump(data: Any, output: Path | None = None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, default=str)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        console.print_json(text)


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
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write JSON output.")
    ] = None,
) -> None:
    """Report operational readiness for CI and autonomous-agent runners."""

    if fail_on not in {"fail", "warn", "never"}:
        raise typer.BadParameter("--fail-on must be one of: fail, warn, never")
    report = build_operational_readiness_report()
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
    _dump(report.model_dump(mode="json"), output)
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
        typer.Option("--artifact", "-a", help="Snapshot artifact key: ecpt, bit, or trc."),
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


@app.command(name="compile")
def compile_command(
    records: Annotated[
        Path,
        typer.Option("--records", "-r", help="JSON/YAML file with a top-level records list."),
    ],
    archive_cap: Annotated[
        int, typer.Option("--archive-cap", help="Returned efficiency archive cap.")
    ] = 64,
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
        result = compile_frontier(frontier_records, archive_cap=archive_cap)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _dump(result.model_dump(mode="json"), output)


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
