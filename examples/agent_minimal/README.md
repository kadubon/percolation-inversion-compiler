# Minimal Agent Intake Walkthrough

This walkthrough shows the smallest safe path for an AI agent to use Percolation Inversion Compiler. It is an integration fixture, not an empirical experiment or benchmark.

## 1. Explain The Repository

```powershell
uv run pic agent explain
```

## 2. Run Development Intake

```powershell
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile development
```

Inspect these fields first:

- `runtime_report.residual_ledger`
- `runtime_report.missing_obligations`
- `runtime_report.agent_tasks`
- `runtime_report.route_execution_requests`
- `settled`

`settled=false` is expected unless scoped finite verifier rules actually settle the relevant obligations.

## 3. Optional Production Identity Context

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent intake --text-file examples/agent_minimal/agent_output.txt --profile production --identity-context identity-context.json
```

Production profile is stricter. It may reject or downgrade packet promotion when issuer identity context, rollback, route resolution, edge certificates, or residual policies are missing.

## 4. Portable Commands

PowerShell commands are in `commands.ps1`. Unix shell commands are in `commands.sh`.

For the full feature path, use `full_workflow.ps1` or `full_workflow.sh`. These scripts show orientation, guide, readiness, intake, next-action inspection, snapshot inspection, store initialization, Psi inspection, and collective certification. They are examples of safe CLI flow, not permission to execute arbitrary tools.
