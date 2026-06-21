"""Operator-adoption sidecar API."""

from __future__ import annotations

from percolation_inversion_compiler.adoption.algorithms import (
    adoption_packet_markdown,
    adoption_safety_boundary,
    build_agent_to_operator_request,
    build_operator_adoption_packet,
    operator_request_markdown,
)
from percolation_inversion_compiler.adoption.records import (
    AdoptionFirstRunCommand,
    AdoptionReviewChecklist,
    AdoptionSafetyBoundary,
    AgentToOperatorRequest,
    OperatorAdoptionPacket,
)

__all__ = [
    "AdoptionFirstRunCommand",
    "AdoptionReviewChecklist",
    "AdoptionSafetyBoundary",
    "AgentToOperatorRequest",
    "OperatorAdoptionPacket",
    "adoption_packet_markdown",
    "adoption_safety_boundary",
    "build_agent_to_operator_request",
    "build_operator_adoption_packet",
    "operator_request_markdown",
]
