from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .domain import ExecutionRequest, ExecutionStatus


@dataclass(frozen=True, slots=True)
class VenueResult:
    status: ExecutionStatus
    venue_order_id: str | None = None
    executed_quantity: Decimal | None = None
    average_price: Decimal | None = None
    message: str | None = None


class VenueAdapter(Protocol):
    mode: str

    def execute_exact(self, request: ExecutionRequest) -> VenueResult: ...


class DryRunAdapter:
    mode = "DRY_RUN"

    def execute_exact(self, request: ExecutionRequest) -> VenueResult:
        return VenueResult(
            status=ExecutionStatus.DRY_RUN,
            executed_quantity=None,
            average_price=None,
            message=f"dry-run accepted exact instruction {request.side.value} {request.quantity} {request.instrument}",
        )
