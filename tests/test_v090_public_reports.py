from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import percolation_inversion_compiler.interop as public_interop
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


def test_v090_public_report_matrix_keeps_unsettled_contract() -> None:
    packet = {
        "packet_id": "packet:v090",
        "claim": "candidate claim",
        "construct_definition": "construct",
        "construct_evidence": {"witness": True},
        "externality_hazard_ledger": {"hazard": 0},
        "hazard_ledger": {"hazard": 0},
        "measurement_protocol": "protocol",
        "mission_bridge": "bridge",
        "mission_law": {"law": "mission"},
        "negative_controls": ["control"],
        "target_scope": "target",
    }
    cost = {
        "cost_id": "cost:v090",
        "cost_coordinates": ["latency"],
        "irreversible_loss_absent": True,
        "scalarization": "max",
        "upper_bounds": {"latency": 10},
    }
    token = {
        "token_id": "token:v090",
        "counterfactual_contrast": "contrast",
        "cost_ledger": {"latency": 1},
        "dependency_graph": ["dep"],
        "deprecation_conditions": ["stale"],
        "failure_contract": "fail closed",
        "interface": {"input": "trace"},
        "leakage_exclusion": True,
        "lineage_closed": True,
        "mechanism": "mechanism",
        "parents": ["trace:v090"],
        "provenance": {"source": "trace"},
        "scope": "target",
        "verifier_binding": "verifier",
    }
    trace = {
        "trace_id": "trace:v090",
        "clock": "logical",
        "events": [{"event_id": "e1"}],
        "provenance": {"source": "fixture"},
        "resource_flows": [
            {
                "flow_id": "flow:v090",
                "trace_index": 1,
                "rollback_compensation_free": False,
            }
        ],
        "steps": [{"step": "observe"}],
    }
    certificates = [
        {
            "certificate_id": "cert:v090",
            "finite_witness": True,
            "gain": 2,
            "cost": 1,
            "unit_ledger": {"unit": "packet"},
        }
    ]
    queue_state = {
        "state_id": "queue:v090",
        "audit_fuel": 3,
        "checker_thresholds": {"max_cost": 10},
        "diagnostic_reserve": 1,
        "mandatory_obligations": ["verify"],
        "mechanism_compatibility_status": "accepted",
        "root_checker_integrity": True,
        "semantic_egress_status": "accepted",
        "verification_cost_status": "in_band",
    }
    resource_state = {
        "state_id": "resource:v090",
        "conversions": [
            {
                "conversion_id": "conv:v090",
                "from": "tokens",
                "to": "checks",
                "loss": 0.1,
                "meta_occupation_charge": 1,
                "rate": 2,
            }
        ],
        "diagnostic_reserve": 2,
        "diagnostic_reserve_lower_bound": 1,
        "diagnostic_reserve_upper_bound": 3,
        "modalities": {"tokens": 2, "checks": 1},
    }

    cases = [
        ("token_lineage_report", (token,), {}),
        ("token_interface_standard_report", (token, {"required_fields": ["token_id"]}), {}),
        ("trace_instrumentation_contract_report", (trace, {"requires_clock": True}), {}),
        (
            "trace_sufficiency_report",
            (
                trace,
                {
                    "estimand_id": "estimand:v090",
                    "identification_assumptions": ["finite"],
                    "negative_controls": ["nc"],
                    "target_quantity": "effect",
                },
            ),
            {},
        ),
        (
            "mechanism_ablation_report",
            (
                token,
                {
                    "control_condition": "control",
                    "confound_charge": 0,
                    "metric": "gain",
                    "proxy_charge": 0,
                    "surface_charge": 0,
                    "transport_charge": 0,
                    "treatment_condition": "treatment",
                    "verifier_binding": "verifier",
                },
            ),
            {},
        ),
        (
            "opportunity_measure_report",
            (
                {
                    "target_id": "target",
                    "mission_law": {},
                    "population": "p",
                    "sampling_frame": "f",
                    "cost_model": {},
                },
            ),
            {},
        ),
        ("fcu_check_report", (cost,), {}),
        ("construct_validity_report", (packet,), {}),
        (
            "lifecycle_cost_report",
            (
                {
                    **packet,
                    "lifecycle_cost_ledger": {
                        "formation": 1,
                        "deployment": 1,
                        "validation": 1,
                        "maintenance": 1,
                        "depreciation": 1,
                    },
                    "telemetry_contract": {},
                },
            ),
            {},
        ),
        (
            "telemetry_check_report",
            (
                {
                    "telemetry_id": "telemetry:v090",
                    "events": [],
                    "clock": "logical",
                    "resource_use": [],
                },
                {},
            ),
            {},
        ),
        (
            "dynamic_risk_report",
            (
                {
                    "ledger_id": "risk:v090",
                    "risk_coordinates": ["r"],
                    "update_rule": "bounded",
                    "hazard_charge_upper_bound": 1,
                },
            ),
            {},
        ),
        (
            "stopped_sheaf_report",
            (
                [
                    {
                        "evidence_id": "e1",
                        "stopped": True,
                        "resource_event": {},
                        "closure_witness": {},
                    }
                ],
            ),
            {},
        ),
        (
            "confidence_sequence_report",
            ([{"evidence_id": "e1", "predictable": True, "alpha": 0.05}],),
            {},
        ),
        (
            "boundary_quotient_report",
            (
                {
                    "quotient_id": "q",
                    "target_id": "t",
                    "boundary_error_ledger": {},
                    "coupling_error_ledger": {},
                    "context": {},
                    "tolerance": 0.1,
                },
                {"target_id": "t"},
            ),
            {},
        ),
        (
            "atlas_check_report",
            ({"atlas_id": "atlas", "strata": [], "transition_maps": [], "boundary_ledger": {}},),
            {},
        ),
        (
            "activation_cache_report",
            (
                {
                    "state_id": "cache",
                    "activation_mode": "direct",
                    "dependency_hash": "h",
                    "invalidation_keys": ["k"],
                },
            ),
            {},
        ),
        (
            "queue_morphism_report",
            (
                {"diagnostic_reserve": 1, "rollback_priority": 2, "blocking_residuals": 0},
                {"diagnostic_reserve": 1, "rollback_priority": 2, "blocking_residuals": 0},
            ),
            {},
        ),
        ("exchange_tensor_report", (resource_state,), {}),
        ("diagnostic_reserve_report", (resource_state,), {}),
        (
            "protocol_mutation_report",
            ({"state_id": "protocol", "protocol_mutated": True, "quarantined": True},),
            {},
        ),
        (
            "checker_cost_report",
            (
                {
                    "state_id": "checker",
                    "checker_cost": 1,
                    "cost_budget": 2,
                    "verification_queue": [],
                },
            ),
            {},
        ),
        (
            "trc_observation_window_report",
            (
                {
                    "window_id": "window",
                    "observer": "observer",
                    "start": 0,
                    "end": 1,
                    "relative_scope": "scope",
                    "verifier": "verifier",
                },
            ),
            {},
        ),
        (
            "lifecycle_scheduler_report",
            ({"certificates": [{"certificate_id": "c1", "lifecycle_status": "stale"}]},),
            {},
        ),
        (
            "tolerance_scheduler_report",
            ({"certificates": [{"certificate_id": "c1", "tolerance_status": "stale"}]},),
            {},
        ),
        (
            "efficiency_archive_report",
            ({"frontier_id": "frontier", "frontier": [{"gain": 2, "cost": 1}]},),
            {},
        ),
        (
            "mechanism_cube_report",
            (
                {
                    "cube_id": "cube",
                    "direct_supply_charge": 0,
                    "observation_drift_charge": 0,
                    "logging_drift_charge": 0,
                    "factorization_error_charge": 0,
                    "rank_failure_charge": 0,
                    "proxy_bridge_charge": 0,
                },
            ),
            {},
        ),
        (
            "release_interval_report",
            (
                {
                    "program_id": "program",
                    "unit_ledger": {},
                    "primal_witness": {},
                    "dual_witness": {},
                    "solver_gap": 0,
                },
            ),
            {},
        ),
        (
            "martingale_partition_report",
            ({"audit_id": "audit", "partition": [], "filtration": [], "deficiency_bound": 0},),
            {},
        ),
        (
            "anchor_transfer_report",
            (
                {
                    "certificate_id": "anchor",
                    "source_anchor": "s",
                    "target_anchor": "t",
                    "cross_validation": {},
                    "transfer_error_bound": 0,
                },
            ),
            {},
        ),
        ("performance_bench_report", ({"cache_entries": 1},), {}),
        ("cache_status_report", (), {}),
        ("cache_rebuild_report", (), {}),
        ("sqot_protocol_integrity_report", (queue_state,), {}),
        ("sqot_resource_exchange_report", (resource_state,), {}),
        (
            "probe_stop_report",
            (
                {
                    "probe_id": "probe",
                    "diagnostic_reserve": 2,
                    "probe_cost": 1,
                    "meta_occupation_band": 2,
                    "meta_occupation_charge": 1,
                },
            ),
            {},
        ),
        ("bit_mec_frontier_report", (certificates,), {}),
        ("bit_certificate_compiler_report", (certificates,), {}),
        ("bit_unit_compatibility_report", (certificates,), {}),
        (
            "cegar_simulation_barrier_report",
            (
                {
                    "barrier_id": "barrier",
                    "finite_transition_table": [],
                    "refinement_record": {},
                    "bad_state_bound_certified": True,
                },
            ),
            {},
        ),
        (
            "dynamic_regime_acceleration_report",
            (
                {
                    "surface_id": "surface",
                    "dynamic_baseline_resource_matched": True,
                    "positivity_floor": 0.1,
                    "censoring_charge": 0,
                    "competing_stop_charge": 0,
                    "truncation_charge": 0,
                    "arrival_gain_lower_bound": 0.2,
                },
            ),
            {},
        ),
    ]

    for name, args, kwargs in cases:
        report = getattr(public_interop, name)(*args, **kwargs)
        assert report["ok"] is True, name
        assert report["settled"] is False, name
        assert report["schema_version"].startswith("pic."), name
        assert any("not" in item or "is_" in item for item in report["non_claims"]), name


def test_v090_public_report_residual_branches_are_fail_closed() -> None:
    branch_reports = [
        public_interop.token_lineage_report({"token_id": "token:orphan"}),
        public_interop.token_dedup_report(
            [
                {"token_id": "token:a", "claim": "same mechanism with bounded proxy charge"},
                {"token_id": "token:b", "claim": "same mechanism with bounded proxy charges"},
            ]
        ),
        public_interop.trace_instrumentation_contract_report(
            {"trace_id": "trace:no-clock", "events": [{}]},
            {"required_fields": ["trace_id", "events"], "requires_clock": True},
        ),
        public_interop.trace_sufficiency_report(
            {"trace_id": "trace:thin"},
            {"estimand_id": "estimand", "target_quantity": "effect"},
        ),
        public_interop.mechanism_ablation_report(
            {"token_id": "token:thin"},
            {"control_condition": "c", "treatment_condition": "t", "metric": "gain"},
        ),
        public_interop.mission_validity_report(
            {
                "packet_id": "packet:hazard",
                "construct_evidence": {},
                "externality_hazards": ["spillover"],
                "hazard_ledger": {},
                "mission_law": {},
                "target_scope": "target",
            }
        ),
        public_interop.construct_validity_report(
            {
                "packet_id": "packet:construct",
                "aggregate_benchmark_success": True,
                "construct_definition": "construct",
                "measurement_protocol": "protocol",
                "negative_controls": [],
            }
        ),
        public_interop.telemetry_check_report(
            {"telemetry_id": "telemetry:failed", "status": "failed", "events": [], "clock": "t"},
            {"required_fields": ["events", "clock"]},
        ),
        public_interop.stopped_sheaf_report([{"evidence_id": "e:open"}]),
        public_interop.confidence_sequence_report([{"evidence_id": "e:unpredictable"}]),
        public_interop.ecpt_quotient_report([], profile="unknown-profile"),
        public_interop.boundary_quotient_report(
            {
                "quotient_id": "quotient:mismatch",
                "boundary_error_ledger": {},
                "context": {},
                "coupling_error_ledger": {},
                "target_id": "source-target",
                "tolerance": 0.1,
            },
            {"target_id": "destination-target"},
        ),
        public_interop.activation_cache_report(
            {
                "state_id": "cache:sampler",
                "activation_mode": "sampler",
                "dependency_hash": "h",
                "invalidation_keys": ["k"],
            }
        ),
        public_interop.activation_cache_report(
            {
                "state_id": "cache:factorized",
                "activation_mode": "factorized",
                "dependency_hash": "h",
                "invalidation_keys": ["k"],
            }
        ),
        public_interop.queue_morphism_report(
            {
                "blocking_residuals": 1,
                "diagnostic_reserve": 1,
                "rollback_priority": 1,
            },
            {
                "blocking_residuals": 0,
                "diagnostic_reserve": 2,
                "rollback_priority": 3,
            },
        ),
        public_interop.diagnostic_reserve_report(
            {
                "state_id": "reserve:outside",
                "diagnostic_reserve": 5,
                "diagnostic_reserve_lower_bound": 1,
                "diagnostic_reserve_upper_bound": 3,
            }
        ),
        public_interop.protocol_mutation_report(
            {"state_id": "protocol:mutated", "protocol_mutated": True}
        ),
        public_interop.checker_cost_report(
            {
                "state_id": "checker:over",
                "checker_cost": 5,
                "cost_budget": 1,
                "verification_queue": [],
            }
        ),
        public_interop.trc_resource_flow_report({"trace_id": "trace:no-flow"}),
        public_interop.efficiency_archive_report(
            {"frontier_id": "frontier:risk", "promotes_risk_provisional": True}
        ),
        public_interop.unseen_frontier_report([]),
    ]

    blockers = {blocker for report in branch_reports for blocker in report.get("blockers", [])}

    assert "lineage_origin_required" in blockers
    assert "clock_required" in blockers
    assert "support_or_negative_controls_required" in blockers
    assert "externality_hazard_ledger_required" in blockers
    assert "telemetry_failure_charge_required" in blockers
    assert "target_profile_mismatch" in blockers
    assert "diagnostic_reserve_above_band" not in blockers
    assert all(report["settled"] is False for report in branch_reports)
