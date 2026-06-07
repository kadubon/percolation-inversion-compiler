# Edge Relation Verifiers

ECPT packet edges need more than tag overlap. v0.3.2 adds semantic finite edge
checks for relation types such as:

- `theorem-to-code`
- `code-to-test`
- `obligation-to-verifier`
- `receiver-compatibility`
- `execution-path`
- `rollback-support`
- `liquidity-transfer`

Each `EdgeRelationVerifierSpec` declares evidence markers, source/target tag
requirements, verifier-resolution requirements, receiver overlap, and minimum
confidence. `verify_edge_relation` returns an `EdgeRelationVerificationReport`
with residual charges when the relation is only structural or under-evidenced.

```powershell
uv run pic ecology verify-edge --registry examples/ecology_packets.json --certificate examples/edge_relation_certificate.json
```

Accepted relations are finite packet-ecology evidence. They still do not settle
external domain obligations.
