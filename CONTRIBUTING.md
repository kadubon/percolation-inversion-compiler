# Contributing

This repository accepts changes that preserve the finite-checker boundary:
registries are metadata, checker-derived status is authoritative, and unresolved
external obligations must remain visible in residual ledgers.
New certificate checkers must state which finite obligations they discharge and
which `ExternalProofObligation` records remain unresolved.

Contributions should include focused tests, deterministic JSON-facing APIs, and
license notes for any optional OSS dependency. Do not vendor canonical TeX/PDF
papers, private keys, local datasets, or simulator outputs.

Before proposing a change, run:

```powershell
uv sync --all-extras --dev
uv run pytest --cov=percolation_inversion_compiler --cov-report=term-missing --cov-fail-under=84
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv build
```
