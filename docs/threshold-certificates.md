# Threshold And Certificate Reports

Phase Lab threshold status compares a `PhaseWindowObservation` against an
`ASIProxyThresholdSpec`. Certificate generation emits a candidate only when all
finite requirements pass; otherwise it emits abstention or rejection details.

Example:

```powershell
pic phase lab threshold-status --store pic-phase-lab --threshold examples/thresholds/asi_proxy_development.json
pic phase lab certify --store pic-phase-lab --threshold examples/thresholds/asi_proxy_development.json
```

These reports are protocol-relative only. They do not prove real ASI or physical
truth. `accepted=true` on a scoped certificate candidate still does not imply
global settlement, hidden authority, or autonomous action safety. Residual
obligations remain explicit.
