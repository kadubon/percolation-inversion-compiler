# v0.6.0 Audit

This document records the v0.6.0 release boundary for PIC. The release target is
practical CCR interoperability plus TRC operation-readiness diagnostics, not
canonical settlement of all ECPT/BIT/TRC/SQOT/ALT claims.

## Release Target

- Package version: `0.6.0`.
- Release date: `2026-07-01`.
- New agent-facing surfaces: `pic trc trace-normalize`, `pic trc trace-check`,
  `pic trc trace-to-packet`, phase-plan CCR task/residual JSONL emissions, BIT
  registry extraction, SQOT repair-task emission, and ALT-to-ECPT bridge reports.
- New example boundary: `examples/asi_proxy_benchmark_bundle/` demonstrates a
  PIC TraceNF report that CCR can convert into a dry-run operation plan.

## Safety Boundary

The v0.6.0 operation-readiness gate is finite and residual-preserving. A trace
must expose scoped authority, resource, rollback, witness, causal schedule, and
tolerance-ledger data before it is marked operation-ready. This does not prove a
real ASI state, a physical outcome, policy compliance outside the declared
domain, or permission to execute provider actions.

The CCR interop commands emit data-only JSON or JSONL for downstream runtimes.
They do not mutate repositories, run shells, call networks, or execute provider
safe commands. CCR must still preserve residuals and apply its own settlement,
provider, baseline, and phase gates.

## Required Local Gates

Run these before publishing from a clean checkout:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src scripts
uv run pytest --cov=percolation_inversion_compiler --cov-report=term-missing --cov-fail-under=90
uv run pip-audit
uv run bandit -r src -c pyproject.toml
uv run python scripts/check_publish_safety.py
uv build
uv run python -m twine check dist/percolation_inversion_compiler-0.6.0-py3-none-any.whl dist/percolation_inversion_compiler-0.6.0.tar.gz
uv run python scripts/check_distribution_artifacts.py --dist-dir dist --version 0.6.0
uv run python scripts/validate_citation.py
```

## Non-Claims

`accepted`, `workflow_usable`, `real_world_operation_ready`, route availability,
safe commands, and CCR task emission remain candidate or diagnostic state until
the relevant verifier and runtime gates discharge their explicit obligations.
