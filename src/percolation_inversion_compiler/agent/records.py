"""Portable agent-facing records."""

from __future__ import annotations

from pydantic import BaseModel, Field

from percolation_inversion_compiler.core.live_policy import (
    default_allow_live_connectors,
    live_default_mode,
)
from percolation_inversion_compiler.core.operations import CommercialReadinessSummary
from percolation_inversion_compiler.runtime.records import (
    RuntimeIdentityContext,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)


class AgentIntakeRequest(BaseModel):
    """High-level request for agents that do not want to assemble runtime records."""

    request_id: str = "agent-intake"
    agent_output: str | None = None
    profile: str = "development"
    identity_profile: str | None = None
    state: RuntimeState | None = None
    step_input: RuntimeStepInput | None = None
    identity_context: RuntimeIdentityContext | None = None
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)


class AgentIntakeReport(BaseModel):
    """High-level residual-preserving report returned by agent intake."""

    report_id: str
    profile: str
    runtime_report: RuntimeStepReport
    recommended_next_commands: list[str] = Field(default_factory=list)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentCheckReport(BaseModel):
    """Beginner-readable practical workflow check for installed-package users."""

    report_id: str
    profile: str = "development"
    report_mode: str = "full"
    compact: bool = False
    practical_entrypoint: str = "pic agent check"
    intake_report: AgentIntakeReport
    checked_outputs: dict[str, str] = Field(default_factory=dict)
    unresolved_obligations: list[str] = Field(default_factory=list)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    next_safe_actions: list[str] = Field(default_factory=list)
    schema_refs: list[str] = Field(default_factory=list)
    runbook_steps: list[str] = Field(default_factory=list)
    beginner_glossary: dict[str, str] = Field(default_factory=dict)
    workflow_usable: bool = False
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)


class AgentWorkflowStep(BaseModel):
    """One safe full-feature workflow step for autonomous agents."""

    step_id: str
    title: str
    purpose: str
    safe_commands: list[str] = Field(default_factory=list)
    sdk_entrypoints: list[str] = Field(default_factory=list)
    schemas: list[str] = Field(default_factory=list)
    inspect_fields: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class AgentCommandInvocation(BaseModel):
    """OS-independent command description for autonomous agents."""

    invocation_id: str
    purpose: str
    argv: list[str] = Field(default_factory=list)
    shell_command: str = ""
    requires_source_checkout: bool = False
    requires_agent_full_extra: bool = False
    requires_operator_authority: bool = False
    executes_shell_commands_by_pic: bool = False
    mutates_environment_if_operator_runs_it: bool = False
    safety_notes: list[str] = Field(default_factory=list)


class AgentWorkflowGuide(BaseModel):
    """Deterministic full-feature workflow guide for AI agents."""

    guide_id: str = "agent-workflow-guide"
    profile: str = "development"
    steps: list[AgentWorkflowStep] = Field(default_factory=list)
    pip_core_commands: list[str] = Field(default_factory=list)
    pip_agent_full_commands: list[str] = Field(default_factory=list)
    source_checkout_commands: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = True
    settled: bool = False


class AgentRunbookReport(BaseModel):
    """Compact deterministic command/schema/field guidance for AI agents."""

    report_id: str = "agent-runbook"
    profile: str = "development"
    entrypoint: str = "pic agent check --compact"
    commands: list[str] = Field(default_factory=list)
    pip_core_commands: list[str] = Field(default_factory=list)
    pip_agent_full_commands: list[str] = Field(default_factory=list)
    source_checkout_commands: list[str] = Field(default_factory=list)
    schemas_to_inspect: list[str] = Field(default_factory=list)
    fields_to_inspect: list[str] = Field(default_factory=list)
    runbook_steps: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentFeatureReadinessReport(BaseModel):
    """Agent-facing readiness summary for full runtime use."""

    report_id: str
    profile: str
    runtime_health: dict[str, object] = Field(default_factory=dict)
    readiness: dict[str, str] = Field(default_factory=dict)
    commercial_readiness: CommercialReadinessSummary = Field(
        default_factory=CommercialReadinessSummary
    )
    recommended_next_commands: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = False
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentAutonomyAuditReport(BaseModel):
    """Audit report for non-gated agent activity through installed PIC."""

    report_id: str = "agent-autonomy-audit"
    profile: str = "development"
    adoption_required_for_core: bool = False
    approval_gate_present: bool = False
    safe_commands_executable_by_pic: bool = False
    compact_mode_available: bool = True
    pip_core_workflow_available: bool = True
    agent_full_extra_available: bool = True
    source_checkout_required_for_core: bool = False
    shell_expansion_required_for_sidecars: bool = False
    command_execution_allowed_by_pic: bool = False
    background_crawling_allowed: bool = False
    approval_persistence_created: bool = False
    pip_core_commands: list[str] = Field(default_factory=list)
    pip_agent_full_commands: list[str] = Field(default_factory=list)
    source_checkout_commands: list[str] = Field(default_factory=list)
    recommended_next_invocations: list[AgentCommandInvocation] = Field(default_factory=list)
    autonomy_enablers: list[str] = Field(default_factory=list)
    remaining_friction_points: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    workflow_usable: bool = True
    operationally_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentNextActionReport(BaseModel):
    """Next safe actions derived from an agent intake report."""

    report_id: str
    profile: str
    next_commands: list[str] = Field(default_factory=list)
    next_sdk_calls: list[str] = Field(default_factory=list)
    schemas_to_inspect: list[str] = Field(default_factory=list)
    output_fields_to_inspect: list[str] = Field(default_factory=list)
    residual_summary: dict[str, float] = Field(default_factory=dict)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentCommunicationPolicy(BaseModel):
    """Bounded default-live policy for external communication guidance."""

    profile: str = "development"
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    allowed_source_kinds: list[str] = Field(
        default_factory=lambda: [
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
        ]
    )
    required_env_vars: list[str] = Field(default_factory=list)
    token_policy: str = "environment-only"
    arbitrary_execution_allowed: bool = False
    live_connectors_default_enabled: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    explicit_source_required: bool = True
    candidate_only_by_default: bool = True
    opt_out_available: bool = True
    background_crawling_allowed: bool = False
    residual_behavior: str = "connector failures become diagnostic residual ledger entries"


class AgentCommunicationStep(BaseModel):
    """One safe external-communication workflow step for agents."""

    step_id: str
    title: str
    purpose: str
    allowed_source_kinds: list[str] = Field(default_factory=list)
    required_env_vars: list[str] = Field(default_factory=list)
    safe_commands: list[str] = Field(default_factory=list)
    sdk_entrypoints: list[str] = Field(default_factory=list)
    schemas: list[str] = Field(default_factory=list)
    inspect_fields: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    residual_behavior: str = "preserve diagnostic residuals"
    safety_notes: list[str] = Field(default_factory=list)


class AgentCommunicationGuide(BaseModel):
    """External communication guide for networked collective-phase workflows."""

    guide_id: str = "agent-communication-guide"
    profile: str = "development"
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    policy: AgentCommunicationPolicy = Field(default_factory=AgentCommunicationPolicy)
    steps: list[AgentCommunicationStep] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = False
    settled: bool = False


class AgentNetworkReadinessReport(BaseModel):
    """Network and external-communication readiness for agent workflows."""

    report_id: str
    profile: str = "development"
    allow_live_connectors: bool = Field(default_factory=default_allow_live_connectors)
    live_default_mode: str = Field(default_factory=live_default_mode)
    opt_out_available: bool = True
    bounded_candidate_intake: bool = True
    connector_dependency_present: bool = False
    github_token_present: bool = False
    runtime_token_present: bool = False
    allowed_source_kinds: list[str] = Field(default_factory=list)
    readiness: dict[str, str] = Field(default_factory=dict)
    recommended_next_commands: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = False
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
