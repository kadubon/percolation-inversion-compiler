# ECPT Phase Acceleration Score

`PhaseAccelerationScore` is a finite ranking signal for agent work. It is not a
certificate that ASI has been achieved. It summarizes how a runtime step changes
the protocol-relative ASI-proxy planning surface.

The score combines:

- `finite_proxy_gain`: ECPT phase-control gain plus bottleneck intervention
  gain.
- `psi_distance_reduction`: improvement in finite Psi components.
- `verification_throughput_score`: packet edge and route throughput proxy.
- `residual_debt_charge`: residual ledger burden carried by packets, phase
  planning, and SQOT scheduling.
- `risk_charge`: risk charges from phase-control candidates.
- `stale_packet_charge`: expired packet ratio.
- `false_liquidity_charge`: queue occupation by low-contribution packets.
- `missing_route_charge`: missing verifier route and residual external
  obligation penalty.

Higher scores rank actions that improve finite proxy mass and Psi distance while
keeping evidence debt and route uncertainty low. The runtime still returns
`settled=false` unless verifier evidence discharges the relevant finite scope.

Agent usage:

1. Sort `agent_tasks` by `priority_score`.
2. Check `phase_acceleration_score.total_score` to compare step-level options.
3. Refuse main operational execution when `missing_obligations` is nonempty.
4. Route `route_execution_requests` and re-run the runtime after evidence
   verification.
