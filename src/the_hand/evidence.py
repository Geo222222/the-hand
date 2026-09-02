from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .domain import ExecutionReceipt
from .verification import AuthorizationProof


@dataclass(frozen=True, slots=True)
class EvidenceDraft:
    """Private HAND.* Book Evidence Protocol v2 draft produced by The Hand."""

    event_type: str
    evidence_class: str
    privacy_class: str
    visibility_scope: tuple[str, ...]
    subject_id: str
    payload: bytes
    payload_ref: str | None
    correlation_id: str
    causation_receipt_id: str
    evidence_receipt_ids: tuple[str, ...]
    source_event_at: datetime | None
    occurred_at: datetime
    known_at: datetime
    produced_at: datetime
    valid_from: datetime | None
    valid_until: datetime | None


class EvidencePublisher(Protocol):
    """Producer-side gateway that durably persists signed HAND.* evidence."""

    def publish(self, draft: EvidenceDraft) -> str: ...


def execution_draft(
    receipt: ExecutionReceipt,
    *,
    authorization: AuthorizationProof,
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
        privacy_class="CONFIDENTIAL_EVIDENCE",
        visibility_scope=("HAND_EXECUTION", "BENJAMIN_RECONCILIATION", "BENJAMIN_AUDITOR"),
        subject_id=receipt.receipt_id,
        payload=payload,
        payload_ref=f"vault://hand/executions/{receipt.receipt_id}",
        correlation_id=authorization.correlation_id,
        causation_receipt_id=authorization.book_receipt_id,
        evidence_receipt_ids=(authorization.decision_receipt_id,),
        source_event_at=authorization.evaluated_at,
        occurred_at=receipt.executed_at,
        known_at=receipt.executed_at,
        produced_at=receipt.executed_at,
        valid_from=None,
        valid_until=None,
    )
