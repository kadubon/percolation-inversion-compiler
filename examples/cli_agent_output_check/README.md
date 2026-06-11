# Minimal CLI Example for Checking AI Agent Output

This is the simplest local use case for Percolation Inversion Compiler. It
checks AI-generated text before reuse and emits a residual-preserving JSON
report.

Run from a source checkout:

```bash
uv run pic agent intake \
  --text-file examples/cli_agent_output_check/agent_output.txt \
  --profile development \
  --output cli-agent-output-report.json
```

Read the report as an audit artifact. `settled=false` is expected when missing
obligations remain. The report is not a truth certificate and does not turn raw
agent text into verified evidence.

