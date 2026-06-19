# Portability Conformance Pack

This directory contains stable JSON outputs for cross-language implementations.
Each file is intended to validate against the public schema named in
`manifest.json`.

The examples are protocol-relative and intentionally keep `settled=false` where
external or route-level obligations remain. Ports should preserve the separate
meanings of `accepted`, `operationally_usable`, `finite_checks_passed`, and
`settled` rather than collapsing them into one success flag.
