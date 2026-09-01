# Benjamin / Book / Hand Protocol

The execution instruction remains `AuthorizedExecutionRequest` schema v1.0.

Before The Hand accepts that instruction, its `AuthorizationVerifier` must independently resolve the request to valid `BENJAMIN.AUTHORIZATION` evidence in `Geo222222/the-book` and return:

```text
AuthorizationProof
  book_receipt_id
  correlation_id
```

After exact execution, The Hand publishes:

```text
event_type: HAND.EXECUTION
evidence_class: ECONOMIC
subject_id: ExecutionReceipt.receipt_id
correlation_id: inherited from authorization proof
causation_receipt_id: Benjamin authorization Book receipt
payload: canonical ExecutionReceipt wire representation
```

Producer signing and Book ingestion are adapter concerns. The Hand never receives The Book's private infrastructure keys and never signs for another namespace.
