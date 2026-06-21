from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_adoption_packet_json_is_sidecar_only() -> None:
    result = runner.invoke(
        app,
        ["adoption", "packet", "--profile", "development", "--format", "json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["operator_adoption_status"] == "not-recorded"
    assert data["settled"] is False
    assert data["safety_boundary"]["sidecar_only"] is True
    assert data["safety_boundary"]["affects_agent_check"] is False
    assert data["safety_boundary"]["affects_phase_plan"] is False
    assert data["safety_boundary"]["affects_settled"] is False
    assert data["safety_boundary"]["approval_settles_truth"] is False
    assert any("does not prove real ASI" in item for item in data["what_pic_does_not_do"])


def test_adoption_packet_markdown_has_no_workflow_gate_claim() -> None:
    result = runner.invoke(app, ["adoption", "packet", "--format", "markdown"])

    assert result.exit_code == 0
    assert "PIC Operator Adoption Packet" in result.output
    assert "does not require adoption approval for agent check" in result.output
    assert "operator adoption does not settle runtime obligations" in result.output


def test_adoption_public_schemas_export() -> None:
    for schema_name in [
        "OperatorAdoptionPacket",
        "AgentToOperatorRequest",
        "AdoptionSafetyBoundary",
        "AdoptionFirstRunCommand",
        "AdoptionReviewChecklist",
    ]:
        schema = schema_by_type(schema_name)
        Draft202012Validator.check_schema(schema)
