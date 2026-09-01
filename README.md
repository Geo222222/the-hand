# The Hand

> **The Hand executes. It does not decide.**

The Hand is Benjamin's isolated execution boundary. It accepts a valid `AuthorizedExecutionRequest`, verifies that the authorization is trusted and unexpired, executes the instruction exactly once, and returns an `ExecutionReceipt`.

The Hand contains no research, signal generation, portfolio construction, investment thesis, autonomous strategy, investor logic, or distribution logic.

## Constitutional boundary

```text
Epinnox
  |
  v
Benjamin / Steward
  |
  v
Watchman
  |
  v
AuthorizedExecutionRequest
  |
  v
THE HAND
  |
  v
Broker / Exchange / Venue
```

The Hand is not permitted to:

- invent an order;
- change BUY to SELL or SELL to BUY;
- increase or decrease authorized quantity;
- substitute an instrument;
- extend an expired authorization;
- execute an authorization that cannot be independently verified;
- execute the same idempotency key twice;
- infer investment intent from market data or model output.

## H0 — Execution Boundary Kernel

H0 provides:

- strict parsing of Benjamin's versioned execution contract;
- default-deny authorization verification;
- expiration enforcement;
- exact-instruction propagation;
- idempotent execution receipts;
- a dry-run adapter only;
- tests proving that malformed, expired, untrusted, and duplicate instructions cannot become duplicate venue actions.

## Status

**DRY RUN ONLY. NO LIVE BROKER OR EXCHANGE ADAPTER EXISTS IN H0.**

Live execution is a future milestone and must require an explicit constitutional change, concrete venue adapter, credential boundary, reconciliation path, kill switch, and production qualification.
