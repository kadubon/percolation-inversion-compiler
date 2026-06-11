# Minimal GitHub Action for Checking AI Agent Output

This example shows how to run Percolation Inversion Compiler in GitHub Actions
as an AI agent output checker. It collects a small text candidate, runs
`pic agent intake`, and uploads the residual-preserving report as an artifact.

## Purpose

Use this workflow when a coding agent, issue triage bot, research assistant, or
workflow agent produces text that should be checked before reuse. PIC treats the
text as a packet candidate, preserves missing obligations, and emits JSON for
humans and agents to inspect.

## Files

- `pic-agent-output-check.yml`: inactive example workflow to copy into another repository.
- `agent_output.txt`: tiny local text input for trying the command outside Actions.

## Setup

Copy the workflow to your repository:

```text
.github/workflows/pic-agent-output-check.yml
```

The default workflow uses `uv sync --all-extras --dev` because this example
lives inside the PIC repository. In another repository, once PyPI publication is
available, use the commented `uv pip install percolation-inversion-compiler`
line instead.

## Expected Artifact

The workflow uploads an artifact named:

```text
pic-agent-output-check
```

It contains:

- `agent-output.txt`
- `pic-agent-output-report.json`

## Reading The Output

- `accepted=true` means PIC accepted the text as a reportable runtime input.
- `settled=false` is expected and is not workflow failure.
- `residual_summary` shows what still needs checking.
- `runtime_report.missing_obligations` lists obligations that should not be treated as done.
- The report is an audit artifact, not a truth certificate.

## Safety Boundary

The workflow is read-only and artifact-only. It does not use
`pull_request_target`, does not grant write permissions, does not comment on
pull requests, does not pass secrets, does not call live connectors, and does
not execute commands from agent output.

After understanding this boundary, users can adapt the workflow to their own
review process while keeping agent text as untrusted candidate input.

