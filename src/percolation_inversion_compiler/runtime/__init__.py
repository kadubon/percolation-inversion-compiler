"""ECPT active agent runtime public API."""

from __future__ import annotations

from percolation_inversion_compiler.runtime.algorithms import (
    build_runtime_step,
    collect_missing_routes,
    loop_state_after_report,
    phase_acceleration_score,
    run_runtime_loop,
    runtime_health,
)
from percolation_inversion_compiler.runtime.records import (
    ActionCommit,
    ActionCommitPolicy,
    AgentRuntimeConfig,
    AgentTask,
    PhaseAccelerationScore,
    RouteExecutionRequest,
    RuntimeHealthReport,
    RuntimeServiceSettings,
    RuntimeState,
    RuntimeStepInput,
    RuntimeStepReport,
)
from percolation_inversion_compiler.runtime.service import create_runtime_app, run_runtime_service

__all__ = [
    "ActionCommit",
    "ActionCommitPolicy",
    "AgentRuntimeConfig",
    "AgentTask",
    "PhaseAccelerationScore",
    "RouteExecutionRequest",
    "RuntimeHealthReport",
    "RuntimeServiceSettings",
    "RuntimeState",
    "RuntimeStepInput",
    "RuntimeStepReport",
    "build_runtime_step",
    "collect_missing_routes",
    "create_runtime_app",
    "loop_state_after_report",
    "phase_acceleration_score",
    "run_runtime_loop",
    "run_runtime_service",
    "runtime_health",
]
