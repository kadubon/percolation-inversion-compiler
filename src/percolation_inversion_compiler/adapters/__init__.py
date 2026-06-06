"""Optional adapters for scientific OSS dependencies."""

from __future__ import annotations

from percolation_inversion_compiler.adapters.domain import (
    replay_trc_physical_trace,
    verify_archive_domain_evidence,
    verify_ecpt_generator_limit,
    verify_ecpt_numerical_envelope,
    verify_trc_telemetry_calibration,
)
from percolation_inversion_compiler.adapters.graphs import shortest_path_lengths
from percolation_inversion_compiler.adapters.optimization import solve_linear_release
from percolation_inversion_compiler.adapters.transport import sinkhorn_transport
from percolation_inversion_compiler.adapters.units import assert_compatible_units

__all__ = [
    "assert_compatible_units",
    "replay_trc_physical_trace",
    "shortest_path_lengths",
    "sinkhorn_transport",
    "solve_linear_release",
    "verify_archive_domain_evidence",
    "verify_ecpt_generator_limit",
    "verify_ecpt_numerical_envelope",
    "verify_trc_telemetry_calibration",
]
