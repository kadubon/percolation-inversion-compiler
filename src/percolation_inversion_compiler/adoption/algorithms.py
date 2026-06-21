"""Operator-adoption sidecar builders."""

from __future__ import annotations

from percolation_inversion_compiler.adoption.records import (
    AdoptionFirstRunCommand,
    AdoptionReviewChecklist,
    AdoptionSafetyBoundary,
    AgentToOperatorRequest,
    OperatorAdoptionPacket,
)

_FIRST_CHECK_TEXT = "Candidate packet: route evidence and preserve residuals."
_INSTALL_COMMAND = "python -m pip install percolation-inversion-compiler"
_FIRST_CHECK_COMMAND = (
    'pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." '
    "--profile development"
)
_NEXT_PHASE_COMMAND = (
    'pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." '
    "--profile development"
)


def adoption_safety_boundary() -> AdoptionSafetyBoundary:
    """Return the fixed non-authority contract for adoption sidecars."""

    return AdoptionSafetyBoundary()


def build_operator_adoption_packet(profile: str = "development") -> OperatorAdoptionPacket:
    """Build a deterministic operator-facing adoption packet."""

    commands = [
        AdoptionFirstRunCommand(
            command_id="minimal-pypi-install",
            command=_INSTALL_COMMAND,
            purpose="Install PIC from PyPI when the operator has chosen to allow local use.",
            requires_operator_authority=True,
            mutates_environment_if_operator_runs_it=True,
            expected_output="PIC package installed in the selected Python environment",
        ),
        AdoptionFirstRunCommand(
            command_id="minimal-first-check",
            command=_FIRST_CHECK_COMMAND,
            purpose="Run the shortest compact agent-output contract after installation.",
            expected_output=(
                "compact JSON with accepted, workflow_usable, settled, residuals, and blockers"
            ),
        ),
        AdoptionFirstRunCommand(
            command_id="minimal-next-phase-plan",
            command=_NEXT_PHASE_COMMAND,
            purpose="Inspect ranked phase gaps and promotion blockers after the first check.",
            expected_output=(
                "compact PhaseAccelerationPlan JSON with settled=false when obligations remain"
            ),
        ),
    ]
    checklist = AdoptionReviewChecklist(
        items=[
            "Confirm the agent has authority only to request use, not to self-install.",
            "Confirm PIC output will be treated as candidate work, not final truth.",
            "Confirm safe_commands will be inspected before any execution.",
            (
                "Confirm live connectors, repository mutation, and shell execution require "
                "explicit authority."
            ),
            "Confirm accepted=true and workflow_usable=true do not imply settled=true.",
        ],
        interpretation_rules=[
            "if adoption_sidecar is absent: continue normal checking and planning",
            "if adoption_sidecar is present: treat it as operator-facing documentation only",
            "if operator_adoption is approved: this may authorize local use in that environment",
            "operator adoption does not settle external obligations",
            "operator adoption does not promote packets",
        ],
    )
    return OperatorAdoptionPacket(
        profile=profile,
        what_pic_does=[
            "Checks AI-agent output as capability packet candidates.",
            "Preserves evidence, proof obligations, residual ledgers, and settlement blockers.",
            "Routes finite verifier work and phase-planning diagnostics.",
            "Emits machine-readable JSON contracts for agent and CI workflows.",
        ],
        what_pic_does_not_do=[
            "It does not execute proposed actions from agent output.",
            "It does not bypass operator approval policy.",
            "It does not prove real ASI, physical truth, simulator truth, or oracle truth.",
            "It does not silently promote accepted or workflow_usable outputs to settled.",
            "It does not require adoption approval for agent check, phase plan, or accelerate.",
        ],
        first_run_commands=commands,
        compact_json_fields_to_inspect=[
            "accepted",
            "workflow_usable",
            "settled",
            "unresolved_obligations",
            "residual_summary",
            "safe_commands",
            "cannot_promote_because",
            "candidate_only_reasons",
            "settled_blockers",
            "safety_invariants",
        ],
        features_requiring_explicit_operator_permission=[
            "installing the PyPI package",
            "cloning a source checkout",
            "running commands that mutate local environments or repositories",
            "enabling live network connectors for explicit sources",
            "executing verifier routes or shell commands outside PIC documentation output",
        ],
        distribution_modes=[
            (
                "PyPI install: practical agent checks, bundled snapshots, schema export, "
                "demo bootstrap"
            ),
            "source checkout: root examples, canonical TeX audits, development fixtures",
            "Wiki: human-oriented conceptual guide",
            "ClawHub skill: external agent skill packaging surface when separately provided",
            "full development checkout: tests, release checks, and local implementation work",
        ],
        review_checklist=checklist,
        safety_boundary=adoption_safety_boundary(),
        reasons=[
            "operator adoption sidecar is optional documentation and does not gate "
            "PIC core commands"
        ],
    )


def build_agent_to_operator_request(profile: str = "development") -> AgentToOperatorRequest:
    """Build a short operator request for agents lacking install authority."""

    message = "\n".join(
        [
            "I found PIC.",
            "PIC treats AI-agent output as candidate work.",
            "PIC preserves evidence, proof obligations, residual ledgers, and settlement blockers.",
            "PIC does not execute my proposed actions.",
            "PIC does not bypass your approval policy.",
            "PIC does not prove real ASI or real-world truth.",
            "Please review and decide whether I may use it.",
        ]
    )
    return AgentToOperatorRequest(
        profile=profile,
        plain_english_message=message,
        suggested_first_command=AdoptionFirstRunCommand(
            command_id="operator-request-first-command",
            command=f"{_INSTALL_COMMAND}\n{_FIRST_CHECK_COMMAND}",
            purpose="Install PIC and run the first compact check if the operator approves use.",
            requires_operator_authority=True,
            mutates_environment_if_operator_runs_it=True,
            expected_output="installed package plus compact agent check JSON",
        ),
        suggested_next_command=AdoptionFirstRunCommand(
            command_id="operator-request-next-command",
            command=_NEXT_PHASE_COMMAND,
            purpose="Inspect phase-planning diagnostics after the first check.",
            expected_output="compact PhaseAccelerationPlan JSON",
        ),
        safety_boundary=adoption_safety_boundary(),
        reasons=["agent lacks install authority and should request operator review"],
    )


def adoption_packet_markdown(
    packet: OperatorAdoptionPacket,
    *,
    language: str = "en",
) -> str:
    """Render an adoption packet as deterministic Markdown."""

    if language == "ja":
        lines = [
            "# PIC オペレーター導入パケット",
            "",
            f"- Profile: `{packet.profile}`",
            f"- operator_adoption_status: `{packet.operator_adoption_status}`",
            f"- settled: `{str(packet.settled).lower()}`",
            "",
            "## PIC が行うこと",
            *[f"- {item}" for item in packet.what_pic_does],
            "",
            "## PIC が行わないこと",
            *[f"- {item}" for item in packet.what_pic_does_not_do],
            "",
            "## 候補作業",
            packet.candidate_work_rationale,
            "",
            "## 最初のコマンド",
            *[f"- `{item.command}`: {item.purpose}" for item in packet.first_run_commands],
            "",
            "## compact JSON で見るフィールド",
            *[f"- `{item}`" for item in packet.compact_json_fields_to_inspect],
            "",
            "## レビュー項目",
            *[f"- {item}" for item in packet.review_checklist.items],
            "",
            "## 安全境界",
            *[f"- {item}" for item in packet.safety_boundary.invariants],
        ]
        return "\n".join(lines) + "\n"

    lines = [
        "# PIC Operator Adoption Packet",
        "",
        f"- Profile: `{packet.profile}`",
        f"- Operator adoption status: `{packet.operator_adoption_status}`",
        f"- Settled: `{str(packet.settled).lower()}`",
        "",
        "## What PIC Does",
        *[f"- {item}" for item in packet.what_pic_does],
        "",
        "## What PIC Does Not Do",
        *[f"- {item}" for item in packet.what_pic_does_not_do],
        "",
        "## Candidate Work",
        packet.candidate_work_rationale,
        "",
        "## First Commands",
        *[f"- `{item.command}`: {item.purpose}" for item in packet.first_run_commands],
        "",
        "## Compact JSON Fields",
        *[f"- `{item}`" for item in packet.compact_json_fields_to_inspect],
        "",
        "## Review Checklist",
        *[f"- {item}" for item in packet.review_checklist.items],
        "",
        "## Safety Boundary",
        *[f"- {item}" for item in packet.safety_boundary.invariants],
    ]
    return "\n".join(lines) + "\n"


def operator_request_markdown(
    request: AgentToOperatorRequest,
    *,
    language: str = "en",
) -> str:
    """Render an agent-to-operator request as deterministic Markdown."""

    if language == "ja":
        return "\n".join(
            [
                "# エージェントからオペレーターへのリクエスト",
                "",
                request.plain_english_message,
                "",
                f"Warning: {request.warning}",
                "",
                "## 推奨される最初のコマンド",
                "```bash",
                request.suggested_first_command.command,
                "```",
                "",
                "## 推奨される次のコマンド",
                "```bash",
                request.suggested_next_command.command,
                "```",
                "",
                "## 安全境界",
                *[f"- {item}" for item in request.safety_boundary.invariants],
                "",
            ]
        )

    return "\n".join(
        [
            "# Agent To Operator Request",
            "",
            request.plain_english_message,
            "",
            f"Warning: {request.warning}",
            "",
            "## Suggested First Command",
            "```bash",
            request.suggested_first_command.command,
            "```",
            "",
            "## Suggested Next Command",
            "```bash",
            request.suggested_next_command.command,
            "```",
            "",
            "## Safety Boundary",
            *[f"- {item}" for item in request.safety_boundary.invariants],
            "",
        ]
    )
