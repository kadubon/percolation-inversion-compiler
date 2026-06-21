from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.agent import AgentIntakeRequest, run_agent_intake
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def _runtime_report_file(tmp_path: Path) -> Path:
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output="Candidate packet: route evidence and preserve residuals.",
            profile="development",
        )
    ).runtime_report
    path = tmp_path / "runtime-report.json"
    path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")
    return path


def test_packet_export_inspect_merge_and_lineage_are_non_promoting(tmp_path: Path) -> None:
    runtime_report = _runtime_report_file(tmp_path)
    packet_path = tmp_path / "packet.json"

    exported = runner.invoke(
        app,
        ["packet", "export", "--report", str(runtime_report), "--output", str(packet_path)],
    )
    assert exported.exit_code == 0
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["settled"] is False
    assert packet["candidate_only_reasons"]

    packet["content"]["embedded_command"] = "powershell Remove-Item important-file"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    inspected = runner.invoke(app, ["packet", "inspect", "--packet", str(packet_path)])
    assert inspected.exit_code == 0
    inspection = json.loads(inspected.output)
    assert inspection["content_treated_as_data"] is True
    assert inspection["executed_command_count"] == 0
    assert inspection["embedded_command_like_values"]
    assert inspection["settled"] is False

    merge_path = tmp_path / "merge.json"
    merged = runner.invoke(
        app,
        [
            "packet",
            "merge",
            "--packets",
            str(packet_path),
            "--packets",
            str(packet_path),
            "--output",
            str(merge_path),
        ],
    )
    assert merged.exit_code == 0
    merge_data = json.loads(merge_path.read_text(encoding="utf-8"))
    assert merge_data["input_packet_count"] == 2
    assert merge_data["merged_packet_count"] == 1
    assert merge_data["candidate_only_preserved"] is True
    assert merge_data["settled"] is False

    lineage = runner.invoke(app, ["packet", "lineage", "--packet", str(merge_path)])
    assert lineage.exit_code == 0
    lineage_data = json.loads(lineage.output)
    assert lineage_data["packet_ids"]
    assert lineage_data["candidate_only"] is True
    assert lineage_data["settled"] is False


def test_packet_exchange_schemas_and_examples_validate() -> None:
    examples = {
        "PacketExchangeEnvelope": "examples/packet_exchange/packet_envelope.example.json",
        "PacketMergeReport": "examples/packet_exchange/packet_merge_report.example.json",
    }
    for schema_name in [
        "PacketExchangeEnvelope",
        "PacketImportInspectionReport",
        "PacketMergeReport",
        "PacketLineageDigest",
        "ResidualCarryForwardReport",
    ]:
        Draft202012Validator.check_schema(schema_by_type(schema_name))
    for schema_name, path in examples.items():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema_by_type(schema_name)).iter_errors(data),
            key=str,
        )
        assert errors == []
