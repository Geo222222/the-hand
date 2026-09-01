# The Hand

> **The Hand executes. It does not decide. It privately proves what it did.**

The Hand is Benjamin's isolated execution boundary. It accepts an exact authorization, independently verifies the matching `BENJAMIN.AUTHORIZATION` proof in the **private Big Book**, performs the instruction exactly once, and publishes its own private `HAND.EXECUTION` proof.

The Hand owns **execution truth**. It does not own investment intent, capital governance, stewardship history, or public disclosure.

## Private proof boundary

```text
Benjamin
  |
  | BENJAMIN.AUTHORIZATION
  v
BIG BOOK <------ scoped independent verification
  |
  v
THE HAND
  |
  | exact venue action
  v
Venue
  |
  v
ExecutionReceipt
  |
  | HAND.EXECUTION / CONFIDENTIAL_EVIDENCE
  v
BIG BOOK
```

A successful verifier returns an `AuthorizationProof` identifying the exact private Big Book authorization receipt and lifecycle correlation id. The Hand uses that receipt as the causal parent of its execution proof.

## Minimum necessary information

The Hand should know only what it needs to execute:

```text
authorization id
fund/portfolio execution context
instrument
side
quantity/order constraints
expiry
verified Big Book authorization proof
```

It does not need the full investment thesis, unrelated positions, investor records, family history, or internal deliberations.

## Privacy

Ordinary execution proofs are `CONFIDENTIAL_EVIDENCE`, visible only to execution, reconciliation, and authorized audit roles.

The Hand does **not** publish execution events to the Little Book. If the institution later needs an external proof, The Book creates a separate minimum-necessary public attestation derived from a Big Book commitment.

Venue credentials, account secrets, raw broker payloads, identity documents, and other secret/regulated source material stay in restricted operational storage or The Vault.

## The Hand may not

- invent an order;
- infer investment intent;
- change side, instrument, or quantity;
- extend an authorization;
- trust a Benjamin claim that cannot be independently resolved to the Big Book;
- execute the same idempotency key twice;
- sign `BENJAMIN.*`, `EPINNOX.*`, or `MARTIANS.*` proof;
- rewrite Big Book history;
- automatically project execution history to the Little Book.

## H1.1 — Privacy-scoped Execution Kernel

H1.1 remains **dry run only**. Every accepted dry-run execution produces a private `HAND.EXECUTION` proof linked to the verified Benjamin authorization receipt.

A future live milestone requires a durable execution outbox, production signing-key isolation, Big Book availability/recovery policy, concrete venue adapter, reconciliation, kill switch, and qualification evidence. Live adapters remain refused.

See `PRIVACY.md` and `COVENANT.md`.

## Status

**DRY RUN ONLY — NO LIVE BROKER OR EXCHANGE EXECUTION.**
