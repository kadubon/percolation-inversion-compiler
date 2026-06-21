# Release Checklist

- Confirm `pyproject.toml`, `__version__`, `CITATION.cff`, and `CHANGELOG.md` agree.
- Run local quality gates, publish safety scan, Bandit, pip-audit, and Zizmor.
- Run `uv build` and check only the target-version artifacts before any PyPI
  publication, for example
  `uv run python -m twine check dist\percolation_inversion_compiler-0.4.4-py3-none-any.whl dist\percolation_inversion_compiler-0.4.4.tar.gz`.
  Local `dist/` directories may contain old release artifacts; do not publish
  local `dist/*`. Prefer the clean GitHub Trusted Publishing workflow.
- Run `uv run python scripts\check_distribution_artifacts.py` and confirm the
  wheel contains `py.typed`, bundled theory snapshots, and only the curated
  `percolation_inversion_compiler.data.demo` assets.
- Verify the pip-first installed-package path:
  `pic demo installed-smoke --profile development`,
  `pic demo bootstrap --output-dir pic-demo`, and
  `pic runtime step --state pic-demo/runtime_state.json --input pic-demo/runtime_step_input.json --profile development`.
- Confirm README, AGENTS.md, and quickstart docs separate the PyPI path from
  the clone-recommended full workflow, including
  `git clone https://github.com/kadubon/percolation-inversion-compiler.git`
  and current `uv` install commands.
- Verify `pic doctor --profile production --fail-on never` reports expected
  fail-closed production gaps rather than silent promotion. Missing provenance
  or production identity context is a diagnostic gap, not a hidden pass.
- Generate the schema bundle, provenance manifest, SBOM, wheel, and sdist
  release assets in a clean temporary or CI workspace.
- Verify `pic routes bindings`, `pic evidence verify --profile production`,
  `pic evidence discharge --profile production`, and
  `pic doctor --profile production --provenance <manifest> --fail-on fail`.
  The provenance-backed doctor command is the release gate; a production doctor
  run without provenance is expected to fail closed.
- Verify `pic sqot schedule`, `pic ecology build-edges`, `pic ecology psi`,
  `pic ecology plan`, and `pic ecology loop` smoke tests.
- Confirm no canonical TeX/PDF files, local paths, secrets, private keys, or build artifacts are staged.
- Confirm the wheel does not include root `examples/`, local virtualenvs,
  vendored archives, model weights, serialized datasets, credential folders, or
  private-key-like files.
- Confirm `.github/workflows/pypi-publish.yml` uses PyPI Trusted Publishing,
  the `pypi` environment, `id-token: write`,
  `uv publish --trusted-publishing always`, and no API token or password fields.
- Confirm PyPI Trusted Publisher settings match repository
  `kadubon/percolation-inversion-compiler`, workflow `pypi-publish.yml`, and
  environment `pypi`.
- Confirm certificate, residual-ledger, `ExternalProofObligation`, live
  communication, and ASI-proxy phase wording remains protocol-relative and does
  not claim unobserved physical outcomes, oracle truth, or real ASI proof.
- Create or verify the annotated version tag, publish from the matching tag via
  Trusted Publishing, and verify GitHub CI/Security success on `main`.
