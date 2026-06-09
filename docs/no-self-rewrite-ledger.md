# No Self-Rewrite Ledger

ECPT collective phase progress is modeled as packet percolation under a declared
protocol, not as one model rewriting its own weights. v0.3.4 makes this an
explicit runtime invariant through `AgentPolicyIdentity` and
`FixedPopulationLedger`.

`FixedPopulationLedger` compares the before/after agent population:

- agent ids must match;
- policy digests must match;
- model digests must match when declared;
- `self_rewrite_allowed` and `weight_update_allowed` must remain false;
- the observation window must stay fixed.

If any check fails, collective phase certification fails closed and the residual
ledger receives a diagnostic coordinate. This lets an agent use the runtime for
collective packet verification and scheduling without accidentally converting a
self-modification claim into an ECPT collective phase claim.
