# Local Runtime HTTP Service

The optional v0.3.0 service exposes the ECPT active runtime over loopback HTTP.
It is behind the `[server]` extra and uses the FastAPI/Uvicorn stack. The
service returns the same finite certificate, proof-obligation, and residual
ledger records as the CLI and SDK.

```powershell
uv sync --all-extras --dev
$env:PIC_RUNTIME_TOKEN = "replace-with-local-token"
uv run pic runtime service --host 127.0.0.1 --port 8765 --profile production
```

Production policy:

- Binds to `127.0.0.1` by default.
- Requires `Authorization: Bearer <PIC_RUNTIME_TOKEN>`.
- Does not store bearer tokens, private keys, or local absolute paths.
- Does not call live connectors unless request JSON explicitly opts in and the
  service was started with `--allow-live-connectors`.
- Returns deterministic diagnostic JSON for failures rather than stack traces.

Endpoints:

- `GET /health`
- `POST /runtime/step`
- `POST /runtime/loop`
- `POST /ecology/ingest`
- `POST /evidence/verify`
- `GET /schemas/openapi.json`

Example service request:

```powershell
uv run pic runtime export-openapi --output runtime-openapi.json
```

The same payload shape is stored in
`examples/runtime_service_step_request.json`. The service response is a
`RuntimeStepReport`, so an agent can use the same schema bundle for CLI, SDK,
and HTTP integration.
