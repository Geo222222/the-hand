# The Hand Privacy Doctrine

The Hand owns execution truth. It does not own public disclosure.

## Default posture

Execution instructions and outcomes are private institutional facts by default. They may reveal positions, strategy, counterparties, prices, quantities, timing, venue relationships, or operational controls.

The Hand therefore publishes ordinary `HAND.EXECUTION` proofs only to the **Big Book** as `CONFIDENTIAL_EVIDENCE`.

Default readers are limited to:

- `HAND_EXECUTION`;
- `BENJAMIN_RECONCILIATION`;
- `BENJAMIN_AUDITOR`.

## Authorization visibility

The Hand verifier receives only enough Big Book access to establish that the exact `BENJAMIN.AUTHORIZATION` exists and is valid for the requested instruction. It does not need unrelated portfolio, recommendation, risk, or family history.

## Little Book

The Hand has no automatic Little Book publisher. Execution activity is never public merely because an execution receipt exists.

If the institution intentionally needs a public proof derived from execution history, The Book creates a separate minimum-necessary public attestation under disclosure policy. The Hand does not export the private receipt.

## Source evidence

Venue payloads, credentials, account identifiers, API secrets, and raw broker/exchange responses remain in restricted operational storage or The Vault according to retention policy. Big Book evidence should contain only the proof needed to establish the action and its lineage.
