# AFST Satisfaction Flux

AFST means Abundance-Flux Stabilization. In PIC v1.0.0 it is a
residual-preserving checker for proposed satisfaction-flux transfers.

Run from an installed package:

```bash
pic demo bootstrap --output-dir pic-demo --overwrite
pic afst check --case pic-demo/afst/minimal_accepted.json --compact
pic afst check --case pic-demo/afst/blocked_refusal.json --output pic-demo/afst-report.json
pic afst emit-ccr-tasks --report pic-demo/afst-report.json
```

AFST checks:

- satisfaction deficits and certified abundance;
- non-market liquidity rather than price-only signals;
- authority envelopes;
- consent and refusal channels;
- physical resource-balance witnesses;
- stabilization buffers against shock envelopes;
- bounded-friction handover protocols.

`accepted=true` means the finite AFST checker accepted the record. It does not
mean settlement, provider dispatch, physical outcome proof, market or ownership
override, consent bypass, refusal suppression, resource creation, ALT capital
admission, ECPT phase promotion, or ASI proof.

Blocked examples are copied to `pic-demo/afst/` by `pic demo bootstrap`. In a
source checkout they also live in `examples/afst/`. They cover active refusal,
missing authority, buffer insufficiency, missing shock envelopes, unit mismatch,
and resource-balance violations.

When a required field is missing, PIC emits an explicit residual with the form
`missing_<record_type>_<field>`, for example
`missing_certified_abundance_cell_id`. This makes incomplete AFST input easy to
search, route to a repair task, and compare across Python and TypeScript
implementations.

Search terms: AFST, abundance flux stabilization, satisfaction flux, certified
abundance, satisfaction deficit, non-market liquidity, refusal preservation,
consent channel, stabilization buffer, shock envelope, bounded handover, CCR
repair task, PIC.
