# The Hand

> **The Hand executes. It does not decide. It proves what it did.**

The Hand is Benjamin's isolated execution boundary. It accepts an exact authorization, independently verifies that matching `BENJAMIN.AUTHORIZATION` evidence exists in The Book, performs the instruction exactly once, and publishes its own `HAND.EXECUTION` evidence.

## Evidence-aware boundary

```text
Benjamin
  |
  | BENJAMIN.AUTHORIZATION
  v
The Book <------ independent verification
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
  | HAND.EXECUTION
  v
The Book
```

The verifier no longer returns a bare boolean. A successful verification returns an `AuthorizationProof` containing the Book authorization receipt and lifecycle correlation id. The Hand uses that exact Book receipt as the causal parent of its execution evidence.

## The Hand may not

- invent an order;
- infer investment intent;
- change side, instrument, or quantity;
- extend an authorization;
- trust a Benjamin claim that cannot be independently resolved to The Book;
- execute the same idempotency key twice;
- sign `BENJAMIN.*` or `EPINNOX.*` evidence;
- rewrite Book history.

## H1 — Evidence-aware Execution Kernel

H1 is still **dry run only**. Every accepted dry-run execution must produce a `HAND.EXECUTION` evidence draft linked to the verified Benjamin authorization receipt.

A future live milestone requires a durable execution outbox, production signing key isolation, Book availability/recovery policy, concrete venue adapter, reconciliation, kill switch, and qualification evidence. H1 intentionally refuses live adapters.

## Status

**DRY RUN ONLY — NO LIVE BROKER OR EXCHANGE EXECUTION.**
