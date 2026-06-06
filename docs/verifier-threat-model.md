# Verifier Threat Model

The verifier SDK is an evidence-routing layer, not an oracle. A valid envelope
may discharge listed external obligations only when its route contract, evidence
kind, SHA-256 digest, schema digest, verifier identity, verifier version, and
determinism checks pass.

Threats considered:

- forged registry status or self-declared settled claims;
- missing or unknown residual coordinates hidden as zero;
- nondeterministic simulator output presented as finite evidence;
- evidence references whose content hash does not match the envelope;
- unavailable optional adapters treated as accepted verifiers;
- physical, oracle, or ASI-related claims promoted without external evidence.

The safe default is diagnostic output with residual charge preservation.
Every unresolved `ExternalProofObligation` remains outside the settled certificate
boundary until a route-specific verifier accepts a deterministic evidence
envelope.
