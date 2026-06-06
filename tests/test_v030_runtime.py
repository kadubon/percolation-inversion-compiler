from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.core import (
    AdapterRouteSpec,
    EvidenceArtifact,
    EvidencePolicy,
    VerifierEvidenceEnvelope,
    evidence_policy,
    resolve_adapter_route,
)
from percolation_inversion_compiler.core.ledger import CoordinateKind, Ledger
from percolation_inversion_compiler.ecology import build_packet_registry
from percolation_inversion_compiler.ecology.records import (
    CapabilityPacketCandidate,
    PacketIngestionReport,
    PacketSourceKind,
)
from percolation_inversion_compiler.ecpt import PhaseControlAction
from percolation_inversion_compiler.io.schema import load_data, schema_by_type
from percolation_inversion_compiler.runtime import (
    AgentRuntimeConfig,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    build_runtime_step,
    create_runtime_app,
    run_runtime_loop,
    runtime_health,
)

runner = CliRunner()


def _runtime_state() -> RuntimeState:
    return RuntimeState.model_validate(load_data("examples/runtime_state.json"))


def _runtime_input() -> RuntimeStepInput:
    return RuntimeStepInput.model_validate(load_data("examples/runtime_step_input.json"))


def test_runtime_step_is_deterministic_and_never_settles_from_planning() -> None:
    state = _runtime_state()
    step_input = _runtime_input()
    config = AgentRuntimeConfig(profile="production")
    first = build_runtime_step(state, step_input, config)
    second = build_runtime_step(state, step_input, config)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.accepted
    assert first.agent_tasks
    assert first.route_execution_requests
    assert first.finite_checks_passed
    assert not first.operationally_usable
    assert not first.settled
    assert all(not task.settled for task in first.agent_tasks)
    assert any(
        "proxy-target-grounding-proof" in request.residual_external_obligations
        for request in first.route_execution_requests
    )
    recommend_only = build_runtime_step(
        state,
        step_input,
        AgentRuntimeConfig(profile="production", action_commit_policy="recommend_only"),
    )
    assert "policy is recommend_only" in recommend_only.action_commits[0].reasons


def test_runtime_loop_preserves_residual_ledgers_across_steps() -> None:
    state = _runtime_state()
    lines = Path("examples/runtime_loop_inputs.jsonl").read_text(encoding="utf-8").splitlines()
    inputs = [RuntimeStepInput.model_validate(json.loads(line)) for line in lines if line.strip()]
    reports = run_runtime_loop(state, inputs, AgentRuntimeConfig(profile="production"), max_steps=2)
    assert [report.step_index for report in reports] == [0, 1]
    assert reports[1].residual_ledger.burden_sum() >= reports[0].residual_ledger.burden_sum()
    assert not any(report.settled for report in reports)


def test_runtime_score_penalizes_residual_debt_and_rewards_proxy_gain() -> None:
    state = _runtime_state()
    step_input = _runtime_input()
    config = AgentRuntimeConfig(profile="research")
    normal = build_runtime_step(state, step_input, config)
    debt_state = state.model_copy(
        update={
            "residual_ledger": Ledger().add_coordinate(
                "test:debt",
                5.0,
                kind=CoordinateKind.RESIDUAL,
            )
        }
    )
    debt = build_runtime_step(debt_state, step_input, config)
    assert normal.phase_acceleration_score.total_score > debt.phase_acceleration_score.total_score
    assert normal.phase_acceleration_score.finite_proxy_gain > 0.0


def test_runtime_live_connector_requires_explicit_dual_opt_in() -> None:
    state = _runtime_state()
    live_input = RuntimeStepInput(
        input_id="live-disabled",
        live_sources=["https://github.com/kadubon/percolation-inversion-compiler"],
        allow_live_connectors=False,
    )
    report = build_runtime_step(
        state,
        live_input,
        AgentRuntimeConfig(profile="production", allow_live_connectors=False),
    )
    assert not report.ingestion_reports[0].accepted
    assert report.ingestion_reports[0].rejected_sources
    assert "live connector" in " ".join(report.ingestion_reports[0].reasons)
    assert not report.allow_live_connectors


def test_runtime_branches_for_live_local_duplicate_unknown_route_and_empty_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import percolation_inversion_compiler.runtime.algorithms as runtime_algorithms

    state = _runtime_state().model_copy(update={"phase_actions": []})
    duplicate = state.packet_registry.packets[0]
    live_packet = CapabilityPacketCandidate(
        packet_id=duplicate.packet_id,
        source_kind=PacketSourceKind.GITHUB,
        source_ref="owner/repo",
        content_sha256="2" * 64,
        claim="Live ECPT packet",
        evidence_refs=["sha256:" + "2" * 64],
        expected_downstream_gain=0.3,
        verification_cost=0.1,
        verifier_routes=["missing.route"],
    )

    def fake_live_source(
        source: str,
        *,
        kind: PacketSourceKind,
        token: str | None = None,
    ) -> PacketIngestionReport:
        _ = source, kind, token
        return PacketIngestionReport(
            report_id="packet-ingestion:fake-live",
            accepted=True,
            source_kind=PacketSourceKind.GITHUB,
            packets=[live_packet],
        )

    monkeypatch.setattr(runtime_algorithms, "ingest_live_source", fake_live_source)
    local_source = tmp_path / "runtime-local.txt"
    local_source.write_text("Local ECPT runtime packet with certificate route.", encoding="utf-8")
    step_input = RuntimeStepInput(
        input_id="branch-step",
        local_sources=["missing-runtime-source.txt", str(local_source)],
        live_sources=["https://github.com/owner/repo"],
        packets=[duplicate],
        allow_live_connectors=True,
    )
    report = build_runtime_step(
        state,
        step_input,
        AgentRuntimeConfig(
            profile="development",
            allow_live_connectors=True,
            action_commit_policy="allow_finite_scope_commit",
            required_routes=["missing.route"],
        ),
    )
    assert report.allow_live_connectors
    assert any(not ingestion.accepted for ingestion in report.ingestion_reports)
    assert "phase-control-action-catalog" in report.phase_run_report.plan.missing_obligations
    assert any(
        request.obligation_category == "unknown-route"
        for request in report.route_execution_requests
    )
    assert any("duplicate packet id" in reason for reason in report.reasons)
    next_state = runtime_algorithms.loop_state_after_report(state, report)
    assert next_state.step_index == state.step_index + 1
    assert runtime_algorithms.collect_missing_routes(["missing.route"]) == ["missing.route"]
    empty_registry = build_packet_registry([], [])
    assert runtime_algorithms._stale_ratio(empty_registry) == 0.0
    assert runtime_algorithms._false_liquidity_rate(empty_registry) == 0.0
    skipped = runtime_algorithms._agent_tasks(
        phase_actions=[
            PhaseControlAction(
                action_id="negative",
                target_node="phase-transition-proxy",
                activation_delta=0.0,
                burden_delta=1.0,
            )
        ],
        bottleneck_interventions=[],
        route_specs={},
        max_tasks=1,
        minimum_task_score=0.0,
    )
    assert skipped == []


def test_runtime_health_and_public_schemas() -> None:
    state = _runtime_state()
    health = runtime_health(state, AgentRuntimeConfig(profile="production"))
    assert health.accepted
    assert not health.settled
    for name in [
        "AgentRuntimeConfig",
        "RuntimeState",
        "RuntimeStepInput",
        "RuntimeStepReport",
        "RuntimeHealthReport",
        "RuntimeServiceSettings",
        "PhaseAccelerationScore",
        "AgentTask",
        "RouteExecutionRequest",
        "ActionCommit",
    ]:
        assert schema_by_type(name)["title"] == name


def test_runtime_cli_smoke(tmp_path: Path) -> None:
    step_output = tmp_path / "runtime-step.json"
    step = runner.invoke(
        app,
        [
            "runtime",
            "step",
            "--state",
            "examples/runtime_state.json",
            "--input",
            "examples/runtime_step_input.json",
            "--profile",
            "production",
            "--output",
            str(step_output),
        ],
    )
    assert step.exit_code == 0, step.output
    step_data = json.loads(step_output.read_text(encoding="utf-8"))
    assert step_data["agent_tasks"]
    assert not step_data["settled"]

    loop_output = tmp_path / "runtime-loop.json"
    loop = runner.invoke(
        app,
        [
            "runtime",
            "loop",
            "--state",
            "examples/runtime_state.json",
            "--inputs",
            "examples/runtime_loop_inputs.jsonl",
            "--max-steps",
            "2",
            "--profile",
            "production",
            "--output",
            str(loop_output),
        ],
    )
    assert loop.exit_code == 0, loop.output
    assert len(json.loads(loop_output.read_text(encoding="utf-8"))["reports"]) == 2

    health = runner.invoke(
        app,
        ["runtime", "health", "--state", "examples/runtime_state.json", "--profile", "production"],
    )
    assert health.exit_code == 0, health.output
    assert json.loads(health.output)["finite_checks_passed"]

    openapi_path = tmp_path / "openapi.json"
    openapi = runner.invoke(app, ["runtime", "export-openapi", "--output", str(openapi_path)])
    assert openapi.exit_code == 0, openapi.output
    assert "/runtime/step" in json.loads(openapi_path.read_text(encoding="utf-8"))["paths"]


def test_runtime_service_auth_and_step(monkeypatch: pytest.MonkeyPatch) -> None:
    fastapi = pytest.importorskip("fastapi")
    _ = fastapi
    from fastapi.testclient import TestClient

    settings = RuntimeServiceSettings(profile="production")
    service = create_runtime_app(settings)
    client = TestClient(service)
    missing = client.get("/health")
    assert missing.status_code == 503
    monkeypatch.setenv("PIC_RUNTIME_TOKEN", "runtime-token")
    wrong = client.get("/health", headers={"Authorization": "Bearer wrong"})
    assert wrong.status_code == 401
    ok = client.get("/health", headers={"Authorization": "Bearer runtime-token"})
    assert ok.status_code == 200

    request_payload = load_data("examples/runtime_service_step_request.json")
    step = client.post(
        "/runtime/step",
        headers={"Authorization": "Bearer runtime-token"},
        json=request_payload,
    )
    assert step.status_code == 200
    data = step.json()
    assert data["agent_tasks"]
    assert not data["settled"]
    openapi = client.get(
        "/schemas/openapi.json",
        headers={"Authorization": "Bearer runtime-token"},
    )
    assert openapi.status_code == 200
    assert "/runtime/loop" in openapi.json()["paths"]

    loop = client.post(
        "/runtime/loop",
        headers={"Authorization": "Bearer runtime-token"},
        json={
            "state": request_payload["state"],
            "inputs": [request_payload["input"]],
            "config": request_payload["config"],
            "max_steps": 1,
        },
    )
    assert loop.status_code == 200
    assert len(loop.json()["reports"]) == 1

    ingest = client.post(
        "/ecology/ingest",
        headers={"Authorization": "Bearer runtime-token"},
        json={"source": "ECPT service packet", "kind": "agent-output"},
    )
    assert ingest.status_code == 200
    assert ingest.json()["accepted"]

    disabled_live = client.post(
        "/ecology/ingest",
        headers={"Authorization": "Bearer runtime-token"},
        json={"source": "owner/repo", "kind": "github", "allow_live_connectors": False},
    )
    assert disabled_live.status_code == 200
    assert not disabled_live.json()["accepted"]

    evidence = client.post(
        "/evidence/verify",
        headers={"Authorization": "Bearer runtime-token"},
        json={"envelope": load_data("examples/evidence_envelope.json"), "profile": "development"},
    )
    assert evidence.status_code == 200
    unknown = load_data("examples/evidence_envelope.json")
    unknown["route_id"] = "missing.route"
    rejected = client.post(
        "/evidence/verify",
        headers={"Authorization": "Bearer runtime-token"},
        json=unknown,
    )
    assert rejected.status_code == 422

    dev_client = TestClient(create_runtime_app(RuntimeServiceSettings(profile="development")))
    assert dev_client.get("/health").status_code == 200

    import percolation_inversion_compiler.runtime.service as runtime_service

    def fake_service_live(
        source: str, *, kind: PacketSourceKind, token: str | None = None
    ) -> PacketIngestionReport:
        _ = source, kind, token
        return PacketIngestionReport(
            report_id="packet-ingestion:service-live",
            accepted=True,
            source_kind=PacketSourceKind.GITHUB,
        )

    monkeypatch.setattr(runtime_service, "ingest_live_source", fake_service_live)
    live_client = TestClient(
        create_runtime_app(
            RuntimeServiceSettings(profile="development", allow_live_connectors=True)
        )
    )
    live = live_client.post(
        "/ecology/ingest",
        json={"source": "owner/repo", "kind": "github", "allow_live_connectors": True},
    )
    assert live.status_code == 200
    assert live.json()["accepted"]


def test_runtime_service_runner_uses_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    import percolation_inversion_compiler.runtime.service as runtime_service

    calls: list[tuple[str, int]] = []

    class FakeUvicorn:
        @staticmethod
        def run(_: object, *, host: str, port: int) -> None:
            calls.append((host, port))

    def fake_import(name: str) -> object:
        if name == "uvicorn":
            return FakeUvicorn
        return __import__(name)

    monkeypatch.setattr(runtime_service.importlib, "import_module", fake_import)
    runtime_service.run_runtime_service(
        RuntimeServiceSettings(host="127.0.0.1", port=8766, profile="development")
    )
    assert calls == [("127.0.0.1", 8766)]


def test_verifier_evidence_fail_closed_branches_are_explicit() -> None:
    assert evidence_policy("research").profile.value == "research"
    spec = AdapterRouteSpec(
        route_id="test.unavailable",
        verifier_route="test.unavailable",
        obligation_category="test",
        availability="unavailable",
        required_evidence_kind=["required-kind"],
        residual_policy="preserve-test-residual",
        safe_default="diagnostic-test",
    )
    artifact = EvidenceArtifact(
        artifact_id="artifact:test",
        evidence_kind="wrong-kind",
        sha256="0" * 64,
        media_type="application/json",
        schema_uri="schema:test",
        schema_sha256="1" * 64,
        producer_id="",
        produced_at="2026-06-06T00:00:00Z",
        verifier_id="",
        verifier_version="",
        content_ref="missing-evidence.json",
    )
    envelope = VerifierEvidenceEnvelope(
        envelope_id="envelope:test",
        route_id="test.unavailable",
        evidence_kind=["wrong-kind"],
        evidence_artifacts=[artifact],
        deterministic=False,
    )
    result = resolve_adapter_route(
        spec,
        envelope,
        policy=EvidencePolicy(
            require_signature=True,
            require_attestation_ref=True,
            require_content_ref=True,
        ),
    )
    reasons = " ".join(result.reasons)
    assert "adapter route is declared unavailable" in reasons
    assert "required evidence artifact kind is missing" in reasons
    assert "evidence artifact signature is missing" in reasons
    assert "evidence artifact attestation_ref is missing" in reasons
    assert "evidence artifact producer_id is missing" in reasons
    assert "evidence artifact verifier_id is missing" in reasons
    assert "evidence artifact verifier_version is missing" in reasons
    assert "sha256 mismatch" in reasons
    assert "not deterministic" in reasons
    assert not result.settled
