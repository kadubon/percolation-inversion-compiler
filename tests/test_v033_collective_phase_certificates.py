from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    CapabilityBasinContract,
    CapabilityPacketCandidate,
    CapabilityPacketRegistry,
    EdgeWitness,
    ExecutionAvailablePathCertificate,
    PacketSourceKind,
    ProtocolFrameDigest,
    build_packet_capital_lineage,
    build_packet_registry,
    build_psi_dashboard,
    check_execution_available_path,
    check_no_hidden_capability_injection,
    find_autocatalytic_closures,
    find_execution_available_paths,
)
from percolation_inversion_compiler.io.schema import schema_model_map
from percolation_inversion_compiler.runtime import (
    AgentPolicyIdentity,
    AgentPopulationState,
    FixedPopulationLedger,
    RuntimeExecutorPolicy,
    RuntimeRunReport,
    RuntimeState,
    RuntimeStepInput,
    SQLiteRuntimeStore,
    build_population_runtime_step,
    certify_collective_phase,
    check_fixed_population_ledger,
    run_agent_loop_with_store,
)

runner = CliRunner()


def _packet(packet_id: str, *, source_kind: PacketSourceKind = PacketSourceKind.AGENT_OUTPUT):
    return CapabilityPacketCandidate(
        packet_id=packet_id,
        source_kind=source_kind,
        source_ref=f"{packet_id}.json",
        content_sha256="a" * 64 if packet_id.endswith("a") else "b" * 64,
        claim=f"{packet_id} collective phase packet",
        receiver_family=["agent", "verifier"],
        evidence_refs=[
            "sha256:" + ("a" * 64 if packet_id.endswith("a") else "b" * 64),
            "closure:witness",
            "regeneration:witness",
            "execution:path",
            "rollback:receipt",
        ],
        expected_downstream_gain=0.9,
        verification_cost=0.1,
        verifier_routes=["adapters.domain.verify_ecpt_proxy_target_contract"],
        tags=["phase", "ecpt"],
        rollback_available=True,
    )


def _registry() -> CapabilityPacketRegistry:
    packet_a = _packet("packet:a")
    packet_b = _packet("packet:b")
    edge_ab = EdgeWitness(
        edge_id="edge:a-b",
        source_packet_ids=["packet:a"],
        target_packet_id="packet:b",
        edge_type="autocatalytic-regeneration",
        confidence=0.9,
        evidence_refs=["closure:witness", "regeneration:witness"],
        accepted=True,
    )
    edge_ba = edge_ab.model_copy(
        update={
            "edge_id": "edge:b-a",
            "source_packet_ids": ["packet:b"],
            "target_packet_id": "packet:a",
        }
    )
    return build_packet_registry([packet_a, packet_b], [edge_ab, edge_ba])


def _basin() -> CapabilityBasinContract:
    return CapabilityBasinContract(
        basin_id="collective-basin",
        receiver_family=["agent"],
        target_basis=["packet:b"],
        required_edge_types=["autocatalytic-regeneration"],
        required_verifier_routes=["adapters.domain.verify_ecpt_proxy_target_contract"],
        max_path_cost=4.0,
    )


def _fixed_ledger(*, self_rewrite: bool = False) -> FixedPopulationLedger:
    before = AgentPolicyIdentity(
        agent_id="agent:fixed",
        policy_digest="policy:" + "1" * 64,
        model_digest="model:" + "2" * 64,
        self_rewrite_allowed=self_rewrite,
        weight_update_allowed=False,
        accepted=not self_rewrite,
    )
    after = before.model_copy()
    return FixedPopulationLedger(
        ledger_id="fixed-population:test",
        before_agents=[before],
        after_agents=[after],
        no_self_rewrite=not self_rewrite,
        no_weight_update=True,
        fixed_population=True,
        policy_digests_unchanged=True,
    )


def _protocol(registry: CapabilityPacketRegistry) -> ProtocolFrameDigest:
    return ProtocolFrameDigest(
        protocol_id="protocol:collective-test",
        allowed_source_kinds=["agent-output"],
        allowed_route_ids=["adapters.domain.verify_ecpt_proxy_target_contract"],
        allowed_packet_ids=[packet.packet_id for packet in registry.packets],
        allowed_evidence_prefixes=[
            "sha256:",
            "closure:",
            "regeneration:",
            "execution:",
            "rollback:",
        ],
        sha256="c" * 64,
        accepted=True,
    )


def _runtime_state(registry: CapabilityPacketRegistry | None = None) -> RuntimeState:
    data = json.loads(Path("examples/runtime_state.json").read_text(encoding="utf-8"))
    state = RuntimeState.model_validate(data)
    return state.model_copy(update={"packet_registry": registry or _registry()})


def _population(state: RuntimeState | None = None) -> AgentPopulationState:
    runtime_state = state or _runtime_state()
    return AgentPopulationState(
        population_id="population:collective-test",
        agents=_fixed_ledger().before_agents,
        runtime_states=[runtime_state],
        fixed_population_ledger=_fixed_ledger(),
        protocol_frame=_protocol(runtime_state.packet_registry),
    )


def test_collective_phase_certificate_accepts_only_collective_packet_phase() -> None:
    registry = _registry()
    state = _runtime_state(registry)
    population = _population(state)
    baseline = RuntimeRunReport(run_id="baseline:collective", initial_state_id=state.state_id)
    certificate = certify_collective_phase(
        population,
        state,
        _basin(),
        baseline,
        {"AC": 0.5, "DE": 0.5, "BR": 0.5, "QS": 0.5, "HZ": 0.5},
    )
    assert certificate.accepted
    assert certificate.finite_checks_passed
    assert not certificate.settled
    assert certificate.closure_witnesses[0].accepted
    assert certificate.execution_available_paths[0].accepted
    assert certificate.psi.components["AC"] >= 0.5
    assert certificate.psi.components["DE"] >= 0.5


def test_self_rewrite_hidden_injection_and_executed_path_fail_closed() -> None:
    rejected_ledger = check_fixed_population_ledger(_fixed_ledger(self_rewrite=True))
    assert not rejected_ledger.accepted
    assert "self-rewrite" in " ".join(rejected_ledger.reasons)

    registry = CapabilityPacketRegistry(
        registry_id="registry:hidden",
        packets=[_packet("packet:a", source_kind=PacketSourceKind.GITHUB)],
    )
    hidden = check_no_hidden_capability_injection(registry, _protocol(_registry()))
    assert not hidden.accepted
    assert hidden.rejected_packet_ids == ["packet:a"]

    path = ExecutionAvailablePathCertificate(
        certificate_id="execution:path:bad",
        path_id="path:bad",
        packet_ids=["packet:a"],
        edge_ids=[],
        not_executed=False,
        execution_gates=["ExecGate"],
        authority_granted=True,
        rollback_available=True,
        receiver_context=["agent"],
        evidence_refs=["sha256:" + "a" * 64],
    )
    checked = check_execution_available_path(path, _registry())
    assert not checked.accepted
    assert "already been executed" in " ".join(checked.reasons)


def test_fixed_population_and_collective_certificate_reject_all_drift_modes() -> None:
    before = AgentPolicyIdentity(
        agent_id="agent:a",
        policy_digest="policy:before",
        model_digest="model:before",
        self_rewrite_allowed=True,
        weight_update_allowed=True,
    )
    after = AgentPolicyIdentity(
        agent_id="agent:b",
        policy_digest="policy:after",
        model_digest="model:after",
        self_rewrite_allowed=False,
        weight_update_allowed=False,
    )
    ledger = check_fixed_population_ledger(
        FixedPopulationLedger(
            ledger_id="fixed-population:bad",
            before_agents=[before],
            after_agents=[after],
            no_self_rewrite=False,
            no_weight_update=False,
            fixed_population=False,
            policy_digests_unchanged=False,
        )
    )
    joined = " ".join(ledger.reasons)
    assert not ledger.accepted
    assert "population changed" in joined
    assert "self-rewrite" in joined
    assert "weight update" in joined
    assert "fixed population" in joined

    packet = _packet("packet:a", source_kind=PacketSourceKind.GITHUB).model_copy(
        update={
            "expected_downstream_gain": 0.0,
            "verification_cost": 2.0,
            "hazard_charge": 1.0,
            "route_safe": False,
            "rollback_available": False,
            "verifier_routes": ["route:outside:1", "route:outside:2", "route:outside:3"],
        }
    )
    state = _runtime_state(build_packet_registry([packet], []))
    population = AgentPopulationState(
        population_id="population:bad",
        agents=[before],
        runtime_states=[state],
        fixed_population_ledger=ledger,
        protocol_frame=ProtocolFrameDigest(protocol_id="protocol:bad"),
    )
    certificate = certify_collective_phase(
        population,
        state,
        _basin(),
        RuntimeRunReport(run_id="", initial_state_id=state.state_id),
        {"AC": 1.0, "DE": 1.0, "QS": 0.99, "HZ": 0.99},
    )
    reasons = " ".join(certificate.reasons)
    assert not certificate.accepted
    assert "fixed population" in reasons
    assert "hidden capability" in reasons
    assert "no accepted autocatalytic" in reasons
    assert "no accepted execution-available" in reasons
    assert "Psi threshold" in reasons
    assert "resource-matched baseline" in reasons
    assert "false liquidity" in reasons
    assert "verification backlog" in reasons
    assert "SQOT diagnostic reserve" in reasons
    assert "hazard/authority" in reasons


def test_closure_diagnostics_and_lineage_failure_modes() -> None:
    packet_a = _packet("packet:a").model_copy(
        update={"expected_downstream_gain": 0.0, "verification_cost": 1.0}
    )
    packet_b = _packet("packet:b").model_copy(
        update={"expected_downstream_gain": 0.0, "verification_cost": 1.0}
    )
    weak_edge = EdgeWitness(
        edge_id="edge:weak-a-b",
        source_packet_ids=[packet_a.packet_id],
        target_packet_id=packet_b.packet_id,
        edge_type="liquidity-transfer",
        confidence=0.1,
        accepted=True,
    )
    weak_return = weak_edge.model_copy(
        update={
            "edge_id": "edge:weak-b-a",
            "source_packet_ids": [packet_b.packet_id],
            "target_packet_id": packet_a.packet_id,
        }
    )
    registry = build_packet_registry([packet_a, packet_b], [weak_edge, weak_return])
    closures = find_autocatalytic_closures(
        registry,
        CapabilityBasinContract(basin_id="basin:other", receiver_family=["other"]),
    )
    assert closures
    assert not closures[0].accepted
    joined = " ".join(closures[0].reasons)
    assert "below threshold" in joined
    assert "no accepted regeneration edge" in joined
    assert "no productive packet" in joined
    assert "false-liquidity" in joined
    assert "receiver-compatible" in joined

    lineage = build_packet_capital_lineage(packet_a)
    assert not lineage.accepted
    assert lineage.reasons


def test_raw_packet_volume_alone_cannot_create_collective_phase_certificate() -> None:
    packets = [_packet(f"packet:{index}") for index in range(6)]
    registry = build_packet_registry(packets, [])
    state = _runtime_state(registry)
    population = _population(state)
    baseline = RuntimeRunReport(run_id="baseline:raw-volume", initial_state_id=state.state_id)
    certificate = certify_collective_phase(
        population,
        state,
        _basin(),
        baseline,
        {"AC": 0.1, "DE": 0.1},
    )
    assert not find_autocatalytic_closures(registry)
    assert not certificate.accepted
    assert "no accepted autocatalytic closure witness" in certificate.reasons


def test_psi_uses_accepted_closure_and_execution_path_certificates() -> None:
    registry = _registry()
    closures = find_autocatalytic_closures(registry, _basin())
    paths = find_execution_available_paths(registry, _basin())
    psi = build_psi_dashboard(
        registry,
        threshold={"AC": 0.5, "DE": 0.5},
        closure_witnesses=closures,
        execution_paths=paths,
        basin=_basin(),
    )
    assert closures and closures[0].accepted
    assert paths and paths[0].accepted
    assert psi.components["AC"] >= 0.5
    assert psi.components["DE"] >= 0.5


def test_run_agent_loop_with_store_applies_execution_results(tmp_path: Path) -> None:
    state = _runtime_state()
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    policy = RuntimeExecutorPolicy(
        profile="development",
        allowed_task_types=["bottleneck-intervention", "phase-control-action"],
        require_authority_grant=False,
        require_rollback_receipt=False,
        max_tasks=2,
    )
    reports = run_agent_loop_with_store(
        state,
        [RuntimeStepInput(input_id="loop:collective", agent_output="phase verifier packet")],
        policy,
        store,
        max_steps=1,
    )
    loaded = store.load_state(state.state_id)
    assert reports
    assert loaded is not None
    assert loaded.step_index >= 1
    assert loaded.execution_report_refs
    assert store.record().execution_report_count >= 1


def test_population_runtime_step_and_schema_registry() -> None:
    population = _population()
    report = build_population_runtime_step(
        population,
        [RuntimeStepInput(input_id="population:input")],
    )
    schemas = schema_model_map()
    assert report.next_population is not None
    assert "CollectivePhaseCertificate" in schemas
    assert "AgentPopulationState" in schemas
    assert "AutocatalyticClosureWitness" in schemas
    assert not report.settled


def test_v033_cli_collective_phase_smoke(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(_registry().model_dump_json(), encoding="utf-8")
    basin_path = tmp_path / "basin.json"
    basin_path.write_text(_basin().model_dump_json(), encoding="utf-8")
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(_protocol(_registry()).model_dump_json(), encoding="utf-8")
    events_path = tmp_path / "events.json"
    events_path.write_text('{"events":[]}', encoding="utf-8")
    population_path = tmp_path / "population.json"
    population_path.write_text(_population().model_dump_json(), encoding="utf-8")
    inputs_path = tmp_path / "inputs.jsonl"
    inputs_path.write_text('{"input_id":"population-cli-input"}\n', encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text(_runtime_state().model_dump_json(), encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        RuntimeRunReport(
            run_id="baseline:cli",
            initial_state_id="runtime-demo",
        ).model_dump_json(),
        encoding="utf-8",
    )
    threshold_path = tmp_path / "threshold.json"
    threshold_path.write_text('{"threshold":{"AC":0.5,"DE":0.5,"BR":0.5,"QS":0.5,"HZ":0.5}}')

    for command in [
        [
            "ecology",
            "closures",
            "--registry",
            str(registry_path),
            "--basin",
            str(basin_path),
        ],
        [
            "ecology",
            "execution-paths",
            "--registry",
            str(registry_path),
            "--basin",
            str(basin_path),
        ],
        [
            "ecology",
            "hidden-injection-check",
            "--registry",
            str(registry_path),
            "--events",
            str(events_path),
            "--protocol",
            str(protocol_path),
        ],
        [
            "runtime",
            "population-step",
            "--population",
            str(population_path),
            "--inputs",
            str(inputs_path),
        ],
        [
            "runtime",
            "collective-certify",
            "--population",
            str(population_path),
            "--state",
            str(state_path),
            "--basin",
            str(basin_path),
            "--baseline",
            str(baseline_path),
            "--threshold",
            str(threshold_path),
        ],
    ]:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)


def test_v033_service_collective_phase_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    fastapi = pytest.importorskip("fastapi")
    _ = fastapi
    from fastapi.testclient import TestClient

    from percolation_inversion_compiler.runtime import RuntimeServiceSettings, create_runtime_app

    monkeypatch.setenv("PIC_RUNTIME_TOKEN", "runtime-token")
    client = TestClient(create_runtime_app(RuntimeServiceSettings(profile="production")))
    headers = {"Authorization": "Bearer runtime-token"}
    registry = _registry().model_dump(mode="json")
    basin = _basin().model_dump(mode="json")
    population = _population().model_dump(mode="json")
    state = _runtime_state().model_dump(mode="json")
    baseline = RuntimeRunReport(
        run_id="baseline:service",
        initial_state_id="runtime-demo",
    ).model_dump(mode="json")

    assert client.post(
        "/ecology/closures",
        headers=headers,
        json={"registry": registry, "basin": basin},
    ).json()["closures"]
    assert client.post(
        "/ecology/execution-paths",
        headers=headers,
        json={"registry": registry, "basin": basin},
    ).json()["execution_available_paths"]
    assert client.post(
        "/ecology/hidden-injection-check",
        headers=headers,
        json={"registry": registry, "protocol": _protocol(_registry()).model_dump(mode="json")},
    ).json()["accepted"]
    assert (
        client.post(
            "/runtime/population/step",
            headers=headers,
            json={"population": population, "inputs": [{"input_id": "service-population-input"}]},
        ).status_code
        == 200
    )
    cert = client.post(
        "/runtime/collective/certify",
        headers=headers,
        json={
            "population": population,
            "state": state,
            "basin": basin,
            "baseline": baseline,
            "threshold": {"AC": 0.5, "DE": 0.5, "BR": 0.5, "QS": 0.5, "HZ": 0.5},
        },
    )
    assert cert.status_code == 200
    payload = cert.json()
    assert not payload["accepted"]
    assert "Sybil-resistance ledger rejected under selected profile" in payload["reasons"]
