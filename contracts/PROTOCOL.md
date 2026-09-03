# ZLJ / Benjamin / Watchman / Book / Hand Protocol

The target execution boundary is Protocol v2:

```text
ZLJ.INTELLIGENCE
      ↓
BENJAMIN.DECISION
      ↓
WATCHMAN.AUTHORIZATION
      ↓
HAND.EXECUTION
```

The Hand does not accept a Benjamin decision, model confidence, ZLJ evidence, or the legacy `BENJAMIN.AUTHORIZATION` record as sufficient execution authority.

## Execution request

The Hand accepts an exact `WatchmanAuthorizedExecutionRequestV2` containing:

```text
authorization_book_receipt_id
capability
idempotency_key
instrument
side
quantity
decision_id
governance_id
expires_at
```

The request does not create authority. It points The Hand to a specific committed Book receipt that must independently verify as `WATCHMAN.AUTHORIZATION`.

Before any adapter call, `WatchmanAuthorizationVerifier` checks:

- the Book receipt is committed;
- producer is exactly `Watchman`;
- event type is exactly `WATCHMAN.AUTHORIZATION`;
- the Watchman Ed25519 signature verifies using The Hand's public-key trust store;
- the payload digest matches the committed payload;
- the payload identifies the same Benjamin decision and governance result;
- every governance check is `PASS`;
- capability, instrument, side, quantity and idempotency key equal the execution request exactly;
- the Watchman payload, signed envelope and request carry the same expiry;
- the authorization timing is internally consistent.

`WATCHMAN.BLOCK`, unknown keys, tampered signatures, stale authority, mismatched parameters and missing evidence all fail closed.

## Execution evidence

After exact execution, The Hand creates its own evidence:

```text
event_type: HAND.EXECUTION
producer: The Hand
causation_receipt_id: Watchman authorization Book receipt
evidence dependency: Benjamin decision receipt
payload: exact HandExecutionReceiptV2
```

The execution receipt records the requested instrument, side and quantity as well as execution outcome fields. This prevents an auditor from having to infer the instruction that produced an outcome.

The Hand uses its own Ed25519 key:

- `HAND_BOOK_KEY_ID`
- `HAND_BOOK_ED25519_PRIVATE_KEY_B64`

The Hand key may sign only `HAND.*`. It must not be reused as the Watchman, Benjamin or ZLJ Book identity. Signed `HAND.*` evidence is persisted in a durable Hand outbox before Book delivery is attempted, and retry retransmits the exact same signed evidence.

## Legacy H1 compatibility boundary

The former v1.0 request (`authorization_id`, `fund_id`, `risk_id`, `issued_at`, etc.) belonged to the transitional Benjamin-direct H1 path. H2 intentionally rejects that wire contract rather than silently translating it, because translation could create execution authority for fields Watchman never signed.

Historical B1/H1 evidence remains historical evidence. A new execution under H2 requires a new Watchman-authorized v2 request.

## Safety state

H2 remains **DRY_RUN only**. A valid Watchman authorization is necessary for execution but does not itself enable live venue mutation. Live capability promotion still requires separate capability qualification, credential isolation, reconciliation, kill switches, provider failure controls and explicit governing authority.
