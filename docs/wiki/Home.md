# Percolation Inversion Compiler Wiki

Percolation Inversion Compiler, or PIC, is a local checker/compiler for AI
agent output, evidence, unfinished work, safe reuse decisions, and
protocol-relative ASI-proxy phase diagnostics. The current local implementation
target is v0.8.0.

PIC helps a person or agent answer:

- What is being claimed?
- What evidence is attached?
- What residual work remains?
- Which verifier, CCR task, or next check should handle the missing work?
- Can a result be reused under a limited scope?
- Why is a result useful but still not settled?

PIC treats agent output as candidate work. It does not treat confident text,
high priority, raw packet volume, MCP descriptors, A2A handoffs, or provider
evidence as proof.

## Fastest Start

```bash
python -m pip install percolation-inversion-compiler
pic agent check --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic phase plan --compact --text "Candidate packet: route evidence and preserve residuals." --profile development
pic demo installed-smoke --profile development
```

`accepted=true` can be useful while `settled=false` remains normal. It means PIC
kept unresolved work visible.

## What v0.8.0 Adds

v0.8.0 adds a target-valid ASI-proxy/CARA acceleration layer:

- declared target sets;
- baseline upper envelopes;
- runtime capital witnesses;
- phase acceleration reports;
- stricter physical dispatch readiness checks;
- MCP descriptor reports and invocation preflight;
- A2A agent-card and handoff reports;
- SQOT protocol/resource/probe diagnostics;
- BIT MEC frontier, compiler, CEGAR, and dynamic-regime reports;
- CCR roundtrip fixtures under `examples/asi_proxy_acceleration_bundle/`.

`certified_acceleration_candidate=true` is not real ASI proof. It means the
declared target, baseline, and admitted lower-bound capital witnesses satisfy
the v0.8 protocol-relative comparison with positive margin.

Reports fail closed: if the target laws or authority are not accepted, the
baseline is stale or missing, admitted capital witnesses are absent, or an MCP
descriptor changed after approval, PIC returns explicit blockers instead of
promoting the claim.

## Safety Boundary

PIC does not prove real ASI, physical truth, simulator truth, oracle truth,
legal authority, policy success, or arbitrary agent correctness.

PIC does not grant authority to run shell commands, mutate repositories, call
providers, use credentials, change model weights, or self-rewrite.

`provider_dispatch_ready` is not dispatch. `physical_dispatch_ready` is not
physical outcome proof. Observation evidence is not physical outcome proof
without scoped verifier acceptance.

## Search Terms

AI agent output checker, LLM output validation, evidence routing, proof
obligations, residual ledger, capability packet, ECPT, BIT, TRC, SQOT, ALT,
ASI-proxy acceleration, CARA, runtime capital witness, baseline upper envelope,
MCP descriptor report, A2A handoff report, CCR interop, phase acceleration
report, `settled=false`.
