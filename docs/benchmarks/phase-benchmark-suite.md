# Phase Benchmark Suite

`pic phase benchmark-suite` is a diagnostic-only benchmark sidecar:

```powershell
pic phase benchmark-suite --profile development --format json
pic phase benchmark-suite --profile development --format markdown
```

It measures protocol-relative workflow properties:

- missing obligation visibility
- unsafe promotion prevention
- residual preservation
- settled blocker visibility
- next action specificity
- reusable packet candidate visibility
- candidate-only false-promotion prevention
- phase gap visibility
- bottleneck ranking coverage

Benchmark scores do not set `settled=true`, approve execution, promote packets,
or imply real ASI acceleration. The bundled default cases are in code, so the
command works from a PyPI-installed package. Root `examples/benchmarks/...`
files are source-checkout examples only.
