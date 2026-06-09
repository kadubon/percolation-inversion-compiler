# Verified Packet Promotion

`CapabilityPacketCandidate` is observable material: agent output, local files,
or connector-derived metadata. It is not reusable ECPT packet capital until a
finite promotion check accepts it.

v0.3.4 adds:

- `VerifiedCapabilityPacket`
- `PacketPromotionPolicy`
- `PacketPromotionReport`
- `PacketRejection`
- `EdgeWitnessCertificate`
- `CapabilityBasinContract`
- `BasinReachabilityReport`

Promotion checks:

1. Content evidence must bind the packet SHA-256.
2. Required verifier routes must have accepted finite-scope resolutions.
3. Receiver compatibility must be explicit.
4. Stale, hash-invalid, unsafe-route, authority-invalid, and rollback-missing
   packets fail closed.
5. Accepted edge certificates contribute confidence and false-edge residuals.
6. Residual external obligations remain on the packet ledger and do not settle.

This is the main distinction between packet volume and packet capital. The
runtime may ingest many candidates, but only verified packets should be treated
as reusable finite assets by an agent.

Example:

```powershell
uv run pic runtime step --state examples/runtime_state.json --input examples/runtime_step_input_with_evidence.json --profile production
```

The `promotion_report` field shows verified packets and rejected candidates.
Rejected packets keep concrete residual coordinates so other agents can improve
the evidence rather than silently reuse weak material.
