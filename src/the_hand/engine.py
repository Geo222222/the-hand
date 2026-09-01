from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .adapter import VenueAdapter
from .domain import ExecutionReceipt, ExecutionRequest
from .evidence import EvidencePublisher, execution_draft
from .verification import AuthorizationVerifier


class HandError(RuntimeError):
    pass


class ContractError(HandError):
    pass


class UntrustedAuthorization(HandError):
    pass


class AuthorizationExpired(HandError):
    pass


class IdempotencyConflict(HandError):
    pass


class LiveExecutionDisabled(HandError):
    pass


class EvidencePublicationError(HandError):
    pass


@dataclass(frozen=True, slots=True)
class RecordedExecution:
    receipt: ExecutionReceipt
    book_receipt_id: str


class ExecutionEngine:
    """H1 execution boundary: exact, Book-verified, idempotent, evidence-recorded, dry-run only."""

    def __init__(
        self,
        adapter: VenueAdapter,
        verifier: AuthorizationVerifier,
        evidence_publisher: EvidencePublisher,
    ) -> None:
        self._adapter = adapter
        self._verifier = verifier
        self._evidence_publisher = evidence_publisher
        self._records: dict[str, tuple[str, RecordedExecution]] = {}

    def execute(self, wire: dict[str, object], *, now: datetime | None = None) -> RecordedExecution:
        try:
            request = ExecutionRequest.from_wire(wire)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc

        if self._adapter.mode != "DRY_RUN":
            raise LiveExecutionDisabled("H1 permits DRY_RUN adapters only")

        proof = self._verifier.verify(request)
        if proof is None:
            raise UntrustedAuthorization("no trusted BENJAMIN.AUTHORIZATION evidence found in The Book")

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ContractError("execution clock must be timezone-aware")
        if current_time >= request.expires_at:
            raise AuthorizationExpired("authorization has expired")

        fingerprint = request.fingerprint()
        existing = self._records.get(request.idempotency_key)
        if existing is not None:
            existing_fingerprint, record = existing
            if existing_fingerprint != fingerprint:
                raise IdempotencyConflict("idempotency key reused with different instruction")
            return record

        result = self._adapter.execute_exact(request)
        receipt = ExecutionReceipt(
            schema_version="1.0",
            receipt_id=f"EXE-{uuid4()}",
            authorization_id=request.authorization_id,
            idempotency_key=request.idempotency_key,
            status=result.status,
            venue_order_id=result.venue_order_id,
            executed_quantity=result.executed_quantity,
            average_price=result.average_price,
            executed_at=current_time,
            message=result.message,
        )

        try:
            book_receipt_id = self._evidence_publisher.publish(
                execution_draft(
                    receipt,
                    correlation_id=proof.correlation_id,
                    authorization_book_receipt_id=proof.book_receipt_id,
                )
            )
        except Exception as exc:
            raise EvidencePublicationError(
                "execution evidence publication failed; H1 dry-run result is not considered recorded"
            ) from exc

        record = RecordedExecution(receipt=receipt, book_receipt_id=book_receipt_id)
        self._records[request.idempotency_key] = (fingerprint, record)
        return record
