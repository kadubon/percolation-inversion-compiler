# Percolation Inversion Compiler

`percolation-inversion-compiler` (PIC) is a certificate compiler and local AI
agent runtime. It turns finite inputs into checked capability packets, proof
obligations, residual ledgers, typed trace normal forms, frontier extraction,
salience queues, and verifier tasks. It supports AI agent integration and
protocol-relative ASI-proxy phase-control without claiming real ASI, legal
authority, or an unobserved physical result.

The registry is metadata, not evidence. A report can be useful while
`settled=false`; unresolved work stays explicit instead of being treated as
zero or silently removed.

Version `1.1.0` adds strict public input boundaries, known/unknown measurement,
witness-only positive BIT coordinates, measured SQOT costs, rechecked ALT lift,
finite TRC traces, resource-matched acceleration measurement, and an explicit
approval-bound operation path.

## Agent Skill

This repository includes an Agent Skills-compatible workflow at
[`.agents/skills/percolation-inversion-compiler/SKILL.md`](.agents/skills/percolation-inversion-compiler/SKILL.md).
Compatible agents can discover it from this repository, or copy it to a supported user skills directory
such as `~/.agents/skills/percolation-inversion-compiler/`. The canonical implementation remains this repository.

For a compact, non-executing routing pass, start with `pic agent check --compact`,
then use `pic phase plan --compact` to inspect ranked verifier work and
`pic token admissibility` to check a candidate token. The returned
`safe_commands` are operator-controlled inspection hints; they never grant
execution authority or promote a candidate to settlement.

## Five-Minute Check-Only Quickstart

The PyPI package is intended for practical agent output checking. Install the
base package and run only local, non-executing checks:

```bash
python -m pip install percolation-inversion-compiler==1.1.0
pic agent check --compact
pic doctor --fail-on never
pic demo bootstrap --output-dir pic-demo --overwrite
pic afst check --case pic-demo/afst/minimal_accepted.json --compact
```

The bootstrap example is inert data. Check commands do not dispatch providers,
run packet text, grant shell authority, or mark physical outcomes as proven.

Clone the repository for canonical TeX audits and development fixtures:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
uv run pic doctor --fail-on never
```

Installed-package examples use `pic-demo/...`. Source-checkout examples use
`examples/...`; do not mix the two path styles.

## Verified Capability Formation

PIC uses two separate acceleration decisions:

1. `accepted=true` means a finite protocol found a positive structural lower
   bound under matching resources and preserved residual debt.
2. `acceleration_metrics_certified=true` means baseline and candidate used the
   same observation protocol, receiver family, fixed horizon, stopping rule,
   evidence requirements, and resource envelope; at least one declared metric
   improved and none regressed beyond tolerance.

A measured accelerator claim requires both fields to be true. It is still not
proof of real ASI or general intelligence.

```bash
pic runtime compare \
  --baseline examples/runtime_baseline_run.json \
  --candidate examples/runtime_candidate_run.json \
  --threshold examples/runtime_threshold.json

pic runtime certify-acceleration \
  --baseline examples/runtime_baseline_run.json \
  --candidate examples/runtime_candidate_run.json
```

The compared metrics are time-to-verified, verification yield, residual
half-life, receiver reuse, certified capital gain, resource cost, and absolute
error correlation. See [Resource-matched measurement](docs/resource-matched-measurement.md).

## Six Theory Systems

| System | Practical role | Positive claims require |
| --- | --- | --- |
| ECPT | Verified packet and capability-path formation | checked packets, edges, closure, execution-available paths, and bounded queues |
| BIT | Bottleneck ranking and inversion | an intervention law, units, resource-matched baseline, evidence, and verifier witness |
| TRC | Typed finite traces and operation frontiers | authority, resource, tolerance, rollback, observation, and verifier records |
| SQOT | Attention and verification queue control | measured per-item costs, reserve, age, hazard, and explicit unknowns |
| ALT | Reusable abstraction capital | receiver lift, mechanism, leakage, transport, lifecycle, cost, and evidence |
| AFST | Satisfaction-flux stabilization diagnostics | abundance, deficit, units, refusal, authority, buffers, handover, and physical balance |

Missing required coordinates remain unknown. Raw candidate count, agent count,
cache hits, and dispatch receipts do not become positive phase progress.

## Real-World Operation Dry Run

All ordinary PIC checks are non-executing. Real-world effects are isolated in
the explicit sequence `adapter-check -> plan -> preflight -> approve ->
dispatch -> verify -> reconcile`.

```bash
python -m pip install "percolation-inversion-compiler[operation]==1.1.0"
pic operation adapter-check --manifest examples/operation/https_readonly.adapter.json
pic operation plan \
  --manifest examples/operation/https_readonly.adapter.json \
  --request examples/operation/https_readonly.request.json \
  --output operation-plan.json
```

Planning is a dry run. Dispatch additionally requires a digest-bound plan,
fresh scoped approvals, an unused nonce, adapter restrictions, and the exact
body or process digest. A dispatch receipt proves only that a provider call was
attempted. `physical_outcome_proven` remains false; only an independent signed
observation can set `physical_outcome_verified=true`.

Read [Operation security](docs/operation-security.md) before enabling dispatch.

## SDK

```python
from percolation_inversion_compiler.runtime import (
    RuntimeRunReport,
    certify_runtime_acceleration,
)

baseline = RuntimeRunReport.model_validate(baseline_data)
candidate = RuntimeRunReport.model_validate(candidate_data)
certificate = certify_runtime_acceleration(baseline, candidate)

usable_acceleration = (
    certificate.accepted and certificate.acceleration_metrics_certified
)
```

The Python/TypeScript decision contract is
[`contracts/v1.1/pic-cross-language-contract.json`](contracts/v1.1/pic-cross-language-contract.json).

## For AI Agents

Start with `pic agent check --compact`, then inspect `accepted`,
`finite_checks_passed`, `operationally_usable`, `settled`, blockers, and the
residual ledger separately. Never infer dispatch or settlement from
`accepted=true`.

Use `pic doctor` before production integration. Production identity and
provenance checks fail closed when required evidence is absent. Safe command
hints are text and are never executed automatically.

For connectors, identity, and the optional local service:

```bash
python -m pip install "percolation-inversion-compiler[agent-full]==1.1.0"
```

## Optional Sidecars

Dashboards, adoption packets, operator requests, GitHub Actions, and packet
exchange helpers are optional views over the same reports.
They do not gate the main workflow.

## Integration Examples

PIC is not limited to GitHub Actions. Use the integration that matches the
host agent or orchestration system:

- [Integration index](docs/integrations/README.md)
- [CLI AI agent output checker](examples/cli_agent_output_check/README.md)
- [Python SDK AI agent output checker](examples/python_sdk_agent_output_check/README.md)
- [GitHub Actions AI agent output checker](examples/github_action_agent_output_check/README.md)
- [GitHub Actions integration guide](docs/integrations/github-actions.md)

## Safety Boundary

PIC does not:

- prove real ASI, consciousness, model-weight change, legal authority, or
  physical/oracle truth;
- convert missing values to zero or candidate volume to verified capability;
- override consent, refusal, contracts, policy, or provider controls;
- execute packet content, trace content, safe-command hints, or check results;
- treat `operation_ready`, `provider_dispatch_ready`, or a receipt as an
  observed outcome.

## Documentation

- [Documentation index](docs/index.md)
- [Unknown semantics](docs/unknown-semantics.md)
- [BIT witness requirements](docs/bit-witness.md)
- [Resource-matched measurement](docs/resource-matched-measurement.md)
- [Operation security](docs/operation-security.md)
- [Cross-language contract](docs/cross-language-contract.md)
- [CLI reference](docs/cli-reference.md)
- [Migration from v1.0](docs/migration-v1.1.md)
- [Security policy](SECURITY.md)

## Canonical Sources

The five cited theory papers and the AFST specification snapshot are the
semantic sources for the checkers. The package contains machine-readable
schemas and audit snapshots, not a claim that every theorem has been proven by
the software. See [Theory coverage](docs/theory-coverage.md).

## Development Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src scripts
uv run pytest --cov=percolation_inversion_compiler --cov-fail-under=90
uv run bandit -c pyproject.toml -r src
uv run pip-audit --skip-editable
uv build
uv run python -m twine check dist/*.whl dist/*.tar.gz
```

Search terms: percolation inversion compiler, PIC, collective intelligence,
multi-agent systems, ECPT, BIT, TRC, SQOT, ALT, AFST, capability packet,
certificate compiler, proof obligations, residual ledgers, typed trace normal
forms, frontier extraction, abstraction liquidity, salience queue, verifier
routing, resource-matched acceleration, ASI-proxy phase-control, AI agent
integration, operation approval, Ed25519, SSRF protection.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
