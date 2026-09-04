# The Hand Privacy Doctrine

The Hand owns **execution/capability truth**. It does not own public disclosure, market intelligence, capital decisions, or governance.

> **ZLJ sees. Benjamin decides. Watchman governs. The Hand executes. The Book remembers and proves.**

## Default posture

Authorized action instructions, provider translation mechanics, plans, and eventual outcomes are private institutional facts by default. They may reveal positions, strategy, counterparties, prices, quantities, timing, account relationships, destinations, venue relationships, or operational controls.

Foundation v1 publishes only minimum-necessary `HAND.EXECUTION_PLAN` evidence for the canonical planning path. The inherited dry-run compatibility path may publish historical `HAND.EXECUTION` evidence under its already-certified semantics. Both are confidential Big Book evidence unless a narrower policy applies.

Default readers should be limited to roles that require execution, reconciliation, governance verification, or audit access.

## Authorization visibility

Foundation v1 receives only enough Book/governance access to establish that the exact **Watchman authorization** exists, is authentic, unexpired, compatible with the requested capability/economic path, and bound to the correct institutional lineage and idempotency rules.

It does not need unrelated portfolio history, ZLJ model internals, Benjamin deliberation, other participants' information, or private institutional history.

The canonical `WatchmanAuthorizedAction` contains bounded economic authority. Provider-native quantity, contract count, lot/step mechanics, and provider order parameters are not Watchman/Benjamin authority fields; they are created only below The Hand translation boundary.

### Legacy H1/H2 compatibility

Historical H1/H2 execution contracts remain private and retain only their historical implementation meaning. The earlier H2 dry-run request includes a provider-facing quantity after Watchman proof verification; it is not the canonical Foundation-v1 economic authority contract and must not be reinterpreted as placing provider-native quantity in Benjamin or Watchman.

No historical record is silently upgraded or rewritten.

## Plan privacy and deterministic evidence

A `ProviderExecutionPlan` contains minimum mechanical information needed to prove how authorized economic authority would be expressed through a qualified provider capability. It may include provider/instrument identity, native quantity/unit, reference-price evidence identity, metadata/TranslationPolicy hashes, translation error, and provider constraints.

Plan identity and `HAND.EXECUTION_PLAN` payload are deterministic from immutable causal inputs. Runtime replay records contain only idempotency/input/plan hashes; they do not contain provider credentials and do not create provider execution authority.

Foundation v1 does not emit submission, acceptance, fill, settlement, or reconciliation evidence because those events do not occur in this phase.

## Little Book

The Hand has no automatic Little Book publisher. Execution/planning activity is never public merely because a Hand receipt exists.

If the institution intentionally needs a public proof derived from private Hand history, The Book creates a separate minimum-necessary public attestation under disclosure policy. The Hand does not export its private receipt directly.

## Source evidence and secrets

Venue/provider payloads, credentials, account identifiers, API secrets, bank credentials, signing keys, custody secrets, seed phrases, withdrawal material, and raw broker/exchange responses remain in restricted operational storage or The Vault according to retention policy.

Big Book evidence should contain only the minimum proof/reference needed to establish the plan/action and its lineage.

Foundation v1 provisions no provider credentials or production account authority. The repository's existing `HAND_BOOK_KEY_ID` / `HAND_BOOK_ED25519_PRIVATE_KEY_B64` interface belongs only to The Hand's private Book evidence producer identity. Secret values are runtime material and must not be committed to Git or included in evidence payloads.

## Capability privacy

The Hand may eventually expose many financial capability families—exchange, broker, wallet/custody, bank, payment, treasury, settlement, and other approved integrations.

Capability inventory itself may be sensitive where it reveals account relationships, provider dependencies, limits, or operational defenses. Discovery or qualification of a capability does not imply permission to invoke it. Watchman authorization remains separately required, and Foundation v1 still ends at plan construction.

## Core privacy invariant

> **The Hand receives and reveals only what is necessary to verify, translate, perform, and prove the exact governed action at the lifecycle stage actually earned.**