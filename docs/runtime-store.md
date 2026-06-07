# Runtime Store

`SQLiteRuntimeStore` is the default persistent store for runtime state,
event-log entries, run reports, and finite acceleration certificates. It uses
the Python standard library and stores deterministic JSON payloads.

```powershell
uv run pic runtime store init --store runtime.sqlite
uv run pic runtime store append --store runtime.sqlite --state examples/runtime_state.json
uv run pic runtime store load --store runtime.sqlite --state-id runtime-demo
uv run pic runtime store export --store runtime.sqlite --output runtime-store.json
```

The store is an audit and replay surface. It does not promote packet or target
status by itself. Store snapshots include an aggregate SHA-256 digest so agents
can detect replay drift across loop iterations.
