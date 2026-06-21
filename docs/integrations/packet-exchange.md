# Packet Exchange

Packet exchange commands are data-only sidecars:

```powershell
pic packet export --report runtime-report.json --output packet.json
pic packet inspect --packet packet.json
pic packet merge --packets packet-a.json --packets packet-b.json --output merged-packets.json
pic packet lineage --packet merged-packets.json
```

Packet content is treated as data, not instruction. Inspection may report
embedded command-like strings, but it never executes them. Merge deduplicates by
content digest, preserves residual carry-forward data, and keeps candidate-only
and unsettled status.

Packet exchange does not promote packets, settle obligations, approve
execution, or prove real-world truth.
