"""Portable agent-facing records."""

from __future__ import annotations

from pydantic import BaseModel, Field

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
    allow_live_connectors: bool = False


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


class AgentWorkflowGuide(BaseModel):
    """Deterministic full-feature workflow guide for AI agents."""

    guide_id: str = "agent-workflow-guide"
    profile: str = "development"
    steps: list[AgentWorkflowStep] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = True
    operationally_usable: bool = True
    settled: bool = False


class AgentFeatureReadinessReport(BaseModel):
    """Agent-facing readiness summary for full runtime use."""

    report_id: str
    profile: str
    runtime_health: dict[str, object] = Field(default_factory=dict)
    readiness: dict[str, str] = Field(default_factory=dict)
    recommended_next_commands: list[str] = Field(default_factory=list)
    safety_invariants: list[str] = Field(default_factory=list)
    accepted: bool = False
    operationally_usable: bool = False
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
    """Explicit opt-in policy for external communication guidance."""

    profile: str = "development"
    allow_live_connectors: bool = False
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
    live_connectors_default_enabled: bool = False
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
    allow_live_connectors: bool = False
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
    allow_live_connectors: bool = False
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
