# Phase Ecology Lab

Phase Ecology Lab is the v0.5.0 local workbench for windowed, multi-packet
phase diagnostics. It stores existing PIC reports and packet sidecars as inert
data, builds effective packet graphs, observes window metrics, detects closure
and execution-available paths, and emits threshold/certificate candidates.

It is protocol-relative only. It does not prove real ASI, physical truth, oracle
truth, legal truth, policy truth, or autonomous action safety. It does not
execute embedded command text, `safe_commands`, tool traces, shell snippets,
network requests, repository mutations, or model changes.

Quick path:

```powershell
pic phase lab init --output-dir pic-phase-lab
pic phase lab ingest --store pic-phase-lab --report examples/phase_lab/runtime_report_1.json
pic phase lab observe --store pic-phase-lab --window latest
pic phase lab graph --store pic-phase-lab
pic phase lab closure --store pic-phase-lab
pic phase lab executable-paths --store pic-phase-lab
pic phase lab certify --store pic-phase-lab --threshold examples/thresholds/asi_proxy_development.json
```

The store is SQLite plus a small manifest. Exported bundles sanitize local paths
and preserve residual ledgers. `settled=false` remains the default for
diagnostic and recommendation-only outputs.

