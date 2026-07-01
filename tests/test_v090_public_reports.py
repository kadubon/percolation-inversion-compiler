from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.interop import (
    cache_invalidation_report,
    duplicate_inflation_report,
    ecpt_quotient_report,
    evidence_product_report,
    fcu_check_report,
    leakage_audit_report,
    mission_validity_report,
    performance_report,
    resource_tensor_report,
    token_admissibility_report,
    token_dedup_report,
    token_extraction_pipeline_report,
    transport_certificate_report,
    trc_observation_consistency_report,
    trc_resource_flow_report,
    unseen_frontier_report,
)

runner = CliRunner()


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[object]) -> Path:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def test_token_reports_preserve_candidate_and_capital_boundary() -> None:
    extracted = token_extraction_pipeline_report(
        {"trace_id": "trace:v090", "steps": [{"tool": "read"}]}
    )
    admissibility = token_admissibility_report({"token_id": "token:v090"})
    leakage = leakage_audit_report(
        {
            "answer_key": "heldout benchmark solution",
            "token_id": "token:leaky",
        }
    )

    assert extracted["settled"] is False
    assert extracted["candidate_token"]["candidate_only"] is True
    assert "token_extraction_is_not_settlement" in extracted["non_claims"]
    assert admissibility["capital_admitted"] is False
    assert "mechanism_mediated_reuse_required" in admissibility["blockers"]
    assert "leakage_exclusion_required" in admissibility["blockers"]
    assert "benchmark_answer_leakage" in leakage["blockers"]


def test_mission_transport_cost_and_evidence_fail_closed() -> None:
    mission = mission_validity_report(
        {
            "packet_id": "packet:v090",
            "generated_law_gain": True,
            "mission_law": {},
            "target_scope": "target",
        }
    )
    transport = transport_certificate_report(
        {"scope": "source"},
        {"scope": "target"},
        {"certificate_id": "transport:v090", "support_miss": True},
    )
    fcu = fcu_check_report({"cost_id": "cost:v090"})
    evidence = evidence_product_report([{"evidence_id": "e:v090", "e_value": 2}])

    assert mission["accepted"] is False
    assert "generated_law_bridge_required" in mission["blockers"]
    assert transport["accepted"] is False
    assert "support_miss" in transport["blockers"]
    assert fcu["accepted"] is False
    assert "missing_upper_bounds" in fcu["blockers"]
    assert evidence["accepted"] is False
    assert "conditional_witness_required" in evidence["blockers"]


def test_duplicate_quotient_sqot_trc_bit_and_cache_reports_are_residual_preserving() -> None:
    packets = [
        {"packet_id": "packet:1", "claim": "same claim"},
        {"packet_id": "packet:2", "claim": "same claim"},
    ]
    dedup = token_dedup_report(packets)
    quotient = ecpt_quotient_report(packets)
    duplicate = duplicate_inflation_report(packets)
    sqot = resource_tensor_report({"state_id": "sqot:v090", "unknown_budget_is_zero": True})
    observation = trc_observation_consistency_report(
        {
            "window_id": "window:v090",
            "observer": "verifier",
            "postcondition_observed": False,
            "resource_use_observed": False,
        }
    )
    resource_flow = trc_resource_flow_report(
        {"trace_id": "trace:v090", "resource_flows": [{"rollback_compensation_free": True}]}
    )
    frontier = unseen_frontier_report(
        [{"unseen_mass": 2, "duplicate_mass": 1, "false_entry_bound": 0.5}]
    )
    cache = cache_invalidation_report({"coordinates": ["coord:a"]})

    assert dedup["duplicate_mass_report"]["duplicate_mass_count"] == 1
    assert "held_out_or_uniform_ledger_required" in quotient["blockers"]
    assert duplicate["inflated_support_allowed"] is False
    assert sqot["accepted"] is False
    assert "unknown_budget_cannot_be_zero" in sqot["blockers"]
    assert "postcondition_not_observed" in observation["blockers"]
    assert "rollback_compensation_not_free" in resource_flow["blockers"]
    assert frontier["unseen_frontier_mass"] == 2
    assert cache["dirty_set"] == ["coord:a"]


def test_v090_cli_public_reports_and_compact_outputs(tmp_path: Path) -> None:
    trace = _write_json(
        tmp_path / "trace.json",
        {
            "trace_id": "trace:v090",
            "steps": [{"step": "inspect"}],
            "provenance": {"source": "fixture"},
            "task_context": "local",
        },
    )
    token = _write_json(tmp_path / "token.json", {"token_id": "token:v090"})
    tokens = _write_jsonl(
        tmp_path / "tokens.jsonl",
        [
            {"token_id": "token:1", "claim": "same claim"},
            {"token_id": "token:2", "claim": "same claim"},
        ],
    )

    extracted = runner.invoke(
        app,
        ["token", "extract-pipeline", "--trace", str(trace), "--compact"],
    )
    admissibility = runner.invoke(
        app,
        ["token", "admissibility", "--token", str(token), "--compact"],
    )
    dedup = runner.invoke(app, ["token", "dedup", "--tokens", str(tokens)])
    perf = runner.invoke(app, ["performance", "report", "--json"])

    assert extracted.exit_code == 0, extracted.output
    assert admissibility.exit_code == 0, admissibility.output
    assert dedup.exit_code == 0, dedup.output
    assert perf.exit_code == 0, perf.output
    assert json.loads(extracted.output)["schema_version"] == "pic.compact_report.v1"
    assert json.loads(admissibility.output)["source_schema_version"] == (
        "pic.token_admissibility_report.v1"
    )
    assert json.loads(dedup.output)["duplicate_mass_report"]["duplicate_mass_count"] == 1
    assert json.loads(perf.output)["schema_version"] == "pic.performance_report.v1"


def test_v090_generated_assets_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "schemas/token-extraction-pipeline-report.schema.json",
        "schemas/observation-window-report.schema.json",
        "schemas/performance-report.schema.json",
        "examples/asi_proxy_loop_bundle/target.json",
        "examples/asi_proxy_loop_bundle/performance_report.example.json",
        "docs/asi-proxy-loop.md",
        "docs/cross-repo-loop-conformance.md",
    ]:
        assert (root / relative).is_file()


def test_performance_report_keeps_local_only_non_claims() -> None:
    report = performance_report(
        fixture={
            "cache_entries": 2,
            "jsonl_lines_processed": 3,
            "graph_nodes": 4,
        }
    )

    assert report["schema_version"] == "pic.performance_report.v1"
    assert report["cache_entries"] == 2
    assert report["jsonl_lines_processed"] == 3
    assert report["settled"] is False
    assert "performance_report_is_local_diagnostic" in report["non_claims"]
