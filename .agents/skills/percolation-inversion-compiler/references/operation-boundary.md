# Operation boundary

The default skill path is non-executing. Use a consequential path only with an explicit request, host authorization, scoped identity/authority, and a selected adapter. Preserve the sequence: adapter-check, plan, preflight, approve, dispatch, verify, reconcile. Each transition can fail or leave residuals. A receipt documents a provider-reported event; verification and reconciliation must not silently infer a physical outcome, consent, legal authority, or settlement.
