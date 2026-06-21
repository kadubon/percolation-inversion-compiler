"""Operator-adoption sidecar records.

The adoption layer is documentation-only.  It does not create an approval gate
for agent checking, phase planning, packet exchange, or runtime promotion.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdoptionSafetyBoundary(BaseModel):
    """Non-authority boundary for operator-adoption sidecars."""

    boundary_id: str = "adoption-safety-boundary"
    sidecar_only: bool = True
    pure_output_generator: bool = True
    installs_package: bool = False
    clones_repository: bool = False
    calls_network: bool = False
    executes_shell_commands: bool = False
    mutates_runtime_state: bool = False
    modifies_config_files: bool = False
    creates_required_approval_state: bool = False
    affects_agent_check: bool = False
    affects_phase_plan: bool = False
    affects_agent_accelerate: bool = False
    affects_packet_promotion: bool = False
    affects_settled: bool = False
    approval_settles_truth: bool = False
    safe_commands_are_execution_authority: bool = False
    settled: bool = False
    invariants: list[str] = Field(
        default_factory=lambda: [
            "adoption sidecars are optional operator-facing documentation",
            "absence of an adoption sidecar is normal and is not a blocker",
            "operator adoption does not settle runtime obligations",
            "operator adoption does not prove real ASI, physical truth, or oracle truth",
            "operator adoption does not promote packet candidates",
            "agents without install authority should generate an operator request instead",
        ]
    )


class AdoptionFirstRunCommand(BaseModel):
    """Command text for operator review; PIC does not execute it."""

    command_id: str
    command: str
    purpose: str
    requires_operator_authority: bool = False
    executed_by_pic: bool = False
    mutates_environment_if_operator_runs_it: bool = False
    expected_output: str = "operator-reviewed command output"


class AdoptionReviewChecklist(BaseModel):
    """Operator-facing checklist for deciding whether local use is allowed."""

    checklist_id: str = "adoption-review-checklist"
    items: list[str] = Field(default_factory=list)
    interpretation_rules: list[str] = Field(default_factory=list)
    accepted: bool = True
    settled: bool = False


class OperatorAdoptionPacket(BaseModel):
    """Operator-facing overview packet for optional PIC adoption."""

    packet_id: str = "operator-adoption-packet"
    profile: str = "development"
    operator_adoption_status: str = "not-recorded"
    what_pic_does: list[str] = Field(default_factory=list)
    what_pic_does_not_do: list[str] = Field(default_factory=list)
    candidate_work_rationale: str = (
        "AI-agent output is treated as candidate work until finite verifier, residual, "
        "identity, route, rollback, and promotion checks accept the scoped packet."
    )
    first_run_commands: list[AdoptionFirstRunCommand] = Field(default_factory=list)
    compact_json_fields_to_inspect: list[str] = Field(default_factory=list)
    accepted_true_meaning: str = (
        "accepted=true means the finite checker accepted the report shape and routing record; "
        "it does not mean final truth or settled obligations."
    )
    settled_false_meaning: str = (
        "settled=false means unresolved obligations remain explicit; it is not command failure."
    )
    safe_commands_meaning: str = (
        "safe_commands are deterministic hints to inspect or run only under operator authority."
    )
    features_requiring_explicit_operator_permission: list[str] = Field(default_factory=list)
    distribution_modes: list[str] = Field(default_factory=list)
    review_checklist: AdoptionReviewChecklist = Field(default_factory=AdoptionReviewChecklist)
    safety_boundary: AdoptionSafetyBoundary = Field(default_factory=AdoptionSafetyBoundary)
    accepted: bool = True
    workflow_usable: bool = True
    operationally_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)


class AgentToOperatorRequest(BaseModel):
    """Short request an agent can hand to an operator."""

    request_id: str = "agent-to-operator-request"
    profile: str = "development"
    operator_adoption_status: str = "not-recorded"
    plain_english_message: str
    warning: str = (
        "Agents without install authority should not self-install PIC. "
        "They should generate an operator request instead."
    )
    suggested_first_command: AdoptionFirstRunCommand
    suggested_next_command: AdoptionFirstRunCommand
    safety_boundary: AdoptionSafetyBoundary = Field(default_factory=AdoptionSafetyBoundary)
    accepted: bool = True
    workflow_usable: bool = True
    operationally_usable: bool = True
    settled: bool = False
    reasons: list[str] = Field(default_factory=list)
