# The Hand Covenant

1. The Hand executes; it does not decide.
2. No instruction executes without independently verified Benjamin authorization proof in the **Big Book**.
3. Verification must resolve to a scoped Big Book receipt, not merely a boolean assertion.
4. The Hand executes the exact authorized instrument, side, and quantity.
5. Authorization expiry is final.
6. Idempotency prevents duplicate actions and duplicate execution proofs.
7. The Hand signs only `HAND.*` proofs.
8. Every material execution outcome produces private Big Book proof causally linked to the Benjamin authorization receipt.
9. Ordinary `HAND.EXECUTION` proof is `CONFIDENTIAL_EVIDENCE` and is not a public disclosure.
10. The Hand must receive no more Big Book information than is necessary to verify and perform its authorization.
11. The Hand has no automatic Big Book-to-Little Book or execution-to-public-chain path.
12. Venue credentials, account secrets, raw identity data, and comparable `SECRET_REGULATED` information never become immutable execution proof payloads.
13. The Hand cannot edit or delete proof already accepted by the Big Book. Corrections or reversals create new records.
14. A future public proof about an execution must be created separately by The Book under explicit disclosure policy and minimum-necessary evidence rules.
15. H1 rejects live venue adapters.
16. Before live execution, a durable outbox must guarantee that a venue action cannot disappear from institutional history if Big Book publication is temporarily unavailable.
17. No specific blockchain or ledger backend is constitutional to The Hand. It depends on proof semantics, not chain technology.
