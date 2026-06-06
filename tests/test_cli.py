from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from percolation_inversion_compiler.cli import app

runner = CliRunner()


def test_cli_explain() -> None:
    result = runner.invoke(app, ["explain", "status"])
    assert result.exit_code == 0
    assert "Settled claims require" in result.output


def test_cli_doctor_reports_operational_status() -> None:
    result = runner.invoke(app, ["doctor", "--fail-on", "never"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["report_id"] == "pic-operational-readiness"
    assert data["overall_status"] in {"pass", "warn", "fail"}
    assert data["summary"]["snapshot_count"] == 3
    assert data["summary"]["adapter_route_count"] >= 1
    assert (
        "unresolved external obligations do not promote to settled" in (data["safety_invariants"])
    )


def test_cli_doctor_rejects_bad_fail_on() -> None:
    result = runner.invoke(app, ["doctor", "--fail-on", "bad"])
    assert result.exit_code != 0
    assert "--fail-on must be one of" in result.output


def test_cli_demo_datacenter() -> None:
    result = runner.invoke(app, ["demo", "datacenter"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["compile_result"]["main_frontier"]


def test_cli_coverage_minimal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "coverage.tex"
    source.write_text(
        r"""
\section{A}
\begin{definition}[Observation consistency complex]\label{def:x}
\end{definition}
\begin{theorem}[No status promotion]\label{thm:x}
\end{theorem}
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["coverage", "--source", str(source)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["definitions"] == 1
    assert data["claims"] == 1


def test_cli_schema_type() -> None:
    result = runner.invoke(app, ["schema", "--type", "TheoryAuditReport"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["title"] == "TheoryAuditReport"


def test_cli_schema_bundle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    output_dir = tmp_path / "schemas"
    result = runner.invoke(app, ["schema", "--all", "--output-dir", str(output_dir)])
    assert result.exit_code == 0
    assert (output_dir / "FiniteOrder.schema.json").exists()
    assert (output_dir / "ExecutableTraceNormalForm.schema.json").exists()
    assert (output_dir / "ExternalVerifierHook.schema.json").exists()
    assert (output_dir / "StoppedEvidenceSheafCertificate.schema.json").exists()
    assert (output_dir / "FinitePhaseControlCertificate.schema.json").exists()
    bundle = json.loads((output_dir / "bundle.schema.json").read_text(encoding="utf-8"))
    assert "AgentConnectorSpec" in bundle["schemas"]
    assert "safe_failure_behavior" in bundle["schemas"]["AgentConnectorSpec"]["properties"]
    assert "AdapterRouteSpec" in bundle["schemas"]
    assert "residual_policy" in bundle["schemas"]["ExternalVerifierHook"]["properties"]
    assert "TheorySnapshot" in bundle["schemas"]
    assert "VerifierResolution" in bundle["schemas"]
    assert "OperationalReadinessReport" in bundle["schemas"]
    catalog_props = bundle["schemas"]["ExternalObligationCatalog"]["properties"]
    assert "category_summary" in catalog_props
    assert "verifier_route_summary" in catalog_props
    for schema in bundle["schemas"].values():
        Draft202012Validator.check_schema(schema)


def test_cli_extract_minimal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "x.tex"
    source.write_text(
        r"""
\begin{filecontents*}[overwrite]{claims.json}
{"schema_version":"x","artifact":"a","claims":[{"claim_id":"c","kind":"theorem","label":"C"}]}
\end{filecontents*}
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["extract", "--source", str(source)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["claim_count"] == 1
    assert data["mr_record_counts"]["total"] == 0


def test_cli_check_strict_projection_and_audit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "x.tex"
    source.write_text(
        r"""
\begin{filecontents*}[overwrite]{claims.json}
{"schema_version":"registry-1.0","artifact":"a","claims":[{"claim_id":"c","kind":"theorem","label":"C","dependency_labels":["d"]}]}
\end{filecontents*}
""",
        encoding="utf-8",
    )
    check = runner.invoke(
        app,
        ["check", "--source", str(source), "--strict-projection", "--derive-status"],
    )
    assert check.exit_code == 0
    check_data = json.loads(check.output)
    assert check_data["registries"][0]["projection_sound"]
    assert check_data["derived_status_summary"]["provisional"] == 1
    audit = runner.invoke(app, ["audit", "theory", "--source", str(source)])
    assert audit.exit_code == 0
    audit_data = json.loads(audit.output)
    assert audit_data["projection_audits"][0]["accepted"]
    assert "coverage_delta" in audit_data


def test_cli_json_determinism_for_check() -> None:
    command = [
        "check",
        "--source",
        str(Path("tests") / "fixtures" / "minimal_claims.tex"),
        "--strict-projection",
        "--derive-status",
    ]
    first = runner.invoke(app, command)
    second = runner.invoke(app, command)
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == second.output


def test_cli_audit_fail_on_unsupported(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "unsupported.tex"
    source.write_text(
        r"""
\begin{definition}[Unknown unsupported construct]\label{def:unsupported}
\end{definition}
""",
        encoding="utf-8",
    )
    audit = runner.invoke(
        app,
        ["audit", "theory", "--source", str(source), "--fail-on", "unsupported"],
    )
    assert audit.exit_code == 1


def test_cli_explain_coverage_uses_env_tex_dir(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "Executable Capability Percolation Theory.tex"
    source.write_text(
        r"""
\section{A}
\begin{definition}[No status promotion]\label{def:no-status}
\end{definition}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PIC_CANONICAL_TEX_DIR", str(tmp_path))
    result = runner.invoke(app, ["explain", "coverage", "def:no-status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["item_id"] == "def:no-status"


def test_cli_explain_external_uses_env_tex_dir(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "Typed Reality Compilation.tex"
    source.write_text(
        r"""
\section{A}
\begin{definition}[Typed physical null-channel transfer complex]\label{def:null-channel-routing}
\end{definition}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PIC_CANONICAL_TEX_DIR", str(tmp_path))
    result = runner.invoke(app, ["explain", "external", "def:null-channel-routing"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["item_id"] == "def:null-channel-routing"
    assert data["obligation_category"] == "physical-hybrid-system"
    assert data["verifier_route"] == "trc.adapters.physical_hybrid.verify_envelope"
    assert data["safe_default"] == "diagnostic-with-physical-obligation"
    assert "physical-system-witness-missing" in data["failure_modes"]


def test_cli_explain_external_rejects_unknown_item(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "Typed Reality Compilation.tex"
    source.write_text(
        r"""
\section{A}
\begin{definition}[Typed physical null-channel transfer complex]\label{def:null-channel-routing}
\end{definition}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PIC_CANONICAL_TEX_DIR", str(tmp_path))
    result = runner.invoke(app, ["explain", "external", "def:missing"])
    assert result.exit_code != 0
    assert "external item 'def:missing' was not found" in result.output


def test_cli_snapshot_list_show_and_routes() -> None:
    listed = runner.invoke(app, ["snapshot", "list"])
    assert listed.exit_code == 0
    listed_data = json.loads(listed.output)
    assert [item["artifact_key"] for item in listed_data["snapshots"]] == ["ecpt", "bit", "trc"]

    shown = runner.invoke(app, ["snapshot", "show", "--artifact", "trc"])
    assert shown.exit_code == 0
    shown_data = json.loads(shown.output)
    assert shown_data["coverage_counts"]["unsupported"] == 0
    assert shown_data["external_obligation_category_summary"]["physical-hybrid-system"] == 6

    routes = runner.invoke(app, ["snapshot", "routes"])
    assert routes.exit_code == 0
    route_data = json.loads(routes.output)
    assert any(
        route["verifier_route"] == "trc.adapters.physical_hybrid.verify_envelope"
        for route in route_data["routes"]
    )


def test_cli_explain_external_from_snapshot_without_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("PIC_CANONICAL_TEX_DIR", raising=False)
    result = runner.invoke(
        app,
        ["explain", "external", "def:null-channel-routing", "--from-snapshot"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["obligation_category"] == "physical-hybrid-system"


def test_cli_explain_external_from_snapshot_rejects_unknown() -> None:
    result = runner.invoke(
        app,
        ["explain", "external", "def:missing", "--from-snapshot"],
    )
    assert result.exit_code != 0
    assert "snapshot external item 'def:missing' was not found" in result.output


def test_cli_audit_fail_on_snapshot_delta(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "Typed Reality Compilation.tex"
    source.write_text(
        r"""
\section{A}
\begin{definition}[Observation window]\label{def:observation-window}
\end{definition}
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["audit", "theory", "--source", str(source), "--fail-on", "snapshot"],
    )
    assert result.exit_code == 1
