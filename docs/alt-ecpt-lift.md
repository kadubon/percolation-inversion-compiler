# ALT To ECPT Lift

ALT-to-ECPT lift checks whether abstraction liquidity affects concrete ECPT
phase proxy components: downstream search cost, semantic edge support, receiver
context, execution-available path density, closure, or bottleneck distance.

Commands:

```powershell
pic alt ecpt-lift --packets examples/packet_exchange/packet_envelope.example.json --graph effective_graph.json
pic alt receiver-lift --packet packet.json --receiver-context receiver.json
pic alt liquidity-to-paths --packet packet.json --graph effective_graph.json
pic alt capital-impact --reports examples/alt_lift/alt_ecpt_lift.example.json
```

Positive ALT liquidity does not automatically become ECPT packet capital. If no
ECPT component is affected, the lift report fails closed as diagnostic-only and
preserves the blockers.
