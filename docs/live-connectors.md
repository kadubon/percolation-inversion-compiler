# Live Connectors And General Intake

PIC supports optional live connector ingestion for GitHub, Zenodo, arXiv, and bounded
general HTTP(S)/feed sources. Connectors are intentionally small and fail closed:
network errors, rate limits, missing optional dependencies, authentication failures,
private-network targets, unsupported content types, and oversized responses return
diagnostic reports rather than verified packet capital.

Install with all extras:

```powershell
uv sync --all-extras --dev
```

Commands:

```powershell
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest --source kadubon/percolation-inversion-compiler --kind github
uv run pic ecology ingest --source https://zenodo.org/records/20526451 --kind zenodo
uv run pic ecology ingest --source arxiv:salience queue --kind arxiv
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic ecology discover-web --source examples/agent_network/page.html
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
```

Live web intake remains explicit. The CLI sets both the source descriptor and intake policy
only when `--allow-live-connectors` is present; runtime/service callers must also set their
own runtime config flag.

```powershell
uv run pic ecology ingest-general --source https://example.org --kind web-page --allow-live-connectors
uv run pic ecology discover-web --source https://example.org --allow-live-connectors
```

Connector policy:

- GitHub uses public REST metadata. `GITHUB_TOKEN` may be set in the environment
  to raise rate limits; no token is stored in the repo or output examples.
- Zenodo uses record metadata and never vendors PDFs or TeX files.
- arXiv uses the public Atom API and stores only derived packet metadata.
- General HTTP(S) intake is bounded by scheme, private-network rejection, redirect limit,
  timeout, content type, byte limit, depth, and page count.
- Use `local_only`, `controlled_web`, `federated_agents`, `production_network`, or
  `adversarial_network` presets to make communication constraints explicit and portable.
- Local fixture intake for HTML/feed/NDJSON uses the same byte limit, so staged external
  artifacts cannot bypass size controls.
- RSS/Atom parsing uses a defused XML parser and treats entity expansion as diagnostic input.
- Fetch reports preserve sanitized provenance and `web_fetch_reports`: final URL without query
  tokens, validated redirect chain, raw content SHA-256, byte count, content type,
  robots/rate decision, and residual coordinates.
- Live web discovery fetches each visited page once and uses the same bounded response for
  packet creation and link extraction.
- Local HTML discovery follows only links inside the seed file directory; `..` path escapes are
  ignored.
- Web discovery does not execute scripts, submit forms, or mutate repositories.
- CI tests use fixtures or mocks, not live network availability.

Connectors produce candidate packets. A candidate still needs edge witnesses, verifier routes,
identity/issuer checks, rollback checks, residual accounting, and downstream checker output
before an agent can use it for operational planning. Use `pic ecology bridge-runtime` to map
general intake into SQOT diagnostic/verifier/quarantine work while preserving
`ecpt_phase_contribution_allowed=false`.
