"""Finite certificate compiler interfaces for ECPT, BIT, TRC, SQOT, and ALT."""

from __future__ import annotations

__version__ = "0.4.4"

from percolation_inversion_compiler.acceleration import (
    build_phase_benchmark_suite,
    build_phase_dashboard,
)
from percolation_inversion_compiler.adoption import (
    build_agent_to_operator_request,
    build_operator_adoption_packet,
)
from percolation_inversion_compiler.agent import build_agent_autonomy_audit
from percolation_inversion_compiler.io import build_canonical_implementation_readiness_report
from percolation_inversion_compiler.packet_exchange import (
    packet_exchange_envelope_from_runtime_report,
)

__all__ = [
    "__version__",
    "build_agent_autonomy_audit",
    "build_agent_to_operator_request",
    "build_canonical_implementation_readiness_report",
    "build_operator_adoption_packet",
    "build_phase_benchmark_suite",
    "build_phase_dashboard",
    "packet_exchange_envelope_from_runtime_report",
]
