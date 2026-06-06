# Agent Closed-Loop Runtime

The closed-loop runtime is the agent-facing ECPT/SQOT workflow:

1. Agent produces output.
2. Output becomes a `CapabilityPacketCandidate`.
3. Edge witnesses are built against the packet registry.
4. Psi dashboard is recomputed.
5. Bottleneck interventions are ranked.
6. Next agent tasks are emitted.
7. Residual and hazard ledgers remain charged until verifier evidence exists.

```powershell
uv run pic ecology loop --state examples\ecology_loop_state.json --agent-output "SQOT reserve packet for ECPT active phase-control."
```

The output is `ClosedLoopAgentIteration`:

- `ingestion`: accepted or diagnostic packet candidate creation.
- `registry`: packets plus edge witnesses.
- `psi`: finite ASI-proxy component dashboard.
- `plan`: bottleneck-inversion intervention menu.
- `next_agent_tasks`: deterministic task strings an agent runner can route.

Operational rules:

- Agent output is a packet candidate, not proof.
- Planning does not promote status to `settled`.
- External route residuals stay visible in the ledger.
- Stale, hash-invalid, unsafe, or authority-invalid queue items must be
  quarantined or rolled back by SQOT scheduling before operational reuse.
