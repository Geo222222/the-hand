# Benjamin ↔ The Hand Protocol v1.0

The JSON schemas in this directory are the cross-repository boundary.

For B0/H0:

- Benjamin is the producer of `AuthorizedExecutionRequest`.
- The Hand is the consumer.
- The Hand produces `ExecutionReceipt`.
- Benjamin's Book is the intended consumer of receipts.
- Decimal quantities are serialized as strings; binary floating point is not part of the protocol.
- `additionalProperties: false` is intentional. Silent contract drift is prohibited.
- H0 authorization trust is injected through `AuthorizationVerifier`; cryptographic signing/key rotation is reserved for a later milestone and must not be replaced by trusting an `AUTH-` prefix.

The schema copies should remain byte-for-byte aligned with the matching Benjamin protocol version.
