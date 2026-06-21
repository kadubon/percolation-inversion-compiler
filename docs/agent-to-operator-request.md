# Agent To Operator Request

Use this sidecar when an agent has found PIC but lacks install, clone, or tool
authority.

```powershell
pic adoption request --profile development --format markdown
```

The request states that PIC treats AI-agent output as candidate work, preserves
evidence and residual ledgers, does not execute proposed actions, does not
bypass approval policy, and does not prove real ASI or real-world truth.

Suggested first operator-reviewed command:

```powershell
python -m pip install percolation-inversion-compiler
pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
```

Suggested next command:

```powershell
pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
```

The request is documentation only. It does not create approval state and does
not change the main PIC workflow.
