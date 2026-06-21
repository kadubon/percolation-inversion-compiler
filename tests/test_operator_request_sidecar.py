from __future__ import annotations

import json

from typer.testing import CliRunner

from percolation_inversion_compiler.adoption import build_agent_to_operator_request
from percolation_inversion_compiler.cli import app

runner = CliRunner()


def test_operator_request_contains_plain_english_handoff() -> None:
    request = build_agent_to_operator_request("development")

    assert request.settled is False
    assert "I found PIC." in request.plain_english_message
    assert "PIC treats AI-agent output as candidate work." in request.plain_english_message
    assert "PIC does not execute my proposed actions." in request.plain_english_message
    assert "PIC does not bypass your approval policy." in request.plain_english_message
    assert "PIC does not prove real ASI or real-world truth." in request.plain_english_message
    assert "should not self-install PIC" in request.warning
    assert "python -m pip install percolation-inversion-compiler" in (
        request.suggested_first_command.command
    )


def test_operator_request_cli_json_and_markdown() -> None:
    json_result = runner.invoke(app, ["adoption", "request", "--format", "json"])
    assert json_result.exit_code == 0
    data = json.loads(json_result.output)
    assert data["operator_adoption_status"] == "not-recorded"
    assert data["settled"] is False
    assert data["safety_boundary"]["creates_required_approval_state"] is False

    markdown = runner.invoke(app, ["adoption", "request", "--format", "markdown"])
    assert markdown.exit_code == 0
    assert "Agent To Operator Request" in markdown.output
    assert "Agents without install authority should not self-install PIC." in markdown.output
    assert "pic phase plan --compact" in markdown.output
