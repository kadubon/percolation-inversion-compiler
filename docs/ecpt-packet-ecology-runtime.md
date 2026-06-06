# ECPT Packet Ecology Runtime

The packet ecology runtime turns finite artifacts into ECPT capability packet
candidates, builds edge witnesses, measures the ASI-proxy bundle Psi, and ranks
bottleneck interventions. It is an active planning layer over ECPT certificates,
not proof of unobserved ASI or physical outcomes.

```powershell
uv run pic ecology ingest --source README.md --kind local
uv run pic ecology build-edges --packets examples\ecology_packets.json --output ecology-registry.json
uv run pic ecology psi --registry ecology-registry.json --threshold examples\ecology_threshold.json --output ecology-psi.json
uv run pic ecology plan --registry ecology-registry.json --psi ecology-psi.json --profile production
```

Runtime stages:

1. `ingest`: create `CapabilityPacketCandidate` records from local files, agent
   outputs, or optional live connector metadata.
2. `build-edges`: construct `EdgeWitness` records for semantic dependency and
   packet-to-receiver compatibility.
3. `psi`: compute the finite ECPT ASI-proxy dashboard.
4. `plan`: rank bottleneck interventions against limiting Psi components.

Psi components:

- `G`: effective reachable component proxy.
- `DE`: execution-available path density proxy.
- `AC`: autocatalytic closure proxy.
- `VT`: verification-throughput adequacy.
- `LX`: cross-context liquidity through verifier route diversity.
- `SD`: downstream search-cost descent proxy.
- `CV`: constraint-viability proxy after residual debt.
- `FR`: false-liquidity restraint.
- `BR`: target-basin reachability proxy.

The dashboard always reports `distance_to_threshold` and
`limiting_components`. The bottleneck planner uses those fields to recommend
actions such as edge-witness construction, verifier queue execution, liquidity
bridging, false-liquidity quarantine, and target-basin packet ingestion.
