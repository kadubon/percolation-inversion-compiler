from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.acceleration.records import (
    BottleneckCandidate,
    PhaseAccelerationPlan,
)
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.interop.ccr import (
    alt_ecpt_bridge_report,
    bit_registry_report,
    bit_tasks_from_registry,
    ccr_residuals_from_phase_plan,
    ccr_tasks_from_phase_plan,
    diagnose_sqot_queue_state,
    trace_check_report,
    trace_normal_form_report,
    trace_packet_candidate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _schema(relative: str) -> dict[str, object]:
    data = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_phase_plan_to_ccr_tasks_preserves_hints_without_authority() -> None:
    plan = PhaseAccelerationPlan(
        plan_id="phase-plan:test",
        profile="development",
        bottlenecks=[
            BottleneckCandidate(
                candidate_id="bottleneck:sqot",
                source="sqot",
                bottleneck_kind="queue-service-and-diagnostic-reserve",
                target_component="SQOT",
                priority_score=8.0,
                residual_coordinates=["diagnostic_reserve"],
                next_safe_commands=["pic phase plan --compact --profile development"],
                cannot_promote_because=["missing diagnostic reserve"],
                candidate_only=True,
            )
        ],
        candidate_only_reasons=["external candidate has no verifier route"],
        settled_blockers=["baseline not resource matched"],
        safe_commands=["pic phase gap --compact --profile development"],
    )

    tasks = ccr_tasks_from_phase_plan(plan)
    task_validator = Draft202012Validator(_schema("schemas/interop/ccr_task.schema.json"))
    for task in tasks:
        task_validator.validate(task)
        assert task["constraints"]["allowed_commands"] == []
        assert task["pic_interop"]["candidate_only_until_checked"] is True
        assert task["status"] == "open"

    safe_hint_tasks = [task for task in tasks if task["extensions"]["x_pic_safe_command_hints"]]
    assert safe_hint_tasks
    assert all(task["schema_version"] == "ccr.task.v0.1" for task in tasks)

    residuals = ccr_residuals_from_phase_plan(plan)
    residual_validator = Draft202012Validator(_schema("schemas/interop/ccr_residual.schema.json"))
    for residual in residuals:
        residual_validator.validate(residual)
    assert any(item["blocking"] for item in residuals)
    assert any(item["kind"] == "candidate_only_reason" for item in residuals)


def test_alt_ecpt_bridge_keeps_proxy_negative_and_missing_baseline_as_residuals() -> None:
    report = alt_ecpt_bridge_report(
        {
            "packet_id": "alt-packet:test",
            "receiver_family": ["ccr-runtime"],
            "negative_liquidity_certificate": {"reason": "downstream cost increased"},
            "liquidity_certificate": {
                "cost_ledger": {"formation_cost": 1.0},
                "hazard_envelope_certificate": {"hazard_refs": ["hazard:test"]},
                "transport_certificate": {
                    "target_receiver_family": ["ccr-runtime"],
                },
                "value_bridge_report": {"proxy_only": True},
            },
        }
    )

    kinds = {item["kind"] for item in report["residuals"]}
    assert report["accepted"] is False
    assert report["settled"] is False
    assert "missing_baseline" in kinds
    assert "negative_liquidity_preserved" in kinds
    assert "proxy_only_value_evidence" in kinds
    assert report["ecpt_contribution"]["liquidity_lower_bound"] is None


def test_sqot_queue_state_does_not_treat_scalar_or_unknown_budget_as_zero() -> None:
    report = diagnose_sqot_queue_state({"queue_score": 0.1})
    kinds = {item["kind"] for item in report["residuals"]}

    assert report["queue_status"] == "diagnostic"
    assert "missing_diagnostic_reserve" in kinds
    assert "missing_verifier_capacity" in kinds
    assert "scalar_queue_score_incomplete" in kinds
    assert report["diagnostic_reserve"]["available"] is None
    assert any(
        task["extensions"]["x_pic_task_kind"] == "sqot_queue_repair"
        for task in report["repair_tasks"]
    )


def test_trc_trace_normal_form_requires_authority_without_executing() -> None:
    normalized = trace_normal_form_report(
        {
            "trace_id": "trace:test",
            "steps": [
                {
                    "step_id": "s1",
                    "tool": "local-check",
                    "input": {"path": "candidate.json"},
                    "output": {"accepted": True},
                }
            ],
        }
    )
    checked = trace_check_report(normalized)
    packet = trace_packet_candidate(normalized)
    residual_kinds = {item["kind"] for item in checked["residuals"]}

    assert normalized["accepted"] is True
    assert checked["accepted"] is False
    assert checked["execution_available"] is False
    assert "missing_authority_envelope" in residual_kinds
    assert "missing_step_witness" in checked["execution_blockers"]
    assert "missing_resource_ledger" in checked["execution_blockers"]
    assert "missing_rollback_escrow_obligation" in checked["execution_blockers"]
    assert "missing_tolerance_ledger" in checked["execution_blockers"]
    assert checked["real_world_operation_gate"]["operation_ready"] is False
    assert packet["status"] == "candidate"
    assert packet["settled"] is False


def test_trc_trace_check_requires_resource_rollback_and_tolerance_for_operation() -> None:
    normalized = trace_normal_form_report(
        {
            "trace_id": "trace:operation",
            "steps": [
                {
                    "authority_envelope": {
                        "issuer": "operator:test",
                        "scope": "local_fixture",
                        "status": "approved",
                    },
                    "evidence_refs": ["evidence:fixture"],
                    "postcondition": {"fixture_written": True},
                    "precondition": {"fixture_exists": True},
                    "resource_ledger": {"budget": 1, "units": "fixture"},
                    "rollback_escrow_obligation": {"rollback": "delete fixture output"},
                    "step_id": "s1",
                    "tolerance_ledger": {"observation_error": 0.0},
                    "tool": "fixture-provider",
                    "validity_domain": {"environment": "local-test"},
                }
            ],
        }
    )
    checked = trace_check_report(normalized)

    assert checked["accepted"] is True
    assert checked["execution_available"] is True
    assert checked["execution_blockers"] == []
    assert checked["real_world_operation_gate"]["operation_ready"] is True
    assert checked["real_world_operation_gate"]["executed"] is False


def test_bit_registry_extracts_dependencies_and_emits_witness_tasks() -> None:
    registry = bit_registry_report(
        "\n".join(
            [
                "MRRecord|claim|claim:alpha|text=Alpha claim",
                "MRRecord|depends|claim:alpha|depends_on=claim:seed",
                "MRRecord|unsupported|x|field",
            ]
        ),
        source="inline-test",
    )

    assert registry["dependency_edges"] == [
        {"source": "claim:seed", "target": "claim:alpha", "type": "depends"}
    ]
    assert registry["missing_witness_claims"] == ["claim:alpha"]
    residual_kinds = {item["kind"] for item in registry["residuals"]}
    assert "partial_field" in residual_kinds
    assert "unknown_record_type" in residual_kinds

    tasks = bit_tasks_from_registry(registry)
    assert len(tasks) == 1
    assert tasks[0]["role"] == "formalizer"
    assert tasks[0]["constraints"]["allowed_commands"] == []


def test_bit_cli_roundtrip_recognizes_witness_claim_fields(tmp_path: Path) -> None:
    source = tmp_path / "registry.tex"
    registry = tmp_path / "registry.jsonl"
    source.write_text(
        "\n".join(
            [
                "MRRecord|claim|claim:alpha|text=Alpha claim",
                "MRRecord|witness|w1|claim=claim:alpha",
            ]
        ),
        encoding="utf-8",
    )

    extracted = runner.invoke(
        app,
        ["bit", "extract-registry", "--source", str(source), "--output", str(registry)],
    )
    verified = runner.invoke(app, ["bit", "verify-witnesses", "--registry", str(registry)])

    assert extracted.exit_code == 0
    assert verified.exit_code == 0
    assert json.loads(verified.output)["accepted"] is True

    missing_source = tmp_path / "missing.tex"
    missing_registry = tmp_path / "missing.jsonl"
    missing_source.write_text(
        "MRRecord|claim|claim:beta|text=Beta claim",
        encoding="utf-8",
    )
    runner.invoke(
        app,
        [
            "bit",
            "extract-registry",
            "--source",
            str(missing_source),
            "--output",
            str(missing_registry),
        ],
    )
    emitted = runner.invoke(app, ["bit", "emit-ccr-tasks", "--registry", str(missing_registry)])

    assert emitted.exit_code == 0
    emitted_lines = [json.loads(line) for line in emitted.output.splitlines() if line.strip()]
    assert emitted_lines[0]["extensions"]["x_pic_task_kind"] == "bit_witness_completion"


def test_asi_proxy_bundle_request_emits_ccr_tasks() -> None:
    compact = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--request",
            str(REPO_ROOT / "examples/asi_proxy_benchmark_bundle/pic_phase_request.json"),
            "--compact",
        ],
    )
    result = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--request",
            str(REPO_ROOT / "examples/asi_proxy_benchmark_bundle/pic_phase_request.json"),
            "--compact",
            "--emit",
            "ccr-tasks",
        ],
    )

    assert compact.exit_code == 0
    compact_data = json.loads(compact.output)
    expected = json.loads(
        (REPO_ROOT / "examples/asi_proxy_benchmark_bundle/expected_phase_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert compact_data["accepted"] == expected["accepted"]
    assert compact_data["settled"] == expected["settled"]
    assert compact_data["top_bottlenecks"][0]["bottleneck_kind"] == expected["top_bottleneck_kind"]

    assert result.exit_code == 0
    tasks = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert tasks
    assert all(task["schema_version"] == "ccr.task.v0.1" for task in tasks)
    assert all(task["constraints"]["allowed_commands"] == [] for task in tasks)


def test_asi_proxy_bundle_trc_trace_is_operation_ready_candidate(tmp_path: Path) -> None:
    trace_nf = tmp_path / "trace_nf.json"
    trace_report = tmp_path / "trc_trace_report.json"
    normalized = runner.invoke(
        app,
        [
            "trc",
            "trace-normalize",
            "--input",
            str(REPO_ROOT / "examples/asi_proxy_benchmark_bundle/trc_agent_trace.json"),
            "--output",
            str(trace_nf),
        ],
    )
    checked = runner.invoke(
        app,
        [
            "trc",
            "trace-check",
            "--trace",
            str(trace_nf),
            "--output",
            str(trace_report),
        ],
    )

    assert normalized.exit_code == 0
    assert checked.exit_code == 0
    data = json.loads(trace_report.read_text(encoding="utf-8"))
    assert data["execution_available"] is True
    assert data["real_world_operation_gate"]["operation_ready"] is True
    assert data["real_world_operation_gate"]["executed"] is False


def test_pic_consumes_ccr_runtime_export_fixture() -> None:
    ccr_export = (
        Path("C:/Users/1991m/Collective Capability Runtime")
        / "examples/asi_proxy_benchmark_bundle/runtime_report_for_pic.json"
    )
    if not ccr_export.exists():
        return

    result = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--runtime-report",
            str(ccr_export),
            "--compact",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["settled"] is False
    blockers = [
        *data.get("settled_blockers", []),
        *data.get("reasons", []),
        *data.get("missing_obligations", []),
        *data.get("cannot_promote_because", []),
    ]
    assert "experiment export does not settle phase claims" in blockers
