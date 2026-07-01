from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner

from percolation_inversion_compiler.agent import agent_manifest_payload
from percolation_inversion_compiler.cli import app

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_INDEX = ROOT / "docs" / "integrations" / "README.md"
GITHUB_ACTIONS_DOC = ROOT / "docs" / "integrations" / "github-actions.md"
GITHUB_ACTIONS_WORKFLOW = (
    ROOT / "examples" / "github_action_agent_output_check" / "pic-agent-output-check.yml"
)
CLI_EXAMPLE = ROOT / "examples" / "cli_agent_output_check"
PYTHON_SDK_EXAMPLE = ROOT / "examples" / "python_sdk_agent_output_check"

runner = CliRunner()


def _workflow() -> dict[str, Any]:
    data = yaml.safe_load(GITHUB_ACTIONS_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_integration_index_lists_supported_surfaces() -> None:
    text = INTEGRATIONS_INDEX.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in [
        "CLI",
        "Python SDK",
        "GitHub Actions",
        "Runtime service",
        "External intake",
        "Agent messages",
        "ALT foundry",
        "general AI agent output checker",
        "runtime verification layer",
        "not specific to GitHub Actions",
    ]:
        assert phrase in normalized


def test_readme_reframes_github_actions_as_one_integration() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Integration Examples" in readme
    assert "## GitHub Actions Example" not in readme
    assert "PIC is not limited to GitHub Actions" in readme
    assert "docs/integrations/README.md" in readme


def test_github_actions_guide_links_back_to_integration_index() -> None:
    text = GITHUB_ACTIONS_DOC.read_text(encoding="utf-8")
    assert "This is one integration pattern" in text
    assert "[Integration Examples](README.md)" in text
    assert "pull_request_target" in text
    assert "read-only permissions" in text


def test_integration_examples_exist() -> None:
    for path in [
        CLI_EXAMPLE / "README.md",
        CLI_EXAMPLE / "agent_output.txt",
        PYTHON_SDK_EXAMPLE / "README.md",
        PYTHON_SDK_EXAMPLE / "check_agent_output.py",
        GITHUB_ACTIONS_WORKFLOW,
    ]:
        assert path.is_file()


def test_github_actions_example_stays_read_only() -> None:
    text = GITHUB_ACTIONS_WORKFLOW.read_text(encoding="utf-8")
    workflow = _workflow()
    permissions = workflow["permissions"]
    assert "pull_request_target" not in text
    assert permissions["contents"] == "read"
    assert permissions["pull-requests"] == "read"
    assert not any(value == "write" for value in permissions.values())
    assert "pic-agent-output-report.json" in text
    assert "pic-agent-output-check" in text


def test_manifest_and_schema_index_expose_deployment_surfaces() -> None:
    expected = [
        "cli",
        "python-sdk",
        "github-actions",
        "runtime-service",
        "external-intake",
        "agent-messages",
        "alt-foundry",
        "agent-autonomy-audit",
        "canonical-implementation-readiness",
        "operator-adoption-sidecar",
        "packet-exchange-sidecar",
        "phase-dashboard-sidecar",
        "phase-ecology-lab",
        "bit-inversion-engine",
        "sqot-controller",
        "alt-ecpt-lift",
        "trc-trace-adapter",
        "ccr-interop",
        "trc-operation-readiness",
        "target-valid-cara-acceleration",
        "mcp-a2a-safety-reports",
        "sqot-protocol-integrity",
        "bit-mec-frontier",
        "token-extraction",
        "trc-observation-residuals",
        "cache-index-performance",
        "agent-loop-protocol",
    ]
    manifest = json.loads((ROOT / "agent-manifest.json").read_text(encoding="utf-8"))
    schema_index = json.loads((ROOT / "schemas" / "index.json").read_text(encoding="utf-8"))
    fallback = agent_manifest_payload()
    for payload in [manifest, schema_index, fallback]:
        assert payload["deployment_surfaces"] == expected
    for path in [
        "docs/integrations/README.md",
        "examples/cli_agent_output_check/README.md",
        "examples/python_sdk_agent_output_check/README.md",
        "examples/github_action_agent_output_check/README.md",
    ]:
        assert path in manifest["recommended_docs"]


def test_cli_example_intake_preserves_unsettled_status(tmp_path: Path) -> None:
    output = tmp_path / "cli-agent-output-report.json"
    result = runner.invoke(
        app,
        [
            "agent",
            "intake",
            "--text-file",
            str(CLI_EXAMPLE / "agent_output.txt"),
            "--profile",
            "development",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["accepted"] is True
    assert data["settled"] is False


def test_python_sdk_example_prints_unsettled_summary() -> None:
    result = subprocess.run(
        [sys.executable, str(PYTHON_SDK_EXAMPLE / "check_agent_output.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["accepted"] is True
    assert data["settled"] is False
    assert "missing_obligation_count" in data
