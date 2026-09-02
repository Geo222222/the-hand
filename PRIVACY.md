# The Hand Privacy Doctrine

The Hand owns **execution/capability truth**. It does not own public disclosure, market intelligence, capital decisions, or governance.

> **ZLJ sees. Benjamin decides. Watchman governs. The Hand executes. The Book remembers and proves.**

## Default posture

Authorized action instructions and outcomes are private institutional facts by default. They may reveal positions, strategy, counterparties, prices, quantities, timing, account relationships, destinations, venue relationships, or operational controls.

The Hand therefore publishes ordinary `HAND.EXECUTION` / Hand action evidence only to the **Big Book** as confidential evidence unless a narrower policy applies.

Default readers should be limited to roles that require execution, reconciliation, governance verification, or audit access.

## Authorization visibility

The target live verifier receives only enough Book/governance access to establish that the exact **Watchman authorization** exists, is authentic, unexpired, compatible with the requested capability, and has not already been consumed contrary to its idempotency rules.

It does not need unrelated portfolio history, ZLJ model internals, Benjamin reasoning, other participants' information, or private institutional history.

### Transitional H1 compatibility

Current H1 code may still verify a legacy `BENJAMIN.AUTHORIZATION` receipt because that kernel predates the final separation of Benjamin decision ownership from Watchman authorization ownership.

That legacy receipt remains private and valid only according to its historical implementation semantics. It must not be read as a constitutional statement that Benjamin owns target live authorization.

Future bridge work should migrate target verification toward explicit Watchman-owned authorization while preserving historical evidence meaning.

## Little Book

The Hand has no automatic Little Book publisher. Execution activity is never public merely because an execution receipt exists.

If the institution intentionally needs a public proof derived from execution history, The Book creates a separate minimum-necessary public attestation under disclosure policy. The Hand does not export its private receipt directly.

## Source evidence and secrets

Venue/provider payloads, credentials, account identifiers, API secrets, bank credentials, signing keys, custody secrets, and raw broker/exchange responses remain in restricted operational storage or The Vault according to retention policy.

Big Book evidence should contain only the minimum proof/reference needed to establish the action and its lineage.

## Capability privacy

The Hand may eventually expose many financial capability families—exchange, broker, wallet/custody, bank, payment, treasury, settlement, and other approved integrations.

Capability inventory itself may be sensitive where it reveals account relationships, provider dependencies, limits, or operational defenses. Discovery of a capability by an internal consumer does not imply permission to invoke it.

## Core privacy invariant

> **The Hand receives and reveals only what is necessary to perform and prove the exact governed action.**
