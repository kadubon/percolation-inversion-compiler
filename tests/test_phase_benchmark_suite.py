from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_phase_benchmark_suite_cli_is_diagnostic_only() -> None:
    result = runner.invoke(
        app,
        ["phase", "benchmark-suite", "--profile", "development", "--format", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["cases"]
    assert data["settled"] is False
    assert data["workflow_usable"] is True
    assert any(
        "benchmark scores do not set settled=true" in item for item in data["safety_invariants"]
    )
    assert all(case["settled"] is False for case in data["cases"])


def test_phase_benchmark_suite_markdown_and_schema() -> None:
    markdown = runner.invoke(app, ["phase", "benchmark-suite", "--format", "markdown"])
    assert markdown.exit_code == 0
    assert "Phase Benchmark Suite" in markdown.output
    assert "settled=`false`" in markdown.output

    for schema_name in [
        "ProtocolRelativeBenchmarkMetric",
        "PhaseBenchmarkTask",
        "PhaseBenchmarkCaseResult",
        "PhaseBenchmarkSuiteReport",
    ]:
        Draft202012Validator.check_schema(schema_by_type(schema_name))


def test_phase_benchmark_suite_example_validates() -> None:
    schema = schema_by_type("PhaseBenchmarkSuiteReport")
    data = json.loads(
        Path("examples/benchmarks/phase_benchmark_suite_report.example.json").read_text(
            encoding="utf-8"
        )
    )
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=str)
    assert errors == []
