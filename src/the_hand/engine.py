from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .adapter import VenueAdapter
from .domain import ExecutionReceipt, ExecutionRequest
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


class ExecutionEngine:
    """H0 execution boundary: exact, verified, idempotent, dry-run only."""

    def __init__(self, adapter: VenueAdapter, verifier: AuthorizationVerifier) -> None:
        self._adapter = adapter
        self._verifier = verifier
        self._receipts: dict[str, tuple[str, ExecutionReceipt]] = {}

    def execute(self, wire: dict[str, object], *, now: datetime | None = None) -> ExecutionReceipt:
        try:
            request = ExecutionRequest.from_wire(wire)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc

        if self._adapter.mode != "DRY_RUN":
            raise LiveExecutionDisabled("H0 permits DRY_RUN adapters only")
        if not self._verifier.verify(request):
            raise UntrustedAuthorization("authorization verifier denied request")

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ContractError("execution clock must be timezone-aware")
        if current_time >= request.expires_at:
            raise AuthorizationExpired("authorization has expired")

        fingerprint = request.fingerprint()
        existing = self._receipts.get(request.idempotency_key)
        if existing is not None:
            existing_fingerprint, receipt = existing
            if existing_fingerprint != fingerprint:
                raise IdempotencyConflict("idempotency key reused with different instruction")
            return receipt

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
        self._receipts[request.idempotency_key] = (fingerprint, receipt)
        return receipt
