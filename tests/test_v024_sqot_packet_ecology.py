from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.ecology import (
    build_bottleneck_plan,
    build_edge_witnesses,
    build_packet_registry,
    build_psi_dashboard,
    closed_loop_iteration,
    ingest_agent_output,
    ingest_local_file,
    packet_from_text,
    registry_from_json,
    registry_to_json,
    verification_throughput,
)
from percolation_inversion_compiler.ecology.algorithms import (
    _bounded_ratio,
    _reachable_packets,
)
from percolation_inversion_compiler.ecology.connectors import (
    infer_live_kind,
    ingest_live_source,
)
from percolation_inversion_compiler.ecology.records import (
    CapabilityPacketCandidate,
    EdgeWitness,
    PacketSourceKind,
)
from percolation_inversion_compiler.io.sbom import build_sbom_document
from percolation_inversion_compiler.io.schema import schema_by_type
from percolation_inversion_compiler.io.snapshots import load_theory_snapshot
from percolation_inversion_compiler.io.tex import (
    extract_theory_coverage,
    strict_tex_parse_report,
)
from percolation_inversion_compiler.sqot import (
    DiagnosticReservePolicy,
    RiskBudgetLedger,
    SalienceDecision,
    SalienceQueueRecord,
    build_salience_schedule,
    check_salience_record,
    reserve_is_adequate,
    salience_priority,
)

runner = CliRunner()


def test_sqot_strict_parse_and_snapshot_when_present() -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    source = (
        Path(canonical_dir) / "Salience-Queue Occupation Theory.tex"
        if canonical_dir
        else Path("missing-sqot-source.tex")
    )
    if not source.exists():
        snapshot = load_theory_snapshot("sqot")
        assert snapshot.coverage_counts["unsupported"] == 0
        return
    grammar = strict_tex_parse_report(source)
    assert grammar.accepted
    coverage = extract_theory_coverage(source)
    assert coverage.definitions == 59
    assert coverage.claims == 74
    assert coverage.counts_by_status()["unsupported"] == 0
    assert coverage.counts_by_status()["partial"] == 0


def test_sqot_scheduler_quarantines_invalid_packet_and_preserves_reserve() -> None:
    valid = SalienceQueueRecord(
        record_id="valid",
        item_type="diagnostic",
        expected_downstream_gain=0.8,
        residual_reduction=0.5,
        verification_cost=0.2,
        salience_class="diagnostic",
    )
    invalid = SalienceQueueRecord(
        record_id="invalid",
        expected_downstream_gain=0.9,
        residual_reduction=0.5,
        verification_cost=0.1,
        evidence_hash_valid=False,
        rollback_available=True,
    )
    report = build_salience_schedule([invalid, valid], attention_budget=1.0, risk_budget=1.0)
    assert report.accepted
    assert reserve_is_adequate(report)
    decisions = {decision.record_id: decision for decision in report.decisions}
    assert decisions["valid"].decision == SalienceDecision.RUN
    assert decisions["invalid"].decision == SalienceDecision.ROLLBACK
    assert not decisions["invalid"].settled


def test_sqot_scheduler_exercises_fail_closed_decisions() -> None:
    invalid = SalienceQueueRecord(
        record_id="invalid",
        expected_downstream_gain=-0.1,
        residual_reduction=-0.1,
        verification_cost=-0.1,
        hazard_charge=-0.1,
        stale=True,
        evidence_hash_valid=False,
        route_safe=False,
        authority_required=True,
        authority_granted=False,
        obligation_ids=["sqot:obligation"],
    )
    rollback_missing = SalienceQueueRecord(
        record_id="rollback-missing",
        item_type="rollback",
        expected_downstream_gain=1.0,
        residual_reduction=0.2,
        verification_cost=0.1,
        rollback_available=False,
    )
    negative_score = SalienceQueueRecord(
        record_id="negative-score",
        expected_downstream_gain=0.0,
        residual_reduction=0.0,
        verification_cost=0.2,
    )
    budget_exhausted = SalienceQueueRecord(
        record_id="budget-exhausted",
        expected_downstream_gain=4.0,
        residual_reduction=1.0,
        verification_cost=2.0,
    )
    reserve_violation = SalienceQueueRecord(
        record_id="reserve-violation",
        expected_downstream_gain=4.0,
        residual_reduction=1.0,
        verification_cost=0.2,
    )
    risk_exceeded = SalienceQueueRecord(
        record_id="risk-exceeded",
        expected_downstream_gain=4.0,
        residual_reduction=1.0,
        verification_cost=0.2,
        hazard_charge=1.0,
    )

    invalid_check = check_salience_record(invalid)
    assert not invalid_check.accepted
    assert "queue record is stale" in invalid_check.reasons
    assert invalid_check.missing_obligations == ["sqot:obligation"]
    assert salience_priority(invalid) <= 0.0
    assert RiskBudgetLedger(risk_charges={"a": 0.2, "b": -5.0}).total_charge() == 0.2

    no_records = build_salience_schedule([], attention_budget=-1.0, risk_budget=-1.0)
    assert not no_records.accepted
    assert no_records.false_liquidity_rate == 0.0
    assert no_records.stale_packet_ratio == 0.0

    report = build_salience_schedule(
        [
            invalid,
            rollback_missing,
            negative_score,
            budget_exhausted,
            reserve_violation,
            risk_exceeded,
        ],
        attention_budget=1.0,
        diagnostic_reserve=DiagnosticReservePolicy(minimum_reserve=2.0),
        risk_budget=0.5,
    )
    decisions = {decision.record_id: decision for decision in report.decisions}
    assert decisions["invalid"].decision == SalienceDecision.QUARANTINE
    assert decisions["rollback-missing"].decision == SalienceDecision.QUARANTINE
    assert decisions["negative-score"].decision == SalienceDecision.DEFER
    assert decisions["budget-exhausted"].decision == SalienceDecision.ABSTAIN
    assert decisions["reserve-violation"].decision == SalienceDecision.DEFER
    assert decisions["risk-exceeded"].decision == SalienceDecision.DEFER
    assert report.quarantine_ledger.quarantined_items == ["invalid", "rollback-missing"]
    assert report.residual_debt_growth > 0.0

    risk_report = build_salience_schedule(
        [
            SalienceQueueRecord(
                record_id="risk-only",
                expected_downstream_gain=4.0,
                residual_reduction=1.0,
                verification_cost=0.2,
                hazard_charge=1.0,
            )
        ],
        attention_budget=1.0,
        diagnostic_reserve=DiagnosticReservePolicy(minimum_reserve=0.0),
        risk_budget=0.1,
    )
    assert risk_report.decisions[0].decision == SalienceDecision.DEFER
    assert risk_report.decisions[0].reasons == ["risk budget would be exceeded"]


def test_sqot_scheduler_reports_v042_attention_diagnostics() -> None:
    diagnostic = SalienceQueueRecord(
        record_id="diag",
        item_type="diagnostic",
        salience_class="diagnostic",
        expected_downstream_gain=0.8,
        residual_reduction=0.4,
        verification_cost=0.4,
        effective_reserve_eligible=True,
        aggregation_group="shared-signal",
        rollback_class="none",
    )
    verifier = SalienceQueueRecord(
        record_id="verifier",
        item_type="verifier",
        salience_class="verifier",
        expected_downstream_gain=0.8,
        residual_reduction=0.4,
        verification_cost=0.2,
        latency_cost=0.1,
        deadline_loss=0.2,
        audit_recursion_depth=3,
        rollback_class="soft",
        aggregation_group="shared-signal",
        label_laundering_suspected=True,
    )
    report = build_salience_schedule(
        [diagnostic, verifier],
        attention_budget=1.0,
        diagnostic_reserve=DiagnosticReservePolicy(minimum_reserve=0.2, audit_depth=1),
        risk_budget=1.0,
    )
    decisions = {decision.record_id: decision for decision in report.decisions}
    assert decisions["diag"].decision == SalienceDecision.RUN
    assert decisions["verifier"].decision == SalienceDecision.DEFER
    assert "audit recursion budget would be exceeded" in decisions["verifier"].reasons
    assert report.effective_diagnostic_reserve == 0.4
    assert report.audit_recursion_violations == ["verifier"]
    assert abs(report.latency_deadline_loss - 0.3) < 1e-9
    assert report.rollback_class_summary["soft"] == 1
    assert report.aggregation_group_counts["shared-signal"] == 2
    assert "aggregation-group:shared-signal" in report.label_laundering_suspicions
    assert "verifier" in report.label_laundering_suspicions


def test_packet_ecology_builds_edges_psi_and_bottleneck_plan() -> None:
    ingestion = ingest_agent_output(
        "ECPT packet verifier output for SQOT salience queue.\n"
        "Depends: packet:seed\n"
        "The verifier route preserves residual obligations."
    )
    assert ingestion.accepted
    seed = ingestion.packets[0].model_copy(
        update={"packet_id": "packet:seed", "dependencies": [], "tags": ["ecpt", "sqot"]}
    )
    target = ingestion.packets[0].model_copy(
        update={"packet_id": "packet:target", "dependencies": ["packet:seed"]}
    )
    edges = build_edge_witnesses([seed, target])
    assert any(edge.accepted for edge in edges)
    registry = build_packet_registry([seed, target], edges, registry_id="test-registry")
    dashboard = build_psi_dashboard(registry, threshold={"G": 0.9, "VT": 0.9, "BR": 0.1})
    assert "VT" in dashboard.components
    assert dashboard.limiting_components
    plan = build_bottleneck_plan(registry, dashboard, profile="production")
    assert plan.interventions
    assert not plan.settled


def test_packet_ecology_residuals_errors_and_empty_dashboard(tmp_path: Path) -> None:
    local = tmp_path / "packet.txt"
    local.write_text(
        "Proxy target bridge telemetry physical trace packet.\nDepends: missing",
        encoding="utf-8",
    )
    ingestion = ingest_local_file(local)
    assert ingestion.accepted
    packet = ingestion.packets[0].model_copy(update={"residual_charge": 0.4})
    support = CapabilityPacketCandidate(
        packet_id="packet:support",
        source_ref="support",
        content_sha256="0" * 64,
        claim="support packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:0"],
        expected_downstream_gain=0.1,
        verification_cost=0.3,
        expires_at="expired",
        tags=["packet"],
    )
    target = CapabilityPacketCandidate(
        packet_id="packet:target",
        source_ref="target",
        content_sha256="1" * 64,
        claim="target packet",
        receiver_family=["agent"],
        evidence_refs=["sha256:1"],
        dependencies=["packet:support", "packet:missing"],
        expected_downstream_gain=2.0,
        verification_cost=0.2,
        tags=["packet"],
        verifier_routes=["ecpt.adapters.bridge.verify_cross_theory_bridge"],
    )
    ignored = CapabilityPacketCandidate(
        packet_id="packet:ignored",
        source_ref="ignored",
        content_sha256="2" * 64,
        claim="ignored",
        evidence_refs=["sha256:2"],
        tags=["unrelated"],
    )
    edges = build_edge_witnesses([packet, support, target, ignored], minimum_confidence=0.2)
    assert any(edge.edge_type == "missing-dependency" for edge in edges)
    assert any(edge.edge_type == "packet-to-receiver-compatibility" for edge in edges)
    registry = build_packet_registry([packet, support, target, ignored], edges)
    assert registry.residual_ledger.burden_sum() > 0.0
    throughput = verification_throughput(registry)
    assert throughput.stale_packet_ratio > 0.0
    assert throughput.false_liquidity_rate > 0.0
    assert throughput.evidence_hash_mismatch_rate > 0.0
    assert registry_to_json(registry)["packets"]
    high_confidence_edges = build_edge_witnesses([support, target], minimum_confidence=0.5)
    assert not any(
        edge.edge_type == "packet-to-receiver-compatibility" for edge in high_confidence_edges
    )

    empty_registry = build_packet_registry([], [])
    empty_dashboard = build_psi_dashboard(empty_registry, threshold={"G": 0.0})
    assert empty_dashboard.components["G"] == 0.0
    assert build_bottleneck_plan(empty_registry, empty_dashboard).interventions

    parsed = registry_from_json({"registry_id": "x", "packets": [], "edges": []})
    assert parsed.registry_id == "x"
    for bad in [{"packets": "bad", "edges": []}, {"packets": [], "edges": "bad"}]:
        try:
            registry_from_json(bad)
        except ValueError as exc:
            assert "must be a list" in str(exc)
        else:  # pragma: no cover - defensive assertion branch
            raise AssertionError("registry_from_json accepted malformed registry")

    generic = packet_from_text(
        "plain capability text",
        packet_id="packet:generic",
        source_kind=PacketSourceKind.AGENT_OUTPUT,
        source_ref="generic",
    )
    assert generic.tags == ["general"]
    assert generic.verifier_routes == []
    assert _bounded_ratio(3.0, 0.0) == 1.0
    assert _reachable_packets(
        {"packet:support"},
        [
            EdgeWitness(
                edge_id="edge:rejected",
                source_packet_ids=["packet:support"],
                target_packet_id="packet:target",
                accepted=False,
            )
        ],
    ) == {"packet:support"}


def test_closed_loop_iteration_is_deterministic() -> None:
    first = closed_loop_iteration(
        state_id="loop",
        agent_output="SQOT diagnostic reserve packet for ECPT ASI-proxy phase-control.",
    )
    second = closed_loop_iteration(
        state_id="loop",
        agent_output="SQOT diagnostic reserve packet for ECPT ASI-proxy phase-control.",
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.next_agent_tasks


def test_v024_schemas_are_public() -> None:
    for name in [
        "SalienceQueueRecord",
        "SalienceScheduleReport",
        "CapabilityPacketCandidate",
        "CapabilityPacketRegistry",
        "EdgeWitness",
        "PsiDashboard",
        "BottleneckInversionPlan",
        "ClosedLoopAgentIteration",
    ]:
        assert schema_by_type(name)["title"] == name
    assert build_sbom_document("pic")["bomFormat"] == "PIC-SBOM"


def test_v024_cli_smoke(tmp_path: Path) -> None:
    schedule = runner.invoke(
        app,
        [
            "sqot",
            "schedule",
            "--packets",
            "examples/sqot_queue.json",
            "--profile",
            "production",
        ],
    )
    assert schedule.exit_code == 0, schedule.output
    schedule_data = json.loads(schedule.output)
    assert schedule_data["decisions"]

    ingest = runner.invoke(
        app,
        [
            "ecology",
            "ingest",
            "--source",
            "SQOT packet ecology agent output for ECPT verifier routing.",
            "--kind",
            "agent-output",
        ],
    )
    assert ingest.exit_code == 0, ingest.output
    ingest_data = json.loads(ingest.output)
    assert ingest_data["packets"]

    registry_path = tmp_path / "nested" / "registry.json"
    build_edges = runner.invoke(
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
    assert build_edges.exit_code == 0, build_edges.output

    psi_path = tmp_path / "psi.json"
    psi = runner.invoke(
        app,
        [
            "ecology",
            "psi",
            "--registry",
            str(registry_path),
            "--threshold",
            "examples/ecology_threshold.json",
            "--output",
            str(psi_path),
        ],
    )
    assert psi.exit_code == 0, psi.output

    plan = runner.invoke(
        app,
        [
            "ecology",
            "plan",
            "--registry",
            str(registry_path),
            "--psi",
            str(psi_path),
            "--profile",
            "production",
        ],
    )
    assert plan.exit_code == 0, plan.output
    plan_data = json.loads(plan.output)
    assert "interventions" in plan_data

    loop = runner.invoke(
        app,
        [
            "ecology",
            "loop",
            "--state",
            "examples/ecology_loop_state.json",
            "--agent-output",
            "SQOT reserve packet for ECPT active phase-control.",
        ],
    )
    assert loop.exit_code == 0, loop.output
    loop_data = json.loads(loop.output)
    assert loop_data["next_agent_tasks"]


def test_live_connectors_are_fixture_driven_and_fail_closed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeResponse:
        def __init__(
            self,
            *,
            status_code: int = 200,
            payload: dict[str, object] | None = None,
            text: str = "",
        ) -> None:
            self.status_code = status_code
            self._payload = payload or {}
            self.text = text

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeHttpx:
        class HTTPError(Exception):
            pass

        headers_seen: ClassVar[list[dict[str, str] | None]] = []

        @staticmethod
        def get(
            url: str,
            headers: dict[str, str] | None = None,
            timeout: float = 20.0,
        ) -> FakeResponse:
            FakeHttpx.headers_seen.append(headers)
            _ = timeout
            if "api.github.com" in url:
                return FakeResponse(
                    payload={
                        "description": "ECPT SQOT packet ecology repository",
                        "full_name": "kadubon/percolation-inversion-compiler",
                        "language": "Python",
                        "stargazers_count": 1,
                    }
                )
            if "zenodo.org" in url:
                return FakeResponse(
                    payload={
                        "metadata": {
                            "description": "SQOT salience queue manuscript",
                            "title": "Salience-Queue Occupation Theory",
                        }
                    }
                )
            if "arxiv.org" in url:
                return FakeResponse(
                    text=(
                        "<feed><entry><id>https://arxiv.org/abs/0000.0000</id>"
                        "<title>Packet ecology</title>"
                        "<summary>ECPT SQOT verifier routing</summary></entry></feed>"
                    )
                )
            return FakeResponse(status_code=404)

    monkeypatch.setattr(
        "percolation_inversion_compiler.ecology.connectors.importlib.import_module",
        lambda _: FakeHttpx,
    )
    github = ingest_live_source(
        "kadubon/percolation-inversion-compiler",
        kind=PacketSourceKind.GITHUB,
    )
    github_with_token = ingest_live_source(
        "https://github.com/owner/repo",
        kind=PacketSourceKind.GITHUB,
        token="test-token",
    )
    zenodo = ingest_live_source(
        "https://zenodo.org/records/20526451",
        kind=PacketSourceKind.ZENODO,
    )
    arxiv = ingest_live_source("arxiv:packet ecology", kind=PacketSourceKind.ARXIV)
    assert github.accepted and github.packets[0].source_kind == PacketSourceKind.GITHUB
    assert github_with_token.accepted
    assert github_with_token.packets[0].source_ref == "owner/repo"
    assert any(
        headers is not None and headers.get("Authorization") == "Bearer test-token"
        for headers in FakeHttpx.headers_seen
    )
    assert zenodo.accepted and zenodo.packets[0].source_kind == PacketSourceKind.ZENODO
    assert arxiv.accepted and arxiv.packets[0].source_kind == PacketSourceKind.ARXIV
    assert infer_live_kind("kadubon/percolation-inversion-compiler") == PacketSourceKind.GITHUB
    assert infer_live_kind("https://zenodo.org/records/20526451") == PacketSourceKind.ZENODO
    assert infer_live_kind("arxiv:packet ecology") == PacketSourceKind.ARXIV

    failed = ingest_live_source("unsupported", kind=PacketSourceKind.AUTO)
    assert not failed.accepted
    assert failed.residual_ledger.burden_sum() > 0
    assert infer_live_kind("local-file.txt") == PacketSourceKind.LOCAL


def test_live_connector_missing_dependency_and_local_decode_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    def missing_import(_: str) -> object:
        raise ModuleNotFoundError("httpx")

    monkeypatch.setattr(
        "percolation_inversion_compiler.ecology.connectors.importlib.import_module",
        missing_import,
    )
    missing = ingest_live_source("kadubon/repo", kind=PacketSourceKind.GITHUB)
    assert not missing.accepted
    assert "httpx" in " ".join(missing.reasons)

    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff\xfe\x00")
    decoded = ingest_local_file(binary)
    assert not decoded.accepted
    assert decoded.rejected_sources == ["binary.bin"]


def test_live_connectors_status_empty_and_http_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FakeResponse:
        def __init__(self, *, status_code: int = 200, text: str = "") -> None:
            self.status_code = status_code
            self.text = text

        def json(self) -> dict[str, object]:
            return {}

    class FailingHttpx:
        class HTTPError(Exception):
            pass

        calls = 0

        @classmethod
        def get(cls, url: str, **_: object) -> FakeResponse:
            cls.calls += 1
            if cls.calls == 1:
                raise cls.HTTPError("network down")
            if "github" in url:
                return FakeResponse(status_code=403)
            if "zenodo" in url:
                return FakeResponse(status_code=404)
            if "arxiv" in url:
                if "status" in url:
                    return FakeResponse(status_code=429)
                return FakeResponse(text="<feed></feed>")
            return FakeResponse(status_code=500)

    monkeypatch.setattr(
        "percolation_inversion_compiler.ecology.connectors.importlib.import_module",
        lambda _: FailingHttpx,
    )
    http_failed = ingest_live_source("owner/repo", kind=PacketSourceKind.GITHUB)
    github_status = ingest_live_source("owner/repo", kind=PacketSourceKind.GITHUB)
    zenodo_status = ingest_live_source("https://zenodo.org/records/0", kind=PacketSourceKind.ZENODO)
    arxiv_status = ingest_live_source("arxiv:status", kind=PacketSourceKind.ARXIV)
    arxiv_empty = ingest_live_source("arxiv:none", kind=PacketSourceKind.ARXIV)
    assert "connector request failed" in http_failed.reasons[0]
    assert github_status.reasons == ["github status 403"]
    assert zenodo_status.reasons == ["zenodo status 404"]
    assert arxiv_status.reasons == ["arxiv status 429"]
    assert arxiv_empty.reasons == ["arxiv returned no entries"]
