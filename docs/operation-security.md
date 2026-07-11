# Explicit Operation Security

PIC never dispatches a side effect from check, AFST, phase, BIT, SQOT, ALT, or
runtime admission commands. The explicit sequence is:

1. `adapter-check` validates a fixed HTTPS or process adapter.
2. `plan` binds adapter digest, parameters or body digest, resource limits,
   scope, risk, expiry, nonce, idempotency key, rollback, hazard, verifier
   contract, and secret names.
3. `approve` signs the exact canonical plan with an environment-resolved
   Ed25519 key.
4. `preflight` rechecks current time, signatures, secrets, DNS/IP, executable
   digest, and risk requirements.
5. `dispatch` consumes the nonce once and calls only the fixed adapter.
6. `verify` checks an independent signed outcome observation.
7. `reconcile` reports completed and dispatch-uncertain nonce records.

Read-only access needs explicit policy. Reversible writes need one independent
signature and rollback. Irreversible, physical, or externally unsandboxed
process operations need two distinct signers using two distinct approval keys,
rollback or safe abort, a hazard contract, and a verifier contract. Changing a
signer label does not make one key count twice.

HTTPS adapters require a fixed HTTPS origin, public A/AAAA addresses, pinned
connection IP, no proxy, no redirect, byte/time limits, and request/response
schema checks. Process adapters require an absolute digest-pinned executable,
fixed cwd and argv schema, environment allowlist, no stdin, bounded output,
timeout, and `shell=false`. `.bat`, `.cmd`, `.ps1`, PATH lookup, and symlink
escape are rejected.

A receipt proves only that a provider call was attempted. It always keeps
`physical_outcome_proven=false`. Verifier keys belong in
`verifier_public_keys_b64`, separate from approval `public_keys_b64`; a key
present in both sets is rejected. Only an independent signature with matching
scope and observation window may set `physical_outcome_verified=true`.
