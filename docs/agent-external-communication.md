# Agent External Communication

This guide shows how an AI agent can use external communication without leaving the
fail-closed ECPT runtime boundary. External content improves packet availability and verifier
routing, but it remains candidate evidence until downstream checks accept it.

## Communication Surfaces

- Local files and fixtures: safe default, no network.
- General intake: bounded HTTP(S), local HTML, RSS/Atom, JSON feed, and NDJSON.
- Specialized metadata: GitHub, Zenodo, and arXiv connectors.
- Agent-to-agent exchange: local JSON/JSONL inboxes and `AgentMessageEnvelope` records.
- Runtime service: optional loopback HTTP service with bearer auth in production.

## Safe First Commands

```powershell
uv run pic agent communication-guide --profile development --no-allow-live-connectors
uv run pic agent network-readiness --profile development --no-allow-live-connectors
uv run pic ecology policy explain --profile controlled_web
uv run pic ecology ingest-general --source examples/agent_network/feed.xml --kind rss
uv run pic ecology bridge-runtime --report examples/agent_network/general_intake_report.example.json
uv run pic agent message contract --message examples/agent_network/agent_message.json
uv run pic ecology ingest-general --source examples/agent_network/page.html --kind web-page
uv run pic agent message ingest --message examples/agent_network/agent_message.json
```

Live web intake is explicit:

```powershell
uv run pic ecology ingest-general --source https://example.org --kind web-page --allow-live-connectors
uv run pic ecology discover-web --source https://example.org --allow-live-connectors
```

## Policy Boundary

- Network access is disabled by default.
- Live intake requires three aligned opt-ins: the source descriptor, the request/CLI flag, and
  the runtime or service policy must all set `allow_live_connectors=true`.
- Private, loopback, and link-local hosts are rejected.
- Discovery is bounded by depth, page count, byte count, redirects, timeout, and content type.
- Local HTML/feed/NDJSON fixture intake uses the same byte limit, so agents can safely stage
  external communication artifacts on disk before ingesting them.
- Feed and inbox intake also have entry-count limits (`max_feed_entries` and
  `max_agent_messages_per_inbox`). A large queue becomes diagnostic work instead of raw packet
  volume.
- HTTP(S) intake validates every URL in the redirect chain, not only the final URL.
- Live discovery reuses the fetched body for packet creation and link extraction, so each
  visited resource is fetched once under the active policy.
- Scripts are not executed, forms are not submitted, and repositories are not mutated.
- Tokens such as `GITHUB_TOKEN` and `PIC_RUNTIME_TOKEN` are environment-only.
- Reports include sanitized public source refs, content SHA-256 digests, redirect-chain
  summaries, robots/rate diagnostics, `web_fetch_reports`, and residual coordinates. They do
  not expose query tokens, cookies, bearer tokens, or local absolute paths.
- Early failures such as disabled live access, unsupported schemes, private hosts, missing
  `httpx`, robots uncertainty, and transport errors still emit `web_fetch_reports`, so agents
  can inspect one stable field for HTTP(S) intake diagnostics.
- Diagnostic residual coordinates include source and reason digests. Agents can therefore keep
  separate repair tasks for separate failing sources instead of collapsing all HTTP failures into
  one undifferentiated queue item.
- `candidate_only=true` and `ecpt_phase_contribution_allowed=false` are the default for all
  general intake reports. External candidate volume by itself cannot improve positive Psi
  components such as G, SD, DE, BR, or AC, and cannot accept a collective phase certificate.
  Candidate exclusion is recorded as residual debt.
- `policy_digest` and `source_policy_decisions` let an agent replay exactly which communication
  envelope was used for a source.
- For HTTP(S) failures, `residual_ledger.coordinates` and
  `provenance[].residual_coordinates` point to the same diagnostic coordinates. Carry those
  coordinates forward into SQOT or verifier-routing tasks; do not synthesize a new settled claim
  from a connector failure.
- Local HTML discovery follows relative links only inside the seed file directory. It does not
  use `..` links to read sibling directories as external packet sources.
- RSS/Atom parsing uses a defused XML parser; entity expansion and malformed XML become
  diagnostic residuals instead of parser-side trust.

## Profile Recipes

Use `pic ecology policy explain --profile <profile>` before live intake.

| Profile | Use | Default behavior |
| --- | --- | --- |
| `local_only` | Clone-time orientation and CI fixtures | no live fetch, bounded local feed/page/message intake |
| `controlled_web` | Operator-approved web metadata | HTTPS, bounded pages/bytes, diagnostic residuals |
| `federated_agents` | Agent-to-agent packet exchange | signed messages and identity context required |
| `production_network` | Production external intake | HTTPS, signed messages, identity context, robots uncertainty diagnostic |
| `adversarial_network` | Hostile or Sybil-prone environments | tighter redirects/pages/bytes and signed identity context |

## SQOT And ECPT Mapping

Run the bridge step after any general intake report:

```powershell
uv run pic ecology bridge-runtime --report general-intake-report.json
```

The bridge classifies packets as `diagnostic_work`, `verifier_work`, `quarantine_work`, or
`candidate_only`. SQOT can schedule those records as attention-queue work, but ECPT phase
contribution remains disabled until separate semantic edge, verifier route, identity, rollback,
and residual checks promote a packet. Low-level Psi calculation also excludes raw external
candidate packets, candidate-only closure witnesses, candidate-only execution paths, and
candidate-only basin paths from positive phase components. This preserves ECPT's distinction
between packet availability and accepted collective phase progress.

## Failure Repair Table

| Failure | Repair path |
| --- | --- |
| live opt-in mismatch | rerun local-only or set source/request, policy, and runtime flags together |
| host/path outside policy | choose a narrower approved source or update a reviewed policy file |
| oversized source or feed | split the source and preserve the budget residual coordinate |
| malformed feed/XML/JSON | quarantine the source and request a corrected evidence envelope |
| missing production signature | derive identity context and request a signed `AgentMessageEnvelope` |
| replay nonce | keep the nonce ledger and ask the peer for a fresh message |
| bridge quarantine | inspect `quarantine_packet_ids` and do not promote the packet |

## Agent-To-Agent Messages

Use `AgentMessageEnvelope` for local peer exchange. A message records content hash, sender,
optional receiver, replay nonce, declared verifier routes, evidence refs, and optional issuer
refs.

```powershell
uv run pic agent message create --sender agent:alice --text "Candidate packet: preserve residuals." --output message.json
uv run pic agent message contract --message message.json
uv run pic agent message verify --message message.json --profile development
uv run pic agent inbox init --inbox inbox.json
uv run pic agent inbox append --inbox inbox.json --message message.json
uv run pic ecology ingest-general --source inbox.json --kind agent-inbox
```

Message verification checks the content digest, optional replay nonce, `issued_at`,
`expires_at`, issuer refs, and signature fields. In `production` and `adversarial` profiles,
the signature fields must also connect to an accepted identity/Sybil context:

```powershell
uv run pic identity derive-context --population examples/agent_population_signed.json --profile production --output identity-context.json
uv run pic agent message verify --message message.json --profile production --identity-context identity-context.json
```

If identity context is absent, the message is retained as diagnostic candidate work; it cannot
become verified packet capital. Signed messages prove protocol-relative key control only; they
do not prove legal identity, global uniqueness, real ASI, physical outcomes, simulator truth, or
oracle truth.

Large inboxes are bounded by policy. If a peer sends more messages than the active profile
allows, keep the residual coordinate and route a smaller signed batch rather than treating queue
volume as ECPT phase progress.

## Output Fields To Inspect

- `accepted`
- `settled`
- `packets`
- `provenance`
- `web_fetch_reports`
- `rejected_sources`
- `reasons`
- `residual_ledger`
- `signature_required`
- `replay_detected`
- `identity_verified`
- `nonce_ledger`
- `source_kind`

`settled=false` is expected. It means the intake produced candidate work while preserving
unresolved obligations for later verifier routes.
