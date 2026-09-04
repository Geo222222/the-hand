# The Hand

> **ZLJ sees. Benjamin decides. Watchman governs. The Hand executes. The Book remembers and proves.**

The Hand is the institution's governed **execution/capability organ**. Its constitutional role is to receive authority that has already passed Benjamin and Watchman, resolve a qualified capability, translate economic intent into provider-native mechanics, and eventually perform and prove the exact authorized external effect.

**Foundation v1 does not perform that external effect.** The highest state earned by this branch is a deterministic `ProviderExecutionPlan` and minimum-necessary `HAND.EXECUTION_PLAN` evidence. Live provider submission remains unreachable.

The Hand is an execution mechanism, not an economic decision-maker.

## Constitutional boundary

```text
BENJAMIN
CandidateEconomicPath
bounded economic objective / amount
          |
          v
WATCHMAN
pre-action capital assessment
          |
          v
WATCHMAN.AUTHORIZATION
bounded economic authority
          |
          v
THE HAND
authorization verification
          |
          v
capability resolution
          |
          v
provider instrument/unit metadata
          |
          v
deterministic translation policy
          |
          v
ProviderExecutionPlan
          |
          +----> HAND.EXECUTION_PLAN -> The Book
          |
          v
FUTURE PROVIDER ADAPTER
NOT REACHABLE IN FOUNDATION V1
```

Benjamin owns economic judgment. Watchman owns permission, constraints, blocking, and authorization. The Hand owns execution mechanics below that authorization boundary. The Book owns durable institutional evidence and lineage.

The Hand may never use capability availability, synthetic qualification, provider metadata, a Benjamin decision, or a caller-supplied boolean as a substitute for Watchman authority.

## Foundation v1 contracts

### Capability Registry

`HandCapability` is a durable, typed declaration of what an installation could technically perform through an integration. It binds capability/version, provider family and adapter version, environment, capability kind, supported Watchman capital-action classes, economic path families, instrument families, provider-native unit model, permission requirements, lifecycle/qualification state, idempotency semantics, limits, and provenance/hash.

The invariant is explicit:

```text
capability exists
!= capability qualified
!= Watchman authorized
!= plan constructed
!= provider submitted
!= filled
!= settled
```

A capability record creates no authority to call a provider.

### Watchman Authorized Action intake

The canonical Foundation-v1 authority object is `WatchmanAuthorizedAction`. It is an **economic authorization**, not an exchange/broker order instruction. It binds, among other lineage:

- Capital Structure ID;
- Benjamin decision ID/hash and Book receipt;
- CandidateEconomicPath ID/hash;
- Watchman pre-action assessment ID/hash;
- Watchman Capital Envelope ID/hash;
- responsibility reference/version;
- Watchman capital-action class;
- economic root, instrument intent, path type, and direction;
- authorized economic amount and bounded range;
- maximum capital commitment;
- validity window and idempotency key;
- permitted capability IDs/provider families;
- Watchman policy/signature/content identity.

The Hand independently verifies committed `WATCHMAN.AUTHORIZATION` Book evidence and Watchman's signature. Missing, malformed, future-dated, expired, mismatched, or conflicting authority fails closed.

Provider-native fields such as quantity, contract count, lot size, step size, or provider order parameters are not members of this contract and are rejected as extra fields.

### Economic amount versus provider-native amount

This is a hard boundary:

```text
economic amount != provider-native quantity
```

Benjamin/Watchman may authorize an economic objective such as increasing BTC exposure by `$10,000`. Only The Hand may translate that authority into a provider representation such as base-asset quantity, quote notional, contracts, or lots after exact provider metadata is known.

The Hand may translate the objective. It may not reinterpret it, reverse its direction, increase its capital authority, or originate a different amount.

### ProviderInstrumentMetadata

`ProviderInstrumentMetadata` describes the exact provider/instrument unit semantics required for translation. Foundation v1 supports four declared unit families:

```text
spot / base-asset quantity
spot / quote notional
linear derivative contracts
inverse derivative contracts
```

Metadata can bind provider/instrument ID, economic root, asset/instrument family, base/quote/settlement assets, native unit, contract type, multiplier/value convention, inverse/linear semantics, price unit, tick size, quantity step, minimum quantity/notional, precision, lot rules, margin denomination, version/provenance, and effective/known-at validity.

Core Hand code does not assume that one provider's derivative formula is universal. Provider-specific semantics must be declared in metadata and separately qualified.

### TranslationPolicy

`TranslationPolicy` makes quantization behavior explicit and content-addressed. It binds the policy/version, rounding rule, permitted lowering/upward translation behavior, and absolute/relative error limits.

There is no implicit tolerance. `HAND.EXACT_ONLY` has zero tolerance. A non-exact translation is acceptable only when an explicit policy permits it while all Watchman bounds remain satisfied.

The planner fails closed when, among other cases:

- authorization is not yet valid or expired;
- capability or exact capability/metadata qualification is absent;
- metadata is unavailable/stale;
- required reference price is stale;
- provider minimums cannot represent the authority;
- native quantity violates declared step/minimum rules;
- quantization exceeds explicit tolerance;
- translated economic notional exceeds Watchman's maximum/commitment;
- action class or economic direction would change.

### ProviderExecutionPlan

`ProviderExecutionPlan` is the content-addressed answer to:

> Given this exact Watchman economic authorization, qualified capability, provider-instrument metadata, reference-price evidence, and TranslationPolicy, how would The Hand express the authorized action through this provider?

A plan binds source Watchman authorization and CandidateEconomicPath identities, capability/version/hash, provider/instrument, economic root/action class/direction, authorized economic amount, provider-native quantity/unit, quantization rule, reference-price evidence, translated economic notional/error, TranslationPolicy identity, provider constraints, idempotency key, planner version, metadata hash, exact causal input hashes, causal known-at time, validity, and plan content hash.

**Plan != execution.** No provider API is called by the Foundation-v1 planner.

### Deterministic replay and idempotency

The runtime planning clock is used only to validate current freshness and validity. It does not participate in content-addressed plan identity.

`ProviderExecutionPlan.known_at` is derived from the latest causal knowledge timestamp carried by immutable inputs actually used by v1: Watchman authorization issuance, provider metadata knowledge time, and reference-price knowledge time when a price is required. Capability, metadata, price, policy, authorization/path, and planner versions/hashes all participate in plan identity.

Therefore:

- the same immutable inputs at different invocation times reconstruct the exact same plan/hash and evidence payload;
- the same inputs after restart reconstruct the same semantic plan;
- materially different inputs cannot reuse an idempotency key;
- stale/expired inputs are revalidated on every replay and cannot be revived from durable state.

The durable replay store records only an idempotency binding between immutable-input identity and plan identity. It never returns a cached plan in place of fresh validation and has no submit/execute surface.

### Synthetic unit qualification

`InstrumentQualification` binds an exact capability hash to an exact provider-instrument metadata hash for a declared qualification scope. Foundation v1 includes deterministic synthetic qualification for spot, linear derivative, and inverse derivative mechanics.

Synthetic qualification proves **mechanism correctness only**. It does not prove provider availability, live fill quality, slippage, profitability, live derivatives safety, or live-capital readiness. `SYNTHETIC_MECHANISM` does not satisfy `LIVE_MECHANISM`.

Changing material metadata such as a contract multiplier changes the metadata hash and requires a new qualification instead of silently inheriting the prior result.

## Book evidence boundary

The highest evidence event earned by the Foundation-v1 planning path is:

```text
HAND.EXECUTION_PLAN
```

It proves minimum-necessary plan lineage including Watchman authorization identity, CandidateEconomicPath identity, capability identity, provider/instrument, governed economic amount, planned native quantity/unit, metadata hash, TranslationPolicy/version/hash, translation error, planner version, exact inputs, and plan content hash.

Foundation v1 does **not** emit or simulate:

```text
HAND.EXECUTION_SUBMITTED
HAND.EXECUTION_ACCEPTED
HAND.EXECUTION_FILLED
HAND.SETTLEMENT
HAND.RECONCILIATION
```

No submission/fill/settlement fact exists to prove yet.

The inherited pre-Foundation dry-run `HAND.EXECUTION` compatibility path remains in the repository for historical/certified interpretation. It is not the Foundation-v1 target authority/translation path and it does not establish live execution qualification.

Ordinary Hand evidence is private/confidential. Evidence payloads do not contain provider API keys, access tokens, private signing material, withdrawal credentials, or unnecessary raw provider credential objects.

## Legacy H2 compatibility boundary

The repository predates Foundation v1 and retains the already-certified H2 dry-run `ExecutionRequest` / `WatchmanAuthorizedExecutionRequestV2` compatibility contract. That legacy wire contains provider-facing fields such as `instrument`, `side`, and `quantity` because it represented an exact dry-run capability instruction after Watchman verification.

That wire is **not** the canonical Foundation-v1 economic authority contract and must never be treated as Benjamin's or Watchman's economic language. New Foundation-v1 planning uses:

```text
WatchmanAuthorizedAction
    economic amount / path / objective
        ↓
The Hand translation boundary
        ↓
ProviderExecutionPlan
    provider-native quantity / mechanics
```

Historical H1/H2 records preserve their historical meaning; they are not silently upgraded or reinterpreted.

## Credentials and live execution

Provider credentials, account secrets, withdrawal secrets, seed phrases, and provider signing material are not provisioned by Foundation v1.

The repository contains an existing separate Hand Book evidence-signing boundary (`HAND_BOOK_KEY_ID` / `HAND_BOOK_ED25519_PRIVATE_KEY_B64`) for signing `HAND.*` evidence. Those are runtime secret *interfaces*, not embedded key material and not provider execution credentials. The Hand identity may sign only its own evidence namespace and must not reuse Benjamin/Watchman/ZLJ identities.

Foundation v1 adds no live provider adapter, production account connection, withdrawal path, settlement adapter, or capital authority. Existing execution guards remain fail-closed and inherited adapters remain dry-run only.

## The Hand may not

- originate an economic action or strategy;
- infer investment intent from prose;
- change an authorized economic direction or amount;
- treat a Benjamin decision as self-authorizing;
- treat a Watchman block as authority;
- fabricate or weaken Watchman authorization;
- substitute capability availability/qualification for authority;
- move provider-native quantity above The Hand translation boundary;
- silently round beyond an explicit TranslationPolicy;
- exceed Watchman bounds or maximum capital commitment;
- use replay/idempotency to mutate or revive authority;
- expose provider credentials/secrets in evidence;
- call a provider merely because a capability exists;
- sign as Benjamin, Watchman, ZLJ, or The Book;
- emit fill/settlement/reconciliation evidence for events that did not happen.

## Earned status

**HAND FOUNDATION V1 — GOVERNED CAPABILITY + ECONOMIC AUTHORIZATION INTAKE + DETERMINISTIC PROVIDER TRANSLATION/PLAN EVIDENCE.**

**NO LIVE FINANCIAL EXECUTION. NO PROVIDER SUBMISSION. NO WITHDRAWALS. NO SETTLEMENT.**

Future shadow/live work requires separate qualification and governing authority. See `COVENANT.md`, `PRIVACY.md`, and `contracts/PROTOCOL.md`.