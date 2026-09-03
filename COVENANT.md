# The Hand Covenant

> **ZLJ sees. Benjamin decides. Watchman governs. The Hand executes. The Book remembers and proves.**

1. The Hand executes authorized external financial actions; it does not decide whether the underlying economic action is desirable.
2. The Hand is the home for governed external-action capabilities and adapters, not merely one exchange/broker implementation.
3. Production action authority comes from Watchman after a Benjamin decision. The Hand must not treat model confidence, ZLJ evidence, or a Benjamin decision alone as sufficient live authority.
4. A target authorization must resolve to exact, scoped, independently verifiable Watchman authority, not merely a boolean assertion.
5. The Hand executes only the exact authorized action family and material parameters.
6. Authorization expiry is final.
7. Idempotency prevents duplicate external actions and duplicate execution proofs.
8. The Hand may route among technically equivalent adapters only when the authorization and capability policy explicitly permit that routing.
9. Adapter selection may not materially change side, instrument, asset, destination, amount, account, economic purpose, or risk beyond the authorized envelope.
10. A materially changed action requires a new Benjamin decision and/or Watchman authorization as applicable.
11. The Hand signs or emits only `HAND.*` execution/capability evidence for truth it owns.
12. Every material external-action outcome must be causally linkable to the governing Watchman authorization and preserved through The Book.
13. Ordinary Hand evidence is private/confidential unless a narrower policy explicitly applies.
14. The Hand receives no more Benjamin, Watchman, ZLJ, portfolio, or Book information than is necessary to verify and perform the authorized action.
15. The Hand has no automatic execution-to-Little-Book or execution-to-public-chain disclosure path.
16. Venue credentials, signing keys, bank credentials, custody secrets, raw identity data, and comparable `SECRET_REGULATED` material never become raw immutable execution-proof payloads.
17. General-purpose reasoning models must not receive unrestricted production signing authority merely because they help operate or troubleshoot a capability.
18. The Hand cannot edit or delete proof already accepted by The Book. Corrections, reversals, and later reconciliation create new records.
19. A future public proof about an action must be created separately by The Book under explicit disclosure policy and minimum-necessary evidence rules.
20. Read-only market observation belongs upstream in ZLJ where it supports perception. Authenticated financial write operations belong in The Hand.
21. Capability families may include exchanges, brokers, wallet/custody signers, blockchain transaction submission, banks/ACH/wires, payment processors, treasury/settlement rails, and future approved financial integrations.
22. The existence of a capability does not grant permission to use it.
23. Before live execution, durable outbox/receipt behavior must ensure an external action cannot disappear from institutional history if Book publication is temporarily unavailable.
24. Before live execution, capability-specific reconciliation, kill switches, credential isolation, deterministic constraints, provider failure handling, and qualification evidence are required.
25. No specific blockchain, broker, exchange, bank, payment processor, custody provider, ledger backend, or integration vendor is constitutional to The Hand. Capability contracts must survive adapter replacement where feasible.
26. The Hand must fail closed when authorization is missing, ambiguous, expired, incompatible with the requested capability, blocked, cryptographically invalid, or not committed in The Book.
27. The Hand must never infer an external financial action from conversational prose when a typed authorized action is required.
28. The Hand may report capability availability, expected operational constraints, or execution feasibility upstream; those facts do not let it originate investment intent.

## H2 implementation rule

H2 implements the target organ boundary:

`ZLJ evidence -> Benjamin decision -> Watchman authorization -> The Hand capability invocation -> Hand execution evidence`

The Hand requires a typed Protocol v2 request that points to a specific committed `WATCHMAN.AUTHORIZATION` receipt. It independently verifies the Watchman signature and exact capability constraints before any adapter call. The legacy H1 `BENJAMIN.AUTHORIZATION` execution wire is intentionally rejected rather than silently translated.

The Hand uses a separate `HAND.*` producer identity for execution evidence. Physical access to Benjamin or Watchman code or keys does not grant The Hand authority to sign for those organs.

H2 remains dry-run/shadow infrastructure. This bridge completes the authority boundary; it does not authorize live financial action or relax any live-execution qualification requirement.
