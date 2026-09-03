# The Hand

> **ZLJ sees. Benjamin decides. Watchman governs. The Hand executes. The Book remembers and proves.**

The Hand is Epinnox's **authorized external-action capability plane**.

It is broader than one broker or exchange executor. The Hand is the home for tools/adapters that can create an external financial effect after the required governance has authorized the action.

The Hand owns **execution/capability truth**: what authorized capability was invoked, against which external system, with what exact bounded parameters, and what actually happened.

It does **not** own market intelligence, capital judgment, governance policy, or institutional memory.

## Capability model

The Hand may eventually contain many independently qualified capability families, for example:

```text
The Hand
  |- exchange adapters
  |- broker adapters
  |- wallet / custody signing
  |- blockchain transaction submission
  |- bank / ACH / wire integrations
  |- payment processors
  |- treasury transfer / sweep capabilities
  |- settlement providers
  `- future approved external financial tools
```

A capability is not authority. The existence of an exchange adapter, bank API, signer, or payment integration does not permit The Hand to use it on its own.

## Authority path

```text
ZLJ.INTELLIGENCE
      |
      v
BENJAMIN.DECISION
      |
      v
WATCHMAN.AUTHORIZATION / WATCHMAN.BLOCK
      |
      | exact bounded capability
      v
THE HAND
      |
      | independently verify authorization
      | perform exact authorized effect
      v
External system
      |
      v
HAND.EXECUTION
      |
      v
THE BOOK
```

H2 implements **Watchman-authorized action -> Hand capability invocation**. Benjamin cannot authorize its own economic decision.

## What The Hand receives

The H2 execution request carries only the fields required to perform and prove the action:

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

The request points to a specific committed `WATCHMAN.AUTHORIZATION` Book receipt. It does not itself create authority.

The Hand does not need the full Benjamin thesis, unrelated portfolio state, ZLJ model stack, investor records, or internal deliberations.

## Independent authorization verification

Before any adapter call, The Hand independently verifies that the committed Book evidence:

- was produced by Watchman;
- is exactly `WATCHMAN.AUTHORIZATION`, not `WATCHMAN.BLOCK`;
- has a valid Ed25519 Watchman signature;
- has an untampered payload digest;
- contains only passing governance checks;
- authorizes the same capability, instrument, side, quantity and idempotency key requested;
- covers the same Benjamin decision and governance result;
- has consistent evaluation/production/recording timing;
- has not expired.

A legacy `BENJAMIN.AUTHORIZATION` wire is rejected by H2 rather than silently upgraded.

## Capability routing

The Hand may contain multiple integrations capable of performing the same approved action.

Example:

```text
capability: market_order.submit
allowed_adapters:
  - venue_a
  - venue_b
```

The Hand may select among technically equivalent adapters **only when Watchman authorization and capability policy permit that routing**.

It may optimize operational details such as provider availability, deterministic fee bounds, retry semantics, or supported order mechanics within the authorized envelope. It may not alter the economic intent.

A different side, amount, destination, instrument, account, or economic purpose requires new governed authority.

## Read versus write boundary

Read-only market observation generally belongs upstream in ZLJ when used for perception/modeling.

Authenticated operations that can change external financial state belong in The Hand, including:

- submit/cancel/replace orders;
- move or encumber funds;
- sign transactions;
- change custody state;
- settle or sweep value;
- invoke payment/banking write operations;
- create other governed external financial effects.

This keeps ZLJ from becoming an executor simply because an exchange API supports both market data and trading.

## Private proof boundary

Every material Hand outcome is designed to be causally linked to the exact Watchman authorization and preserved through The Book under minimum-necessary evidence rules.

```text
WATCHMAN.AUTHORIZATION
       |
       v
THE HAND
       |
       v
external action
       |
       v
HAND.EXECUTION
       |
       v
BIG BOOK
```

`HAND.EXECUTION` records the requested instrument, side and quantity together with outcome fields. The Hand signs this evidence with its own `HAND.*` identity and persists the exact signed record in a durable outbox before Book delivery.

Ordinary execution/action evidence is private. The Hand does not publish actions directly to the Little Book.

If the institution later needs an external proof, The Book creates a separate minimum-necessary public attestation under explicit disclosure policy.

## Credentials and secret material

Venue credentials, signing keys, account secrets, raw identity data, banking credentials, and other secret/regulated material stay in restricted operational storage or governed secret systems.

The Hand Book identity uses separate runtime secrets:

- `HAND_BOOK_KEY_ID`
- `HAND_BOOK_ED25519_PRIVATE_KEY_B64`

The Hand key signs only `HAND.*` and must not be reused as the Watchman, Benjamin, or ZLJ identity.

Credentials and secret material are not placed in prompts, ordinary model memory, Git, or raw immutable proof payloads. General-purpose reasoning agents should not hold unrestricted production signing material.

## The Hand may not

- invent an economic action;
- infer investment intent from prose;
- treat a Benjamin decision as self-authorizing;
- treat a Watchman block as execution authority;
- bypass or weaken Watchman;
- change side, instrument, destination, amount, account, or other material intent outside the authorization;
- extend an authorization;
- execute an expired authorization;
- execute the same idempotency key twice;
- use a capability that was not authorized for the action;
- sign as ZLJ, Benjamin, Watchman, The Martians, or The Book;
- rewrite Book history;
- automatically project execution history to the Little Book.

## Current H2 status

H2 implements the cryptographic/contract authority bridge but remains **dry-run only**. No H2 code authorizes live broker, exchange, bank, custody, payment, or transfer actions.

A future live capability still requires concrete adapter qualification, isolated credentials/signing, durable reconciliation, kill switches, failure recovery, capability-specific limits, provider failure handling, and explicit governing promotion.

See `COVENANT.md`, `PRIVACY.md`, and `contracts/PROTOCOL.md`.

## Status

**WATCHMAN-AUTHORIZED CAPABILITY FOUNDATION / DRY RUN — NO LIVE FINANCIAL EXECUTION.**
