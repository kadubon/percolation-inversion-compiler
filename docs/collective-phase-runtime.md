# Collective Phase Runtime

v0.3.2 aligns the runtime with ECPT's collective phase certificate picture. The runtime does
not depend on a single agent rewriting itself. It treats progress as finite
capability packets becoming verified, receiver-valid, queue-admissible,
execution-available, and composable inside a declared protocol.

The runtime loop is:

```text
observe -> packetize -> load evidence refs -> verify routes -> verify semantic
edges -> promote packet capital -> compute Psi(G..HZ) -> schedule with SQOT
-> execute allowlisted tasks -> apply results -> compare resource-matched runs
```

Key invariants:

- execution-available packets are not automatically executed;
- raw packet volume is not capability progress;
- `QS` charges salience and verification-queue obstruction;
- `HZ` charges hazard, authority, unsafe route, and rollback gaps;
- accepted acceleration is finite and protocol-relative;
- unobserved physical, oracle, simulator, and real ASI outcomes remain residual
  obligations.

Useful commands:

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic ecology paths --registry examples/ecology_packets.json --basin examples/ecpt_basin_contract.json
uv run pic runtime run-agent-loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --store runtime.sqlite --policy examples/runtime_executor_policy.json
```
