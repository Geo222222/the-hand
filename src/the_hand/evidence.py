from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .domain import ExecutionReceipt


@dataclass(frozen=True, slots=True)
class EvidenceDraft:
    event_type: str
    evidence_class: str
    subject_id: str
    payload: bytes
    payload_ref: str | None
    correlation_id: str
    causation_receipt_id: str


class EvidencePublisher(Protocol):
    """Producer-side signer/client for Geo222222/the-book."""

    def publish(self, draft: EvidenceDraft) -> str: ...


def execution_draft(
    receipt: ExecutionReceipt,
    *,
    correlation_id: str,
    authorization_book_receipt_id: str,
) -> EvidenceDraft:
    payload = json.dumps(
        receipt.to_wire(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return EvidenceDraft(
        event_type="HAND.EXECUTION",
        evidence_class="ECONOMIC",
        subject_id=receipt.receipt_id,
        payload=payload,
        payload_ref=None,
        correlation_id=correlation_id,
        causation_receipt_id=authorization_book_receipt_id,
    )
