# PyPI Distribution

v0.5.0 is the Phase Ecology Lab practical runtime snapshot for
`percolation-inversion-compiler` on PyPI. It keeps v0.4.4 compact agent and
phase-planner behavior stable while adding local windowed graph diagnostics,
BIT bottleneck inversion, SQOT queue diagnostics, ALT-to-ECPT lift checks, TRC
trace adapters, bundled Phase Lab demo data, snapshots, schema export, and
residual-preserving runtime commands.

## Install Modes

Core runtime and CLI:

```powershell
python -m pip install percolation-inversion-compiler
pic agent explain
pic agent autonomy-audit --profile development --format json
pic agent check --compact --text "Candidate packet: preserve residuals." --profile development
pic agent runbook --profile development
pic phase plan --compact --text "Candidate packet: preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: preserve residuals." --profile development
pic agent check --text "Candidate packet: preserve residuals." --profile development
pic demo installed-smoke --profile development
pic demo bootstrap --output-dir pic-demo
pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development
pic phase benchmark-suite --profile development --format json
pic phase dashboard --runtime-report pic-demo/runtime_step_report.json --profile development
pic phase lab init --output-dir pic-demo/phase-lab
pic phase lab ingest --store pic-demo/phase-lab --report pic-demo/phase_lab_runtime_report.json
pic phase lab observe --store pic-demo/phase-lab --window latest
pic phase lab graph --store pic-demo/phase-lab
pic phase lab closure --store pic-demo/phase-lab
pic phase lab executable-paths --store pic-demo/phase-lab
pic phase lab certify --store pic-demo/phase-lab --threshold pic-demo/phase_lab_threshold.json
pic packet inspect --packet pic-demo/packet_envelope.json
pic packet merge --packets pic-demo/packet_envelope.json --output pic-demo/merged-packets.json
pic packet lineage --packet pic-demo/merged-packets.json
pic phase observe --reports pic-demo/phase_dashboard.json --output pic-demo/observation.json
pic audit canonical-readiness --profile development --format json
pic agent message receive --inbox pic-demo/agent_inbox.json
pic agent inbox verify --inbox pic-demo/agent_inbox.json
pic agent intake --text "Candidate packet: preserve residuals." --profile development
pic snapshot list
pic audit canonical-readiness --profile development --format json
pic schema --type AgentIntakeReport
pic schema --type CanonicalImplementationReadinessReport
pic schema --type PhaseAccelerationPlan
```

Optional identity, live-intake, and local service extras:

```powershell
python -m pip install "percolation-inversion-compiler[identity,connectors,server]"
```

Agent-oriented full extra, without the science/OT/LP research stack:

```powershell
python -m pip install "percolation-inversion-compiler[agent-full]"
pic agent network-readiness --profile development
pic agent communication-guide --profile development
```

Full research/development extras:

```powershell
python -m pip install "percolation-inversion-compiler[all]"
```

The wheel includes a curated installed workflow bundle under package data.
`pic agent check` works directly on inline text or user files. `pic demo
bootstrap` exports runtime, agent-output, policy, local agent-message relay,
ALT example JSON, packet sidecar, runtime report, phase dashboard JSON, and
Phase Lab fixture JSON to a directory the user controls. The full root `examples/...` tree, canonical TeX
audits, and release engineering checks require a source checkout. The wheel is
intended for practical runtime, schema, snapshot, curated workflow, and CLI use;
the repository is the full fixture and development workspace.

`pic phase plan --compact`, `pic agent accelerate --compact`, and `pic audit
canonical-readiness` are installed package commands. The canonical-readiness
report uses bundled derived snapshots, not vendored TeX/PDF files, and returns
ECPT/BIT/TRC/SQOT/ALT coverage totals, external residual categories, finite
upgrade candidates, and argv-safe next actions. These outputs are
recommendation-only and keep `settled=false`.

The v0.5.0 Phase Lab commands ingest local JSON/YAML reports as data, derive
effective packet graphs, window observations, closure witnesses, execution
available paths, threshold status, and certificate candidates. They do not
execute packet text, change repository state, fetch background sources, or
promote diagnostic output to `settled=true`.

Live HTTP/feed intake is bounded and candidate-only by default when an explicit source is
supplied. Use `--no-allow-live-connectors` for local-only smoke tests. Default-live mode does
not grant background crawling, shell execution, repository mutation, or hidden promotion to
`settled`.

## Clone Boundary

Clone when an agent needs the full `examples/...` tree, canonical TeX source audits,
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

Run these before publishing or republishing the v0.5.0 distributions:

```powershell
uv run pytest
uv run pytest --cov=percolation_inversion_compiler --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv build
uv run python -m twine check dist\percolation_inversion_compiler-0.5.0-py3-none-any.whl dist\percolation_inversion_compiler-0.5.0.tar.gz
uv run python scripts\check_distribution_artifacts.py --dist-dir dist --version 0.5.0
uv run bandit -q -r src scripts
uv run pip-audit
uv run python scripts\validate_citation.py
uv run python scripts\check_publish_safety.py
```

The distribution-artifact check verifies the wheel contains `py.typed`, bundled
snapshots, curated installed-demo assets, and Phase Lab demo fixtures. The publish-safety check
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
