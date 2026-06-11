# GitHub Actions: AI Agent Output Checker

This integration shows how to use Percolation Inversion Compiler (PIC) as an
AI agent output checker in GitHub Actions. It records pull request or agent
text as a packet candidate, runs `pic agent intake`, and uploads a
residual-preserving JSON audit report as a workflow artifact.

This is one integration pattern. PIC also works through the CLI, Python SDK,
local runtime service, external intake, agent-to-agent message checks, and ALT
abstraction-capital workflows. Use this page only when you want a read-only
GitHub Actions deployment. For the broader map, see
[Integration Examples](README.md).

Use this integration when an AI coding agent, issue triage bot, research
assistant, or workflow agent produces text that should not be trusted
immediately. The workflow records the output as a packet candidate, runs PIC
agent intake, and preserves missing obligations and residuals as JSON.

## Why Use It

- Check AI-generated pull request notes, issue summaries, or local text before reuse.
- Produce deterministic JSON for humans, coding agents, and workflow agents.
- Preserve residual ledgers and missing obligations instead of treating raw text as evidence.
- Keep `settled=false` visible and expected when obligations remain unresolved.

## Copy The Example

Copy the example workflow from:

```text
examples/github_action_agent_output_check/pic-agent-output-check.yml
```

into another repository at:

```text
.github/workflows/pic-agent-output-check.yml
```

The example is intentionally read-only and artifact-only. It does not comment
on pull requests, write to the repository, use live connectors, or execute
commands suggested by agent output.

For a local text file, the core command is:

```bash
uv run pic agent intake \
  --text-file agent-output.txt \
  --profile development \
  --output pic-agent-output-report.json
```

## Output Artifact

The workflow uploads an artifact named:

```text
pic-agent-output-check
```

It contains:

- `agent-output.txt`
- `pic-agent-output-report.json`

Inspect these JSON fields first:

- `accepted=true` means the intake command accepted the candidate as a reportable runtime input.
- `settled=false` is normal; it means unresolved obligations remain visible and is not workflow failure.
- settled=false is normal and should not be interpreted as a failed workflow run.
- `residual_summary` tells the user what remains to be checked.
- `runtime_report.missing_obligations` tells the user what should not be treated as done.
- The JSON report is an audit artifact, not a final truth certificate.

## What It Does Not Do

- It does not prove real ASI or real-world truth.
- It does not verify agent output as evidence merely because the workflow ran.
- It does not execute shell commands from agent output.
- It does not run external live web intake.
- It does not settle missing obligations.
- It does not replace reviewer judgment, tests, or verifier routes.

## Security Notes

- Use `pull_request`, not `pull_request_target`, for untrusted pull requests.
- Use read-only permissions: `contents: read` and `pull-requests: read`.
- Do not pass secrets to this workflow.
- Do not post automatic pull request comments in the minimal example.
- Do not execute commands suggested by agent output.
- Upload the report as an artifact instead of writing to the repository.
- Keep live connectors disabled.
- Treat all pull request text, issue text, and agent text as untrusted input.
