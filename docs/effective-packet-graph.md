# Effective Packet Graph

The effective packet graph separates packet volume from packet contribution.
Candidate-only packets, registry metadata, raw external volume, stale packets,
hash-invalid packets, authority-invalid packets, verification-blocked packets,
and salience-blocked packets can appear in the graph, but they do not increase
positive phase components.

Positive contribution requires accepted or certificate-admissible packet
structure, retrievability, evidence-supported semantic edges, visible residuals,
scope-bounded authority where needed, rollback or safe-abort support where
needed, and validity-domain compatibility.

Commands:

```powershell
pic phase lab graph --store pic-phase-lab --output effective_graph.json
pic ecology effective-graph --reports examples/phase_lab/runtime_report_1.json --output effective_graph.json
```

The graph builder treats agent text and external content as data. It does not
convert declared status into evidence and does not execute any report field.

