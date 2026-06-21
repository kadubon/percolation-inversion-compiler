from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_phase_dashboard_cli_is_observational_only(tmp_path: Path) -> None:
    output = tmp_path / "dashboard.json"
    result = runner.invoke(
        app,
        [
            "phase",
            "dashboard",
            "--profile",
            "development",
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["settled"] is False
    assert "phase dashboard is observational only" in data["dashboard_safety_boundary"]
    assert data["phase_gap_vector"]["components"]

    markdown = runner.invoke(app, ["phase", "dashboard", "--format", "markdown"])
    assert markdown.exit_code == 0
    assert "Phase Dashboard" in markdown.output
    assert "Settled: `false`" in markdown.output


def test_phase_observe_and_dashboard_schema_examples(tmp_path: Path) -> None:
    dashboard = tmp_path / "dashboard.json"
    result = runner.invoke(app, ["phase", "dashboard", "--output", str(dashboard)])
    assert result.exit_code == 0

    observed = runner.invoke(
        app,
        ["phase", "observe", "--reports", str(dashboard), "--output", str(tmp_path / "obs.json")],
    )
    assert observed.exit_code == 0
    observation = json.loads((tmp_path / "obs.json").read_text(encoding="utf-8"))
    assert observation["settled"] is False
    assert observation["aggregate_metrics"]["dashboard_count"] == 1

    for schema_name in ["PhaseDashboardReport", "PhaseObservationReport"]:
        Draft202012Validator.check_schema(schema_by_type(schema_name))
    example = json.loads(Path("examples/phase_dashboard/dashboard.example.json").read_text())
    errors = sorted(
        Draft202012Validator(schema_by_type("PhaseDashboardReport")).iter_errors(example),
        key=str,
    )
    assert errors == []
