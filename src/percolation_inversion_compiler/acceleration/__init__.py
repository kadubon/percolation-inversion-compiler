"""Phase-acceleration planner API."""

from __future__ import annotations

from percolation_inversion_compiler.acceleration.algorithms import (
    build_phase_acceleration_benchmark,
    build_phase_acceleration_plan,
    build_phase_trajectory,
    phase_acceleration_compact_payload,
    phase_acceleration_runbook,
    phase_acceleration_safety_invariants,
)
from percolation_inversion_compiler.acceleration.records import (
    BottleneckCandidate,
    PhaseAccelerationBenchmarkReport,
    PhaseAccelerationPlan,
    PhaseAccelerationRequest,
    PhaseComponentGap,
    PhaseGapVector,
    PhaseTrajectoryReport,
    SafePhaseAction,
)

__all__ = [
    "BottleneckCandidate",
    "PhaseAccelerationBenchmarkReport",
    "PhaseAccelerationPlan",
    "PhaseAccelerationRequest",
    "PhaseComponentGap",
    "PhaseGapVector",
    "PhaseTrajectoryReport",
    "SafePhaseAction",
    "build_phase_acceleration_benchmark",
    "build_phase_acceleration_plan",
    "build_phase_trajectory",
    "phase_acceleration_compact_payload",
    "phase_acceleration_runbook",
    "phase_acceleration_safety_invariants",
]
