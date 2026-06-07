from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import percolation_inversion_compiler.cli as cli_module
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.core import EvidenceArtifact, VerifierEvidenceEnvelope
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitness,
    EdgeWitnessCertificate,
    PacketPromotionPolicy,
    PacketSourceKind,
    build_packet_registry,
    build_psi_dashboard,
    find_accepted_paths_to_basin,
    verify_edge_relation,
)
from percolation_inversion_compiler.io.schema import load_data
from percolation_inversion_compiler.runtime import (
    AgentTask,
    FileEvidenceEnvelopeStore,
    ResourceEnvelope,
    ResourceMatchedBaselineConfig,
    RouteExecutionRequest,
    RuntimeExecutorPolicy,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    SQLiteRuntimeStore,
    build_acceleration_experiment_suite,
    build_runtime_run_report,
    certify_runtime_acceleration,
    compare_runtime_runs,
    create_runtime_app,
    execute_route_batch,
    execute_runtime_task,
    promote_packet_candidate,
    resolve_step_evidence,
)
from percolation_inversion_compiler.runtime import service as runtime_service

runner = CliRunner()


def _runtime_state() -> RuntimeState:
    return RuntimeState.model_validate(json.loads(Path("examples/runtime_state.json").read_text()))


def _packet(packet_id: str, *, route: str = "adapters.domain.verify_ecpt_numerical_envelope"):
    return CapabilityPacketCandidate(
        packet_id=packet_id,
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref=f"{packet_id}.txt",
        content_sha256="a" * 64,
        claim=f"{packet_id} phase packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:" + "a" * 64],
        expected_downstream_gain=0.8,
        verification_cost=0.1,
        verifier_routes=[route],
        tags=["phase", "code"],
        rollback_available=True,
    )


def _resolution_envelope() -> VerifierEvidenceEnvelope:
    artifact = EvidenceArtifact(
        artifact_id="artifact:env",
        evidence_kind="finite-numerical-envelope",
        sha256="b" * 64,
        media_type="application/json",
        schema_uri="schema:finite-numerical-envelope",
        schema_sha256="c" * 64,
        producer_id="test-producer",
        produced_at="2026-06-07T00:00:00Z",
        verifier_id="test-verifier",
        verifier_version="0.3.2",
        content_ref="payload.json",
    )
    return VerifierEvidenceEnvelope(
        envelope_id="env:finite",
        route_id="adapters.domain.verify_ecpt_numerical_envelope",
        obligation_ids=["ob:finite"],
        evidence_kind=["finite-numerical-envelope"],
        evidence_refs=["sha256:" + "b" * 64],
        evidence_artifacts=[artifact],
    )


def test_production_packet_promotion_rejects_without_edge_certificate() -> None:
    packet = _packet("packet:target")
    result = promote_packet_candidate(
        packet,
        [],
        [],
        PacketPromotionPolicy.for_profile("production"),
    )
    assert not getattr(result, "operationally_usable", False)
    assert "packet verifier route resolution is missing" in result.reasons
    assert "packet has no accepted edge certificate" in result.reasons


def test_evidence_ref_store_resolves_content_addressed_envelope(tmp_path: Path) -> None:
    envelope = _resolution_envelope()
    payload = json.dumps(envelope.model_dump(mode="json"), sort_keys=True).encode()
    digest = __import__("hashlib").sha256(payload).hexdigest()
    (tmp_path / f"{digest}.json").write_bytes(payload)
    step_input = RuntimeStepInput(
        input_id="input:evidence-ref",
        evidence_envelope_refs=[f"sha256:{digest}"],
    )
    batch = resolve_step_evidence(
        step_input,
        profile="research",
        envelope_store=FileEvidenceEnvelopeStore(tmp_path),
    )
    assert batch.unresolved_envelope_refs == []
    assert batch.resolutions


def test_evidence_ref_store_fails_closed_on_bad_refs_and_payloads(tmp_path: Path) -> None:
    store = FileEvidenceEnvelopeStore(tmp_path)
    assert store.load("sha256:not-a-digest") is None
    assert store.load("../outside.json") is None
    assert store.load(str((tmp_path / "absolute.json").resolve())) is None
    assert store.load("missing.json") is None

    bad_digest = "0" * 64
    (tmp_path / f"{bad_digest}.json").write_text("{}", encoding="utf-8")
    assert store.load(f"sha256:{'1' * 64}") is None
    mismatch_digest = "1" * 64
    (tmp_path / f"{mismatch_digest}.json").write_text("{}", encoding="utf-8")
    assert store.load(f"sha256:{mismatch_digest}") is None

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert store.load("malformed.json") is None

    invalid_model = tmp_path / "invalid-model.json"
    invalid_model.write_text('{"envelope_id": "missing-route"}', encoding="utf-8")
    assert store.load("invalid-model.json") is None

    no_artifacts = VerifierEvidenceEnvelope(
        envelope_id="env:no-artifacts",
        route_id="adapters.domain.verify_ecpt_numerical_envelope",
    )
    no_artifact_payload = json.dumps(no_artifacts.model_dump(mode="json"), sort_keys=True)
    (tmp_path / "no-artifacts.json").write_text(no_artifact_payload, encoding="utf-8")
    assert store.load("no-artifacts.json", profile="production") is None
    assert store.load("no-artifacts.json", profile="research") is not None
    no_artifact_digest = (
        __import__("hashlib").sha256(no_artifact_payload.encode("utf-8")).hexdigest()
    )
    (tmp_path / f"{no_artifact_digest}.json").write_text(no_artifact_payload, encoding="utf-8")
    assert store.load(f"sha256:{no_artifact_digest}", profile="production") is None


def test_edge_relation_verifier_rejects_missing_semantic_markers() -> None:
    source = _packet("packet:source")
    target = _packet("packet:target")
    registry = CapabilityPacketRegistry(registry_id="registry", packets=[source, target])
    certificate = EdgeWitnessCertificate(
        certificate_id="edge-cert:false",
        edge_id="edge:false",
        relation_type="theorem-to-code",
        source_packet_ids=[source.packet_id],
        target_packet_id=target.packet_id,
        evidence_refs=["sha256:" + "a" * 64],
        confidence_lower_bound=0.9,
        false_edge_residual=0.0,
        accepted=True,
    )
    report = verify_edge_relation(registry, certificate)
    assert not report.accepted
    assert report.missing_evidence_markers == ["claim:", "code:"]


def test_qs_and_hz_reduce_under_queue_and_hazard_load() -> None:
    safe = build_packet_registry([_packet("packet:safe")])
    unsafe_packet = _packet("packet:unsafe")
    unsafe_packet = unsafe_packet.model_copy(
        update={
            "hazard_charge": 1.0,
            "authority_required": True,
            "authority_granted": False,
            "route_safe": False,
            "rollback_available": False,
            "expires_at": "expired",
        }
    )
    unsafe = build_packet_registry([unsafe_packet])
    safe_psi = build_psi_dashboard(safe)
    unsafe_psi = build_psi_dashboard(unsafe)
    assert unsafe_psi.components["QS"] < safe_psi.components["QS"]
    assert unsafe_psi.components["HZ"] < safe_psi.components["HZ"]


def test_basin_paths_require_accepted_edges_not_tags_only() -> None:
    source = _packet("packet:source")
    target = _packet("packet:target")
    edge = EdgeWitness(
        edge_id="edge:source-target",
        source_packet_ids=[source.packet_id],
        target_packet_id=target.packet_id,
        edge_type="semantic-dependency",
        confidence=1.0,
        evidence_refs=["sha256:" + "a" * 64],
        accepted=True,
    )
    registry = build_packet_registry([source, target], [edge])
    basin = CapabilityBasinContract(
        basin_id="basin",
        receiver_family=["agent"],
        target_basis=["packet:target"],
        required_edge_types=["semantic-dependency"],
        max_path_cost=2.0,
    )
    paths = find_accepted_paths_to_basin(registry, basin)
    assert paths
    assert paths[0].accepted
    assert edge.edge_id in paths[0].edge_ids


def test_resource_envelope_mismatch_rejects_acceleration_certificate() -> None:
    runtime_state = _runtime_state()
    baseline = build_runtime_run_report(
        runtime_state,
        [],
        run_id="baseline",
        resource_envelope=ResourceEnvelope(wall_time_seconds=1.0, verifier_calls=1),
    )
    candidate = build_runtime_run_report(
        runtime_state,
        [],
        run_id="candidate",
        resource_envelope=ResourceEnvelope(wall_time_seconds=2.0, verifier_calls=1),
    )
    certificate = certify_runtime_acceleration(baseline, candidate)
    assert not certificate.accepted
    assert not certificate.resource_envelope_matched
    assert "runtime runs are not resource matched" in certificate.reasons
    config_mismatch = certify_runtime_acceleration(
        baseline.model_copy(update={"baseline_config": ResourceMatchedBaselineConfig()}),
        candidate.model_copy(
            update={
                "resource_envelope": ResourceEnvelope(wall_time_seconds=1.0, verifier_calls=1),
                "baseline_config": ResourceMatchedBaselineConfig(
                    observation_protocol_id="different-protocol"
                ),
            }
        ),
    )
    assert not config_mismatch.accepted


def test_resource_matched_experiment_suite_accepts_only_clean_comparisons() -> None:
    runtime_state = _runtime_state()
    baseline = build_runtime_run_report(
        runtime_state,
        [],
        run_id="baseline",
        resource_envelope=ResourceEnvelope(wall_time_seconds=1.0, verifier_calls=1),
    )
    candidate = baseline.model_copy(
        update={
            "run_id": "candidate",
            "score_trajectory": [
                baseline.score_trajectory[0].model_copy(update={"total_score": 2.0})
            ]
            if baseline.score_trajectory
            else [],
            "resource_envelope": ResourceEnvelope(wall_time_seconds=1.0, verifier_calls=1),
        }
    )
    comparison = compare_runtime_runs(baseline, candidate)
    rejected = build_acceleration_experiment_suite(
        "suite:negative-control",
        [comparison],
        negative_control_passed=False,
    )
    assert not rejected.accepted
    assert "negative control failed" in rejected.reasons


def test_route_batch_executes_store_envelopes_and_rejects_policy(tmp_path: Path) -> None:
    payload = load_data("examples/runtime_step_input_with_evidence.json")
    envelope = payload["evidence_envelopes"][0]
    (tmp_path / "runtime-proxy-target-envelope.json").write_text(
        json.dumps(envelope, sort_keys=True),
        encoding="utf-8",
    )
    request = RouteExecutionRequest.model_validate(
        load_data("examples/runtime_route_requests.json")["requests"][0]
    )
    accepted = execute_route_batch(
        [request],
        FileEvidenceEnvelopeStore(tmp_path),
        RuntimeExecutorPolicy(profile="research"),
        profile="research",
    )
    assert accepted.reports
    assert accepted.reports[0].accepted

    rejected = execute_route_batch(
        [request],
        FileEvidenceEnvelopeStore(tmp_path),
        RuntimeExecutorPolicy(
            profile="research",
            allowed_route_ids=["adapters.domain.verify_trc_telemetry_calibration"],
        ),
        profile="research",
    )
    assert not rejected.accepted
    assert "one or more routes are outside executor policy" in rejected.reasons


def test_executor_and_sqlite_store_round_trip(tmp_path: Path) -> None:
    runtime_state = _runtime_state()
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    task = AgentTask(
        task_id="task:evidence",
        task_type="evidence-verify",
        priority_score=1.0,
        target_component="VT",
        action_kind="route-execution",
        metadata={"authority_granted": "true", "rollback_receipt": "receipt"},
    )
    report = execute_runtime_task(
        task,
        runtime_state,
        RuntimeExecutorPolicy(profile="production"),
        store=store,
    )
    store.append_state(runtime_state)
    run = build_runtime_run_report(runtime_state, [], run_id="store-run")
    store.append_run(run)
    store.append_certificate(certify_runtime_acceleration(run, run))
    loaded = store.load_state(runtime_state.state_id)
    snapshot = store.snapshot()
    assert report.accepted
    assert loaded is not None
    assert snapshot.events
    assert snapshot.runs
    assert snapshot.certificates
    assert snapshot.aggregate_sha256 != "0" * 64


def test_executor_rejects_unauthorized_task_variants() -> None:
    runtime_state = _runtime_state()
    task = AgentTask(
        task_id="task:unauthorized",
        task_type="shell",
        priority_score=1.0,
        target_component="HZ",
        action_kind="shell",
        required_routes=["missing.route"],
        rollback_condition="",
        metadata={},
    )
    report = execute_runtime_task(
        task,
        runtime_state,
        RuntimeExecutorPolicy(
            profile="production",
            allowed_route_ids=["adapters.domain.verify_ecpt_numerical_envelope"],
        ),
    )
    joined = " ".join(report.reasons)
    assert not report.accepted
    assert "not allowlisted" in joined
    assert "authority grant" in joined
    assert "rollback receipt" in joined
    assert "outside executor policy" in joined


def test_v032_service_endpoints_and_request_size(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fastapi = pytest.importorskip("fastapi")
    _ = fastapi
    from fastapi.testclient import TestClient

    monkeypatch.setenv("PIC_RUNTIME_TOKEN", "runtime-token")
    client = TestClient(create_runtime_app(RuntimeServiceSettings(profile="production")))
    headers = {"Authorization": "Bearer runtime-token"}
    state = load_data("examples/runtime_state.json")

    task = load_data("examples/runtime_agent_task.json")
    execute = client.post(
        "/runtime/task/execute",
        headers=headers,
        json={"state": state, "task": task, "policy": {"profile": "production"}},
    )
    assert execute.status_code == 200
    assert execute.json()["accepted"]

    routes = client.post(
        "/runtime/routes/execute",
        headers=headers,
        json={
            "requests": load_data("examples/runtime_route_requests.json")["requests"],
            "policy": {"profile": "production"},
        },
    )
    assert routes.status_code == 200
    assert not routes.json()["accepted"]

    store_name = tmp_path.joinpath("service-store.sqlite").name
    append = client.post(
        "/runtime/store/append",
        headers=headers,
        json={
            "store": store_name,
            "state": state,
            "run": load_data("examples/runtime_candidate_run.json"),
        },
    )
    assert append.status_code == 200
    assert append.json()["state_count"] >= 1
    loaded = client.post(
        "/runtime/store/load",
        headers=headers,
        json={"store": store_name, "state_id": state["state_id"]},
    )
    assert loaded.status_code == 200
    assert loaded.json()["state_id"] == state["state_id"]
    missing = client.post(
        "/runtime/store/load",
        headers=headers,
        json={"store": store_name, "state_id": "missing"},
    )
    assert missing.status_code == 200
    assert not missing.json()["accepted"]

    loop = client.post(
        "/runtime/run-agent-loop",
        headers=headers,
        json={
            "state": state,
            "inputs": [load_data("examples/runtime_step_input.json")],
            "policy": {"profile": "production", "max_tasks": 1},
            "store": store_name,
            "max_steps": 1,
        },
    )
    assert loop.status_code == 200
    assert len(loop.json()["reports"]) == 1

    runtime_service._check_request_size(SimpleNamespace(headers={}), 1)
    runtime_service._check_request_size(SimpleNamespace(headers={"content-length": "bad-int"}), 1)
    with pytest.raises(RuntimeError):
        runtime_service._check_request_size(
            SimpleNamespace(headers={"content-length": "2"}),
            1,
        )


def test_v032_cli_executor_store_and_edge_smoke(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    edge_output = tmp_path / "edge-output.json"
    edge_build = runner.invoke(
        app,
        [
            "ecology",
            "build-edges",
            "--packets",
            "examples/ecology_packets.json",
            "--output",
            str(registry_path),
        ],
    )
    assert edge_build.exit_code == 0, edge_build.output

    paths = runner.invoke(
        app,
        [
            "ecology",
            "paths",
            "--registry",
            str(registry_path),
            "--basin",
            "examples/ecpt_basin_contract.json",
        ],
    )
    assert paths.exit_code == 0, paths.output
    assert "paths" in json.loads(paths.output)

    edge = runner.invoke(
        app,
        [
            "ecology",
            "verify-edge",
            "--registry",
            str(registry_path),
            "--certificate",
            "examples/edge_relation_certificate.json",
            "--relation",
            "semantic-dependency",
            "--output",
            str(edge_output),
        ],
    )
    assert edge.exit_code == 0, edge.output
    assert json.loads(edge_output.read_text(encoding="utf-8"))["accepted"]

    task = runner.invoke(
        app,
        [
            "runtime",
            "execute-task",
            "--state",
            "examples/runtime_state.json",
            "--task",
            "examples/runtime_agent_task.json",
            "--policy",
            "examples/runtime_executor_policy.json",
            "--profile",
            "production",
        ],
    )
    assert task.exit_code == 0, task.output
    assert json.loads(task.output)["accepted"]

    routes = runner.invoke(
        app,
        [
            "runtime",
            "execute-routes",
            "--requests",
            "examples/runtime_route_requests.json",
            "--evidence-store",
            str(tmp_path),
            "--profile",
            "development",
        ],
    )
    assert routes.exit_code == 0, routes.output
    assert not json.loads(routes.output)["accepted"]

    store_path = tmp_path / "runtime.sqlite"
    init = runner.invoke(app, ["runtime", "store", "init", "--store", str(store_path)])
    assert init.exit_code == 0, init.output
    append = runner.invoke(
        app,
        [
            "runtime",
            "store",
            "append",
            "--store",
            str(store_path),
            "--state",
            "examples/runtime_state.json",
        ],
    )
    assert append.exit_code == 0, append.output
    loaded = runner.invoke(
        app,
        [
            "runtime",
            "store",
            "load",
            "--store",
            str(store_path),
            "--state-id",
            "runtime-demo",
        ],
    )
    assert loaded.exit_code == 0, loaded.output
    missing = runner.invoke(
        app,
        [
            "runtime",
            "store",
            "load",
            "--store",
            str(store_path),
            "--state-id",
            "missing-state",
        ],
    )
    assert missing.exit_code == 1
    exported = runner.invoke(
        app,
        ["runtime", "store", "export", "--store", str(store_path)],
    )
    assert exported.exit_code == 0, exported.output
    assert json.loads(exported.output)["states"]

    loop = runner.invoke(
        app,
        [
            "runtime",
            "run-agent-loop",
            "--state",
            "examples/runtime_state.json",
            "--inputs",
            "examples/runtime_loop_inputs.jsonl",
            "--store",
            str(store_path),
            "--policy",
            "examples/runtime_executor_policy.json",
            "--max-steps",
            "1",
        ],
    )
    assert loop.exit_code == 0, loop.output
    assert json.loads(loop.output)["reports"]


def test_v032_cli_service_sqot_and_ecpt_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, int, str]] = []

    def fake_run_service(settings: RuntimeServiceSettings) -> None:
        calls.append((settings.host, settings.port, settings.profile))

    monkeypatch.setattr(cli_module, "run_runtime_service", fake_run_service)
    service = runner.invoke(
        app,
        [
            "runtime",
            "service",
            "--host",
            "127.0.0.1",
            "--port",
            "8777",
            "--profile",
            "development",
        ],
    )
    assert service.exit_code == 0, service.output
    assert calls == [("127.0.0.1", 8777, "development")]

    obligations_path = tmp_path / "obligations.json"
    obligations_path.write_text(
        json.dumps(
            {
                "obligations": [
                    {
                        "obligation_id": "obligation:queue-reserve",
                        "verifier_hint": "sqot.adapters.salience.verify_queue_policy",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    schedule = runner.invoke(
        app,
        [
            "sqot",
            "schedule",
            "--packets",
            "examples/sqot_queue.json",
            "--obligations",
            str(obligations_path),
            "--profile",
            "production",
        ],
    )
    assert schedule.exit_code == 0, schedule.output
    assert json.loads(schedule.output)["decisions"]

    audit_path = tmp_path / "ecpt-audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "external_obligation_items": [
                    {
                        "item_id": "ecpt:proxy-target-grounding",
                        "label": "Proxy target grounding",
                        "obligation_category": "proxy-target-grounding",
                        "verifier_route": "adapters.domain.verify_ecpt_proxy_target_contract",
                    },
                    "ignored",
                ]
            }
        ),
        encoding="utf-8",
    )
    routed = runner.invoke(app, ["ecpt", "route-obligations", "--audit", str(audit_path)])
    assert routed.exit_code == 0, routed.output
    assert json.loads(routed.output)["routed_obligations"][0]["route_known"]
