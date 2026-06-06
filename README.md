# Percolation Inversion Compiler

`percolation-inversion-compiler` is a Python reference implementation of a
JSON-first certificate compiler for ECPT, BIT, and TRC. It turns
machine-readable mathematical artifacts into finite checker judgments: proof
obligations, residual ledgers, dependency DAGs, typed trace normal forms,
frontier extraction records, and portable JSON Schemas for AI agent integration.

In practical terms, the input is a paper-derived TeX source, registry-like
JSON/YAML, or a finite certificate record. The output is deterministic JSON that
answers three questions: which finite certificates passed, which proof
obligations remain, and which residual ledger coordinates must stay charged.
Autonomous agents can use that output as a routing layer before they call
domain simulators, frontier planners, or other verifier adapters.

The repository is not an ASI detector and does not assert that artificial
superintelligence has been achieved. Its narrower scientific role is to provide
a protocol-relative ASI-proxy phase-control toolkit: agents can ask which finite
certificates are accepted, which claims still need external evidence, and which
residual costs remain charged rather than hidden.

The three papers play complementary roles:

- ECPT models protocol-relative capability propagation, activation, queues,
  capacity, viability, and phase-control certificates.
- BIT supplies a witness calculus for unlockable potential: unit functors,
  stopped evidence sheaves, martingale deficiency audits, release duality,
  mechanism cubes, and certificate compiler graphs.
- TRC compiles cyber-physical observations into typed executable traces,
  tolerance/resource ledgers, risk gates, and frontier archives.

The implementation rule is strict: a registry is metadata, not evidence.
Registry entries must be projections of extractor/checker judgments. Declared
status is kept separate from checker-derived status, and no claim is promoted to
`settled` without the required certificate route. Non-finite theorem clauses,
external simulators, physical-domain witnesses, oracle claims, and unobserved
ASI claims remain explicit `ExternalProofObligation` records with residual
charges and failure modes.

What this gives an agent:

- a certificate compiler for ECPT/BIT/TRC artifacts;
- proof obligation and residual ledger records suitable for planning logs;
- typed trace normal form checks for TRC frontiers;
- frontier extraction and audit reports for protocol-relative claims;
- derived non-vendored snapshots for users who do not have the TeX sources;
- schema bundles for ports to Rust, TypeScript, Julia, Go, or other runtimes.

What it does not give an agent:

- automatic proof of unobserved physical or ASI claims;
- permission to treat `declared_status` as evidence;
- silent conversion of external simulator/oracle output into `settled` status.

Canonical sources:

- Takahashi, K. (2026). *Executable Capability Percolation Theory*. Zenodo.
  <https://doi.org/10.5281/zenodo.20535654>
- Takahashi, K. (2026). *Bottleneck Inversion Theory: Machine-Readable Witness
  Calculus for Unlockable Potential*. Zenodo.
  <https://doi.org/10.5281/zenodo.20545356>
- Takahashi, K. (2026). *Typed Reality Compilation: Operational Tolerance
  Allocation for Resource-Efficient Cyber-Physical Frontier Compilation*. Zenodo.
  <https://doi.org/10.5281/zenodo.20554083>

## Install

```powershell
uv sync --all-extras --dev
```

## CLI

TeX-free quickstart:

```powershell
uv run pic snapshot list
uv run pic snapshot show --artifact trc
uv run pic snapshot routes
uv run pic explain external def:null-channel-routing --from-snapshot
uv run pic doctor --fail-on never
uv run pic demo datacenter
```

Canonical TeX audit:

```powershell
$env:PIC_CANONICAL_TEX_DIR = "path\to\canonical\tex"
uv run pic extract --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex"
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Executable Capability Percolation Theory.tex" --canonical-key ecpt --strict-projection
uv run pic validate --registry registry.json
uv run pic coverage --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex"
uv run pic audit theory --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --canonical-key trc
uv run pic schema --type TheoryAuditReport
uv run pic schema --all --output-dir schemas
uv run pic check --source "$env:PIC_CANONICAL_TEX_DIR\Typed Reality Compilation.tex" --strict-projection --derive-status
uv run pic demo datacenter
uv run pic explain coverage def:null-channel-routing
uv run pic explain external def:null-channel-routing
uv run pic explain ecpt
```

Agent connector path:

```powershell
uv run pic schema --all --output-dir schemas
uv run pic snapshot routes
uv run pic doctor --fail-on warn
uv run pic validate --registry examples\minimal_registry.json
uv run pic compile --records examples\frontier_records.json
```

For fixture-only smoke tests:

```powershell
uv run pic check --source tests\fixtures\minimal_claims.tex --strict-projection --derive-status
uv run pic audit theory --source tests\fixtures\minimal_claims.tex --fail-on projection
uv run pic schema --all --output-dir schemas
```

## Development Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
```

The package is designed for agent-facing JSON workflows. Registry entries are
metadata projections, not evidence; checked outputs distinguish declared status,
derived status, proof obligations, and residual ledgers.

## Documentation

- [Architecture](docs/architecture.md)
- [Mathematical contracts](docs/mathematical-contracts.md)
- [Theory coverage](docs/theory-coverage.md)
- [External obligations](docs/external-obligations.md)
- [Agent integration](docs/agent-integration.md)
- [Tutorial](docs/tutorial.md)
- [Porting guide](docs/porting.md)

## License

Code in this repository is licensed under Apache-2.0. The cited Zenodo papers are
licensed CC-BY-4.0 by their publisher metadata and are not vendored here.
