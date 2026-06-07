# Collective Phase Walkthrough

This walkthrough uses existing example JSON files from the parent `examples` directory. It demonstrates the ECPT v0.3.3 flow without self-rewrite, fine-tuning, or model-weight changes.

## Flow

1. Inspect accepted closure witnesses.
2. Inspect execution-available paths.
3. Check for hidden capability injection against a declared protocol frame.
4. Run one population step.
5. Certify the protocol-relative collective phase candidate.

## Commands

```powershell
uv run pic ecology closures --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology execution-paths --registry examples/collective_packet_registry.json --basin examples/ecpt_basin_contract.json
uv run pic ecology hidden-injection-check --registry examples/collective_packet_registry.json --events examples/walkthrough_collective_phase/empty-events.json --protocol examples/collective_protocol_frame.json
uv run pic runtime population-step --population examples/agent_population.json --inputs examples/runtime_loop_inputs.jsonl --profile production
uv run pic runtime collective-certify --population examples/agent_population.json --state examples/collective_runtime_state.json --basin examples/ecpt_basin_contract.json --baseline examples/runtime_baseline_run.json --threshold examples/runtime_threshold.json
```

## How To Read The Result

- `accepted=true` means the finite checks for that artifact passed.
- `operationally_usable=true` means the result can be routed under the selected profile.
- `settled=false` is expected for protocol-relative collective certificates unless every scoped verifier obligation is discharged.
- `residual_ledger` records what remains unresolved.
- `hidden_injection_report.accepted=true` means no undeclared packet, route, source, event, or evidence prefix was found for the declared protocol.

The walkthrough is a finite ASI-proxy collective phase demonstration. It is not a claim that real ASI has occurred.
