# SQOT Queue Sovereignty

The v0.5.0 SQOT controller reports queue occupation, salience obstruction,
diagnostic reserve, quarantine decisions, and rebalance plans over an effective
packet graph.

Commands:

```powershell
pic sqot diagnose-queue --graph effective_graph.json
pic sqot salience-obstruction --graph effective_graph.json
pic sqot rebalance --graph effective_graph.json
pic sqot quarantine --graph effective_graph.json
pic sqot reserve-check --graph effective_graph.json
```

Rebalance and quarantine outputs are report objects. They do not apply changes,
delete packets, settle obligations, or execute verifier work. Diagnostic reserve
is explicit so low-value queue occupation cannot silently displace high-value
verification or residual-preservation work.

