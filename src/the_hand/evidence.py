from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .authorization import VerifiedWatchmanAuthorizedAction
from .domain import ExecutionReceipt
from .planning import ProviderExecutionPlan
from .verification import AuthorizationProof


@dataclass(frozen=True)
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


def execution_plan_draft(
    plan: ProviderExecutionPlan,
    *,
    authorization: VerifiedWatchmanAuthorizedAction,
) -> EvidenceDraft:
    """Draft minimum-necessary evidence for a plan that has not been submitted.

    The payload is the deterministic provider execution plan only. It contains
    no credentials and makes no submission, acceptance, fill, settlement, or
    reconciliation claim.
    """

    if plan.source_watchman_authorization_id != authorization.action.authorization_id:
        raise ValueError("plan authorization identity does not match verified Watchman authority")
    if plan.source_watchman_authorization_hash != authorization.action.authorization_content_hash:
        raise ValueError("plan authorization hash does not match verified Watchman authority")
    if plan.candidate_economic_path_id != authorization.action.candidate_economic_path_id:
        raise ValueError("plan candidate economic path does not match verified Watchman authority")
    if plan.candidate_economic_path_hash != authorization.action.candidate_economic_path_hash:
        raise ValueError("plan candidate economic path hash does not match verified Watchman authority")
    if plan.idempotency_key != authorization.action.idempotency_key:
        raise ValueError("plan idempotency key does not match verified Watchman authority")

    payload = json.dumps(
        plan.to_wire(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return EvidenceDraft(
        event_type="HAND.EXECUTION_PLAN",
        evidence_class="ECONOMIC",
        privacy_class="CONFIDENTIAL_EVIDENCE",
        visibility_scope=("HAND_EXECUTION", "BENJAMIN_RECONCILIATION", "BENJAMIN_AUDITOR"),
        subject_id=plan.plan_content_hash,
        payload=payload,
        payload_ref=f"vault://hand/execution-plans/{plan.plan_content_hash}",
        correlation_id=authorization.correlation_id,
        causation_receipt_id=authorization.action.authorization_book_receipt_id,
        evidence_receipt_ids=(authorization.action.benjamin_decision_receipt_id,),
        source_event_at=authorization.action.issued_at,
        occurred_at=plan.known_at,
        known_at=plan.known_at,
        produced_at=plan.known_at,
        valid_from=plan.known_at,
        valid_until=plan.valid_until,
    )


def execution_draft(
    receipt: ExecutionReceipt,
    *,
    authorization: AuthorizationProof,
) -> EvidenceDraft:
    """Legacy H2 dry-run execution evidence preserved for historical compatibility."""

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
