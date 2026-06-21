from __future__ import annotations

import json
import tomllib
from importlib.resources import files
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_agent_full_extra_is_declared_and_documented() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]

    assert extras["agent-full"] == [
        "percolation-inversion-compiler[connectors,server,identity]"
    ]
    assert "percolation-inversion-compiler[agent-full]" in (
        ROOT / "README.md"
    ).read_text(encoding="utf-8")
    assert "percolation-inversion-compiler[agent-full]" in (
        ROOT / "docs" / "pypi-distribution.md"
    ).read_text(encoding="utf-8")


def test_installed_demo_bundle_contains_sidecar_assets() -> None:
    root = files("percolation_inversion_compiler.data.demo")
    for name in [
        "runtime_step_report.json",
        "phase_dashboard.json",
        "packet_envelope.json",
    ]:
        assert (root / name).is_file()

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in manifest["files"]}
    assert {"runtime_step_report.json", "phase_dashboard.json", "packet_envelope.json"} <= paths
    assert any("packet merge" in item for item in manifest["recommended_phase_commands"])
    assert any(
        "canonical-readiness" in item for item in manifest["recommended_phase_commands"]
    )


def test_demo_bootstrap_exports_sidecars_and_argv_invocations(tmp_path: Path) -> None:
    target = tmp_path / "pic-demo"
    result = runner.invoke(app, ["demo", "bootstrap", "--output-dir", str(target)])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["settled"] is False
    assert data["recommended_next_invocations"]
    assert any(
        item["invocation_id"] == "packet-merge-bootstrapped"
        for item in data["recommended_next_invocations"]
    )
    assert any(
        item["invocation_id"] == "canonical-readiness"
        for item in data["recommended_next_invocations"]
    )
    for name in [
        "runtime_step_report.json",
        "phase_dashboard.json",
        "packet_envelope.json",
    ]:
        assert (target / name).is_file()


def test_installed_smoke_recommends_sidecar_path() -> None:
    result = runner.invoke(app, ["demo", "installed-smoke", "--profile", "development"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["recommended_next_invocations"]
    joined = "\n".join(data["recommended_next_commands"])
    assert "pic phase benchmark-suite" in joined
    assert "pic packet merge --packets pic-demo/packet*.json" in joined
    assert "pic audit canonical-readiness --profile development --format json" in joined
    assert any(
        item["invocation_id"] == "canonical-readiness"
        for item in data["recommended_next_invocations"]
    )
