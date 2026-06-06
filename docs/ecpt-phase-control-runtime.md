# ECPT Active Phase-Control Runtime

v0.3.1 includes an ECPT-first active runtime for autonomous agents. The runtime
does not claim to prove a real ASI phase transition. It ranks finite,
protocol-relative interventions that may increase an ASI-proxy capability
target under explicit constraints, verifier routes, and residual ledgers.

## Inputs

The runtime accepts three portable JSON inputs:

- `PhaseControlState`: finite capability hypergraph, state vector, hard gates,
  known obligations, verifier routes, and resource budgets.
- `ASIProxyTargetContract` or `PhaseControlObjective`: target nodes, minimum
  finite proxy mass, required obligations, risk tolerance, and residual budget.
- `PhaseControlAction[]`: candidate interventions with sources, target node,
  activation delta, burden, risk charge, resource cost, preconditions,
  postconditions, and required verifier routes.

Example:

```powershell
uv run pic ecpt plan --state examples\ecpt_phase_control_state.json --target examples\ecpt_asi_proxy_target.json --budget examples\ecpt_phase_control_budget.json --profile production
```

## Outputs

`pic ecpt plan` returns a `PhaseControlRunReport`:

- `baseline_reachable_mass` and `controlled_reachable_mass` from finite ECPT
  reachable-mass recursion.
- ranked `InterventionCandidate` records with finite proxy gain, score,
  resource cost, residual charge, required evidence routes, and missing
  obligations.
- a `PhaseControlPlan` with selected actions, residual ledger, missing
  obligations, required evidence routes, and safe operational flags.

The planner intentionally keeps `settled=false`. Planning output is a routing
and intervention recommendation, not a theorem proof or domain witness.

## Safety Contract

Agents should use `operationally_usable`, `missing_obligations`, and the
residual ledger as the operational truth. `accepted=true` only means that a
finite planning recommendation exists. It does not discharge external ECPT
obligations such as proxy grounding, ontology extension, policy
counterfactuals, speculative channel repair, or cross-theory bridge proof.

Route unresolved obligations before acting:

```powershell
uv run pic routes explain --route ecpt.adapters.proxy.verify_target_contract
uv run pic evidence verify --envelope examples\evidence_envelope.json --profile production
```

## Simulation

`pic ecpt simulate` runs finite reachable-mass response for proposed actions
without target-objective policy:

```powershell
uv run pic ecpt simulate --state examples\ecpt_phase_control_state.json --actions examples\ecpt_phase_control_actions.json
```

This command is useful for agent what-if search and regression tests. It still
preserves the same safety invariants: no hidden status promotion and no
unobserved ASI or physical claim settlement.
