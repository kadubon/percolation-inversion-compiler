# Abstraction Liquidity Theory

ALT means **Abstraction Liquidity Theory**. In this repository it is the
abstraction-capital foundry layer for ECPT collective phase workflows.

ALT answers a narrow operational question: when can an observed trace, external
intake result, or agent output become reusable abstraction capital for later
agents? The answer is not raw volume or a persuasive claim. A token contributes
only after finite checks accept its trace support, mission validity, value
evidence level, transport scope, root-of-trust, telemetry accounting,
lifecycle/finality, hazard bounds, and certified lower-bound surplus.

## What ALT Adds

- `AbstractionToken`: a candidate reusable abstraction with receiver family,
  validity domain, dependencies, interface refs, evidence refs, authority refs,
  and verifier routes.
- `LiquidityCertificate`: a lower-bound surplus certificate. It subtracts
  formation, deployment, validation, certification, settlement, maintenance,
  depreciation, contamination, hidden-resource, telemetry, absorption,
  misapplication, and hazard costs from downstream search-cost reduction. Its
  `value_evidence_level` separates `proxy-only`, `calibrated-proxy`, and
  `causal`; proxy-only evidence is useful diagnostic work but cannot certify
  reusable abstraction capital.
- `ValueBridgeReport`: a typed diagnostic inside liquidity output. It states
  whether the value claim is only a proxy, whether a calibrated proxy is bridged
  to a common estimand, whether causal effect evidence is present, and which
  refs support each step. v0.4.2 also reports instrumentation/contamination,
  transportability, baseline refresh, negative-liquidity preservation,
  CARA-residual preservation, and foundry capacity labels. In common terms, it
  separates "this metric moved" from "this reusable abstraction has checked
  downstream value."
- `NegativeLiquidityCertificate`: a scoped certificate that a token is harmful,
  stale, nonportable, contaminated, or no longer cost-positive for the declared
  receiver and opportunity measure.
- `ALTDeprecationRecord` and `ALTResurrectionRecord`: lineage-preserving
  transitions for pruning unsafe capital and restoring it only as a candidate
  after current positive checks override the old failure mode.
- `BaselineRefreshCertificate`, `RootFinalityCertificate`,
  `TelemetryCostCertificate`, and `HazardEnvelopeCertificate`: finite guards for
  baseline drift, root/quorum/finality, observer cost/tamper status, authority,
  rollback, tail risk, and noncompensable hazard.
- `ReproductionMatrixCertificate`: a finite diagnostic for abstraction-capital
  reproduction. External causal reproduction remains an explicit obligation.
- `ExecutableALTCertificatePacket`: a portable packet carrying the token,
  trace sufficiency, liquidity certificate, evidence refs, and residual ledger.
- `FoundryControlDashboard`: a finite dashboard for evidence, transport, risk,
  capacity, and certified abstraction capital bottlenecks.
- `ALTCARACertificate`: a protocol-relative acceleration certificate requiring
  target validity, resource-matched baseline envelope, certified capital
  witness, live predicates, and unresolved-obligation preservation.

## Safe Agent Route

```powershell
uv run pic alt tokenize --trace examples/alt/trace.json
uv run pic alt check-token --token examples/alt/token_candidate.json
uv run pic alt check-transport --certificate examples/alt/transport_certificate.json
uv run pic alt certify-liquidity --certificate examples/alt/liquidity_certificate.json
uv run pic alt admit --packet examples/alt/admission_packet.json
uv run pic alt negative-certify --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt deprecate --token-id alt-token:demo --certificate examples/alt/negative_liquidity_certificate.json
uv run pic alt resurrect --deprecation examples/alt/deprecation_record.json --packet examples/alt/admission_packet.json --override-failure-mode stale
uv run pic alt refresh-baseline --certificate examples/alt/baseline_refresh_certificate.json
uv run pic alt reproduction-report --certificate examples/alt/reproduction_certificate.json
uv run pic alt check-cara --certificate examples/alt/alt_cara_certificate.json
uv run pic alt foundry-dashboard --state examples/alt/foundry_state.json
```

The output is protocol-relative. `accepted=true` means the finite ALT checker
accepted the scoped certificate packet. `settled=false` remains normal unless
separate verifier routes discharge the full finite settlement scope.

Development and research profiles should keep useful but under-certified tokens
as repairable candidates. Production and adversarial profiles should require
complete finite evidence before treating a token as certified abstraction
capital. Missing transport, root/finality, telemetry, lifecycle, hazard, or
baseline-refresh evidence should create residual obligations and repair routes,
not silent success and not permanent deletion. Foundry dashboards label the
current bottleneck as evidence-limited, transport-limited, risk-limited,
capacity-limited, subcritical, or unsaturated-supercritical so an agent can pick
the next verifier route.

## Connection To ECPT And SQOT

General intake and agent messages may create ALT token candidates. They do not
become verified packet capital or improve positive Psi components by volume.
SQOT should route uncertified ALT candidates as diagnostic, verifier, or
quarantine work. ECPT phase metrics may use ALT-certified abstraction capital
only after the token passes lower-bound surplus, transport, root, telemetry,
lifecycle, hazard, semantic edge, identity, rollback, and residual-policy
checks.

ALT-certified capital can contribute only to liquidity-related ECPT components,
and only inside the declared receiver family and validity domain. Raw candidate
volume, tag-only `liquidity-transfer` edges, stale lifecycle claims, unresolved
hazard envelopes, or external causal reproduction claims do not improve Psi,
collective certificates, verified packet capital, or `settled`.

## Repair And Control Patterns

- Negative liquidity should deprecate only the declared token scope; it should
  not erase lineage or unrelated candidate evidence.
- Resurrection requires the current packet to pass positive checks and
  explicitly override the prior failure mode.
- Baseline refresh is a bridge: it preserves or invalidates earlier surplus
  claims after baseline, opportunity, toolchain, or cost-model drift.
- Reproduction reports are diagnostics unless gauge compatibility, transport,
  capacity, and causal evidence discharge the scoped obligations.
- ALT-CARA certificates are finite ASI-proxy acceleration certificates only.
  They preserve external physical, oracle, simulator, and real-ASI obligations.

This is useful for ASI-proxy collective phase workflows because it turns
external knowledge into auditable reusable capital instead of treating every
external item as immediately liquid. It does not prove real ASI, physical
outcomes, oracle truth, legal identity, or global Sybil uniqueness.
