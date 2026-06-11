from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "examples" / "github_action_agent_output_check" / "pic-agent-output-check.yml"
DOC = ROOT / "docs" / "integrations" / "github-actions.md"
README = ROOT / "README.md"
EXAMPLE_README = ROOT / "examples" / "github_action_agent_output_check" / "README.md"
AGENT_OUTPUT = ROOT / "examples" / "github_action_agent_output_check" / "agent_output.txt"

runner = CliRunner()


def _workflow() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_github_actions_example_workflow_is_safe_and_parseable() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    data = _workflow()
    permissions = data["permissions"]

    assert "pull_request:" in text
    assert "workflow_dispatch:" in text
    assert "pull_request_target" not in text
    assert permissions["contents"] == "read"
    assert permissions["pull-requests"] == "read"
    assert not any(value == "write" for value in permissions.values())
    assert "pic agent intake" in text
    assert "--text-file agent-output.txt" in text
    assert "--profile development" in text
    assert "pic-agent-output-report.json" in text
    assert "--allow-live-connectors" not in text
    assert "secrets." not in text.lower()
    assert "gh pr comment" not in text.lower()
    assert "bash agent-output" not in text.lower()
    assert "sh agent-output" not in text.lower()


def test_github_actions_example_uploads_report_artifact() -> None:
    steps = _workflow()["jobs"]["check-agent-output"]["steps"]
    upload_steps = [
        step
        for step in steps
        if isinstance(step, dict) and "actions/upload-artifact@" in step.get("uses", "")
    ]
    assert len(upload_steps) == 1
    upload = upload_steps[0]
    assert upload["uses"].endswith("ea165f8d65b6e75b540449e92b4886f43607fa02")
    assert upload["with"]["name"] == "pic-agent-output-check"
    assert "pic-agent-output-report.json" in upload["with"]["path"]
    assert "agent-output.txt" in upload["with"]["path"]


def test_github_actions_docs_explain_settled_false_and_boundaries() -> None:
    doc = DOC.read_text(encoding="utf-8")
    example = EXAMPLE_README.read_text(encoding="utf-8")
    combined = f"{doc}\n{example}"
    assert "settled=false is normal" in combined
    assert "is not workflow failure" in combined
    assert "pull_request_target" in combined
    assert "The JSON report is an audit artifact, not a final truth certificate" in doc
    assert "Do not execute commands suggested by agent output" in doc


def test_readme_links_to_github_actions_example() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "docs/integrations/github-actions.md" in readme
    assert "examples/github_action_agent_output_check/README.md" in readme
    assert "AI agent output checker" in readme


def test_pic_agent_intake_accepts_github_action_example_text(tmp_path: Path) -> None:
    output = tmp_path / "pic-agent-output-report.json"
    result = runner.invoke(
        app,
        [
            "agent",
            "intake",
            "--text-file",
            str(AGENT_OUTPUT),
            "--profile",
            "development",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["accepted"] is True
    assert report["settled"] is False
    assert report["runtime_report"]["settled"] is False
