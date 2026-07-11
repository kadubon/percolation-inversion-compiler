# Security

Public inputs reject coercion, non-finite numbers, negative zero, excessive
depth, oversized files, excessive JSONL lines, and unsafe YAML aliases.

Operation security includes digest binding, expiry, nonce replay protection,
signer independence, secret redaction, SSRF controls, redirect denial, fixed
process binaries, symlink checks, timeouts, byte limits, and fail-closed crash
reconciliation.

Never place private keys or provider credentials in plans, reports, examples,
issues, or logs.

