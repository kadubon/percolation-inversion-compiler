# Agent Network Intake Walkthrough

This directory contains offline fixtures for broad intake and agent-to-agent exchange.
The commands are live-capable by default for explicit sources. Local fixture commands do not
contact the network; use `--no-allow-live-connectors` for a local-only dry run.

```powershell
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic ecology discover-web --source examples/agent_network/page.html
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
uv run pic agent message ingest --message examples/agent_network/agent_message.json
uv run pic agent inbox export --inbox examples/agent_network/inbox.json
```

Optional live metadata intake uses explicit sources:

```powershell
uv run pic ecology ingest-general --source https://example.org --kind web-page
uv run pic ecology ingest-general --source https://example.org --kind web-page --no-allow-live-connectors
```

Failure fixtures are included for fail-closed checks:

```powershell
uv run pic ecology ingest-general --source examples/agent_network/malformed_feed.xml --kind rss
uv run pic agent message verify --message examples/agent_network/expired_message.json --profile production
uv run pic ecology ingest-general --source examples/agent_network/replay_inbox.json --kind agent-inbox
```

Policy and bridge fixtures:

- `policy_controlled_web.json`: operator-reviewed web/feed intake profile.
- `policy_adversarial_network.json`: tighter profile for hostile network environments.
- `general_intake_report.example.json`: minimal candidate-only report.
- `runtime_bridge_report.example.json`: SQOT/runtime classification for that report.
- `agent_message_signed_shape.json`: signed-field shape with no private key material.

For live HTTP(S), the source must be explicit and the intake/runtime policy must allow
live connectors. Reports include
sanitized provenance, `web_fetch_reports`, and residual coordinates, not query secrets or local
absolute paths. HTTP(S) redirect chains are validated URL-by-URL, and live discovery fetches each
visited resource once. Local HTML discovery follows relative links only inside the seed file
directory and does not fetch external links found in a local fixture.

External content becomes packet candidates only. It is not verified packet capital and does not
settle physical, oracle, policy, legal identity, or real ASI claims.
Raw external packet volume also does not improve positive Psi components such as G, SD, DE,
BR, or AC, and cannot accept a collective certificate. Candidate-only phase attempts are
kept as residual debt until semantic edge, route, identity, rollback, and residual checks promote
the packet.
