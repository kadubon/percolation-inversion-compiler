from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io import (
    build_canonical_implementation_readiness_report,
    canonical_implementation_readiness_markdown,
)
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_canonical_readiness_uses_bundled_snapshots_without_gating() -> None:
    report = build_canonical_implementation_readiness_report("development")

    assert report.accepted is True
    assert report.workflow_usable is True
    assert report.operationally_usable is True
    assert report.settled is False
    assert report.snapshot_count == 5
    assert set(report.theory_summaries) == {"ecpt", "bit", "trc", "sqot", "alt"}
    assert report.total_implemented_items > 0
    assert report.total_external_obligations > 0
    assert report.unsupported_total == 0
    assert report.partial_total == 0
    assert report.source_checkout_required is False
    assert report.canonical_tex_required_for_this_report is False
    assert report.source_tex_vendored is False
    assert report.adoption_required_for_core is False
    assert report.approval_gate_present is False
    assert report.safe_commands_executable_by_pic is False
    assert report.automatic_execution_present is False
    assert any(
        item["invocation_id"] == "canonical-readiness"
        and item["argv"]
        == [
            "pic",
            "audit",
            "canonical-readiness",
            "--profile",
            "development",
            "--format",
            "json",
        ]
        and item["requires_source_checkout"] is False
        for item in report.recommended_invocations
    )


def test_canonical_readiness_cli_markdown_and_schema_export() -> None:
    result = runner.invoke(
        app,
        ["audit", "canonical-readiness", "--profile", "development", "--format", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is True
    assert data["settled"] is False
    assert data["canonical_tex_required_for_this_report"] is False
    assert data["approval_gate_present"] is False
    assert data["theory_summaries"]["ecpt"]["external_obligation_total"] > 0

    markdown = runner.invoke(
        app,
        ["audit", "canonical-readiness", "--profile", "development", "--format", "markdown"],
    )
    assert markdown.exit_code == 0
    assert "PIC Canonical Implementation Readiness" in markdown.output
    assert "Settled: `false`" in markdown.output

    for schema_name in [
        "CanonicalImplementationReadinessReport",
        "CanonicalTheorySnapshotSummary",
    ]:
        schema = schema_by_type(schema_name)
        assert schema["title"] == schema_name
        Draft202012Validator.check_schema(schema)
        cli_schema = runner.invoke(app, ["schema", "--type", schema_name])
        assert cli_schema.exit_code == 0
        assert json.loads(cli_schema.output)["title"] == schema_name


def test_canonical_readiness_markdown_rejects_unknown_language() -> None:
    report = build_canonical_implementation_readiness_report("development")

    try:
        canonical_implementation_readiness_markdown(report, language="fr")
    except ValueError as exc:
        assert "language must be one of" in str(exc)
    else:
        raise AssertionError("unknown language should fail")
