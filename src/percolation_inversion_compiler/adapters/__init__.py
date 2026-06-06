"""Optional adapters for scientific OSS dependencies."""

from __future__ import annotations

from percolation_inversion_compiler.adapters.graphs import shortest_path_lengths
from percolation_inversion_compiler.adapters.optimization import solve_linear_release
from percolation_inversion_compiler.adapters.transport import sinkhorn_transport
from percolation_inversion_compiler.adapters.units import assert_compatible_units

__all__ = [
    "assert_compatible_units",
    "shortest_path_lengths",
    "sinkhorn_transport",
    "solve_linear_release",
]
