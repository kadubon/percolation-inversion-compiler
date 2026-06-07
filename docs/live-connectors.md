# Live Connectors

v0.3.2 keeps optional live connector ingestion for GitHub, Zenodo, and arXiv
metadata. Connectors are intentionally small and fail closed: network errors,
rate limits, missing optional dependencies, and authentication failures return
diagnostic `PacketIngestionReport` records rather than accepted packets.

Install with all extras:

```powershell
uv sync --all-extras --dev
```

Commands:

```powershell
uv run pic ecology ingest --source kadubon/percolation-inversion-compiler --kind github
uv run pic ecology ingest --source https://zenodo.org/records/20526451 --kind zenodo
uv run pic ecology ingest --source arxiv:salience queue --kind arxiv
```

Connector policy:

- GitHub uses public REST metadata. `GITHUB_TOKEN` may be set in the environment
  to raise rate limits; no token is stored in the repo or output examples.
- Zenodo uses record metadata and never vendors PDFs or TeX files.
- arXiv uses the public Atom API and stores only derived packet metadata.
- CI tests use fixtures or mocks, not live network availability.

Connectors produce candidate packets. A candidate still needs edge witnesses,
verifier routes, residual accounting, and downstream checker output before an
agent can use it for operational planning.
