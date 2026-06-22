from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

runner = CliRunner()


def test_packet_merge_expands_literal_glob_patterns(tmp_path: Path) -> None:
    target = tmp_path / "pic-demo"
    bootstrap = runner.invoke(app, ["demo", "bootstrap", "--output-dir", str(target)])
    assert bootstrap.exit_code == 0

    output = tmp_path / "merged.json"
    result = runner.invoke(
        app,
        [
            "packet",
            "merge",
            "--packets",
            str(target / "packet*.json"),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["input_packet_count"] == 1
    assert data["settled"] is False


def test_phase_observe_expands_literal_glob_patterns(tmp_path: Path) -> None:
    target = tmp_path / "pic-demo"
    bootstrap = runner.invoke(app, ["demo", "bootstrap", "--output-dir", str(target)])
    assert bootstrap.exit_code == 0

    output = tmp_path / "observation.json"
    result = runner.invoke(
        app,
        [
            "phase",
            "observe",
            "--reports",
            str(target / "phase_dashboard*.json"),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["aggregate_metrics"]["dashboard_count"] == 1
    assert data["settled"] is False


def test_unmatched_literal_glob_reports_clear_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "packet",
            "merge",
            "--packets",
            str(tmp_path / "missing*.json"),
        ],
    )

    assert result.exit_code != 0
    assert "pattern matched no files" in result.output
