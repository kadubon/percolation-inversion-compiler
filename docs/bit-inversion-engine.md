# BIT Inversion Engine

The v0.5.0 BIT engine diagnoses practical bottlenecks from an
`EffectivePacketGraph` and emits recommendation-only inversion candidates.
Bottleneck classes include missing evidence, verifier route, semantic edge,
rollback support, authority, receiver context, identity/Sybil readiness, stale
packet state, false liquidity, salience obstruction, queue occupation, missing
ALT lift, trace-boundary mismatch, and external-domain obligations.

Commands:

```powershell
pic bit diagnose --graph effective_graph.json --output bottlenecks.json
pic bit invert --bottlenecks bottlenecks.json --output inversion_candidates.json
pic bit mec --bottleneck <id> --bottlenecks bottlenecks.json
pic bit certificate --candidate inversion_candidates.json
```

Activation gain is a protocol-relative phase-proxy estimate. An inversion
candidate is not execution authority and does not mutate shells, repositories,
networks, models, or external systems.

