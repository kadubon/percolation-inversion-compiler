from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

runner = CliRunner()


def test_compact_contract_docs_state_sidecar_interpretation_rules() -> None:
    agent_contract = Path("docs/contracts/agent-check-compact-contract.md").read_text(
        encoding="utf-8"
    )
    phase_contract = Path("docs/contracts/phase-plan-compact-contract.md").read_text(
        encoding="utf-8"
    )
    adoption_contract = Path("docs/contracts/operator-adoption-sidecar-contract.md").read_text(
        encoding="utf-8"
    )

    assert "if `settled == false`: do not claim final completion" in agent_contract
    assert "safe_commands" in phase_contract
    assert "missing adoption approval is not a `settled_blocker`" in adoption_contract
    assert "pure output generators" in adoption_contract


def test_safe_commands_remain_inspection_hints_not_authority() -> None:
    result = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--compact",
            "--text",
            "Candidate packet: preserve residuals.",
            "--profile",
            "development",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["safe_commands"]
    joined = " ".join(data["safety_invariants"]).lower()
    assert "recommendation-only" in joined
    assert "no arbitrary shell execution" in joined
