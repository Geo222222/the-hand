# The Hand Covenant

The Hand is deliberately less intelligent than the systems upstream of it. Its excellence is exact, safe execution.

## HAND-001 — No order without trusted authority
A syntactically valid request is not enough. An injected authorization verifier must affirm that Benjamin actually authorized the request. The default verifier denies everything.

## HAND-002 — Exact means exact
Instrument, side, and quantity are immutable after acceptance. The Hand may refuse an instruction; it may not improve, resize, reverse, or substitute it.

## HAND-003 — Expiration is final
An expired authorization cannot be extended locally or executed late.

## HAND-004 — Idempotency precedes venue action
The same idempotency key must not create a second venue action. A conflicting payload using an existing key is an error.

## HAND-005 — Execution produces evidence
Every accepted attempt returns a versioned `ExecutionReceipt` suitable for Benjamin's Book and reconciliation process.

## HAND-006 — H0 is dry-run only
No live adapter is permitted in H0. A non-dry-run adapter is rejected before execution.

## HAND-007 — No investment cognition
The Hand contains no strategy selection, signal interpretation, thesis generation, portfolio optimization, or autonomous trade origination.
