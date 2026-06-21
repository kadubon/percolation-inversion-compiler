from __future__ import annotations

import json

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

runner = CliRunner()
TEXT = "Candidate packet: route evidence and preserve residuals."


def test_core_agent_commands_work_without_adoption_state() -> None:
    commands = [
        ["agent", "check", "--compact", "--text", TEXT, "--profile", "development"],
        ["phase", "plan", "--compact", "--text", TEXT, "--profile", "development"],
        ["agent", "accelerate", "--compact", "--text", TEXT, "--profile", "development"],
        ["agent", "intake", "--text", TEXT, "--profile", "development"],
    ]

    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["accepted"] is True
        assert data["settled"] is False
        assert "adoption" not in json.dumps(data).lower()


def test_adoption_absence_is_not_settled_blocker_or_phase_gap() -> None:
    result = runner.invoke(
        app,
        ["phase", "plan", "--compact", "--text", TEXT, "--profile", "development"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    joined_blockers = " ".join(data["settled_blockers"]).lower()
    joined_reasons = " ".join(
        data["candidate_only_reasons"] + data["cannot_promote_because"]
    ).lower()
    phase_components = json.dumps(data["phase_gap_vector"]).lower()
    assert "adoption" not in joined_blockers
    assert "operator approval" not in joined_blockers
    assert "adoption" not in joined_reasons
    assert "adoption" not in phase_components
