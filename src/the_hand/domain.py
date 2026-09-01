from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    DRY_RUN = "DRY_RUN"


_REQUIRED = {
    "schema_version",
    "authorization_id",
    "idempotency_key",
    "fund_id",
    "instrument",
    "side",
    "quantity",
    "decision_id",
    "risk_id",
    "issued_at",
    "expires_at",
}


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    schema_version: str
    authorization_id: str
    idempotency_key: str
    fund_id: str
    instrument: str
    side: OrderSide
    quantity: Decimal
    decision_id: str
    risk_id: str
    issued_at: datetime
    expires_at: datetime

    @classmethod
    def from_wire(cls, wire: dict[str, Any]) -> "ExecutionRequest":
        if set(wire) != _REQUIRED:
            missing = sorted(_REQUIRED - set(wire))
            extra = sorted(set(wire) - _REQUIRED)
            raise ValueError(f"contract fields mismatch; missing={missing}, extra={extra}")
        if wire["schema_version"] != "1.0":
            raise ValueError("unsupported schema_version")
        if not isinstance(wire["authorization_id"], str) or not wire["authorization_id"].startswith("AUTH-"):
            raise ValueError("invalid authorization_id")
        if not isinstance(wire["decision_id"], str) or not wire["decision_id"].startswith("DEC-"):
            raise ValueError("invalid decision_id")
        if not isinstance(wire["risk_id"], str) or not wire["risk_id"].startswith("RSK-"):
            raise ValueError("invalid risk_id")
        if not isinstance(wire["idempotency_key"], str) or not re.fullmatch(r"[a-f0-9]{64}", wire["idempotency_key"]):
            raise ValueError("invalid idempotency_key")
        if not isinstance(wire["fund_id"], str) or not wire["fund_id"]:
            raise ValueError("fund_id is required")
        if not isinstance(wire["instrument"], str) or not wire["instrument"]:
            raise ValueError("instrument is required")

        try:
            side = OrderSide(wire["side"])
            quantity = Decimal(wire["quantity"])
            issued_at = datetime.fromisoformat(wire["issued_at"])
            expires_at = datetime.fromisoformat(wire["expires_at"])
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise ValueError("invalid typed contract value") from exc

        if quantity <= 0 or not quantity.is_finite():
            raise ValueError("quantity must be positive and finite")
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if expires_at <= issued_at:
            raise ValueError("authorization expiry must follow issuance")

        return cls(
            schema_version="1.0",
            authorization_id=wire["authorization_id"],
            idempotency_key=wire["idempotency_key"],
            fund_id=wire["fund_id"],
            instrument=wire["instrument"],
            side=side,
            quantity=quantity,
            decision_id=wire["decision_id"],
            risk_id=wire["risk_id"],
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def fingerprint(self) -> str:
        material = {
            "schema_version": self.schema_version,
            "authorization_id": self.authorization_id,
            "idempotency_key": self.idempotency_key,
            "fund_id": self.fund_id,
            "instrument": self.instrument,
            "side": self.side.value,
            "quantity": format(self.quantity, "f"),
            "decision_id": self.decision_id,
            "risk_id": self.risk_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    schema_version: str
    receipt_id: str
    authorization_id: str
    idempotency_key: str
    status: ExecutionStatus
    venue_order_id: str | None
    executed_quantity: Decimal | None
    average_price: Decimal | None
    executed_at: datetime
    message: str | None

    def to_wire(self) -> dict[str, str | None]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "authorization_id": self.authorization_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "venue_order_id": self.venue_order_id,
            "executed_quantity": None if self.executed_quantity is None else format(self.executed_quantity, "f"),
            "average_price": None if self.average_price is None else format(self.average_price, "f"),
            "executed_at": self.executed_at.isoformat(),
            "message": self.message,
        }
