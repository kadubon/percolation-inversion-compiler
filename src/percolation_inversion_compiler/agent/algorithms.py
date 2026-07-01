"""High-level agent intake helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import os

from percolation_inversion_compiler import __version__
from percolation_inversion_compiler.acceleration import (
    PhaseAccelerationPlan,
    PhaseAccelerationRequest,
    build_phase_acceleration_plan,
)
from percolation_inversion_compiler.agent.records import (
    AgentAutonomyAuditReport,
    AgentCheckReport,
    AgentCommandInvocation,
    AgentCommunicationGuide,
    AgentCommunicationPolicy,
    AgentCommunicationStep,
    AgentFeatureReadinessReport,
    AgentIntakeReport,
    AgentIntakeRequest,
    AgentNetworkReadinessReport,
    AgentNextActionReport,
    AgentRunbookReport,
    AgentWorkflowGuide,
    AgentWorkflowStep,
)
from percolation_inversion_compiler.core.live_policy import (
    default_allow_live_connectors,
    live_default_non_authorities,
    live_default_safety_invariant,
)
from percolation_inversion_compiler.ecology.records import (
    CapabilityPacketCandidate,
    PacketSourceKind,
)
from percolation_inversion_compiler.ecpt.records import (
    ASIProxyTargetContract,
    CapabilityEdge,
    CapabilityHypergraph,
    CapabilityPacket,
    CapabilityStateVector,
    PhaseControlAction,
    PhaseControlObjective,
    PhaseControlState,
)
from percolation_inversion_compiler.io.commercial import build_commercial_readiness_summary
from percolation_inversion_compiler.runtime.algorithms import build_runtime_step, runtime_health
from percolation_inversion_compiler.runtime.records import (
    AgentRuntimeConfig,
    RuntimeIdentityContext,
    RuntimeState,
    RuntimeStepInput,
)

_CMD_AGENT_COMM_GUIDE_DEV = "uv run pic agent communication-guide --profile development"
_CMD_AGENT_NETWORK_DEV = "uv run pic agent network-readiness --profile development"
_CMD_INGEST_FEED = (
    "uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss"
)
_CMD_INGEST_PAGE = (
    "uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page"
)
_CMD_DISCOVER_PAGE = "uv run pic ecology discover-web --source examples/agent_network/page.html"
_CMD_AGENT_MESSAGE_INGEST = (
    "uv run pic agent message ingest --message examples/agent_network/agent_message.json"
)
_CMD_AGENT_MESSAGE_CONTRACT = (
    "uv run pic agent message contract --message examples/agent_network/agent_message.json"
)
_CMD_AGENT_INBOX_EXPORT = "uv run pic agent inbox export --inbox examples/agent_network/inbox.json"
_CMD_GITHUB_INGEST = (
    "uv run pic ecology ingest --source kadubon/percolation-inversion-compiler --kind github"
)
_CMD_ZENODO_INGEST = (
    "uv run pic ecology ingest --source https://zenodo.org/records/20526451 --kind zenodo"
)
_CMD_EVIDENCE_VERIFY_PROD = (
    "uv run pic evidence verify --envelope examples/evidence_envelope.json --profile production"
)
_CMD_PROVENANCE_CREATE = (
    "uv run pic provenance create --schema-dir schemas/generated --output provenance.json"
)
_CMD_LIVE_WEB_INGEST = (
    "uv run pic ecology ingest-general --source https://example.org --kind web-page"
)
_CMD_LIVE_WEB_DISCOVER = "uv run pic ecology discover-web --source https://example.org"
_CMD_ALT_NEGATIVE = (
    "uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json"
)
_CMD_ALT_REFRESH_BASELINE = (
    "uv run pic alt refresh-baseline --certificate examples/alt/baseline_refresh_certificate.json"
)
_CMD_ALT_CHECK_CARA = (
    "uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json"
)
_CHECK_TEXT = "Candidate packet: preserve residuals."


def pip_core_commands(profile: str = "development") -> list[str]:
    """Return commands expected to work from a bare PyPI install."""

    return [
        "python -m pip install percolation-inversion-compiler",
        "pic agent explain",
        f"pic agent autonomy-audit --profile {profile} --format json",
        f'pic agent check --compact --text "{_CHECK_TEXT}" --profile {profile}',
        f'pic phase plan --compact --text "{_CHECK_TEXT}" --profile {profile}',
        f'pic agent accelerate --compact --text "{_CHECK_TEXT}" --profile {profile}',
        f"pic demo installed-smoke --profile {profile}",
        "pic demo bootstrap --output-dir pic-demo",
        f"pic runtime step --state pic-demo/runtime_state.json --input "
        f"pic-demo/runtime_step_input.json --profile {profile}",
        f"pic phase benchmark-suite --profile {profile} --format json",
        f"pic phase dashboard --profile {profile} --format json",
        "pic phase lab init --output-dir pic-demo/phase-lab",
        "pic phase lab ingest --store pic-demo/phase-lab "
        "--report pic-demo/phase_lab_runtime_report.json",
        "pic phase lab observe --store pic-demo/phase-lab --window latest",
        "pic phase lab graph --store pic-demo/phase-lab",
        "pic phase lab closure --store pic-demo/phase-lab",
        "pic phase lab executable-paths --store pic-demo/phase-lab",
        "pic phase lab certify --store pic-demo/phase-lab "
        "--threshold pic-demo/phase_lab_threshold.json",
        "pic packet inspect --packet pic-demo/packet_envelope.json",
        "pic packet merge --packets pic-demo/packet_envelope.json "
        "--output pic-demo/merged-packets.json",
        "pic packet lineage --packet pic-demo/merged-packets.json",
        "pic phase observe --reports pic-demo/phase_dashboard.json "
        "--output pic-demo/observation.json",
        "pic snapshot list",
        f"pic audit canonical-readiness --profile {profile} --format json",
        "pic schema --type AgentAutonomyAuditReport",
        "pic schema --type CanonicalImplementationReadinessReport",
    ]


def pip_agent_full_commands(profile: str = "development") -> list[str]:
    """Return commands unlocked by the agent-full extra without a source checkout."""

    return [
        'python -m pip install "percolation-inversion-compiler[agent-full]"',
        f"pic agent network-readiness --profile {profile}",
        f"pic agent communication-guide --profile {profile}",
        f"pic agent communication-guide --profile {profile} --no-allow-live-connectors",
        f"pic agent relay-readiness --profile {profile}",
    ]


def source_checkout_commands(profile: str = "development") -> list[str]:
    """Return fixture-backed commands that still require repository examples."""

    return [
        "uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss",
        "uv run pic ecology bridge-runtime --report "
        "examples/agent_network/general_intake_report.example.json",
        "uv run pic alt admit --packet examples/alt/admission_packet.json",
        "uv run pic ecology effective-graph --reports examples/phase_lab/runtime_report_1.json",
        "uv run pic phase lab init --output-dir pic-phase-lab",
        "uv run pic phase lab ingest --store pic-phase-lab "
        "--report examples/phase_lab/runtime_report_1.json",
        "uv run pic phase lab graph --store pic-phase-lab",
        "uv run pic bit diagnose --graph examples/phase_lab/effective_graph.example.json",
        "uv run pic sqot diagnose-queue --graph examples/phase_lab/effective_graph.example.json",
        "uv run pic alt ecpt-lift --packets examples/packet_exchange/packet_envelope.example.json "
        "--graph examples/phase_lab/effective_graph.example.json",
        "uv run pic trc trace-adapter --input examples/trc_adapter/tool_trace_input.example.json",
        "uv run pic agent message contract --message examples/agent_network/agent_message.json",
        "uv run pic phase plan --request "
        "examples/phase_acceleration/phase_acceleration_request.json "
        f"--compact --profile {profile}",
    ]


def _argv(command: str) -> list[str]:
    if command.startswith('pic agent check --compact --text "'):
        return [
            "pic",
            "agent",
            "check",
            "--compact",
            "--text",
            _CHECK_TEXT,
            "--profile",
            command.rsplit(" ", maxsplit=1)[-1],
        ]
    if command.startswith('pic phase plan --compact --text "'):
        return [
            "pic",
            "phase",
            "plan",
            "--compact",
            "--text",
            _CHECK_TEXT,
            "--profile",
            command.rsplit(" ", maxsplit=1)[-1],
        ]
    if command.startswith('pic agent accelerate --compact --text "'):
        return [
            "pic",
            "agent",
            "accelerate",
            "--compact",
            "--text",
            _CHECK_TEXT,
            "--profile",
            command.rsplit(" ", maxsplit=1)[-1],
        ]
    if command.startswith('python -m pip install "'):
        return ["python", "-m", "pip", "install", "percolation-inversion-compiler[agent-full]"]
    return command.split()


def _invocation(
    invocation_id: str,
    command: str,
    purpose: str,
    *,
    requires_source_checkout: bool = False,
    requires_agent_full_extra: bool = False,
    requires_operator_authority: bool = False,
    mutates_environment_if_operator_runs_it: bool = False,
) -> AgentCommandInvocation:
    return AgentCommandInvocation(
        invocation_id=invocation_id,
        purpose=purpose,
        argv=_argv(command),
        shell_command=command,
        requires_source_checkout=requires_source_checkout,
        requires_agent_full_extra=requires_agent_full_extra,
        requires_operator_authority=requires_operator_authority,
        mutates_environment_if_operator_runs_it=mutates_environment_if_operator_runs_it,
        safety_notes=[
            "argv is the portable invocation; shell_command is display text",
            "PIC emits this command as data and does not execute it",
        ],
    )


def agent_manifest_payload() -> dict[str, object]:
    """Return the deterministic machine-readable agent manifest payload."""

    return {
        "important_schemas": [
            "RuntimeStepInput",
            "RuntimeStepReport",
            "CapabilityPacketCandidate",
            "VerifiedCapabilityPacket",
            "PacketPromotionReport",
            "SybilResistanceLedger",
            "RuntimeIdentityContext",
            "CollectivePhaseCertificate",
            "AgentIntakeRequest",
            "AgentIntakeReport",
            "AgentCheckReport",
            "AgentCommandInvocation",
            "AgentAutonomyAuditReport",
            "CanonicalImplementationReadinessReport",
            "CanonicalTheorySnapshotSummary",
            "AgentWorkflowGuide",
            "AgentNextActionReport",
            "AgentFeatureReadinessReport",
            "PhaseAccelerationRequest",
            "PhaseAccelerationPlan",
            "PhaseGapVector",
            "PhaseComponentGap",
            "BottleneckCandidate",
            "SafePhaseAction",
            "PhaseTrajectoryReport",
            "PhaseAccelerationBenchmarkReport",
            "ProtocolRelativeBenchmarkMetric",
            "PhaseBenchmarkTask",
            "PhaseBenchmarkCaseResult",
            "PhaseBenchmarkSuiteReport",
            "PhaseDashboardReport",
            "PhaseObservationReport",
            "OperatorAdoptionPacket",
            "AgentToOperatorRequest",
            "AdoptionSafetyBoundary",
            "AdoptionFirstRunCommand",
            "AdoptionReviewChecklist",
            "PacketExchangeEnvelope",
            "PacketImportInspectionReport",
            "PacketMergeReport",
            "PacketLineageDigest",
            "ResidualCarryForwardReport",
            "AgentCommunicationPolicy",
            "AgentCommunicationGuide",
            "AgentNetworkReadinessReport",
            "GeneralIntakeProfile",
            "GeneralIntakePolicy",
            "GeneralIntakePolicyDecision",
            "GeneralIntakeSource",
            "GeneralIntakeReport",
            "GeneralIntakeRuntimeBridgeReport",
            "ExternalCandidateClassification",
            "AgentMessageContractReport",
            "IntakeProvenanceRecord",
            "WebFetchPolicy",
            "WebFetchReport",
            "RobotsDecision",
            "WebDiscoveryReport",
            "AgentMessageEnvelope",
            "AgentMessageVerificationContext",
            "AgentMessageNonceLedger",
            "AgentInboxRecord",
            "AgentPacketExchangeReport",
            "AbstractionToken",
            "LiquidityCertificate",
            "NegativeLiquidityCertificate",
            "ALTDeprecationRecord",
            "ALTResurrectionRecord",
            "BaselineRefreshCertificate",
            "OpportunityMeasureContract",
            "RootFinalityCertificate",
            "TelemetryCostCertificate",
            "HazardEnvelopeCertificate",
            "ReproductionMatrixCertificate",
            "ALTAdmissionDecision",
            "ALTCARACertificate",
            "ALTKernelTransitionReport",
            "FoundryControlDashboard",
            "CertifiedAbstractionCapital",
            "PhaseLabStoreManifest",
            "PhaseLabIngestReport",
            "PhaseLabExportManifest",
            "EffectivePacketGraph",
            "PhaseWindowObservation",
            "PhaseWindowComparison",
            "AutocatalyticClosureReport",
            "AutocatalyticClosureWitness",
            "ExecutionAvailablePathReport",
            "ExecutionAvailableHyperpath",
            "ASIProxyThreshold",
            "ASIProxyThresholdStatus",
            "CollectivePhaseCertificateCandidate",
            "BottleneckInversionReport",
            "QueueOccupationReport",
            "AltEcptLiftReport",
            "TypedAgentTrace",
        ],
        "machine_contract": {
            "arbitrary_shell_execution": False,
            "candidate_only_closure_execution_and_basin_paths_do_not_improve_phase_status": True,
            "curated_demo_bundle_in_wheel": True,
            "examples_path_requires_source_checkout": True,
            "external_candidate_volume_cannot_improve_phase_status": True,
            "external_content_is_candidate_only": True,
            "feed_and_inbox_entry_counts_are_bounded": True,
            "general_intake_reports_sanitized_fetch_provenance": True,
            "general_intake_requires_explicit_source": True,
            "general_intake_is_bounded_candidate_only_by_default": True,
            "installed_package_smoke_commands_available": True,
            "adoption_required_for_core": False,
            "approval_gate_present": False,
            "safe_commands_executable_by_pic": False,
            "compact_mode_available": True,
            "pip_core_workflow_available": True,
            "agent_full_extra_available": True,
            "source_checkout_required_for_core": False,
            "shell_expansion_required_for_sidecars": False,
            "command_execution_allowed_by_pic": False,
            "approval_persistence_created": False,
            "live_connectors_default_enabled": True,
            "live_connectors_opt_out_available": True,
            "live_discovery_fetches_each_resource_once": True,
            "local_staged_intake_uses_byte_limits": True,
            "local_web_discovery_disallows_seed_directory_escape": True,
            "operator_adoption_sidecar_optional": True,
            "sidecar_absence_is_not_failure": True,
            "benchmark_dashboard_and_packet_exchange_are_diagnostic_only": True,
            "phase_lab_diagnostics_are_non_executing": True,
            "phase_lab_outputs_are_settled_false_by_default": True,
            "bit_sqot_alt_lift_trc_outputs_are_diagnostic_only": True,
            "production_requires_identity_context": True,
            "redirect_chain_urls_are_policy_validated": True,
            "residuals_are_not_failures": True,
            "rss_atom_uses_defused_xml": True,
            "sanitized_outputs_only": True,
            "settled_false_is_expected": True,
        },
        "install_modes": [
            {
                "mode": "pip",
                "command": "python -m pip install percolation-inversion-compiler",
                "intended_for": [
                    "practical agent output checking",
                    "curated installed workflow",
                    "bundled snapshots",
                    "schema export",
                    "library and CLI runtime checks",
                    "ALT admission smoke with bundled data",
                ],
                "does_not_include": [
                    "root examples tree",
                    "canonical TeX files",
                    "release engineering fixtures",
                ],
            },
            {
                "mode": "pip-agent-full-extra",
                "command": 'python -m pip install "percolation-inversion-compiler[agent-full]"',
                "intended_for": [
                    "bounded explicit-source live connector readiness",
                    "cryptographic identity verification",
                    "local runtime service dependencies",
                ],
                "does_not_include": [
                    "science/OT/LP research dependencies",
                    "root examples tree",
                    "canonical TeX files",
                ],
            },
            {
                "mode": "source-checkout",
                "command": (
                    "git clone https://github.com/kadubon/percolation-inversion-compiler.git"
                ),
                "intended_for": [
                    "examples-backed commands",
                    "canonical TeX audits",
                    "development tests",
                    "release engineering",
                ],
            },
        ],
        "deployment_surfaces": [
            "cli",
            "python-sdk",
            "github-actions",
            "runtime-service",
            "external-intake",
            "agent-messages",
            "alt-foundry",
            "agent-autonomy-audit",
            "canonical-implementation-readiness",
            "operator-adoption-sidecar",
            "packet-exchange-sidecar",
            "phase-dashboard-sidecar",
            "phase-ecology-lab",
            "bit-inversion-engine",
            "sqot-controller",
            "alt-ecpt-lift",
            "trc-trace-adapter",
            "ccr-interop",
            "trc-operation-readiness",
        ],
        "clone_url": "https://github.com/kadubon/percolation-inversion-compiler.git",
        "clone_recommended_for_full_use": False,
        "clone_recommended_for": [
            "canonical TeX audits",
            "development fixtures",
            "release engineering",
            "editing examples and docs",
        ],
        "uv_install_commands": {
            "windows_powershell": (
                'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
            ),
            "macos_linux": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "pypi_fallback": "python -m pip install uv",
        },
        "pip_boundary": {
            "agent_full_extra": "percolation-inversion-compiler[agent-full]",
            "pip_core_commands": pip_core_commands(),
            "pip_agent_full_commands": pip_agent_full_commands(),
            "source_checkout_commands": source_checkout_commands(),
            "pip_supports": [
                "pic agent explain",
                "pic agent check",
                "pic agent autonomy-audit",
                "pic demo installed-smoke",
                "pic demo bootstrap",
                "pic runtime step with bootstrapped demo files",
                "pic phase benchmark-suite",
                "pic phase dashboard",
                "pic phase lab with bootstrapped Phase Lab files",
                "pic audit canonical-readiness",
                "pic packet inspect/merge/lineage with bootstrapped packet files",
                "pic snapshot list/show",
                "pic schema export",
                "Python SDK imports",
            ],
            "clone_required_for": [
                "commands that reference examples/...",
                "canonical TeX/PDF audits through local source files",
                "release checks and provenance/SBOM asset generation",
            ],
        },
        "name": "percolation-inversion-compiler",
        "non_goals": [
            "real ASI detection",
            "real ASI creation",
            "model self-rewrite",
            "model weight update",
            "legal identity proof",
            "global Sybil resistance",
            "oracle or simulator truth settlement",
            "unbounded web crawling",
            "arbitrary shell execution",
        ],
        "primary_use_cases": [
            "AI agent workflow verification",
            "evidence routing",
            "capability packet promotion",
            "residual ledger preservation",
            "SQOT queue scheduling",
            "identity and Sybil resistance",
            "explicit opt-in live metadata ingestion",
            "bounded general web intake",
            "agent-to-agent packet exchange",
            "general intake SQOT runtime bridging",
            "collective phase certificate generation",
            "abstraction-token candidate certification",
            "ALT reusable abstraction capital foundry dashboards",
            "ALT negative-liquidity deprecation and resurrection",
            "ALT-CARA protocol-relative acceleration certification",
            "Phase Ecology Lab windowed packet diagnostics",
            "BIT bottleneck inversion diagnostics",
            "SQOT queue occupation diagnostics",
            "ALT-to-ECPT lift diagnostics",
            "TRC typed trace adapters",
            "CLI AI agent output checking",
            "Python SDK agent runtime embedding",
            "read-only GitHub Actions audit artifact generation",
            "bounded default-live explicit-source intake",
            "deterministic phase acceleration planning",
        ],
        "purpose": (
            "AI agent runtime verification and ECPT ASI-proxy collective phase acceleration"
        ),
        "recommended_docs": [
            "README.md",
            "AGENTS.md",
            "docs/for-agents.md",
            "docs/integrations/README.md",
            "docs/agent-external-communication.md",
            "docs/integrations/github-actions.md",
            "docs/operator-adoption.md",
            "docs/agent-to-operator-request.md",
            "docs/integrations/packet-exchange.md",
            "docs/phase-dashboard.md",
            "docs/phase-ecology-lab.md",
            "docs/effective-packet-graph.md",
            "docs/bit-inversion-engine.md",
            "docs/sqot-queue-sovereignty.md",
            "docs/alt-ecpt-lift.md",
            "docs/trc-trace-adapter.md",
            "docs/ccr-pic-roundtrip.md",
            "docs/asi-proxy-acceleration.md",
            "docs/threshold-certificates.md",
            "docs/benchmarks/phase-benchmark-suite.md",
            "docs/canonical-implementation-readiness.md",
            "docs/pypi-distribution.md",
            "docs/01-quickstart.md",
            "docs/identity-and-sybil-resistance.md",
            "docs/04-collective-phase-certificate.md",
            "examples/cli_agent_output_check/README.md",
            "examples/python_sdk_agent_output_check/README.md",
            "examples/github_action_agent_output_check/README.md",
        ],
        "full_feature_stages": [
            "orient",
            "inspect snapshots",
            "run intake",
            "derive identity context",
            "external communication readiness",
            "general web/feed intake",
            "agent-to-agent packet exchange",
            "live metadata ingest",
            "phase acceleration planning",
            "phase ecology lab diagnostics",
            "verify evidence/routes",
            "promote packets",
            "run/store loop",
            "inspect Psi/SQOT",
            "collective certify",
            "ALT abstraction-liquidity foundry admission",
            "preserve residuals/provenance",
        ],
        "safe_cli_entrypoints": [
            "python -m pip install percolation-inversion-compiler",
            "pic agent explain",
            'pic agent check --text "Candidate packet: preserve residuals." --profile development',
            (
                'pic phase plan --compact --text "Candidate packet: preserve residuals." '
                "--profile development"
            ),
            (
                'pic agent accelerate --compact --text "Candidate packet: preserve residuals." '
                "--profile development"
            ),
            "pic demo installed-smoke --profile development",
            "pic demo bootstrap --output-dir pic-demo",
            (
                "pic runtime step --state pic-demo/runtime_state.json "
                "--input pic-demo/runtime_step_input.json --profile development"
            ),
            'pic agent intake --text "Candidate packet: preserve residuals." --profile development',
            (
                "uv run pic agent intake --text-file "
                "examples/cli_agent_output_check/agent_output.txt --profile development "
                "--output cli-agent-output-report.json"
            ),
            "uv run python examples/python_sdk_agent_output_check/check_agent_output.py",
            "pic snapshot list",
            "pic schema --type AgentIntakeReport",
            "pic schema --type PhaseAccelerationPlan",
            "pic schema --type PhaseAccelerationBenchmarkReport",
            "pic agent autonomy-audit --profile development --format json",
            "pic adoption request --format markdown",
            "pic adoption packet --format markdown",
            "pic phase benchmark-suite --profile development --format json",
            "pic phase dashboard --profile development --format json",
            "pic phase lab init --output-dir pic-demo/phase-lab",
            "pic phase lab ingest --store pic-demo/phase-lab "
            "--report pic-demo/phase_lab_runtime_report.json",
            "pic phase lab observe --store pic-demo/phase-lab --window latest",
            "pic phase lab graph --store pic-demo/phase-lab",
            "pic phase lab closure --store pic-demo/phase-lab",
            "pic phase lab executable-paths --store pic-demo/phase-lab",
            "pic phase lab certify --store pic-demo/phase-lab "
            "--threshold pic-demo/phase_lab_threshold.json",
            "pic audit canonical-readiness --profile development --format json",
            "pic schema --type OperatorAdoptionPacket",
            "pic schema --type CanonicalImplementationReadinessReport",
            "pic schema --type PacketExchangeEnvelope",
            "pic schema --type PhaseDashboardReport",
            "uv run pic --help",
            "uv run pic agent explain",
            _CMD_AGENT_COMM_GUIDE_DEV,
            _CMD_AGENT_NETWORK_DEV,
            _CMD_INGEST_FEED,
            _CMD_INGEST_PAGE,
            "uv run pic ecology policy explain --profile controlled_web",
            "uv run pic ecology bridge-runtime --report general-intake-report.json",
            "uv run pic alt admit --packet examples/alt/admission_packet.json",
            "uv run pic ecology effective-graph --reports examples/phase_lab/runtime_report_1.json",
            "uv run pic bit diagnose --graph examples/phase_lab/effective_graph.example.json",
            "uv run pic sqot diagnose-queue --graph "
            "examples/phase_lab/effective_graph.example.json",
            "uv run pic trc trace-adapter --input "
            "examples/trc_adapter/tool_trace_input.example.json",
            _CMD_ALT_NEGATIVE,
            _CMD_ALT_REFRESH_BASELINE,
            _CMD_ALT_CHECK_CARA,
            "uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json",
            "uv run pic agent message contract --message examples/agent_network/agent_message.json",
            _CMD_AGENT_MESSAGE_INGEST,
            "uv run pic agent relay-readiness --profile development",
            (
                "uv run pic agent message send --inbox inbox.json --sender agent:alice "
                '--text "Candidate packet: preserve residuals."'
            ),
            "uv run pic agent message receive --inbox inbox.json",
            "uv run pic schema --type IntakeProvenanceRecord",
            "uv run pic runtime health --state examples/runtime_state.json --profile development",
            (
                "uv run pic runtime step --state examples/runtime_state.json "
                "--input examples/runtime_step_input.json --profile development"
            ),
            "uv run pic identity explain-profile --profile research",
            (
                "uv run pic identity derive-context --population "
                "examples/agent_population_signed.json --profile production "
                "--output identity-context.json"
            ),
        ],
        "version": __version__,
    }


def agent_safety_invariants() -> list[str]:
    """Return safety invariants every agent-facing report should carry."""

    return [
        "settled=false is expected unless scoped finite verifier rules settle obligations",
        "residual ledgers and missing obligations must be preserved",
        "this package does not prove real ASI, physical, simulator, oracle, or policy outcomes",
        "this package does not require self-rewrite, fine-tuning, or model-weight changes",
        "agent-facing commands are recommendation-only and do not execute arbitrary shell commands",
        "production packet promotion requires accepted identity context",
        live_default_safety_invariant(),
        *live_default_non_authorities(),
        "external metadata packets remain candidates until downstream checks pass",
        "candidate-only external intake cannot improve Psi, BR, AC, or collective certificates",
        "general web intake is bounded and does not execute scripts, forms, or repo mutation",
        "agent-to-agent messages are packet candidates, not proof of external-world truth",
    ]


def build_agent_autonomy_audit(profile: str = "development") -> AgentAutonomyAuditReport:
    """Audit whether agents can continue useful work without approval bottlenecks."""

    core_commands = pip_core_commands(profile)
    full_commands = pip_agent_full_commands(profile)
    checkout_commands = source_checkout_commands(profile)
    invocations = [
        _invocation(
            "pip-core-install",
            core_commands[0],
            "Install the bare package when local environment mutation is authorized.",
            requires_operator_authority=True,
            mutates_environment_if_operator_runs_it=True,
        ),
        _invocation(
            "compact-agent-check",
            core_commands[3],
            "Run the shortest compact candidate-output check.",
        ),
        _invocation(
            "compact-phase-plan",
            core_commands[4],
            "Rank phase gaps and bottlenecks without adoption state.",
        ),
        _invocation(
            "compact-agent-accelerate",
            core_commands[5],
            "Build an agent-facing acceleration plan without changing settled semantics.",
        ),
        _invocation(
            "canonical-readiness",
            f"pic audit canonical-readiness --profile {profile} --format json",
            "Inspect canonical implementation coverage from bundled snapshots without TeX files.",
        ),
        _invocation(
            "sidecar-packet-merge",
            "pic packet merge --packets pic-demo/packet_envelope.json "
            "--output pic-demo/merged-packets.json",
            "Merge bootstrapped packet sidecars without shell glob expansion.",
        ),
        _invocation(
            "agent-full-install",
            full_commands[0],
            "Install connector, identity, and service extras when that capability is needed.",
            requires_agent_full_extra=True,
            requires_operator_authority=True,
            mutates_environment_if_operator_runs_it=True,
        ),
    ]
    return AgentAutonomyAuditReport(
        profile=profile,
        pip_core_commands=core_commands,
        pip_agent_full_commands=full_commands,
        source_checkout_commands=checkout_commands,
        recommended_next_invocations=invocations,
        autonomy_enablers=[
            "compact reports keep the first workflow machine-readable",
            "operator adoption sidecars are optional documentation",
            "packet exchange, dashboard, and benchmark sidecars are diagnostic-only",
            "canonical readiness is available from pip through bundled snapshot metadata",
            "argv arrays avoid shell-specific quoting and do not require shell glob expansion",
            "agent-full extra exposes connector, identity, and service dependencies via pip",
        ],
        remaining_friction_points=[
            "installing packages still mutates the selected Python environment",
            "canonical source-file audits and repository fixtures still require a source checkout",
            "production packet promotion still requires accepted protocol-relative "
            "identity context",
        ],
        safety_invariants=[
            *agent_safety_invariants(),
            "adoption approval is not a phase input or settled blocker",
            "safe_commands are not executable authority",
            "PIC does not persist approval state",
        ],
        reasons=[
            "core PIC activity is not gated by operator adoption state",
            "autonomy is increased through portable records and sidecar diagnostics",
        ],
    )


def agent_autonomy_audit_markdown(
    report: AgentAutonomyAuditReport,
    *,
    language: str = "en",
) -> str:
    """Render an autonomy audit as deterministic localized Markdown."""

    if language == "ja":
        lines = [
            "# PIC エージェント自律性監査",
            "",
            f"- Profile: `{report.profile}`",
            f"- adoption_required_for_core: `{str(report.adoption_required_for_core).lower()}`",
            f"- approval_gate_present: `{str(report.approval_gate_present).lower()}`",
            "- safe_commands_executable_by_pic: "
            f"`{str(report.safe_commands_executable_by_pic).lower()}`",
            f"- settled: `{str(report.settled).lower()}`",
            "",
            "## 自律性を上げる要素",
            *[f"- {item}" for item in report.autonomy_enablers],
            "",
            "## 次の argv 呼び出し",
        ]
        for invocation in report.recommended_next_invocations:
            lines.append(f"- `{invocation.invocation_id}`: `{invocation.argv}`")
        lines.extend(
            [
                "",
                "## 安全境界",
                *[f"- {item}" for item in report.safety_invariants],
            ]
        )
        return "\n".join(lines) + "\n"

    lines = [
        "# PIC Agent Autonomy Audit",
        "",
        f"- Profile: `{report.profile}`",
        f"- adoption_required_for_core: `{str(report.adoption_required_for_core).lower()}`",
        f"- approval_gate_present: `{str(report.approval_gate_present).lower()}`",
        "- safe_commands_executable_by_pic: "
        f"`{str(report.safe_commands_executable_by_pic).lower()}`",
        f"- settled: `{str(report.settled).lower()}`",
        "",
        "## Autonomy Enablers",
        *[f"- {item}" for item in report.autonomy_enablers],
        "",
        "## Next argv Invocations",
    ]
    for invocation in report.recommended_next_invocations:
        lines.append(f"- `{invocation.invocation_id}`: `{invocation.argv}`")
    lines.extend(["", "## Safety Boundary"])
    lines.extend(f"- {item}" for item in report.safety_invariants)
    return "\n".join(lines) + "\n"


def _communication_policy(
    profile: str,
    allow_live_connectors: bool,
) -> AgentCommunicationPolicy:
    required_env_vars: list[str] = []
    if profile.lower() == "production":
        required_env_vars.append("PIC_RUNTIME_TOKEN")
    return AgentCommunicationPolicy(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        required_env_vars=required_env_vars,
    )


def build_agent_communication_guide(
    profile: str = "development",
    allow_live_connectors: bool = default_allow_live_connectors(),
) -> AgentCommunicationGuide:
    """Build a deterministic guide for bounded external communication workflows."""

    policy = _communication_policy(profile, allow_live_connectors)
    live_flag = "--allow-live-connectors" if allow_live_connectors else "--no-allow-live-connectors"
    steps = [
        AgentCommunicationStep(
            step_id="01-local-only-baseline",
            title="Local-Only Baseline",
            purpose="Run agent intake and runtime health with no network access.",
            safe_commands=[
                "uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt "
                f"--profile {profile}",
                (
                    f"uv run pic agent network-readiness --profile {profile} "
                    "--no-allow-live-connectors"
                ),
            ],
            schemas=["AgentIntakeReport", "AgentNetworkReadinessReport"],
            inspect_fields=["settled", "residual_summary", "readiness.live_metadata_ingest"],
            failure_modes=["missing local files", "diagnostic residuals"],
            residual_behavior="local diagnostics remain explicit residuals",
            safety_notes=["Use --no-allow-live-connectors when a local-only dry run is required."],
        ),
        AgentCommunicationStep(
            step_id="02-token-env-readiness",
            title="Token And Environment Readiness",
            purpose="Check optional connector and service auth readiness without network calls.",
            required_env_vars=[*policy.required_env_vars, "GITHUB_TOKEN"],
            safe_commands=[f"uv run pic agent network-readiness --profile {profile} {live_flag}"],
            schemas=["AgentNetworkReadinessReport", "RuntimeServiceSettings"],
            inspect_fields=["connector_dependency_present", "github_token_present"],
            failure_modes=["missing httpx extra", "missing token", "token kept out of output"],
            residual_behavior="missing optional dependency or token is diagnostic, not settled",
            safety_notes=["Tokens are environment-only and must not be stored in repo outputs."],
        ),
        AgentCommunicationStep(
            step_id="03-general-web-feed-intake",
            title="General Web And Feed Intake",
            purpose="Ingest bounded HTTP(S), local HTML, RSS/Atom, JSON feed, or NDJSON sources.",
            allowed_source_kinds=[
                "http",
                "web-page",
                "rss",
                "atom",
                "json-feed",
                "ndjson",
                "web-crawl",
            ],
            safe_commands=[
                f"uv run pic ecology policy explain --profile {profile}",
                _CMD_INGEST_FEED,
                _CMD_INGEST_PAGE,
                _CMD_DISCOVER_PAGE,
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.ecology.ingest_general_source",
                "percolation_inversion_compiler.ecology.discover_web_packets",
            ],
            schemas=[
                "GeneralIntakePolicy",
                "GeneralIntakePolicyDecision",
                "GeneralIntakeReport",
                "IntakeProvenanceRecord",
                "WebDiscoveryReport",
                "GeneralIntakeRuntimeBridgeReport",
            ],
            inspect_fields=[
                "accepted",
                "packets",
                "provenance",
                "web_fetch_reports",
                "source_policy_decisions",
                "candidate_residual_coordinates",
                "ecpt_phase_contribution_allowed",
                "rejected_sources",
                "residual_ledger",
            ],
            failure_modes=[
                "private network target",
                "oversized response",
                "unsupported content type",
                "robots or rate uncertainty",
            ],
            residual_behavior="web/feed intake failures return diagnostic residuals",
            safety_notes=[
                "General web intake never executes scripts or submits forms.",
                "Live HTTP(S) requires an explicit source and remains bounded.",
                "External candidate volume alone cannot improve accepted ECPT phase status.",
            ],
        ),
        AgentCommunicationStep(
            step_id="04-agent-message-exchange",
            title="Agent Message Exchange",
            purpose="Exchange local agent messages without status promotion.",
            allowed_source_kinds=["agent-message", "agent-inbox"],
            safe_commands=[
                _CMD_AGENT_MESSAGE_CONTRACT,
                _CMD_AGENT_MESSAGE_INGEST,
                _CMD_AGENT_INBOX_EXPORT,
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.ecology.verify_agent_message",
                "percolation_inversion_compiler.ecology.ingest_agent_inbox",
            ],
            schemas=[
                "AgentMessageEnvelope",
                "AgentMessageContractReport",
                "AgentMessageVerificationContext",
                "AgentInboxRecord",
                "AgentPacketExchangeReport",
            ],
            inspect_fields=[
                "message_contract_valid",
                "accepted",
                "identity_verified",
                "identity_status",
                "nonce_ledger",
                "nonce_status",
                "signature_required",
                "replay_detected",
                "residual_ledger",
            ],
            failure_modes=[
                "digest mismatch",
                "expired message",
                "future clock skew",
                "replay nonce",
                "missing production signature",
                "missing accepted identity context",
            ],
            residual_behavior="invalid or unsigned messages remain diagnostic candidates",
            safety_notes=["Agent messages do not settle obligations."],
        ),
        AgentCommunicationStep(
            step_id="05-live-metadata-ingest",
            title="Live Metadata Ingest",
            purpose=(
                "Ingest GitHub, Zenodo, or arXiv metadata packet candidates when sources "
                "are explicit."
            ),
            allowed_source_kinds=policy.allowed_source_kinds,
            safe_commands=[
                _CMD_GITHUB_INGEST,
                _CMD_ZENODO_INGEST,
                "uv run pic ecology ingest --source arxiv:salience queue --kind arxiv",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.ingest_live_source"],
            schemas=["PacketIngestionReport", "CapabilityPacketCandidate"],
            inspect_fields=["accepted", "packets", "rejected_sources", "residual_ledger"],
            failure_modes=["rate limit", "auth failure", "network error", "malformed response"],
            residual_behavior="connector failures return diagnostic PacketIngestionReport records",
            safety_notes=["Live metadata packets are candidates, not verified packet capital."],
        ),
        AgentCommunicationStep(
            step_id="06-evidence-envelope-verify",
            title="Evidence Envelope Verify",
            purpose="Verify evidence envelope hashes, schema digests, identities, and determinism.",
            safe_commands=[
                "uv run pic evidence verify --envelope examples/evidence_envelope.json",
                _CMD_EVIDENCE_VERIFY_PROD,
            ],
            sdk_entrypoints=["percolation_inversion_compiler.core.verify_evidence_envelope"],
            schemas=["VerifierEvidenceEnvelope", "EvidenceArtifact"],
            inspect_fields=["accepted", "settled", "residual_ledger", "reasons"],
            failure_modes=[
                "sha256 mismatch",
                "schema digest mismatch",
                "missing verifier identity",
            ],
            residual_behavior="invalid evidence remains diagnostic and cannot promote status",
            safety_notes=["Evidence verification does not prove external physical/oracle truth."],
        ),
        AgentCommunicationStep(
            step_id="07-route-discharge",
            title="Route Discharge",
            purpose="Route external proof obligations through registered verifier bindings.",
            safe_commands=[
                "uv run pic routes bindings",
                "uv run pic evidence discharge --envelope examples/evidence_envelope.json "
                "--obligations examples/external_obligations.json --profile production",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.core.resolve_adapter_route"],
            schemas=["DischargeRouteBinding", "VerifierResolution"],
            inspect_fields=["settled_scope", "residual_external_obligations", "settled"],
            failure_modes=[
                "missing evidence kind",
                "unsupported route",
                "residual external domain",
            ],
            residual_behavior="route residuals remain until scoped obligations are discharged",
            safety_notes=["Route acceptance is scoped; unresolved external obligations remain."],
        ),
        AgentCommunicationStep(
            step_id="08-runtime-service-loopback",
            title="Runtime Service Loopback",
            purpose="Use the local HTTP service with loopback and production bearer auth.",
            required_env_vars=["PIC_RUNTIME_TOKEN"],
            safe_commands=[
                "uv run pic runtime export-openapi --output openapi.json",
                "uv run pic runtime service --host 127.0.0.1 --port 8765 --profile development",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.runtime.create_runtime_app"],
            schemas=["RuntimeServiceSettings", "RuntimeStepInput", "RuntimeStepReport"],
            inspect_fields=["allow_live_connectors", "safety_invariants"],
            failure_modes=["missing server extra", "missing bearer token", "oversized request"],
            residual_behavior="service errors return deterministic diagnostic JSON",
            safety_notes=["Keep service local-first; production requires bearer auth."],
        ),
        AgentCommunicationStep(
            step_id="09-store-provenance",
            title="Store And Provenance",
            purpose="Persist runtime events and provenance for later audit.",
            safe_commands=[
                "uv run pic runtime store init --store runtime.sqlite",
                "uv run pic schema --all --output-dir schemas/generated",
                _CMD_PROVENANCE_CREATE,
            ],
            schemas=["RuntimeStoreSnapshot", "ProvenanceManifest"],
            inspect_fields=["event_log", "schema-digest", "provenance"],
            failure_modes=["missing schema bundle", "modified artifact", "local path leak"],
            residual_behavior="provenance does not settle unresolved obligations",
            safety_notes=["Do not persist secrets or private keys."],
        ),
        AgentCommunicationStep(
            step_id="10-residual-carry-forward",
            title="Residual Carry-Forward",
            purpose="Carry unresolved external communication residuals into the next runtime step.",
            safe_commands=[
                "uv run pic agent next --intake-report intake-report.json --profile production"
            ],
            schemas=["AgentNextActionReport", "LedgerCoordinate"],
            inspect_fields=["residual_summary", "missing_obligations", "next_commands"],
            failure_modes=["dropped residual", "misread settled=false as failure"],
            residual_behavior="residual coordinates are output obligations, not errors to suppress",
            safety_notes=["Never hide connector or route residuals."],
        ),
    ]
    return AgentCommunicationGuide(
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        policy=policy,
        steps=steps,
        safety_invariants=agent_safety_invariants(),
        accepted=True,
        operationally_usable=allow_live_connectors,
        settled=False,
    )


def build_agent_workflow_guide(profile: str = "development") -> AgentWorkflowGuide:
    """Build a deterministic full-feature workflow guide for autonomous agents."""

    steps = [
        AgentWorkflowStep(
            step_id="01-orient",
            title="Orient",
            purpose="Understand repository purpose, non-goals, and safety boundary.",
            safe_commands=["uv run pic agent explain", "uv run pic agent manifest"],
            sdk_entrypoints=["percolation_inversion_compiler.agent.agent_manifest_payload"],
            schemas=["AgentWorkflowGuide"],
            inspect_fields=["what_it_does_not_do", "machine_contract"],
            safety_notes=["Do not claim real ASI or self-rewrite."],
        ),
        AgentWorkflowStep(
            step_id="02-inspect-snapshots",
            title="Inspect Snapshots",
            purpose="Inspect bundled theory snapshots and verifier routes without canonical TeX.",
            safe_commands=[
                "uv run pic snapshot list",
                "uv run pic snapshot show --artifact ecpt",
                "uv run pic snapshot routes",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.io.list_theory_snapshots"],
            schemas=["TheorySnapshot", "AdapterRouteSpec"],
            inspect_fields=["coverage_counts", "external_category_summary", "route_id"],
            safety_notes=["Snapshots are metadata, not evidence."],
        ),
        AgentWorkflowStep(
            step_id="03-run-intake",
            title="Run Intake",
            purpose="Convert agent output into a deterministic runtime step report.",
            safe_commands=[
                'uv run pic agent intake --text "Candidate packet: preserve residuals." '
                f"--profile {profile}"
            ],
            sdk_entrypoints=["percolation_inversion_compiler.agent.run_agent_intake"],
            schemas=["AgentIntakeRequest", "AgentIntakeReport", "RuntimeStepReport"],
            inspect_fields=["residual_summary", "runtime_report.missing_obligations"],
            safety_notes=["Intake recommendations do not settle obligations."],
        ),
        AgentWorkflowStep(
            step_id="04-derive-identity-context",
            title="Derive Identity Context",
            purpose="Derive accepted agent/key context when production packet promotion matters.",
            safe_commands=[
                "uv run pic identity explain-profile --profile production",
                "uv run pic identity derive-context --population "
                "examples/agent_population_signed.json --profile production "
                "--output identity-context.json",
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.runtime.derive_runtime_identity_context"
            ],
            schemas=["RuntimeIdentityContext", "SybilResistanceLedger"],
            inspect_fields=["accepted_agent_ids", "accepted_public_key_ids", "accepted"],
            safety_notes=["Cryptographic identity proves protocol-relative key control only."],
        ),
        AgentWorkflowStep(
            step_id="05-external-communication-readiness",
            title="External Communication Readiness",
            purpose="Check live connector and service readiness before any external communication.",
            safe_commands=[
                f"uv run pic agent communication-guide --profile {profile}",
                f"uv run pic agent network-readiness --profile {profile}",
                f"uv run pic agent communication-guide --profile {profile} "
                "--no-allow-live-connectors",
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.agent.build_agent_communication_guide",
                "percolation_inversion_compiler.agent.agent_network_readiness",
            ],
            schemas=["AgentCommunicationGuide", "AgentNetworkReadinessReport"],
            inspect_fields=["allow_live_connectors", "readiness", "failure_modes"],
            safety_notes=[
                "Default-live mode is bounded and candidate-only for explicit sources.",
                "Use --no-allow-live-connectors for local-only dry runs.",
            ],
        ),
        AgentWorkflowStep(
            step_id="06-general-web-feed-intake",
            title="General Web And Feed Intake",
            purpose="Optionally ingest bounded web, RSS/Atom, JSON feed, or NDJSON sources.",
            safe_commands=[
                "uv run pic ecology policy explain --profile controlled_web",
                _CMD_INGEST_FEED,
                _CMD_INGEST_PAGE,
                _CMD_DISCOVER_PAGE,
                "uv run pic ecology bridge-runtime --report general-intake-report.json",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.ingest_general_source"],
            schemas=[
                "GeneralIntakeReport",
                "WebDiscoveryReport",
                "GeneralIntakePolicy",
                "IntakeProvenanceRecord",
                "GeneralIntakeRuntimeBridgeReport",
            ],
            inspect_fields=[
                "accepted",
                "packets",
                "provenance",
                "web_fetch_reports",
                "rejected_sources",
                "residual_ledger",
            ],
            safety_notes=[
                "General web intake is bounded and does not execute page code.",
                "Live HTTP(S) requires an explicit source and remains candidate-only.",
            ],
        ),
        AgentWorkflowStep(
            step_id="07-agent-to-agent-exchange",
            title="Agent-To-Agent Packet Exchange",
            purpose="Ingest local agent messages or inboxes as candidate packets.",
            safe_commands=[
                _CMD_AGENT_MESSAGE_CONTRACT,
                _CMD_AGENT_MESSAGE_INGEST,
                _CMD_AGENT_INBOX_EXPORT,
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.verify_agent_message"],
            schemas=[
                "AgentMessageEnvelope",
                "AgentMessageContractReport",
                "AgentMessageVerificationContext",
                "AgentInboxRecord",
                "AgentPacketExchangeReport",
            ],
            inspect_fields=[
                "identity_verified",
                "nonce_ledger",
                "signature_required",
                "replay_detected",
                "residual_ledger",
            ],
            safety_notes=["Agent messages are candidate inputs and do not settle obligations."],
        ),
        AgentWorkflowStep(
            step_id="08-live-metadata-ingest",
            title="Live Metadata Ingest",
            purpose="Optionally ingest GitHub, Zenodo, or arXiv metadata as packet candidates.",
            safe_commands=[
                _CMD_GITHUB_INGEST,
                _CMD_ZENODO_INGEST,
                "uv run pic ecology ingest --source arxiv:salience queue --kind arxiv",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.ingest_live_source"],
            schemas=["PacketIngestionReport", "CapabilityPacketCandidate"],
            inspect_fields=["accepted", "packets", "rejected_sources", "residual_ledger"],
            safety_notes=["Live metadata packets are candidates, not verified packet capital."],
        ),
        AgentWorkflowStep(
            step_id="09-verify-evidence-routes",
            title="Verify Evidence And Routes",
            purpose="Inspect route requests and verify finite evidence envelopes where available.",
            safe_commands=[
                "uv run pic routes bindings",
                "uv run pic evidence verify --envelope examples/evidence_envelope.json",
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.core.resolve_adapter_route",
                "percolation_inversion_compiler.runtime.resolve_step_evidence",
            ],
            schemas=["VerifierEvidenceEnvelope", "VerifierResolution"],
            inspect_fields=["route_execution_requests", "evidence_resolution_batch"],
            safety_notes=["Unresolved routes remain residual obligations."],
        ),
        AgentWorkflowStep(
            step_id="10-promote-packets",
            title="Promote Packets",
            purpose="Use verifier results, edge certificates, rollback, and identity context.",
            safe_commands=[
                "uv run pic agent next --intake-report intake-report.json --profile production"
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.promote_packet_candidate"],
            schemas=["PacketPromotionReport", "VerifiedCapabilityPacket"],
            inspect_fields=["promotion_report", "identity_contribution_summary"],
            safety_notes=["Provisional packets are not verified packet capital."],
        ),
        AgentWorkflowStep(
            step_id="11-run-store-loop",
            title="Run And Store Loop",
            purpose="Persist runtime state, event logs, route batches, and residual ledgers.",
            safe_commands=[
                "uv run pic runtime store init --store runtime.sqlite",
                "uv run pic runtime run-agent-loop --state examples/runtime_state.json "
                "--inputs examples/runtime_loop_inputs.jsonl --store runtime.sqlite "
                "--policy examples/runtime_executor_policy.json --profile development",
            ],
            sdk_entrypoints=["percolation_inversion_compiler.runtime.run_agent_loop_with_store"],
            schemas=["RuntimeStoreSnapshot", "RuntimeRunReport"],
            inspect_fields=["event_log", "verified_packets", "quarantine_ledger"],
            safety_notes=["Executor policies must remain allowlist-based."],
        ),
        AgentWorkflowStep(
            step_id="12-inspect-psi-sqot",
            title="Inspect Psi And SQOT",
            purpose="Find limiting collective-phase components and queue obstructions.",
            safe_commands=[
                "uv run pic ecology psi --registry examples/collective_packet_registry.json "
                "--threshold examples/ecology_threshold.json"
            ],
            sdk_entrypoints=["percolation_inversion_compiler.ecology.build_psi_dashboard"],
            schemas=["PsiDashboard", "SalienceScheduleReport"],
            inspect_fields=["limiting_components", "distance_to_threshold", "salience_schedule"],
            safety_notes=["Psi is a protocol-relative finite proxy dashboard."],
        ),
        AgentWorkflowStep(
            step_id="13-collective-certify",
            title="Collective Certify",
            purpose="Check fixed population, no self-rewrite, no hidden injection, and baseline.",
            safe_commands=[
                "uv run pic runtime collective-certify --population examples/agent_population.json "
                "--state examples/collective_runtime_state.json --basin "
                "examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json "
                "--threshold examples/runtime_threshold.json"
            ],
            sdk_entrypoints=["percolation_inversion_compiler.runtime.certify_collective_phase"],
            schemas=["CollectivePhaseCertificate"],
            inspect_fields=["accepted", "settled", "reasons", "residual_ledger"],
            safety_notes=["Accepted finite certificates do not prove real ASI."],
        ),
        AgentWorkflowStep(
            step_id="14-preserve-residuals-provenance",
            title="Preserve Residuals And Provenance",
            purpose="Keep unresolved obligations visible and preserve reproducibility metadata.",
            safe_commands=[
                "uv run pic schema --all --output-dir schemas/generated",
                (
                    "uv run pic provenance create --schema-dir schemas/generated "
                    "--output provenance.json"
                ),
            ],
            sdk_entrypoints=[
                "percolation_inversion_compiler.io.schema_bundle",
                "percolation_inversion_compiler.io.create_provenance_manifest",
            ],
            schemas=["ProvenanceManifest", "SchemaBundleDigest"],
            inspect_fields=["residual_ledger", "schema-digest", "provenance"],
            safety_notes=["Residual preservation is part of the output contract."],
        ),
    ]
    return AgentWorkflowGuide(
        profile=profile,
        steps=steps,
        pip_core_commands=pip_core_commands(profile),
        pip_agent_full_commands=pip_agent_full_commands(profile),
        source_checkout_commands=source_checkout_commands(profile),
        safety_invariants=agent_safety_invariants(),
    )


def agent_check_schema_refs() -> list[str]:
    """Return compact practical schemas that first-time agents should inspect."""

    return [
        "AgentCheckReport",
        "AgentIntakeReport",
        "RuntimeStepReport",
        "PhaseControlAuditSummary",
        "FrontierDebtReport",
        "BottleneckWitnessReport",
        "SalienceScheduleReport",
        "ALTAdmissionDecision",
        "PhaseAccelerationPlan",
        "PhaseGapVector",
        "BottleneckCandidate",
        "SafePhaseAction",
        "AgentCommandInvocation",
        "AgentAutonomyAuditReport",
        "CanonicalImplementationReadinessReport",
    ]


def agent_runbook_steps(profile: str = "development") -> list[str]:
    """Return deterministic practical steps without granting execution authority."""

    return [
        "Run pic agent check --compact on candidate agent output.",
        "Read accepted, workflow_usable, settled, unresolved_obligations, and residual_summary.",
        "Inspect next_safe_actions before promoting any reusable work item.",
        (
            "Read RuntimeStepReport phase_control_audit, frontier_debt_report, "
            "and bottleneck_witness_reports when theory fidelity matters."
        ),
        "Use production identity context before production packet promotion.",
        "Run pic phase plan --compact when an agent needs ranked finite bottlenecks.",
        f"Use profile={profile} consistently across intake, runtime, and readiness commands.",
    ]


def build_agent_runbook(profile: str = "development") -> AgentRunbookReport:
    """Build compact command/schema/field guidance for first-time agents."""

    return AgentRunbookReport(
        profile=profile,
        commands=[
            'pic agent check --compact --text "Candidate packet: preserve residuals."',
            f"pic agent autonomy-audit --profile {profile} --format json",
            f"pic audit canonical-readiness --profile {profile} --format json",
            f"pic agent runbook --profile {profile}",
            "pic schema --type AgentCheckReport",
            "pic schema --type AgentAutonomyAuditReport",
            "pic schema --type CanonicalImplementationReadinessReport",
            "pic schema --type RuntimeStepReport",
            "pic schema --type PhaseAccelerationPlan",
            f"pic phase plan --compact --profile {profile}",
            "pic agent readiness --profile production",
        ],
        pip_core_commands=pip_core_commands(profile),
        pip_agent_full_commands=pip_agent_full_commands(profile),
        source_checkout_commands=source_checkout_commands(profile),
        schemas_to_inspect=agent_check_schema_refs(),
        fields_to_inspect=[
            "accepted",
            "workflow_usable",
            "settled",
            "unresolved_obligations",
            "residual_summary",
            "next_safe_actions",
            "intake_report.runtime_report.phase_control_audit",
            "intake_report.runtime_report.frontier_debt_report",
            "intake_report.runtime_report.bottleneck_witness_reports",
            "phase_gap_vector.limiting_components",
            "cannot_promote_because",
            "candidate_only_reasons",
        ],
        runbook_steps=agent_runbook_steps(profile),
        safety_invariants=agent_safety_invariants(),
        accepted=True,
        operationally_usable=True,
        settled=False,
    )


def agent_network_readiness(
    state: RuntimeState | None = None,
    profile: str = "development",
    allow_live_connectors: bool = default_allow_live_connectors(),
) -> AgentNetworkReadinessReport:
    """Summarize network readiness without making network calls."""

    active_state = state or minimal_runtime_state()
    del active_state
    profile_lower = profile.lower()
    connector_dependency_present = importlib.util.find_spec("httpx") is not None
    github_token_present = bool(os.environ.get("GITHUB_TOKEN"))
    runtime_token_present = bool(os.environ.get("PIC_RUNTIME_TOKEN"))
    readiness = {
        "live_metadata_ingest": "ready" if allow_live_connectors else "disabled",
        "general_http_intake": "ready" if allow_live_connectors else "disabled",
        "rss_atom_feed_intake": "ready" if allow_live_connectors else "local-fixtures-only",
        "json_ndjson_intake": "ready",
        "bounded_web_discovery": "ready" if allow_live_connectors else "local-fixtures-only",
        "agent_message_inbox": "ready",
        "agent_relay_loopback": (
            "ready" if profile_lower != "production" or runtime_token_present else "diagnostic"
        ),
        "connector_dependency": "ready" if connector_dependency_present else "diagnostic",
        "github_token": "ready" if github_token_present else "optional",
        "runtime_service_auth": (
            "ready" if profile_lower != "production" or runtime_token_present else "diagnostic"
        ),
        "route_discharge": "ready",
        "evidence_envelope_verify": "ready",
        "residual_carry_forward": "ready",
    }
    reasons: list[str] = []
    if not allow_live_connectors:
        reasons.append("live connectors disabled by explicit opt-out")
    if not connector_dependency_present:
        reasons.append("optional connector dependency httpx is not installed")
    if profile_lower == "production" and not runtime_token_present:
        reasons.append("production runtime service requires PIC_RUNTIME_TOKEN")
    commands = [
        f"uv run pic agent communication-guide --profile {profile} "
        f"{'--allow-live-connectors' if allow_live_connectors else '--no-allow-live-connectors'}",
        "uv run pic routes bindings",
        "uv run pic evidence verify --envelope examples/evidence_envelope.json",
        "uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss",
        "uv run pic agent message ingest --message examples/agent_network/agent_message.json",
    ]
    if allow_live_connectors:
        commands.extend(
            [
                _CMD_LIVE_WEB_INGEST,
                _CMD_LIVE_WEB_DISCOVER,
                _CMD_GITHUB_INGEST,
                _CMD_ZENODO_INGEST,
                "uv run pic ecology ingest --source arxiv:salience queue --kind arxiv",
            ]
        )
    return AgentNetworkReadinessReport(
        report_id=f"agent-network-readiness:{profile}:{str(allow_live_connectors).lower()}",
        profile=profile,
        allow_live_connectors=allow_live_connectors,
        opt_out_available=True,
        bounded_candidate_intake=True,
        connector_dependency_present=connector_dependency_present,
        github_token_present=github_token_present,
        runtime_token_present=runtime_token_present,
        allowed_source_kinds=[
            "github",
            "zenodo",
            "arxiv",
            "http",
            "web-page",
            "rss",
            "atom",
            "json-feed",
            "ndjson",
            "agent-message",
            "agent-inbox",
            "web-crawl",
        ],
        readiness=readiness,
        recommended_next_commands=commands,
        failure_modes=[
            "missing optional connector dependency",
            "network rate limit",
            "authentication failure",
            "malformed connector response",
            "unsupported source kind",
            "private network target rejected",
            "source/request/policy/runtime opt-in mismatch",
            "missing explicit source for live intake",
            "unsupported content type",
            "oversized response",
            "robots uncertainty",
            "expired agent message",
            "future-skewed agent message",
            "agent message replay nonce",
            "missing production message signature",
            "missing accepted identity context",
        ],
        safety_invariants=agent_safety_invariants(),
        accepted=True,
        operationally_usable=allow_live_connectors and connector_dependency_present,
        settled=False,
        reasons=reasons,
    )


def minimal_runtime_state() -> RuntimeState:
    """Construct a deterministic minimal runtime state without reading example files."""

    route = "adapters.domain.verify_ecpt_proxy_target_contract"
    return RuntimeState(
        state_id="agent-minimal-runtime",
        phase_state=PhaseControlState(
            state_id="agent-minimal-phase-state",
            graph=CapabilityHypergraph(
                nodes={"compute", "models"},
                edges=[
                    CapabilityEdge(
                        edge_id="agent-minimal-model-stack",
                        sources=("compute",),
                        target="models",
                        activation_weight=0.7,
                        burden=0.05,
                    )
                ],
                seed_mass={"compute": 1.0},
            ),
            state_vector=CapabilityStateVector(
                packets=[
                    CapabilityPacket(
                        packet_id="agent-minimal-compute-seed",
                        coordinates={"compute": 1.0},
                        validity_domain="agent-minimal",
                    )
                ],
                validity_domain="agent-minimal",
            ),
            present_obligations=["obligation:baseline-safety"],
            route_ids=[route],
            budgets={"compute": 1.0},
        ),
        phase_objective=PhaseControlObjective(
            objective_id="agent-minimal-objective",
            target=ASIProxyTargetContract(
                target_id="agent-minimal-asi-proxy-target",
                target_nodes=["phase-transition-proxy"],
                minimum_proxy_mass=0.05,
                proxy_coordinates={"phase-transition-proxy": 1.0},
                required_obligations=["obligation:baseline-safety"],
            ),
            horizon=2,
            residual_budget=0.5,
            risk_tolerance=0.4,
            route_preferences=[route],
        ),
        phase_actions=[
            PhaseControlAction(
                action_id="agent-minimal-route-proxy-target-evidence",
                source_nodes=["compute", "models"],
                target_node="phase-transition-proxy",
                activation_delta=0.8,
                burden_delta=0.1,
                residual_charge=0.02,
                risk_charge=0.03,
                resource_cost={"compute": 0.2},
                verifier_routes=[route],
                required_obligations=["obligation:baseline-safety"],
                preconditions=["compute", "models"],
                postconditions=["proxy-frontier-observed"],
            )
        ],
        psi_threshold={"BR": 0.1, "G": 0.7, "VT": 0.7},
    )


def minimal_runtime_step_input(agent_output: str | None = None) -> RuntimeStepInput:
    """Construct a deterministic minimal runtime step input."""

    text = agent_output or (
        "ECPT runtime packet: preserve residual ledgers and route missing verifier work."
    )
    return RuntimeStepInput(
        input_id="agent-intake-step",
        agent_output=text,
        packets=[
            CapabilityPacketCandidate(
                packet_id="packet:agent-intake",
                claim=text,
                source_kind=PacketSourceKind.AGENT_OUTPUT,
                source_ref="agent-intake",
                content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                receiver_family=["agent", "verifier"],
                tags=["ecpt", "phase"],
                expected_downstream_gain=0.2,
                verification_cost=0.1,
                verifier_routes=["adapters.domain.verify_ecpt_proxy_target_contract"],
                rollback_available=False,
            )
        ],
        allow_live_connectors=default_allow_live_connectors(),
    )


def _with_identity_context(
    state: RuntimeState, identity_context: RuntimeIdentityContext | None
) -> RuntimeState:
    if identity_context is None:
        return state
    return state.model_copy(
        update={
            "accepted_agent_ids": list(identity_context.accepted_agent_ids),
            "accepted_public_key_ids": list(identity_context.accepted_public_key_ids),
            "identity_mode": identity_context.identity_profile.value,
        }
    )


def _residual_summary(runtime_report: object) -> dict[str, float]:
    residual_ledger = getattr(runtime_report, "residual_ledger", None)
    raw_coordinates = getattr(residual_ledger, "coordinates", [])
    coordinates = raw_coordinates.values() if isinstance(raw_coordinates, dict) else raw_coordinates
    summary: dict[str, float] = {}
    for coordinate in coordinates:
        raw_kind = getattr(coordinate, "kind", "residual")
        kind = getattr(raw_kind, "value", str(raw_kind))
        summary[kind] = summary.get(kind, 0.0) + float(getattr(coordinate, "value", 0.0))
    return dict(sorted(summary.items()))


def _agent_check_glossary() -> dict[str, str]:
    return {
        "accepted": "The finite checker accepted the report shape and safe routing record.",
        "capability_packet": "A checked reusable work item candidate.",
        "operationally_usable": "The report can be used for stricter operational promotion.",
        "residual_ledger": "Explicit unresolved-work ledger; residuals are not hidden failures.",
        "settled": "All scoped verifier obligations are discharged. This usually remains false.",
        "workflow_usable": (
            "The report is useful for the next verification step even when unresolved "
            "obligations keep settled=false."
        ),
    }


def _unresolved_obligations_from_runtime_report(runtime_report: object) -> list[str]:
    obligations = list(getattr(runtime_report, "missing_obligations", []))
    for request in getattr(runtime_report, "route_execution_requests", []):
        obligations.extend(getattr(request, "residual_external_obligations", []))
        obligations.extend(getattr(request, "obligation_ids", []))
    return sorted(set(str(item) for item in obligations if item))


def _checked_outputs_from_runtime_report(runtime_report: object) -> dict[str, str]:
    route_requests = getattr(runtime_report, "route_execution_requests", [])
    agent_tasks = getattr(runtime_report, "agent_tasks", [])
    promotion_report = getattr(runtime_report, "promotion_report", None)
    salience_schedule = getattr(runtime_report, "salience_schedule", None)
    return {
        "agent_tasks": "present" if agent_tasks else "none",
        "input": "accepted" if getattr(runtime_report, "accepted", False) else "diagnostic",
        "promotion": (
            "accepted"
            if promotion_report is not None and getattr(promotion_report, "accepted", False)
            else "diagnostic"
        ),
        "residual_ledger": "preserved",
        "route_requests": "present" if route_requests else "none",
        "salience_schedule": (
            "accepted"
            if salience_schedule is not None and getattr(salience_schedule, "accepted", False)
            else "diagnostic"
        ),
    }


def _recommended_next_commands(request: AgentIntakeRequest, runtime_report: object) -> list[str]:
    commands = [
        "Inspect runtime_report.residual_ledger and runtime_report.missing_obligations.",
    ]
    if (
        request.profile.lower() in {"production", "adversarial"}
        and request.identity_context is None
    ):
        commands.append(
            "uv run pic identity derive-context --population examples/agent_population_signed.json "
            "--profile production --output identity-context.json"
        )
    route_requests = getattr(runtime_report, "route_execution_requests", [])
    if route_requests:
        commands.append("Inspect runtime_report.route_execution_requests before route execution.")
    agent_tasks = getattr(runtime_report, "agent_tasks", [])
    if agent_tasks:
        commands.append("Review runtime_report.agent_tasks; do not execute arbitrary commands.")
    commands.append("Run another runtime step after new evidence or action results are available.")
    return commands


def run_agent_intake(request: AgentIntakeRequest) -> AgentIntakeReport:
    """Run one safe runtime intake step for an AI agent.

    This helper does not execute shell commands, mutate repositories, or start
    background network activity. It only assembles records and calls
    ``build_runtime_step``.
    """

    state = _with_identity_context(
        request.state or minimal_runtime_state(), request.identity_context
    )
    step_input = request.step_input or minimal_runtime_step_input(request.agent_output)
    if request.agent_output is not None and request.step_input is not None:
        step_input = step_input.model_copy(update={"agent_output": request.agent_output})
    step_input = step_input.model_copy(
        update={"allow_live_connectors": request.allow_live_connectors}
    )
    config = AgentRuntimeConfig(
        profile=request.profile,
        identity_profile=request.identity_profile,
        allow_live_connectors=request.allow_live_connectors,
    )
    runtime_report = build_runtime_step(state, step_input, config)
    provisional = AgentIntakeReport(
        report_id=f"agent-intake:{request.request_id}:{step_input.input_id}",
        profile=request.profile,
        runtime_report=runtime_report,
        accepted=runtime_report.accepted,
        operationally_usable=runtime_report.operationally_usable,
        settled=False,
        reasons=list(runtime_report.reasons),
    )
    return provisional.model_copy(
        update={
            "recommended_next_commands": _recommended_next_commands(request, runtime_report),
            "residual_summary": _residual_summary(runtime_report),
        }
    )


def run_agent_check(request: AgentIntakeRequest, *, compact: bool = False) -> AgentCheckReport:
    """Run a practical installed-package agent-output check.

    This wrapper keeps existing ``accepted``, ``operationally_usable``, and
    ``settled`` semantics unchanged. ``workflow_usable`` only means the report
    is safe and useful for the next verification/routing step.
    """

    intake = run_agent_intake(request)
    runtime_report = intake.runtime_report
    unresolved = _unresolved_obligations_from_runtime_report(runtime_report)
    next_actions = [
        "Inspect unresolved_obligations before reusing the output.",
        "Preserve residual_summary in downstream logs.",
        "Route verifier requests before promoting candidates to reusable work.",
    ]
    next_actions.extend(intake.recommended_next_commands)
    reasons = list(intake.reasons)
    if unresolved:
        reasons.append("unresolved obligations remain; use workflow_usable for routing only")
    return AgentCheckReport(
        report_id=f"agent-check:{request.request_id}",
        profile=request.profile,
        report_mode="compact" if compact else "full",
        compact=compact,
        practical_entrypoint="pic agent check --compact" if compact else "pic agent check",
        intake_report=intake,
        checked_outputs=_checked_outputs_from_runtime_report(runtime_report),
        unresolved_obligations=unresolved,
        residual_summary=intake.residual_summary,
        next_safe_actions=sorted(set(next_actions)),
        schema_refs=agent_check_schema_refs(),
        runbook_steps=agent_runbook_steps(request.profile),
        beginner_glossary=_agent_check_glossary(),
        workflow_usable=bool(intake.accepted),
        accepted=intake.accepted,
        operationally_usable=intake.operationally_usable,
        settled=False,
        reasons=sorted(set(reasons)),
        safety_invariants=agent_safety_invariants(),
    )


def accelerate_agent_phase(
    request: AgentIntakeRequest,
    *,
    compact: bool = False,
) -> PhaseAccelerationPlan:
    """Build a phase-acceleration plan from the practical agent request shape."""

    state = _with_identity_context(
        request.state or minimal_runtime_state(), request.identity_context
    )
    step_input = request.step_input or minimal_runtime_step_input(request.agent_output)
    if request.agent_output is not None and request.step_input is not None:
        step_input = step_input.model_copy(update={"agent_output": request.agent_output})
    step_input = step_input.model_copy(
        update={"allow_live_connectors": request.allow_live_connectors}
    )
    return build_phase_acceleration_plan(
        PhaseAccelerationRequest(
            request_id=f"agent-accelerate:{request.request_id}",
            profile=request.profile,
            state=state,
            step_input=step_input,
            runtime_config=AgentRuntimeConfig(
                profile=request.profile,
                identity_profile=request.identity_profile,
                allow_live_connectors=request.allow_live_connectors,
            ),
            identity_context=request.identity_context,
            compact=compact,
        )
    )


def agent_check_compact_payload(report: AgentCheckReport) -> dict[str, object]:
    """Return the compact JSON contract for CI and agent runners."""

    return {
        "report_id": report.report_id,
        "profile": report.profile,
        "report_mode": "compact",
        "accepted": report.accepted,
        "workflow_usable": report.workflow_usable,
        "operationally_usable": report.operationally_usable,
        "settled": report.settled,
        "checked_outputs": report.checked_outputs,
        "unresolved_obligations": report.unresolved_obligations,
        "residual_summary": report.residual_summary,
        "next_safe_actions": report.next_safe_actions,
        "schema_refs": report.schema_refs,
        "runbook_steps": report.runbook_steps,
        "safety_invariants": report.safety_invariants,
        "reasons": report.reasons,
    }


def agent_feature_readiness(
    state: RuntimeState | None = None,
    profile: str = "development",
) -> AgentFeatureReadinessReport:
    """Summarize whether the agent can use the full runtime feature path."""

    from percolation_inversion_compiler.io.schema import schema_model_map
    from percolation_inversion_compiler.io.snapshots import list_theory_snapshots

    active_state = state or minimal_runtime_state()
    health = runtime_health(active_state, AgentRuntimeConfig(profile=profile))
    profile_lower = profile.lower()
    has_identity_context = bool(
        active_state.accepted_agent_ids and active_state.accepted_public_key_ids
    )
    readiness = {
        "orientation": "ready",
        "snapshot_inspection": "ready",
        "minimal_intake": "ready",
        "identity_context": "ready" if has_identity_context else "diagnostic",
        "route_verification": "diagnostic",
        "packet_promotion": (
            "diagnostic"
            if profile_lower in {"production", "adversarial"} and not has_identity_context
            else "ready"
        ),
        "runtime_store_loop": "ready",
        "psi_sqot_inspection": "ready",
        "collective_certificate": (
            "diagnostic"
            if profile_lower in {"production", "adversarial"} and not has_identity_context
            else "ready"
        ),
        "provenance_preservation": "ready",
    }
    recommendations = [
        "uv run pic agent guide --profile " + profile,
        'uv run pic agent intake --text "Candidate packet: preserve residuals." --profile '
        + profile,
    ]
    reasons: list[str] = []
    if profile_lower in {"production", "adversarial"} and not has_identity_context:
        recommendations.append(
            "uv run pic identity derive-context --population examples/agent_population_signed.json "
            "--profile production --output identity-context.json"
        )
        reasons.append("production/adversarial packet promotion requires identity context")
    commercial = build_commercial_readiness_summary(
        profile=profile,
        schema_count=len(schema_model_map()),
        snapshot_count=len(list_theory_snapshots()),
        provenance_verified=False,
        security_metadata_present=True,
        identity_ready=has_identity_context,
    )
    return AgentFeatureReadinessReport(
        report_id=f"agent-feature-readiness:{active_state.state_id}:{profile}",
        profile=profile,
        runtime_health=health.model_dump(mode="json"),
        readiness=readiness,
        commercial_readiness=commercial,
        recommended_next_commands=recommendations,
        safety_invariants=agent_safety_invariants(),
        accepted=True,
        operationally_usable=not any(
            value in {"blocked", "diagnostic"} for value in readiness.values()
        ),
        settled=False,
        reasons=reasons,
    )


def recommend_agent_next_actions(
    intake_report: AgentIntakeReport,
    profile: str = "development",
) -> AgentNextActionReport:
    """Recommend the next safe actions from an intake report."""

    runtime_report = intake_report.runtime_report
    next_commands = [
        "Inspect intake_report.runtime_report.residual_ledger.",
        "Inspect intake_report.runtime_report.missing_obligations.",
        "Run `pic ecology bridge-runtime --report <general-intake-report.json>` "
        "for external intake reports.",
        "Run `pic agent message contract --message <message.json>` before trusting peer messages.",
    ]
    next_sdk_calls = [
        "percolation_inversion_compiler.agent.build_agent_workflow_guide",
        "percolation_inversion_compiler.runtime.resolve_step_evidence",
    ]
    schemas = [
        "RuntimeStepReport",
        "PacketPromotionReport",
        "GeneralIntakeRuntimeBridgeReport",
        "AgentMessageContractReport",
        "VerifierResolution",
        "RuntimeIdentityContext",
    ]
    fields = [
        "accepted",
        "operationally_usable",
        "settled",
        "residual_ledger",
        "missing_obligations",
        "promotion_report",
        "route_execution_requests",
        "agent_tasks",
    ]
    profile_lower = profile.lower()
    if profile_lower in {"production", "adversarial"}:
        next_commands.append(
            "uv run pic identity derive-context --population examples/agent_population_signed.json "
            "--profile production --output identity-context.json"
        )
        next_sdk_calls.append(
            "percolation_inversion_compiler.runtime.derive_runtime_identity_context"
        )
    if runtime_report.route_execution_requests:
        next_commands.append("Inspect route_execution_requests and verify evidence envelopes.")
        next_sdk_calls.append("percolation_inversion_compiler.core.resolve_adapter_route")
    if not runtime_report.allow_live_connectors:
        next_commands.append(
            "Use `pic agent communication-guide` to inspect bounded live defaults."
        )
        next_commands.append(
            "Use `pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss` "
            "for offline general intake."
        )
        next_commands.append(
            "Use `pic agent message ingest --message examples/agent_network/agent_message.json` "
            "for local agent-to-agent packet exchange."
        )
        next_sdk_calls.append(
            "percolation_inversion_compiler.agent.build_agent_communication_guide"
        )
        next_sdk_calls.append("percolation_inversion_compiler.ecology.ingest_general_source")
    else:
        next_commands.append(
            "Use `pic ecology ingest-general --source <url-or-feed>` for "
            "explicit-source live intake."
        )
        next_commands.append(
            "Use `pic agent message send/receive` for local agent-to-agent relay checks."
        )
    if runtime_report.agent_tasks:
        next_commands.append("Review agent_tasks; execute only through allowlisted policies.")
    if runtime_report.missing_obligations:
        next_commands.append("Preserve missing_obligations in the next runtime step.")
    next_commands.append(
        "Run collective certification only after packet, identity, and baseline checks."
    )
    return AgentNextActionReport(
        report_id=f"agent-next:{intake_report.report_id}:{profile}",
        profile=profile,
        next_commands=next_commands,
        next_sdk_calls=sorted(set(next_sdk_calls)),
        schemas_to_inspect=schemas,
        output_fields_to_inspect=fields,
        residual_summary=dict(sorted(intake_report.residual_summary.items())),
        safety_invariants=agent_safety_invariants(),
        accepted=True,
        operationally_usable=True,
        settled=False,
        reasons=list(intake_report.reasons),
    )
