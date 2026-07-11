# Migrating From v1.0 To v1.1

Version 1.1 is additive: existing v1 command names and JSON fields remain
available. Important public boundaries are stricter:

- JSON/YAML no longer coerces numeric strings or string booleans;
- invalid and expired timestamps block instead of appearing fresh;
- unknown Phase coordinates abstain instead of using default zero;
- BIT class scores remain priority heuristics until a witness certifies gain;
- SQOT reserve requires measured item costs;
- ALT ignores self-reported acceptance and lift;
- runtime task admission reports `executed=false` until explicit operation
  dispatch; and
- acceleration measurement requires paired baseline and candidate metrics.

PIC-TS now implements typed `runtime compare` and
`runtime certify-acceleration` commands and exports the
`percolation-inversion-compiler-ts/runtime` subpath.

Real-world effects use
`operation adapter-check|plan|preflight|approve|dispatch|verify|reconcile`.
AFST and all ordinary check commands remain non-executing.

