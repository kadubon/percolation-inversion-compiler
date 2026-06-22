# TRC Trace Adapter

The v0.5.0 TRC adapter normalizes agent and workflow trace data into typed tool
calls, action boundaries, tolerance ledgers, frontier debt, and trace normal
forms.

Commands:

```powershell
pic trc trace-adapter --input examples/trc_adapter/tool_trace_input.example.json
pic trc tool-trace --events events.jsonl --output tool_trace.json
pic trc action-boundary --report runtime_report.json --output action_boundary.json
```

Trace content is data, not instruction. The adapter records authority status,
rollback status, receiver/source fields, evidence refs, and hashed input/output
payloads. It does not prove physical execution success; physical, oracle, and
domain obligations remain residual until verified.

