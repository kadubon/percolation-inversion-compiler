# Runtime Executor

The v0.3.2 executor is deliberately narrow. It can run allowlisted finite runtime
tasks, but it does not provide general shell automation or unrestricted network
access. This matches ECPT's distinction between execution-available capability
and unconstrained execution.

Executor output is a finite operational certificate surface for agent routing;
it is not a status-promotion path.

`RuntimeExecutorPolicy` controls:

- allowed task types;
- allowed verifier routes;
- network and file-write permissions;
- sandbox root;
- authority grant requirement;
- rollback receipt requirement.

Default production behavior requires authority and rollback metadata. Missing
permissions produce `RuntimeExecutionReport` diagnostics and residual ledger
charges rather than settled claims.

```powershell
uv run pic runtime execute-task --state examples/runtime_state.json --task examples/runtime_agent_task.json --policy examples/runtime_executor_policy.json --profile production
uv run pic runtime execute-routes --requests examples/runtime_route_requests.json --evidence-store evidence-store --profile production
```
