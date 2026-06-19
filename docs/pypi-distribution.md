# PyPI Distribution

v0.4.2 is the practical-readiness patch for
`percolation-inversion-compiler` on PyPI. It keeps existing schemas and
commands stable while making the wheel useful as an installed agent-output and
workflow checker, with bundled demo data, snapshots, schema export, and
residual-preserving runtime commands.

## Install Modes

Core runtime and CLI:

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
pic agent runbook --profile development
pic agent check --text "Candidate packet: preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
pic agent message receive --inbox pic-demo/agent_inbox.json
pic agent inbox verify --inbox pic-demo/agent_inbox.json
pic agent intake --text "Candidate packet: preserve residuals." --profile development
pic snapshot list
pic schema --type AgentIntakeReport
```

Optional identity, live-intake, and local service extras:

```powershell
python -m pip install "percolation-inversion-compiler[identity,connectors,server]"
```

Full research/development extras:

```powershell
python -m pip install "percolation-inversion-compiler[all]"
```

The wheel includes a curated installed workflow bundle under package data.
`pic agent check` works directly on inline text or user files. `pic demo
bootstrap` exports runtime, agent-output, policy, local agent-message relay, and ALT example JSON to a
directory the user controls. The full root `examples/...` tree, canonical TeX
audits, and release engineering checks require a source checkout. The wheel is
intended for practical runtime, schema, snapshot, curated workflow, and CLI use;
the repository is the full fixture and development workspace.

Live HTTP/feed intake is bounded and candidate-only by default when an explicit source is
supplied. Use `--no-allow-live-connectors` for local-only smoke tests. Default-live mode does
not grant background crawling, shell execution, repository mutation, or hidden promotion to
`settled`.

## Clone Boundary

Clone when an agent needs the full `examples/...` tree, canonical TeX audits,
fixture-backed collective phase workflows, local service tests, release
provenance, SBOM generation, or development checks. Basic real use does not
require a checkout.

Install `uv` on Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Install `uv` on macOS/Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Fallback:

```powershell
python -m pip install uv
```

Clone and sync:

```powershell
git clone https://github.com/kadubon/percolation-inversion-compiler.git
cd percolation-inversion-compiler
uv sync --all-extras --dev
```

## Trusted Publishing

PyPI publication uses the `PyPI Publish` GitHub Actions workflow. It can be
triggered from a GitHub Release or manually from the matching version tag,
verifies that the release tag matches the package version, builds the wheel and
sdist, runs `twine check`, and uses `uv publish --trusted-publishing always`
with PyPI Trusted Publishing through GitHub OIDC.

Required PyPI Trusted Publisher settings:

- project name: `percolation-inversion-compiler`
- owner: `kadubon`
- repository: `percolation-inversion-compiler`
- workflow filename: `pypi-publish.yml`
- environment name: `pypi`

No `PYPI_API_TOKEN`, password, private key, or long-lived upload credential is
stored in the repository. Missing Trusted Publisher configuration should fail
the publication workflow instead of falling back to token upload.

## Pre-Publish Checks

Run these before publishing or republishing the v0.4.2 distributions:

```powershell
uv run pytest
uv run pytest --cov=percolation_inversion_compiler --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv build
uv run python -m twine check dist\*.whl dist\*.tar.gz
uv run python scripts\check_distribution_artifacts.py
uv run bandit -q -r src scripts
uv run pip-audit
uv run python scripts\validate_citation.py
uv run python scripts\check_publish_safety.py
git diff --check
```

The distribution-artifact check verifies the wheel contains `py.typed`, bundled
snapshots, and the curated installed-demo assets. The publish-safety check
verifies project URLs, PyPI keywords, `twine` metadata checking, the SHA-pinned
checkout/setup actions, the `uv publish` Trusted Publishing command, absence of
upload tokens, absence of `llms.txt`, and the existing local-path,
vendored-artifact, and secret scans.

## Safety Boundary

PyPI publication does not change the scientific contract. The package helps
agents route finite certificates, proof obligations, residual ledgers, external
knowledge intake, SQOT queues, ALT abstraction capital, and ECPT collective
phase reports. It does not prove real ASI, physical outcomes, simulator
outcomes, oracle truth, legal identity, or world-global Sybil uniqueness.
