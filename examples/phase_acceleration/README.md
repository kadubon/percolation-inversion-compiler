# Phase Acceleration Planner Examples

These examples show the deterministic planner layer for PIC agent workflows.
The planner ranks finite bottlenecks and safe next commands. It does not execute
commands, promote packet candidates, or prove real ASI or physical outcomes.

First practical command:

```sh
pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
```

Request-file workflow:

```sh
pic phase plan --request examples/phase_acceleration/phase_acceleration_request.json --compact
```

`phase_acceleration_request.json` contains a minimal `RuntimeState` and
`RuntimeStepInput`, so it produces a usable plan without source-local side
effects. `request_skeleton.json` is only a shape reference for ports and should
not be used as a positive runtime example.

Agent-facing shortcut:

```sh
pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
```

Use `pic phase runbook` when an agent needs the schemas and fields to inspect
before taking any downstream action.
