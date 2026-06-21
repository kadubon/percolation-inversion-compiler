# Phase Dashboard

The phase dashboard is an observation-only sidecar:

```powershell
pic phase dashboard --profile development --format json
pic phase dashboard --profile development --format markdown
pic phase observe --reports runtime-step.json --output observation.json
```

Metrics include packet candidate counts, accepted packet counts, unsettled
candidate counts, residual debt, missing obligations, identity and route
blockers, SQOT pressure, phase gaps, bottleneck counts, safe command counts,
settled blockers, candidate-only reasons, and promotion blockers.

The dashboard does not claim a real ASI phase transition, does not treat raw
external volume as positive phase progress, does not alter runtime state, and
does not introduce approval requirements.
