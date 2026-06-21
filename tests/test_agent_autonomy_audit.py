from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.agent import build_agent_autonomy_audit
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_agent_autonomy_audit_is_non_gating_and_argv_safe() -> None:
    report = build_agent_autonomy_audit("development")

    assert report.adoption_required_for_core is False
    assert report.approval_gate_present is False
    assert report.safe_commands_executable_by_pic is False
    assert report.compact_mode_available is True
    assert report.pip_core_workflow_available is True
    assert report.agent_full_extra_available is True
    assert report.source_checkout_required_for_core is False
    assert report.shell_expansion_required_for_sidecars is False
    assert report.command_execution_allowed_by_pic is False
    assert report.approval_persistence_created is False
    assert report.settled is False
    assert any(item.argv for item in report.recommended_next_invocations)
    assert any(
        item.invocation_id == "sidecar-packet-merge"
        and item.argv
        == [
            "pic",
            "packet",
            "merge",
            "--packets",
            "pic-demo/packet*.json",
            "--output",
            "pic-demo/merged-packets.json",
        ]
        for item in report.recommended_next_invocations
    )
    assert any(
        item.invocation_id == "canonical-readiness"
        and item.argv
        == [
            "pic",
            "audit",
            "canonical-readiness",
            "--profile",
            "development",
            "--format",
            "json",
        ]
        for item in report.recommended_next_invocations
    )
    assert any(
        "canonical readiness is available from pip" in item for item in report.autonomy_enablers
    )


def test_agent_autonomy_audit_cli_and_schema_export() -> None:
    result = runner.invoke(
        app,
        ["agent", "autonomy-audit", "--profile", "development", "--format", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["adoption_required_for_core"] is False
    assert data["approval_gate_present"] is False
    assert data["safe_commands_executable_by_pic"] is False
    assert data["recommended_next_invocations"]
    assert data["recommended_next_invocations"][0]["argv"]
    assert any(
        item["invocation_id"] == "canonical-readiness"
        for item in data["recommended_next_invocations"]
    )

    for schema_name in ["AgentAutonomyAuditReport", "AgentCommandInvocation"]:
        schema = schema_by_type(schema_name)
        assert schema["title"] == schema_name
        Draft202012Validator.check_schema(schema)
        cli_schema = runner.invoke(app, ["schema", "--type", schema_name])
        assert cli_schema.exit_code == 0
        assert json.loads(cli_schema.output)["title"] == schema_name
