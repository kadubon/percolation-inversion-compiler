from __future__ import annotations

import importlib.util
import json
import tarfile
import zipfile
from importlib.resources import files
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _distribution_script_module() -> object:
    script = ROOT / "scripts" / "check_distribution_artifacts.py"
    spec = importlib.util.spec_from_file_location("check_distribution_artifacts", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_installed_demo_package_resources_exist() -> None:
    root = files("percolation_inversion_compiler.data.demo")
    for name in [
        "manifest.json",
        "runtime_step_report.json",
        "phase_dashboard.json",
        "packet_envelope.json",
        "runtime_state.json",
        "runtime_step_input.json",
        "agent_output.txt",
        "general_intake_policy.json",
        "alt_admission_packet.json",
        "phase_lab_runtime_report.json",
        "phase_lab_threshold.json",
    ]:
        assert (root / name).is_file()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.9.0"
    assert manifest["candidate_only"] is True
    recommended = "\n".join(manifest["recommended_phase_commands"])
    assert "packet*.json" not in recommended
    for command in [
        "pic phase lab observe --store pic-demo/phase-lab --window latest",
        "pic phase lab graph --store pic-demo/phase-lab",
        "pic phase lab closure --store pic-demo/phase-lab",
        "pic phase lab executable-paths --store pic-demo/phase-lab",
        (
            "pic phase lab certify --store pic-demo/phase-lab "
            "--threshold pic-demo/phase_lab_threshold.json"
        ),
    ]:
        assert command in recommended


def test_pic_demo_installed_smoke_returns_unsettled_report() -> None:
    result = runner.invoke(app, ["demo", "installed-smoke", "--profile", "development"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["version"] == "0.9.0"
    assert data["accepted"] is True
    assert data["workflow_usable"] is True
    assert data["settled"] is False
    assert data["runtime_report"]["settled"] is False
    joined = "\n".join(data["recommended_next_commands"])
    assert "packet*.json" not in joined
    assert "pic agent check" in joined
    assert "pic demo bootstrap" in joined
    for command in [
        "pic phase lab observe --store pic-demo/phase-lab --window latest",
        "pic phase lab graph --store pic-demo/phase-lab",
        "pic phase lab closure --store pic-demo/phase-lab",
        "pic phase lab executable-paths --store pic-demo/phase-lab",
        (
            "pic phase lab certify --store pic-demo/phase-lab "
            "--threshold pic-demo/phase_lab_threshold.json"
        ),
    ]:
        assert command in joined


def test_pic_demo_bootstrap_exports_runtime_files(tmp_path: Path) -> None:
    target = tmp_path / "pic-demo"
    result = runner.invoke(app, ["demo", "bootstrap", "--output-dir", str(target)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is True
    assert data["workflow_usable"] is True
    assert data["settled"] is False
    assert any("pic agent check" in item for item in data["recommended_next_commands"])
    joined = "\n".join(data["recommended_next_commands"])
    assert "packet*.json" not in joined
    for command in [
        "phase lab observe",
        "phase lab graph",
        "phase lab closure",
        "phase lab executable-paths",
        "phase lab certify",
    ]:
        assert command in joined
    for name in [
        "manifest.json",
        "runtime_step_report.json",
        "phase_dashboard.json",
        "packet_envelope.json",
        "runtime_state.json",
        "runtime_step_input.json",
        "agent_output.txt",
        "general_intake_policy.json",
        "alt_admission_packet.json",
        "phase_lab_runtime_report.json",
        "phase_lab_threshold.json",
    ]:
        assert (target / name).is_file()

    runtime = runner.invoke(
        app,
        [
            "runtime",
            "step",
            "--state",
            str(target / "runtime_state.json"),
            "--input",
            str(target / "runtime_step_input.json"),
            "--profile",
            "development",
        ],
    )
    assert runtime.exit_code == 0
    runtime_data = json.loads(runtime.output)
    assert runtime_data["settled"] is False


def test_distribution_artifact_checker_accepts_required_wheel_members(tmp_path: Path) -> None:
    module = _distribution_script_module()
    wheel = tmp_path / "demo.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in module.REQUIRED_WHEEL_MEMBERS:
            archive.writestr(name, "{}")
    assert module.validate_wheel(wheel) == []


def test_distribution_artifact_checker_accepts_required_sdist_members(tmp_path: Path) -> None:
    module = _distribution_script_module()
    sdist = tmp_path / "demo.tar.gz"
    root = "percolation_inversion_compiler-0.9.0"
    with tarfile.open(sdist, "w:gz") as archive:
        for suffix in module.REQUIRED_SDIST_SUFFIXES:
            path = tmp_path / suffix
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            archive.add(path, arcname=f"{root}/{suffix}")
    assert module.validate_sdist(sdist) == []


def test_distribution_artifact_checker_rejects_forbidden_sdist_tex(tmp_path: Path) -> None:
    module = _distribution_script_module()
    sdist = tmp_path / "demo.tar.gz"
    root = "percolation_inversion_compiler-0.9.0"
    with tarfile.open(sdist, "w:gz") as archive:
        for suffix in module.REQUIRED_SDIST_SUFFIXES:
            path = tmp_path / suffix
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            archive.add(path, arcname=f"{root}/{suffix}")
        tex = tmp_path / "tests" / "fixtures" / "minimal_claims.tex"
        tex.parent.mkdir(parents=True, exist_ok=True)
        tex.write_text("\\section{fixture}", encoding="utf-8")
        archive.add(tex, arcname=f"{root}/tests/fixtures/minimal_claims.tex")

    failures = module.validate_sdist(sdist)
    assert any("forbidden artifact suffix" in failure for failure in failures)


def test_distribution_artifact_checker_rejects_forbidden_wheel_member(
    tmp_path: Path,
) -> None:
    module = _distribution_script_module()
    wheel = tmp_path / "demo.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in module.REQUIRED_WHEEL_MEMBERS:
            archive.writestr(name, "{}")
        archive.writestr("percolation_inversion_compiler/data/demo/model.safetensors", "")
    failures = module.validate_wheel(wheel)
    assert any("forbidden artifact suffix" in failure for failure in failures)
