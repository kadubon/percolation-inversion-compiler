"""Agent-facing shortcuts for safe PIC runtime integration."""

from __future__ import annotations

from percolation_inversion_compiler.agent.algorithms import (
    agent_feature_readiness,
    agent_manifest_payload,
    agent_network_readiness,
    agent_safety_invariants,
    build_agent_communication_guide,
    build_agent_workflow_guide,
    minimal_runtime_state,
    minimal_runtime_step_input,
    recommend_agent_next_actions,
    run_agent_intake,
)
from percolation_inversion_compiler.agent.records import (
    AgentCommunicationGuide,
    AgentCommunicationPolicy,
    AgentCommunicationStep,
    AgentFeatureReadinessReport,
    AgentIntakeReport,
    AgentIntakeRequest,
    AgentNetworkReadinessReport,
    AgentNextActionReport,
    AgentWorkflowGuide,
    AgentWorkflowStep,
)

__all__ = [
    "AgentCommunicationGuide",
    "AgentCommunicationPolicy",
    "AgentCommunicationStep",
    "AgentFeatureReadinessReport",
    "AgentIntakeReport",
    "AgentIntakeRequest",
    "AgentNetworkReadinessReport",
    "AgentNextActionReport",
    "AgentWorkflowGuide",
    "AgentWorkflowStep",
    "agent_feature_readiness",
    "agent_manifest_payload",
    "agent_network_readiness",
    "agent_safety_invariants",
    "build_agent_communication_guide",
    "build_agent_workflow_guide",
    "minimal_runtime_state",
    "minimal_runtime_step_input",
    "recommend_agent_next_actions",
    "run_agent_intake",
]
