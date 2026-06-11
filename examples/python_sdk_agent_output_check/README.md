# Minimal Python SDK Example for Checking AI Agent Output

This example shows how to embed Percolation Inversion Compiler inside an agent
runtime or orchestration system. It calls the Python SDK directly, checks one
AI-generated output as candidate information, and prints a compact JSON summary.

Run from a source checkout:

```bash
uv run python examples/python_sdk_agent_output_check/check_agent_output.py
```

`settled=false` is expected when obligations remain unresolved. The report is
an audit artifact, not a truth certificate.

