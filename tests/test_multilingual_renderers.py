from __future__ import annotations

import json

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

runner = CliRunner()


def test_adoption_markdown_supports_japanese_without_json_key_translation() -> None:
    markdown = runner.invoke(
        app,
        ["adoption", "packet", "--format", "markdown", "--language", "ja"],
    )
    assert markdown.exit_code == 0
    assert "PIC オペレーター導入パケット" in markdown.output
    assert "operator_adoption_status" in markdown.output

    json_result = runner.invoke(
        app,
        ["adoption", "packet", "--format", "json", "--language", "ja"],
    )
    assert json_result.exit_code == 0
    data = json.loads(json_result.output)
    assert "operator_adoption_status" in data
    assert "オペレーター導入状態" not in data
    assert data["settled"] is False


def test_operator_request_and_autonomy_audit_japanese_markdown() -> None:
    request = runner.invoke(
        app,
        ["adoption", "request", "--format", "markdown", "--language", "ja"],
    )
    assert request.exit_code == 0
    assert "エージェントからオペレーターへのリクエスト" in request.output
    assert "Warning:" in request.output

    audit = runner.invoke(
        app,
        [
            "agent",
            "autonomy-audit",
            "--format",
            "markdown",
            "--language",
            "ja",
        ],
    )
    assert audit.exit_code == 0
    assert "PIC エージェント自律性監査" in audit.output
    assert "adoption_required_for_core" in audit.output
    assert "safe_commands_executable_by_pic" in audit.output
    assert "percolation-inversion-compiler[agent-full]" in audit.output


def test_unsupported_markdown_language_is_rejected() -> None:
    result = runner.invoke(
        app,
        ["agent", "autonomy-audit", "--format", "markdown", "--language", "fr"],
    )

    assert result.exit_code != 0
    assert "--language must be en or ja" in result.output
