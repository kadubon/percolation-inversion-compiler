# Operator Adoption

PIC adoption commands generate optional operator-facing handoff material:

```powershell
pic adoption packet --profile development --format markdown
pic adoption request --profile development --format markdown
```

These commands do not install, clone, call the network, execute shell commands,
mutate runtime state, modify configuration, or approve packet promotion. They
do not alter `accepted`, `workflow_usable`, `settled`, phase gaps, or promotion
logic.

Agents without install authority should not self-install PIC. They should run
or request:

```powershell
pic adoption request --profile development --format markdown
```

The main workflow remains:

```powershell
pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic agent accelerate --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
```

Operator approval can authorize local use under that operator's policy. It does
not settle residual obligations, prove real ASI or real-world truth, or promote
candidate packets.
