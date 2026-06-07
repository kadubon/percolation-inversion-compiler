# Collective Phase Runtime

v0.3.3 aligns the runtime with ECPT's collective phase certificate picture. The
runtime does not depend on a single agent rewriting itself, fine-tuning itself,
or changing model weights. It treats progress as finite capability packets
becoming verified, receiver-valid, queue-admissible, execution-available but not
executed, and composable inside a declared protocol and fixed population.

The runtime loop is:

```text
observe -> packetize -> load evidence refs -> verify routes -> verify semantic
edges -> promote packet capital -> find accepted closures and execution paths
-> compute Psi(G..HZ) -> schedule with SQOT -> execute allowlisted tasks
-> apply results -> compare resource-matched runs -> collective-certify
```

Key invariants:

- execution-available packets are not automatically executed;
- fixed population and no-self-rewrite are part of the certificate contract;
- raw packet volume is not capability progress;
- AC uses accepted autocatalytic closure witnesses when available;
- DE uses execution-available path certificates when available;
- `QS` charges salience and verification-queue obstruction;
- `HZ` charges hazard, authority, unsafe route, and rollback gaps;
- accepted acceleration is finite and protocol-relative;
- unobserved physical, oracle, simulator, and real ASI outcomes remain residual
  obligations.

Useful commands:

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input.json --profile production
uv run pic runtime population-step --population examples/agent_population.json --inputs examples/runtime_loop_inputs.jsonl --profile production
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
uv run pic ecology paths --registry examples/ecology_packets.json --basin examples/ecpt_basin_contract.json
uv run pic ecology closures --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology execution-paths --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic runtime run-agent-loop --state examples/runtime_state.json --inputs examples/runtime_loop_inputs.jsonl --store runtime.sqlite --policy examples/runtime_executor_policy.json
```
