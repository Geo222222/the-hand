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

## Target authority path

```text
ZLJ intelligence
      |
      v
Benjamin decision
      |
      v
Watchman
AUTHORIZE / BLOCK
      |
      | exact authorized action envelope
      v
THE HAND
      |
      | select permitted capability/adapter
      | perform exact authorized effect
      v
External system
      |
      v
Execution / Action Receipt
      |
      v
THE BOOK
```

The target live contract is therefore **Watchman-authorized action -> Hand capability invocation**.

## What The Hand receives

The Hand should receive only what is required to perform and prove the action, such as:

```text
authorization id
capability id / action type
account or execution context
instrument / asset / destination where applicable
side / operation
quantity / amount / bounded constraints
provider-routing permissions if any
expiry
idempotency key
Watchman authorization evidence reference
```

It does not need the full Benjamin thesis, unrelated portfolio state, ZLJ model stack, investor records, or internal deliberations.

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

Every material Hand outcome should be causally linked to the exact governed authorization and preserved through The Book under minimum-necessary evidence rules.

```text
Watchman authorization
       |
       v
THE HAND
       |
       v
external action
       |
       v
Hand receipt / reconciliation
       |
       v
BIG BOOK
```

Ordinary execution/action evidence is private. The Hand does not publish actions directly to the Little Book.

If the institution later needs an external proof, The Book creates a separate minimum-necessary public attestation under explicit disclosure policy.

## Credentials and secret material

Venue credentials, signing keys, account secrets, raw identity data, banking credentials, and other secret/regulated material stay in restricted operational storage or governed secret systems.

They are not placed in prompts, ordinary model memory, Git, or raw immutable proof payloads.

General-purpose reasoning agents should not hold unrestricted production signing material.

## The Hand may not

- invent an economic action;
- infer investment intent from prose;
- treat a Benjamin decision as self-authorizing;
- bypass or weaken Watchman;
- change side, instrument, destination, amount, account, or other material intent outside the authorization;
- extend an authorization;
- execute an expired authorization;
- execute the same idempotency key twice;
- use a capability that was not authorized for the action;
- sign as ZLJ, Benjamin, Watchman, The Martians, or The Book;
- rewrite Book history;
- automatically project execution history to the Little Book.

## Current H1 implementation versus target architecture

The current H1 foundation was built around a narrower execution kernel and may still verify a legacy `BENJAMIN.AUTHORIZATION` proof. That is an implementation fact, not the target constitutional ownership model.

Future bridge work should migrate the live semantic authority toward **Watchman authorization** while preserving historical proof meaning and avoiding silent reinterpretation of already-issued records.

H1 remains dry-run only. No current documentation change authorizes live broker, exchange, bank, custody, payment, or transfer actions.

A future live capability requires durable outbox/receipt behavior, isolated credentials/signing, concrete adapter qualification, reconciliation, kill switches, failure recovery, and Watchman-compatible authorization evidence.

See `COVENANT.md` and `PRIVACY.md`.

## Status

**AUTHORIZED CAPABILITY FOUNDATION / DRY RUN — NO LIVE FINANCIAL EXECUTION.**
