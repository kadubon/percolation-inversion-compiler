from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import percolation_inversion_compiler.phase_lab as phase_lab
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io.schema import schema_by_type

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()

V050_PROMPT_REQUIRED_SCHEMA_NAMES = [
    "EffectivePacketGraph",
    "EffectivePacketNode",
    "EffectivePacketEdge",
    "EffectivePacketGraphBuildReport",
    "EffectivePacketEligibility",
    "PacketContributionStatus",
    "SemanticEdgeEvidence",
    "EffectiveGraphResidualSummary",
    "PhaseWindow",
    "PhaseWindowObservation",
    "PhaseWindowComparison",
    "PhaseThresholdStatus",
    "PhaseComponentObservation",
    "VerificationThroughputWindow",
    "FalseLiquidityLoad",
    "WasteLoad",
    "SalienceObstructionLoad",
    "BasinReachabilityProxy",
    "AutocatalyticClosureWitness",
    "ProductiveClosureWitness",
    "ExecutableClosureWitness",
    "ClosureSupportHyperpath",
    "ClosureDefect",
    "ClosureCertificateCandidate",
    "ClosureAbstentionReason",
    "ExecutionAvailableHyperpath",
    "ExecutionPathWitness",
    "ExecutionPathDefect",
    "ExecutablePathDensityReport",
    "ReceiverContextSupport",
    "ActionBoundaryRequirement",
    "ExecutionAuthorityStatus",
    "CapabilityExpressionPath",
    "BottleneckClassDiagnosis",
    "MinimalEnablingCondition",
    "BottleneckInversionCandidate",
    "InversionCertificate",
    "ActivationGainEstimate",
    "PostInversionAuditPlan",
    "RollbackOrDeactivationPlan",
    "BottleneckInversionReport",
    "QueueOccupationReport",
    "SalienceObstructionDiagnosis",
    "DiagnosticReserveReport",
    "QueueRebalancePlan",
    "PacketQuarantineDecision",
    "ReversibleSalienceSovereigntyCertificate",
    "AttentionBudgetLedger",
    "VerificationQueuePressure",
    "AltEcptLiftReport",
    "ReceiverLiquidityLift",
    "CrossContextTransferWitness",
    "DownstreamSearchCostDelta",
    "CapitalToPathContribution",
    "LiquidityToClosureContribution",
    "AltLiftBlocker",
    "TypedAgentTrace",
    "TypedToolCallTrace",
    "TypedActionBoundary",
    "TraceNormalForm",
    "TraceToleranceLedger",
    "TraceFrontierDebt",
    "TraceAdapterReport",
    "PhaseLabStoreManifest",
    "PhaseLabEvent",
    "PhaseLabWindowIndex",
    "PhaseLabIngestReport",
    "PhaseLabExportManifest",
    "ASIProxyThresholdSpec",
    "ASIProxyThresholdStatus",
    "CollectivePhaseCertificateCandidate",
    "CollectivePhaseAbstentionReport",
    "PhaseCertificateDefect",
]


def test_v050_schema_commands_export() -> None:
    for schema_name in V050_PROMPT_REQUIRED_SCHEMA_NAMES:
        assert schema_by_type(schema_name)["title"] == schema_name
        result = runner.invoke(app, ["schema", "--type", schema_name])
        assert result.exit_code == 0
        assert json.loads(result.output)["title"] == schema_name


def test_v050_phase_lab_package_exports_prompt_records() -> None:
    phase_lab_schema_names = [
        name
        for name in V050_PROMPT_REQUIRED_SCHEMA_NAMES
        if name in getattr(phase_lab, "__all__", [])
    ]
    assert "PacketContributionStatus" in phase_lab_schema_names
    assert "SemanticEdgeEvidence" in phase_lab_schema_names
    assert "PhaseWindow" in phase_lab_schema_names
    assert "ProductiveClosureWitness" in phase_lab_schema_names
    assert "ExecutionPathWitness" in phase_lab_schema_names
    assert "PhaseCertificateDefect" in phase_lab_schema_names
    for schema_name in phase_lab_schema_names:
        assert getattr(phase_lab, schema_name).__name__ == schema_name


def test_v050_schema_all_exports_prompt_required_records(tmp_path) -> None:  # type: ignore[no-untyped-def]
    output_dir = tmp_path / "schemas"
    result = runner.invoke(app, ["schema", "--all", "--output-dir", str(output_dir)])
    assert result.exit_code == 0
    for schema_name in V050_PROMPT_REQUIRED_SCHEMA_NAMES:
        assert (output_dir / f"{schema_name}.schema.json").is_file()


def test_v050_commands_remain_diagnostic_and_unsettled() -> None:
    result = runner.invoke(
        app,
        [
            "trc",
            "trace-adapter",
            "--input",
            "examples/trc_adapter/tool_trace_input.example.json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["settled"] is False
    assert data["executed_action_count"] == 0


def _invoke_json(args: list[str]) -> dict[str, object]:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _invoke_ok(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def test_v050_cli_smoke_matrix_uses_explicit_paths(tmp_path: Path) -> None:
    store = tmp_path / "phase-lab"
    graph = tmp_path / "effective_graph.json"
    ecology_graph = tmp_path / "ecology_graph.json"
    bottlenecks = tmp_path / "bottlenecks.json"
    inversions = tmp_path / "inversions.json"
    observation = tmp_path / "observation.json"

    _invoke_json(["phase", "lab", "init", "--output-dir", str(store)])
    _invoke_json(
        [
            "phase",
            "lab",
            "ingest",
            "--store",
            str(store),
            "--report",
            "examples/phase_lab/runtime_report_1.json",
        ]
    )
    _invoke_json(
        [
            "phase",
            "lab",
            "ingest",
            "--store",
            str(store),
            "--report",
            "examples/phase_lab/runtime_report_2.json",
        ]
    )
    _invoke_json(["phase", "lab", "list-windows", "--store", str(store)])
    _invoke_ok(
        [
            "phase",
            "lab",
            "observe",
            "--store",
            str(store),
            "--window",
            "latest",
            "--output",
            str(observation),
        ]
    )
    _invoke_ok(["phase", "lab", "graph", "--store", str(store), "--output", str(graph)])
    for command in ["closure", "executable-paths", "threshold-status", "certify"]:
        args = ["phase", "lab", command, "--store", str(store)]
        if command in {"threshold-status", "certify"}:
            args.extend(["--threshold", "examples/thresholds/asi_proxy_development.json"])
        data = _invoke_json(args)
        assert data["settled"] is False
    _invoke_json(
        [
            "phase",
            "lab",
            "compare-window",
            "--store",
            str(store),
            "--baseline",
            "previous",
            "--candidate",
            "latest",
        ]
    )
    _invoke_json(
        [
            "phase",
            "lab",
            "export",
            "--store",
            str(store),
            "--output-dir",
            str(tmp_path / "export"),
        ]
    )

    _invoke_ok(
        [
            "ecology",
            "effective-graph",
            "--reports",
            "examples/phase_lab/runtime_report_1.json",
            "--reports",
            "examples/phase_lab/runtime_report_2.json",
            "--output",
            str(ecology_graph),
        ]
    )
    _invoke_json(["ecology", "execution-available-paths", "--graph", str(ecology_graph)])

    _invoke_ok(["bit", "diagnose", "--graph", str(ecology_graph), "--output", str(bottlenecks)])
    _invoke_ok(["bit", "invert", "--bottlenecks", str(bottlenecks), "--output", str(inversions)])
    _invoke_json(
        [
            "bit",
            "mec",
            "--bottlenecks",
            "examples/bit_engine/bottlenecks.example.json",
            "--bottleneck",
            "bit-bottleneck:edge:beta:missing-semantic-edge",
        ]
    )
    _invoke_json(
        [
            "bit",
            "certificate",
            "--candidate",
            "examples/bit_engine/inversion_candidates.example.json",
        ]
    )
    _invoke_json(
        [
            "bit",
            "compare-baseline",
            "--baseline",
            "examples/phase_lab/phase_window_observation.example.json",
            "--candidate",
            str(observation),
        ]
    )

    for command in [
        "diagnose-queue",
        "salience-obstruction",
        "rebalance",
        "quarantine",
        "reserve-check",
    ]:
        data = _invoke_json(["sqot", command, "--graph", str(ecology_graph)])
        assert data["settled"] is False

    _invoke_json(
        [
            "alt",
            "ecpt-lift",
            "--packets",
            "examples/packet_exchange/packet_envelope.example.json",
            "--graph",
            str(ecology_graph),
        ]
    )
    _invoke_json(
        [
            "alt",
            "receiver-lift",
            "--packet",
            "examples/packet_exchange/packet_envelope.example.json",
            "--receiver-context",
            "examples/packet_exchange/packet_envelope.example.json",
        ]
    )
    _invoke_json(
        [
            "alt",
            "liquidity-to-paths",
            "--packet",
            "examples/packet_exchange/packet_envelope.example.json",
            "--graph",
            str(ecology_graph),
        ]
    )
    _invoke_json(
        [
            "alt",
            "capital-impact",
            "--reports",
            "examples/alt_lift/alt_ecpt_lift.example.json",
        ]
    )

    _invoke_json(
        ["trc", "trace-adapter", "--input", "examples/trc_adapter/tool_trace_input.example.json"]
    )
    _invoke_json(
        ["trc", "tool-trace", "--events", "examples/trc_adapter/tool_trace_input.example.json"]
    )
    _invoke_json(
        [
            "trc",
            "action-boundary",
            "--report",
            "examples/portability_conformance/runtime_step_report.json",
        ]
    )


def test_v050_demo_recommendations_are_wildcard_free(tmp_path: Path) -> None:
    for args in [
        ["demo", "installed-smoke", "--profile", "development"],
        ["demo", "bootstrap", "--output-dir", str(tmp_path / "pic-demo")],
    ]:
        data = _invoke_json(args)
        joined = "\n".join(str(item) for item in data["recommended_next_commands"])
        assert "packet*.json" not in joined
        for command in [
            "phase lab observe",
            "phase lab graph",
            "phase lab closure",
            "phase lab executable-paths",
            "phase lab certify",
        ]:
            assert command in joined


def test_v050_docs_and_indexes_reject_stale_shell_glob_examples() -> None:
    checked_paths = [
        ROOT / "README.md",
        ROOT / "docs" / "alt-ecpt-lift.md",
        ROOT / "docs" / "cli-reference.md",
        ROOT / "docs" / "for-agents.md",
        ROOT / "docs" / "pypi-distribution.md",
        ROOT / "docs" / "v050-audit.md",
        ROOT / "agent-manifest.json",
        ROOT / "schemas" / "index.json",
        ROOT / "src" / "percolation_inversion_compiler" / "data" / "demo" / "manifest.json",
    ]
    forbidden = [
        "--baseline earliest",
        "packet*.json",
        "reports/*.json",
        "packets/*.json",
        "dist\\*.whl",
        "dist\\*.tar.gz",
    ]
    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} remains in {path}"
