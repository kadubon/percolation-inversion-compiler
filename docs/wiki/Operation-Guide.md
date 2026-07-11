# Operation Guide

Ordinary checks never dispatch. The only operation lifecycle is:

`adapter-check -> plan -> preflight -> approve -> dispatch -> verify -> reconcile`

Dispatch requires a digest-bound plan, fresh scoped signatures, an unused nonce,
resource limits, and adapter restrictions. HTTPS adapters block SSRF-prone
addresses and redirects. Process adapters require fixed executable digests,
fixed arguments, `shell=false`, timeouts, and output limits.

A receipt proves only a provider call. Independent signed observation is needed
for `physical_outcome_verified=true`; `physical_outcome_proven` stays false.

