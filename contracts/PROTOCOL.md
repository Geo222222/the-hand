# ZLJ / Benjamin / Watchman / Book / Hand Protocol

## Foundation-v1 canonical boundary

The authoritative Foundation-v1 economic/execution-mechanics boundary is:

```text
ZLJ.INTELLIGENCE
      ↓
BENJAMIN.DECISION
CandidateEconomicPath
bounded economic objective / amount
      ↓
WATCHMAN PRE-ACTION ASSESSMENT
      ↓
WATCHMAN.AUTHORIZATION
bounded economic authority
      ↓
THE HAND
capability resolution
provider unit metadata
translation policy
      ↓
ProviderExecutionPlan
      ↓
HAND.EXECUTION_PLAN
      ↓
THE BOOK
```

The Hand does not accept model confidence, ZLJ evidence, a Benjamin decision, capability presence, capability qualification, or a caller-supplied boolean as execution authority. Final capital authority at this boundary must resolve to exact committed `WATCHMAN.AUTHORIZATION` evidence.

The constitutional ownership rule is:

```text
Benjamin chooses the economic objective.
Watchman authorizes or blocks bounded economic authority.
The Hand translates that authority into provider mechanics.
The Hand does not choose what capital should do.
```

## Canonical Watchman authority contract

`WatchmanAuthorizedAction` is the Foundation-v1 cross-repository authority contract. It binds economic intent and institutional lineage, including:

- authorization identity and committed Book receipt;
- Watchman issuer/key/signature reference and content hash;
- Capital Structure ID;
- Benjamin decision receipt/ID/hash;
- CandidateEconomicPath ID/hash;
- Watchman pre-action assessment ID/hash;
- Watchman Capital Envelope ID/hash;
- responsibility reference/version;
- Watchman capital-action class;
- economic root, instrument intent, path type, direction, and economic currency;
- authorized economic amount, minimum/maximum bounds, and maximum capital commitment;
- issued/valid-from/expiry times;
- idempotency key;
- permitted Hand capability IDs and provider families;
- Watchman policy version.

The Hand independently verifies the committed Watchman evidence, producer identity/signature, payload digest, exact payload content, timing, and lineage before accepting it.

The schema is exact (`additionalProperties: false`). Provider-native mechanics are therefore not valid fields in `WatchmanAuthorizedAction`.

Hard boundary:

```text
economic amount != provider-native quantity
```

Fields/concepts such as native quantity, contract count, lot size, quantity step, and provider order parameters belong below the Watchman authorization boundary inside The Hand.

## Capital-action protocol bridge

The Hand supports the stable cross-repository capital-action values:

```text
RISK_INCREASING
RISK_NEUTRAL
RISK_REDUCING
EMERGENCY_PROTECTIVE
```

This is a protocol bridge, not a runtime dependency on Benjamin. The Hand independently validates incoming values and capability compatibility.

## Capability contract

`HandCapability` states what an installation can technically support. It does not grant authority.

A capability binds capability/version, provider family/adapter/version, environment, kind, supported capital-action/economic-path/instrument families, native unit model, permission scopes, declared read/trade/cancel/transfer/withdraw/sign abilities, lifecycle/qualification state, idempotency semantics, limits, and provenance/hash.

The following are distinct states:

```text
CAPABILITY EXISTS
        !=
CAPABILITY QUALIFIED
        !=
WATCHMAN AUTHORIZED
        !=
PROVIDER EXECUTION PLAN CONSTRUCTED
        !=
PROVIDER SUBMITTED
        !=
FILLED
        !=
SETTLED
```

Foundation v1 earns only the planning state.

## Provider unit metadata

`ProviderInstrumentMetadata` is the typed provider-specific declaration used by The Hand to translate economic authority. Foundation v1 supports these declared families:

```text
spot / base-asset quantity
spot / quote notional
linear derivative contracts
inverse derivative contracts
```

Metadata may bind provider instrument ID, canonical economic root, asset/instrument family, base/quote/settlement assets, native quantity unit, contract type/multiplier/value convention, inverse/linear semantics, price unit, tick/step/minimums, precision, lot/contract rules, margin denomination, metadata version/source/provenance, and known/effective/valid times.

Provider-specific formulas are not hard-coded as universal truth. Translation follows the semantics declared by the exact metadata object used and qualified.

## Translation policy

`TranslationPolicy` is an explicit, versioned input. It declares the quantization rule and all permitted error behavior. No translation tolerance is inferred.

Foundation v1 verifies that a translated plan:

- remains within Watchman's authorized maximum and maximum capital commitment;
- preserves economic direction and action class;
- has non-negative provider-native quantity;
- satisfies declared provider minimum/step mechanics;
- remains within explicit translation tolerance;
- uses currently valid authorization, metadata, and required reference-price evidence.

If no valid representation exists, planning fails closed with a typed reason rather than silently changing economic exposure.

## ProviderExecutionPlan

A `ProviderExecutionPlan` is a deterministic, content-addressed mechanical representation of an already-authorized economic action.

Its identity binds the exact causal inputs used to construct it, including:

- Watchman authorization identity/hash;
- CandidateEconomicPath ID/hash;
- capability ID/version/hash;
- provider family/instrument;
- provider metadata hash;
- reference-price evidence hash when required;
- TranslationPolicy ID/version/hash;
- planner version;
- provider constraints and resulting native amount/unit;
- translated economic notional/error;
- idempotency key;
- causal `known_at`, validity, and exact input hashes.

`now`/processing time is used only to evaluate current freshness and validity. Wall-clock invocation time is not a content-addressed plan input.

The causal plan `known_at` is reconstructed from immutable evidence timestamps actually used by Foundation v1 (Watchman authorization issuance, provider metadata knowledge time, and reference-price knowledge time when required). Thus the same immutable inputs reconstruct the exact same plan at different invocation times.

**Plan construction is not provider submission.** Foundation v1 contains no provider call in this path.

## Deterministic replay and idempotency

Foundation-v1 replay reconstructs from durable immutable inputs rather than returning a mutable cached plan.

The durable replay record binds:

```text
idempotency key
    + immutable causal input hash
    + ProviderExecutionPlan content hash
```

Rules:

- same key + same immutable inputs + same plan = idempotent replay;
- same key + materially different immutable inputs/plan = hard reject;
- every replay runs current expiry/freshness validation before the durable record is accepted;
- a prior replay record cannot resurrect expired Watchman authority, stale metadata, or a stale reference price;
- replay creates no execution/submission authority.

Changing Watchman authority, CandidateEconomicPath, capability identity/version/hash, provider metadata/multiplier, reference-price evidence, TranslationPolicy/version, or planner version changes the resulting plan identity as applicable.

## Exact synthetic qualification

`InstrumentQualification` binds an exact capability hash to an exact provider metadata hash for a declared mechanism scope.

Foundation v1 proves deterministic synthetic mechanics, including separate spot, linear-contract, and inverse-contract fixtures. A metadata change such as a contract multiplier change does not inherit the previous qualification.

`SYNTHETIC_MECHANISM` is not `LIVE_MECHANISM`. Synthetic fixtures do not establish real provider availability, fills, slippage, derivatives safety, profitability, or live-capital qualification.

## Foundation-v1 evidence

The highest evidence event earned by the canonical Foundation-v1 planning path is:

```text
event_type: HAND.EXECUTION_PLAN
producer: The Hand
causation: exact Watchman authorization Book receipt
lineage dependency: Benjamin decision receipt
subject: ProviderExecutionPlan content hash
payload: canonical deterministic ProviderExecutionPlan
```

The same reconstructed plan produces the same evidence payload and subject identity. The existing Hand evidence outbox treats the same receipt/payload/envelope meaning idempotently and rejects receipt-identity conflicts.

Foundation v1 does not emit or simulate:

```text
HAND.EXECUTION_SUBMITTED
HAND.EXECUTION_ACCEPTED
HAND.EXECUTION_FILLED
HAND.SETTLEMENT
HAND.RECONCILIATION
```

No provider action occurred, so those facts have not been earned.

## Legacy H2 dry-run compatibility boundary

The repository retains an already-certified earlier dry-run execution path using `ExecutionRequest` / `WatchmanAuthorizedExecutionRequestV2` (`contracts/authorized_execution_request.schema.json`). That compatibility wire includes provider-facing fields such as `instrument`, `side`, and `quantity` because it represented an exact dry-run capability instruction after Watchman proof verification.

It is **not** the canonical Foundation-v1 economic authority contract. Its `quantity` must not be interpreted as Benjamin/CandidateEconomicPath/Watchman economic language, and the legacy contract is not silently translated into `WatchmanAuthorizedAction`.

Historical records retain their historical semantics. Foundation-v1 target work uses:

```text
WatchmanAuthorizedAction
(economic authority)
        ↓
The Hand unit translation
        ↓
ProviderExecutionPlan
(provider-native mechanics)
```

The inherited dry-run `HAND.EXECUTION` evidence remains historical compatibility behavior; it does not raise the evidence earned by the new Foundation-v1 planning path and does not establish live provider qualification.

## Secret and identity boundary

Foundation v1 does not provision provider credentials, API keys, access tokens, seed phrases, withdrawal credentials, production account authority, or provider signing material.

The repository's existing Hand Book producer identity accepts runtime `HAND_BOOK_KEY_ID` / `HAND_BOOK_ED25519_PRIVATE_KEY_B64` for signing only `HAND.*` institutional evidence. These are secret interfaces, not checked-in secret values and not provider trading credentials. Hand, Watchman, Benjamin, and ZLJ evidence identities must remain separate.

Evidence payloads contain minimum-necessary plan mechanics and hashes, not provider credential objects.

## Earned safety state

**HAND FOUNDATION V1 IS NON-LIVE.**

The canonical Foundation-v1 path ends at deterministic `ProviderExecutionPlan` + `HAND.EXECUTION_PLAN`. No live Coinbase/Kraken/Alpaca/broker/bank/wallet/provider mutation, withdrawal, settlement, fill, or reconciliation capability is made reachable by this protocol.

Future shadow/live promotion requires separate implementation, qualification, credential isolation, failure controls, reconciliation, kill switches, execution-outcome evidence, and explicit governing authorization. None of those future states are implied by Foundation v1.