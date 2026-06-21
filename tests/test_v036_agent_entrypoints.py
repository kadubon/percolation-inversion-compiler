from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from percolation_inversion_compiler.agent import (
    AgentCheckReport,
    AgentIntakeReport,
    AgentIntakeRequest,
    agent_check_compact_payload,
    build_agent_communication_guide,
    build_agent_runbook,
    run_agent_check,
    run_agent_intake,
)
from percolation_inversion_compiler.cli import app

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_agents_md_exists_and_states_safety_contract() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for phrase in [
        "residual",
        "settled=false",
        "production",
        "identity",
        "Do not claim real ASI",
    ]:
        assert phrase in text


def test_agent_manifest_json_is_machine_readable() -> None:
    data = json.loads((ROOT / "agent-manifest.json").read_text(encoding="utf-8"))
    assert data["name"] == "percolation-inversion-compiler"
    assert data["version"] == "0.4.4"
    assert "non_goals" in data
    assert "safe_cli_entrypoints" in data
    assert "important_schemas" in data
    assert "AgentIntakeReport" in data["important_schemas"]
    assert "AgentWorkflowGuide" in data["important_schemas"]
    assert "AgentCommunicationGuide" in data["important_schemas"]
    assert "GeneralIntakeReport" in data["important_schemas"]
    assert "IntakeProvenanceRecord" in data["important_schemas"]
    assert "AgentMessageEnvelope" in data["important_schemas"]
    assert "AgentMessageVerificationContext" in data["important_schemas"]
    assert "pic demo installed-smoke --profile development" in data["safe_cli_entrypoints"]
    assert any("pic agent check" in item for item in data["safe_cli_entrypoints"])
    assert data["machine_contract"]["curated_demo_bundle_in_wheel"] is True
    assert data["clone_url"] == "https://github.com/kadubon/percolation-inversion-compiler.git"
    assert data["clone_recommended_for_full_use"] is False
    assert "examples/..." in data["pip_boundary"]["clone_required_for"][0]
    assert "astral.sh/uv/install.ps1" in data["uv_install_commands"]["windows_powershell"]
    assert "astral.sh/uv/install.sh" in data["uv_install_commands"]["macos_linux"]
    assert "general web/feed intake" in data["full_feature_stages"]
    assert "agent-to-agent packet exchange" in data["full_feature_stages"]
    assert "collective certify" in data["full_feature_stages"]
    assert not (ROOT / "llms.txt").exists()


def test_schema_index_json_points_to_schema_bundle_command() -> None:
    data = json.loads((ROOT / "schemas" / "index.json").read_text(encoding="utf-8"))
    assert data["schema_bundle_command"] == "uv run pic schema --all --output-dir schemas/generated"
    assert "RuntimeStepReport" in data["important_schema_names"]
    assert "AgentAutonomyAuditReport" in data["important_schema_names"]
    assert "AgentCommandInvocation" in data["important_schema_names"]
    assert "AgentNextActionReport" in data["important_schema_names"]
    assert "GeneralIntakeReport" in data["important_schema_names"]
    assert "AgentPacketExchangeReport" in data["important_schema_names"]
    assert "IntakeProvenanceRecord" in data["important_schema_names"]
    assert "AgentMessageVerificationContext" in data["important_schema_names"]
    assert "pic demo installed-smoke --profile development" in data["network_safe_cli"]
    assert data["network_contract"]["curated_demo_bundle_in_wheel"] is True
    assert data["clone_url"] == "https://github.com/kadubon/percolation-inversion-compiler.git"
    assert data["clone_recommended_for_full_use"] is False
    assert data["install_modes"][0]["mode"] == "pip"
    install_modes = {item["mode"] for item in data["install_modes"]}
    assert "pip-agent-full-extra" in install_modes
    assert "source-checkout" in install_modes
    assert "astral.sh/uv/install.ps1" in data["uv_install_commands"]["windows_powershell"]


def test_run_agent_intake_returns_report_and_preserves_unsettled_status() -> None:
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output="Candidate packet: route missing evidence and preserve residuals.",
            profile="development",
        )
    )
    assert isinstance(report, AgentIntakeReport)
    assert report.profile == "development"
    assert report.runtime_report.input_id == "agent-intake-step"
    assert report.settled is False
    assert report.runtime_report.settled is False
    assert report.recommended_next_commands


def test_pic_agent_explain_and_manifest_exit_zero() -> None:
    explain = runner.invoke(app, ["agent", "explain"])
    assert explain.exit_code == 0
    explain_data = json.loads(explain.output)
    assert "what_it_does_not_do" in explain_data
    assert (
        "percolation_inversion_compiler.agent.run_agent_intake"
        in explain_data["python_entrypoints"]
    )

    manifest = runner.invoke(app, ["agent", "manifest"])
    assert manifest.exit_code == 0
    manifest_data = json.loads(manifest.output)
    assert manifest_data["machine_contract"]["settled_false_is_expected"] is True
    assert manifest_data["clone_recommended_for_full_use"] is False
    assert manifest_data["install_modes"][0]["mode"] == "pip"
    assert "pic agent check" in "\n".join(manifest_data["safe_cli_entrypoints"])
    assert "pic demo bootstrap" in "\n".join(manifest_data["safe_cli_entrypoints"])


def test_pic_agent_guide_contains_full_workflow_and_invariants() -> None:
    result = runner.invoke(app, ["agent", "guide", "--profile", "production"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile"] == "production"
    step_ids = [step["step_id"] for step in data["steps"]]
    assert step_ids == [
        "01-orient",
        "02-inspect-snapshots",
        "03-run-intake",
        "04-derive-identity-context",
        "05-external-communication-readiness",
        "06-general-web-feed-intake",
        "07-agent-to-agent-exchange",
        "08-live-metadata-ingest",
        "09-verify-evidence-routes",
        "10-promote-packets",
        "11-run-store-loop",
        "12-inspect-psi-sqot",
        "13-collective-certify",
        "14-preserve-residuals-provenance",
    ]
    assert data["settled"] is False
    assert any("real ASI" in item for item in data["safety_invariants"])


def test_pic_agent_intake_development_exit_zero() -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "intake",
            "--text",
            "Candidate packet: preserve residuals and route verifier work.",
            "--profile",
            "development",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile"] == "development"
    assert data["settled"] is False
    assert data["runtime_report"]["settled"] is False


def test_pic_agent_check_reports_beginner_workflow_without_settlement() -> None:
    report = run_agent_check(
        AgentIntakeRequest(
            agent_output="Candidate packet: preserve residuals and route verifier work.",
            profile="development",
        )
    )
    assert isinstance(report, AgentCheckReport)
    assert report.workflow_usable is True
    assert report.accepted is True
    assert report.operationally_usable is False
    assert report.settled is False
    assert report.unresolved_obligations
    assert report.next_safe_actions
    assert report.schema_refs
    assert report.runbook_steps

    result = runner.invoke(
        app,
        [
            "agent",
            "check",
            "--text",
            "Candidate packet: preserve residuals and route verifier work.",
            "--profile",
            "development",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["workflow_usable"] is True
    assert data["settled"] is False
    assert data["unresolved_obligations"]

    compact_report = run_agent_check(
        AgentIntakeRequest(
            agent_output="Candidate packet: preserve residuals and route verifier work.",
            profile="development",
        ),
        compact=True,
    )
    payload = agent_check_compact_payload(compact_report)
    assert payload["report_mode"] == "compact"
    assert "intake_report" not in payload
    assert "AgentCheckReport" in payload["schema_refs"]

    compact_result = runner.invoke(
        app,
        [
            "agent",
            "check",
            "--compact",
            "--text",
            "Candidate packet: preserve residuals and route verifier work.",
            "--profile",
            "development",
        ],
    )
    assert compact_result.exit_code == 0
    compact_data = json.loads(compact_result.output)
    assert compact_data["workflow_usable"] is True
    assert compact_data["settled"] is False
    assert "intake_report" not in compact_data


def test_pic_agent_runbook_reports_practical_next_fields() -> None:
    report = build_agent_runbook("development")
    assert report.accepted
    assert report.settled is False
    assert "AgentCheckReport" in report.schemas_to_inspect
    assert "intake_report.runtime_report.phase_control_audit" in report.fields_to_inspect

    result = runner.invoke(app, ["agent", "runbook", "--profile", "development"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["entrypoint"] == "pic agent check --compact"
    assert "RuntimeStepReport" in data["schemas_to_inspect"]


def test_run_agent_intake_can_explicitly_opt_into_live_config() -> None:
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output="Candidate packet: live config opt-in without source fetch.",
            profile="development",
            allow_live_connectors=True,
        )
    )
    assert report.runtime_report.allow_live_connectors is True
    assert report.settled is False


def test_pic_agent_communication_guide_reports_general_intake() -> None:
    default_result = runner.invoke(
        app,
        ["agent", "communication-guide", "--profile", "development"],
    )
    assert default_result.exit_code == 0
    default_data = json.loads(default_result.output)
    assert default_data["allow_live_connectors"] is True
    assert default_data["policy"]["live_connectors_default_enabled"] is True

    result = runner.invoke(
        app,
        [
            "agent",
            "communication-guide",
            "--profile",
            "development",
            "--no-allow-live-connectors",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    step_ids = [step["step_id"] for step in data["steps"]]
    assert "03-general-web-feed-intake" in step_ids
    assert "04-agent-message-exchange" in step_ids
    assert data["allow_live_connectors"] is False
    assert "web-page" in data["policy"]["allowed_source_kinds"]
    assert any("residual" in item for item in data["safety_invariants"])


def test_pic_agent_network_readiness_has_no_network_side_effects() -> None:
    disabled = runner.invoke(
        app,
        ["agent", "network-readiness", "--profile", "development", "--no-allow-live-connectors"],
    )
    assert disabled.exit_code == 0
    disabled_data = json.loads(disabled.output)
    assert disabled_data["readiness"]["live_metadata_ingest"] == "disabled"
    assert disabled_data["readiness"]["general_http_intake"] == "disabled"
    assert "web-crawl" in disabled_data["allowed_source_kinds"]

    enabled = runner.invoke(
        app,
        ["agent", "network-readiness", "--profile", "development", "--allow-live-connectors"],
    )
    assert enabled.exit_code == 0
    enabled_data = json.loads(enabled.output)
    assert enabled_data["allow_live_connectors"] is True
    assert "connector_dependency_present" in enabled_data


def test_pic_agent_message_send_receive_and_relay_readiness(tmp_path: Path) -> None:
    inbox = tmp_path / "cli-inbox.json"
    readiness = runner.invoke(app, ["agent", "relay-readiness", "--inbox", str(inbox)])
    assert readiness.exit_code == 0
    readiness_data = json.loads(readiness.output)
    assert readiness_data["allow_live_connectors"] is True
    assert readiness_data["readiness"]["local_inbox"] == "create-on-send"

    sent = runner.invoke(
        app,
        [
            "agent",
            "message",
            "send",
            "--inbox",
            str(inbox),
            "--sender",
            "agent:alice",
            "--receiver",
            "agent:bob",
            "--nonce",
            "nonce-cli-1",
            "--text",
            "CLI relay packet: preserve residuals.",
        ],
    )
    assert sent.exit_code == 0
    sent_data = json.loads(sent.output)
    assert sent_data["accepted"] is True
    assert sent_data["action"] == "send"
    assert inbox.exists()

    received = runner.invoke(app, ["agent", "message", "receive", "--inbox", str(inbox)])
    assert received.exit_code == 0
    received_data = json.loads(received.output)
    assert received_data["accepted"] is True
    assert received_data["action"] == "receive"
    assert received_data["nonce_ledger"]["consumed_nonces"] == ["nonce-cli-1"]

    verified = runner.invoke(app, ["agent", "inbox", "verify", "--inbox", str(inbox)])
    assert verified.exit_code == 0
    assert json.loads(verified.output)["accepted"] is True


def test_pic_agent_doctor_production_reports_identity_not_ready() -> None:
    result = runner.invoke(app, ["agent", "doctor", "--profile", "production"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    health = data["runtime_health"]
    assert health["profile"] == "production"
    assert health["production_identity_ready"] is False
    assert health["cryptographic_identity_required"] is True


def test_pic_agent_readiness_production_is_diagnostic_without_identity() -> None:
    result = runner.invoke(app, ["agent", "readiness", "--profile", "production"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile"] == "production"
    assert data["readiness"]["identity_context"] == "diagnostic"
    assert data["readiness"]["packet_promotion"] == "diagnostic"
    assert data["operationally_usable"] is False
    assert data["settled"] is False


def test_pic_agent_next_recommends_safe_follow_up(tmp_path) -> None:  # type: ignore[no-untyped-def]
    intake_path = tmp_path / "intake.json"
    intake = runner.invoke(
        app,
        [
            "agent",
            "intake",
            "--text",
            "Candidate packet: route evidence and preserve residuals.",
            "--profile",
            "development",
            "--output",
            str(intake_path),
        ],
    )
    assert intake.exit_code == 0
    result = runner.invoke(
        app,
        ["agent", "next", "--intake-report", str(intake_path), "--profile", "development"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["settled"] is False
    assert "RuntimeStepReport" in data["schemas_to_inspect"]
    assert any("residual_ledger" in item for item in data["next_commands"])


def test_agent_intake_report_schema_is_exported() -> None:
    result = runner.invoke(app, ["schema", "--type", "AgentIntakeReport"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["title"] == "AgentIntakeReport"

    guide = runner.invoke(app, ["schema", "--type", "AgentWorkflowGuide"])
    assert guide.exit_code == 0
    assert json.loads(guide.output)["title"] == "AgentWorkflowGuide"

    next_report = runner.invoke(app, ["schema", "--type", "AgentNextActionReport"])
    assert next_report.exit_code == 0
    assert json.loads(next_report.output)["title"] == "AgentNextActionReport"

    readiness = runner.invoke(app, ["schema", "--type", "AgentFeatureReadinessReport"])
    assert readiness.exit_code == 0
    assert json.loads(readiness.output)["title"] == "AgentFeatureReadinessReport"

    communication = runner.invoke(app, ["schema", "--type", "AgentCommunicationGuide"])
    assert communication.exit_code == 0
    assert json.loads(communication.output)["title"] == "AgentCommunicationGuide"

    network = runner.invoke(app, ["schema", "--type", "AgentNetworkReadinessReport"])
    assert network.exit_code == 0
    assert json.loads(network.output)["title"] == "AgentNetworkReadinessReport"

    general = runner.invoke(app, ["schema", "--type", "GeneralIntakeReport"])
    assert general.exit_code == 0
    assert json.loads(general.output)["title"] == "GeneralIntakeReport"

    bridge = runner.invoke(app, ["schema", "--type", "GeneralIntakeRuntimeBridgeReport"])
    assert bridge.exit_code == 0
    assert json.loads(bridge.output)["title"] == "GeneralIntakeRuntimeBridgeReport"

    profile = runner.invoke(app, ["schema", "--type", "GeneralIntakeProfile"])
    assert profile.exit_code == 0
    assert "production_network" in json.loads(profile.output)["enum"]

    contract = runner.invoke(app, ["schema", "--type", "AgentMessageContractReport"])
    assert contract.exit_code == 0
    assert json.loads(contract.output)["title"] == "AgentMessageContractReport"

    provenance = runner.invoke(app, ["schema", "--type", "IntakeProvenanceRecord"])
    assert provenance.exit_code == 0
    assert json.loads(provenance.output)["title"] == "IntakeProvenanceRecord"

    verification_context = runner.invoke(
        app, ["schema", "--type", "AgentMessageVerificationContext"]
    )
    assert verification_context.exit_code == 0
    assert json.loads(verification_context.output)["title"] == "AgentMessageVerificationContext"

    check = runner.invoke(app, ["schema", "--type", "AgentCheckReport"])
    assert check.exit_code == 0
    assert json.loads(check.output)["title"] == "AgentCheckReport"

    runbook = runner.invoke(app, ["schema", "--type", "AgentRunbookReport"])
    assert runbook.exit_code == 0
    assert json.loads(runbook.output)["title"] == "AgentRunbookReport"


def test_general_intake_and_agent_message_cli_smoke(tmp_path: Path) -> None:
    policy = runner.invoke(
        app,
        ["ecology", "policy", "explain", "--profile", "controlled_web"],
    )
    assert policy.exit_code == 0
    policy_data = json.loads(policy.output)
    assert policy_data["profile"] == "controlled_web"
    assert policy_data["web_policy"]["max_total_packets_per_run"] == 128

    feed = runner.invoke(
        app,
        [
            "ecology",
            "ingest-general",
            "--source",
            str(ROOT / "examples" / "agent_network" / "feed.xml"),
            "--kind",
            "rss",
        ],
    )
    assert feed.exit_code == 0
    feed_data = json.loads(feed.output)
    assert feed_data["accepted"] is True
    assert feed_data["source_kind"] == "rss"
    assert feed_data["candidate_only"] is True
    assert feed_data["ecpt_phase_contribution_allowed"] is False

    report_path = tmp_path / "general-intake-report.json"
    report_path.write_text(json.dumps(feed_data), encoding="utf-8")

    bridge = runner.invoke(
        app,
        ["ecology", "bridge-runtime", "--report", str(report_path)],
    )
    assert bridge.exit_code == 0
    bridge_data = json.loads(bridge.output)
    assert bridge_data["candidate_only"] is True
    assert bridge_data["settled"] is False

    audit = runner.invoke(
        app,
        ["ecology", "intake-audit", "--report", str(report_path)],
    )
    assert audit.exit_code == 0
    assert json.loads(audit.output)["source_report_id"] == feed_data["report_id"]

    web = runner.invoke(
        app,
        [
            "ecology",
            "discover-web",
            "--source",
            str(ROOT / "examples" / "agent_network" / "page.html"),
        ],
    )
    assert web.exit_code == 0
    web_data = json.loads(web.output)
    assert web_data["accepted"] is True
    assert web_data["packets"]

    message = runner.invoke(
        app,
        [
            "agent",
            "message",
            "ingest",
            "--message",
            str(ROOT / "examples" / "agent_network" / "agent_message.json"),
        ],
    )
    assert message.exit_code == 0
    message_data = json.loads(message.output)
    assert message_data["source_kind"] == "agent-message"
    assert message_data["settled"] is False
    assert message_data["provenance"]

    contract = runner.invoke(
        app,
        [
            "agent",
            "message",
            "contract",
            "--message",
            str(ROOT / "examples" / "agent_network" / "agent_message.json"),
        ],
    )
    assert contract.exit_code == 0
    contract_data = json.loads(contract.output)
    assert contract_data["message_contract_valid"] is True
    assert contract_data["candidate_only"] is True


def test_build_agent_communication_guide_is_deterministic() -> None:
    first = build_agent_communication_guide("development", False).model_dump(mode="json")
    second = build_agent_communication_guide("development", False).model_dump(mode="json")
    assert first == second
