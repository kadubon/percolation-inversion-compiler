"""Finite certificate compiler interfaces for ECPT, BIT, TRC, SQOT, and ALT."""

from __future__ import annotations

__version__ = "0.8.0"

from percolation_inversion_compiler.acceleration import (
    build_phase_benchmark_suite,
    build_phase_dashboard,
)
from percolation_inversion_compiler.adoption import (
    build_agent_to_operator_request,
    build_operator_adoption_packet,
)
from percolation_inversion_compiler.agent import build_agent_autonomy_audit
from percolation_inversion_compiler.alt import verify_alt_ecpt_lift
from percolation_inversion_compiler.bit_engine import (
    diagnose_bottlenecks,
    invert_bottlenecks,
)
from percolation_inversion_compiler.io import build_canonical_implementation_readiness_report
from percolation_inversion_compiler.packet_exchange import (
    packet_exchange_envelope_from_runtime_report,
)
from percolation_inversion_compiler.phase_lab import (
    build_collective_phase_certificate_candidate,
    build_effective_packet_graph,
    build_phase_threshold_status,
    compare_phase_windows,
    detect_autocatalytic_closure,
    detect_execution_available_paths,
    observe_phase_window,
)
from percolation_inversion_compiler.sqot_controller import diagnose_salience_obstruction
from percolation_inversion_compiler.trc import adapt_trc_trace

__all__ = [
    "__version__",
    "adapt_trc_trace",
    "build_agent_autonomy_audit",
    "build_agent_to_operator_request",
    "build_canonical_implementation_readiness_report",
    "build_collective_phase_certificate_candidate",
    "build_effective_packet_graph",
    "build_operator_adoption_packet",
    "build_phase_benchmark_suite",
    "build_phase_dashboard",
    "build_phase_threshold_status",
    "compare_phase_windows",
    "detect_autocatalytic_closure",
    "detect_execution_available_paths",
    "diagnose_bottlenecks",
    "diagnose_salience_obstruction",
    "invert_bottlenecks",
    "observe_phase_window",
    "packet_exchange_envelope_from_runtime_report",
    "verify_alt_ecpt_lift",
]
