from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.acceleration import (
    PhaseAccelerationRequest,
    build_phase_acceleration_benchmark,
    build_phase_acceleration_plan,
    build_phase_trajectory,
    phase_acceleration_compact_payload,
    phase_acceleration_runbook,
)
from percolation_inversion_compiler.agent import (
    AgentIntakeRequest,
    accelerate_agent_phase,
    minimal_runtime_state,
    minimal_runtime_step_input,
)
from percolation_inversion_compiler.alt import ALTAdmissionDecision
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    GeneralIntakeRuntimeBridgeReport,
    PacketIngestionReport,
    PacketSourceKind,
)
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def _phase_request(profile: str = "development") -> PhaseAccelerationRequest:
    return PhaseAccelerationRequest(
        request_id=f"test-phase:{profile}",
        profile=profile,
        state=minimal_runtime_state(),
        step_input=minimal_runtime_step_input(
            "Candidate packet: preserve residuals and route verifier work."
        ),
        compact=True,
    )


def test_phase_acceleration_plan_is_deterministic_and_unsettled() -> None:
    request = _phase_request()
    first = build_phase_acceleration_plan(request)
    second = build_phase_acceleration_plan(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.workflow_usable is True
    assert first.settled is False
    assert first.phase_gap_vector.limiting_components
    assert first.bottlenecks
    assert first.recommended_actions
    assert "missing obligations remain" in first.cannot_promote_because


def test_phase_acceleration_schema_exports_and_validates_compact_shape() -> None:
    schema = schema_by_type("PhaseAccelerationPlan")
    Draft202012Validator.check_schema(schema)

    plan = build_phase_acceleration_plan(_phase_request())
    compact = phase_acceleration_compact_payload(plan)
    assert compact["report_mode"] == "compact"
    assert "runtime_report" not in compact
    assert "PhaseAccelerationPlan" in compact["schema_refs"]


def test_phase_cli_plan_gap_runbook_benchmark_and_agent_shortcut() -> None:
    plan = runner.invoke(
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
    assert plan.exit_code == 0
    plan_data = json.loads(plan.output)
    assert plan_data["workflow_usable"] is True
    assert plan_data["settled"] is False
    assert plan_data["top_bottlenecks"]

    gap = runner.invoke(app, ["phase", "gap", "--compact"])
    assert gap.exit_code == 0
    assert json.loads(gap.output)["limiting_components"]

    runbook = runner.invoke(app, ["phase", "runbook", "--profile", "development"])
    assert runbook.exit_code == 0
    runbook_data = json.loads(runbook.output)
    assert runbook_data["entrypoint"] == "pic phase plan --compact"
    assert "PhaseAccelerationPlan" in runbook_data["schemas_to_inspect"]

    benchmark = runner.invoke(app, ["phase", "benchmark"])
    assert benchmark.exit_code == 0
    benchmark_data = json.loads(benchmark.output)
    assert benchmark_data["invariant_checks"]["settled_not_promoted"] is True

    agent = runner.invoke(
        app,
        [
            "agent",
            "accelerate",
            "--compact",
            "--text",
            "Candidate packet: preserve residuals.",
        ],
    )
    assert agent.exit_code == 0
    agent_data = json.loads(agent.output)
    assert agent_data["workflow_usable"] is True
    assert agent_data["settled"] is False


def test_production_identity_missing_remains_blocker() -> None:
    plan = build_phase_acceleration_plan(_phase_request("production"))

    assert plan.workflow_usable is True
    assert plan.settled is False
    assert "production/adversarial identity context is missing or not accepted" in (
        plan.cannot_promote_because
    )


def test_external_candidate_only_does_not_reduce_phase_gap() -> None:
    base = build_phase_acceleration_plan(_phase_request())
    bridge = GeneralIntakeRuntimeBridgeReport(
        report_id="general-intake-runtime-bridge:test",
        source_report_id="general-intake:test",
        accepted=True,
        candidate_only=True,
        packet_ingestion=PacketIngestionReport(
            report_id="packet-ingestion:test",
            accepted=True,
            source_kind=PacketSourceKind.WEB_PAGE,
            packets=[],
        ),
        ecpt_phase_contribution_allowed=False,
    )
    candidate = build_phase_acceleration_plan(
        _phase_request().model_copy(update={"general_intake_bridge_reports": [bridge]})
    )

    assert candidate.phase_gap_vector.aggregate_gap == base.phase_gap_vector.aggregate_gap
    assert any("candidate-only" in reason for reason in candidate.candidate_only_reasons)
    assert any(item.candidate_only for item in candidate.bottlenecks)


def test_alt_missing_obligations_are_ranked_without_status_promotion() -> None:
    decision = ALTAdmissionDecision(
        decision_id="alt-admission:test",
        packet_id="alt-packet:test",
        missing_obligations=["alt:value-bridge", "alt:transport"],
        reasons=["proxy-only value evidence is insufficient"],
    )
    plan = build_phase_acceleration_plan(
        _phase_request().model_copy(update={"alt_admission_decisions": [decision]})
    )

    assert plan.settled is False
    assert any(item.target_component == "ALT" for item in plan.bottlenecks)
    assert any("ALT admission" in reason for reason in plan.candidate_only_reasons)


def test_sqot_diagnostics_and_benchmark_are_visible() -> None:
    plan = build_phase_acceleration_plan(_phase_request())
    kinds = {item.bottleneck_kind for item in plan.bottlenecks}
    assert "queue-service-and-diagnostic-reserve" in kinds

    benchmark = build_phase_acceleration_benchmark(plan)
    assert benchmark.invariant_checks["candidate_only_volume_does_not_reduce_gap"] is True
    assert benchmark.invariant_checks["planner_does_not_execute_commands"] is True
    assert benchmark.settled is False


def test_phase_trajectory_and_agent_wrapper() -> None:
    first = _phase_request()
    second = _phase_request().model_copy(update={"request_id": "test-phase:second"})
    trajectory = build_phase_trajectory([first, second], profile="development")
    assert trajectory.workflow_usable is True
    assert trajectory.settled is False
    assert len(trajectory.aggregate_gap_trajectory) == 2

    agent_plan = accelerate_agent_phase(
        AgentIntakeRequest(agent_output="Candidate packet: preserve residuals."),
        compact=True,
    )
    assert agent_plan.workflow_usable is True
    assert agent_plan.runtime_report is None


def test_phase_runbook_is_agent_operable_without_execution_authority() -> None:
    runbook = phase_acceleration_runbook("development")
    assert runbook["accepted"] is True
    assert runbook["settled"] is False
    assert "pic phase plan --compact --profile development" in runbook["commands"]


def test_phase_request_example_is_executable_and_compact() -> None:
    result = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--request",
            "examples/phase_acceleration/phase_acceleration_request.json",
            "--compact",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is True
    assert data["workflow_usable"] is True
    assert data["settled"] is False
    assert data["top_bottlenecks"]


def test_phase_request_rejects_runtime_input_mixing() -> None:
    result = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--request",
            "examples/phase_acceleration/phase_acceleration_request.json",
            "--text",
            "Candidate packet: preserve residuals.",
        ],
    )

    assert result.exit_code != 0
    assert "Use --request by itself" in result.output


def test_phase_request_identity_context_override_removes_identity_blocker() -> None:
    identity_context = Path(".phase-identity-context-test.json")
    try:
        identity_context.write_text(
            json.dumps(
                {
                    "accepted": True,
                    "accepted_agent_ids": ["agent:alice"],
                    "accepted_public_key_ids": ["key:alice"],
                    "context_id": "runtime-identity-context:test",
                    "identity_profile": "production",
                }
            ),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "phase",
                "plan",
                "--request",
                "examples/phase_acceleration/phase_acceleration_request.json",
                "--profile",
                "production",
                "--identity-context",
                str(identity_context),
                "--compact",
            ],
        )
    finally:
        identity_context.unlink(missing_ok=True)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile"] == "production"
    assert data["workflow_usable"] is True
    assert data["settled"] is False
    assert (
        "production/adversarial identity context is missing or not accepted"
        not in (data["cannot_promote_because"])
    )


def test_phase_live_connector_default_and_opt_out_are_visible() -> None:
    enabled = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--text",
            "Candidate packet: preserve residuals.",
        ],
    )
    disabled = runner.invoke(
        app,
        [
            "phase",
            "plan",
            "--text",
            "Candidate packet: preserve residuals.",
            "--no-allow-live-connectors",
        ],
    )

    assert enabled.exit_code == 0
    assert disabled.exit_code == 0
    assert json.loads(enabled.output)["runtime_report"]["allow_live_connectors"] is True
    assert json.loads(disabled.output)["runtime_report"]["allow_live_connectors"] is False


def test_phase_acceleration_schema_indexes_include_all_public_models() -> None:
    expected = {
        "PhaseAccelerationRequest",
        "PhaseAccelerationPlan",
        "PhaseGapVector",
        "PhaseComponentGap",
        "BottleneckCandidate",
        "SafePhaseAction",
        "PhaseTrajectoryReport",
        "PhaseAccelerationBenchmarkReport",
    }
    agent_manifest = json.loads(Path("agent-manifest.json").read_text(encoding="utf-8"))
    schema_index = json.loads(Path("schemas/index.json").read_text(encoding="utf-8"))

    assert expected <= set(agent_manifest["important_schemas"])
    assert expected <= set(schema_index["important_schema_names"])
