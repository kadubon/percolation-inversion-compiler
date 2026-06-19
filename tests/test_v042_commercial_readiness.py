from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.agent import agent_feature_readiness
from percolation_inversion_compiler.cli import app
from percolation_inversion_compiler.io import (
    audit_canonical_suite,
    audit_theory_source,
    build_theory_fidelity_report,
    verify_portability_conformance,
)
from percolation_inversion_compiler.io.doctor import build_operational_readiness_report
from percolation_inversion_compiler.io.schema import schema_by_type

runner = CliRunner()


def test_new_public_readiness_and_suite_schemas_are_exported() -> None:
    assert schema_by_type("TheoryAuditSuiteReport")["title"] == "TheoryAuditSuiteReport"
    assert schema_by_type("CommercialReadinessSummary")["title"] == "CommercialReadinessSummary"
    assert schema_by_type("PortabilityConformanceReport")["title"] == (
        "PortabilityConformanceReport"
    )
    assert schema_by_type("TheoryFidelityReport")["title"] == "TheoryFidelityReport"
    assert schema_by_type("PhaseControlAuditSummary")["title"] == "PhaseControlAuditSummary"
    assert schema_by_type("FrontierDebtReport")["title"] == "FrontierDebtReport"
    assert schema_by_type("BottleneckWitnessReport")["title"] == "BottleneckWitnessReport"
    assert schema_by_type("ValueBridgeReport")["title"] == "ValueBridgeReport"
    assert schema_by_type("AgentMessageDeliveryReport")["title"] == "AgentMessageDeliveryReport"
    assert schema_by_type("AgentRelayReadinessReport")["title"] == "AgentRelayReadinessReport"


def test_doctor_adds_commercial_readiness_summary() -> None:
    report = build_operational_readiness_report(profile="development")
    summary = report.commercial_readiness
    assert summary.schema_registry_ready
    assert summary.snapshot_bundle_ready
    assert summary.curated_demo_available
    assert not summary.live_connectors_default_off
    assert summary.live_connectors_default_enabled
    assert summary.live_connector_opt_out_available
    assert summary.install_mode in {"source-checkout", "installed-package"}

    result = runner.invoke(app, ["doctor", "--fail-on", "never"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["commercial_readiness"]["schema_registry_ready"] is True
    assert data["commercial_readiness"]["live_connectors_default_enabled"] is True


def test_agent_readiness_adds_commercial_identity_diagnostic() -> None:
    report = agent_feature_readiness(profile="production")
    assert report.commercial_readiness.production_identity_required
    assert not report.commercial_readiness.identity_ready
    assert "production/adversarial use requires accepted identity context" in (
        report.commercial_readiness.reasons
    )

    result = runner.invoke(app, ["agent", "readiness", "--profile", "production"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["commercial_readiness"]["production_identity_required"] is True
    assert data["commercial_readiness"]["identity_ready"] is False


def test_sqot_audit_rejects_wrong_source_without_misleading_snapshot(tmp_path: Path) -> None:
    wrong = tmp_path / "Observable-Signal Crystallization Theory.tex"
    wrong.write_text(
        r"""
\section{Wrong}
\begin{definition}[Unrelated construct]\label{def:unrelated}
\end{definition}
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["sqot", "audit", "--source", str(wrong), "--no-strict-grammar"],
    )
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["accepted"] is False
    assert data["audit"] is None
    assert data["coverage_counts"] == {}
    assert "Salience-Queue Occupation Theory.tex" in data["reasons"][0]


def test_alt_snapshot_external_category_regression_when_present() -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    source = Path(canonical_dir) / "Abstraction Liquidity Theory.tex"
    report = audit_theory_source(source, canonical_key="alt")
    assert report.snapshot_delta["coverage_counts_match"]
    assert report.snapshot_delta["external_category_summary_match"]


def test_canonical_suite_audit_when_present() -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    report = audit_canonical_suite(canonical_dir)
    assert report.accepted
    assert report.overall_status == "pass"
    assert report.unsupported_total == 0
    assert report.partial_total == 0
    assert report.coverage_counts_match
    assert report.external_category_summary_match

    result = runner.invoke(
        app,
        ["audit", "canonical-suite", "--canonical-dir", canonical_dir],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is True


def test_theory_fidelity_audit_when_present() -> None:
    canonical_dir = os.environ.get("PIC_CANONICAL_TEX_DIR")
    if not canonical_dir:
        pytest.skip("PIC_CANONICAL_TEX_DIR is not set")
    report = build_theory_fidelity_report(canonical_dir)
    assert report.accepted
    assert report.settled is False
    assert report.unsupported_total == 0
    assert report.partial_total == 0
    assert report.external_obligation_totals["alt"] == 54
    assert report.finite_upgrade_candidates["ecpt"]

    result = runner.invoke(
        app,
        ["audit", "fidelity", "--canonical-dir", canonical_dir],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is True
    assert data["suite_status"] == "pass"
    assert data["settled"] is False


def test_canonical_suite_reports_drift_for_noncanonical_sources(tmp_path: Path) -> None:
    minimal = r"""
\section{Minimal}
\begin{definition}[Observation window]\label{def:observation-window}
\end{definition}
"""
    for filename in [
        "Executable Capability Percolation Theory.tex",
        "Bottleneck Inversion Theory.tex",
        "Typed Reality Compilation.tex",
        "Salience-Queue Occupation Theory.tex",
        "Abstraction Liquidity Theory.tex",
    ]:
        (tmp_path / filename).write_text(minimal, encoding="utf-8")

    report = audit_canonical_suite(tmp_path)
    assert not report.accepted
    assert report.overall_status == "fail"
    assert set(report.audits) == {"ecpt", "bit", "trc", "sqot", "alt"}
    assert not report.coverage_counts_match
    assert not report.external_category_summary_match
    assert any("canonical SHA-256 mismatch" in reason for reason in report.reasons)

    fidelity = build_theory_fidelity_report(tmp_path)
    assert not fidelity.accepted
    assert fidelity.suite_status == "fail"
    assert set(fidelity.theory_summaries) == {"ecpt", "bit", "trc", "sqot", "alt"}
    assert all(not healthy for healthy in fidelity.snapshot_health.values())

    result = runner.invoke(
        app,
        ["audit", "canonical-suite", "--canonical-dir", str(tmp_path), "--fail-on", "never"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["accepted"] is False

    fidelity_result = runner.invoke(
        app,
        ["audit", "fidelity", "--canonical-dir", str(tmp_path), "--fail-on", "never"],
    )
    assert fidelity_result.exit_code == 0
    fidelity_data = json.loads(fidelity_result.output)
    assert fidelity_data["accepted"] is False


def test_portability_conformance_examples_validate_against_public_schemas() -> None:
    root = Path("examples/portability_conformance")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "portability-conformance-1.0"
    for example in manifest["examples"]:
        schema = schema_by_type(example["schema"])
        data = json.loads((root / example["file"]).read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=str)
        assert errors == []
        if "settled" in data:
            assert isinstance(data["settled"], bool)

    result = runner.invoke(
        app,
        [
            "portability",
            "verify",
            "--manifest",
            str(root / "manifest.json"),
            "--fail-on",
            "never",
        ],
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["accepted"] is True
    assert report["operationally_usable"] is True
    assert set(report["checked_examples"]) == {example["file"] for example in manifest["examples"]}
    assert set(report["checked_examples"].values()) == {"valid"}
    expected_schemas = {example["file"]: example["schema"] for example in manifest["examples"]}
    expected_schemas.update(
        {example["file"]: example["schema"] for example in manifest.get("negative_examples", [])}
    )
    assert report["schema_names"] == expected_schemas
    assert report["positive_example_count"] == len(manifest["examples"])
    assert report["negative_example_count"] == len(manifest["negative_examples"])
    assert report["expected_failure_count"] == len(manifest["negative_examples"])
    assert report["unexpected_failure_count"] == 0
    assert set(report["checked_negative_examples"].values()) == {
        "missing",
        "schema-invalid",
        "sha256-mismatch",
        "unknown-schema",
    }


def test_portability_conformance_reports_diagnostic_failures(tmp_path: Path) -> None:
    invalid_payload = tmp_path / "invalid.json"
    invalid_payload.write_text("{}", encoding="utf-8")
    mismatch_payload = tmp_path / "mismatch.json"
    mismatch_payload.write_text('{"report_id":"x"}', encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "portability-conformance-1.0",
                "examples": [
                    "bad-entry",
                    {"file": "missing.json", "schema": "AgentIntakeReport"},
                    {
                        "file": "mismatch.json",
                        "schema": "AgentIntakeReport",
                        "sha256": "0" * 64,
                    },
                    {"file": "invalid.json", "schema": "UnknownSchema"},
                    {"file": "invalid.json", "schema": "AgentIntakeReport"},
                    {"file": 1, "schema": "AgentIntakeReport"},
                ],
                "invariants": "not-a-list",
            }
        ),
        encoding="utf-8",
    )
    report = verify_portability_conformance(manifest)
    assert not report.accepted
    assert report.checked_examples["missing.json"] == "missing"
    assert report.checked_examples["mismatch.json"] == "sha256-mismatch"
    assert report.checked_examples["invalid.json"] in {"unknown-schema", "schema-invalid"}
    assert report.unexpected_failure_count == 0
    assert report.semantic_invariants == []
    joined = " ".join(report.reasons)
    assert "manifest example entry must be an object" in joined
    assert "manifest example entries require string file and schema" in joined
    assert "missing.json: example file is missing" in joined
