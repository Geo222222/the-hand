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


_REQUIRED_V2 = {
    "schema_version",
    "authorization_book_receipt_id",
    "capability",
    "idempotency_key",
    "instrument",
    "side",
    "quantity",
    "decision_id",
    "governance_id",
    "expires_at",
}


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Exact capability request whose authority is a Watchman Book receipt."""

    schema_version: str
    authorization_book_receipt_id: str
    capability: str
    idempotency_key: str
    instrument: str
    side: OrderSide
    quantity: Decimal
    decision_id: str
    governance_id: str
    expires_at: datetime

    @classmethod
    def from_wire(cls, wire: dict[str, Any]) -> "ExecutionRequest":
        if set(wire) != _REQUIRED_V2:
            missing = sorted(_REQUIRED_V2 - set(wire))
            extra = sorted(set(wire) - _REQUIRED_V2)
            raise ValueError(f"contract fields mismatch; missing={missing}, extra={extra}")
        if wire["schema_version"] != "2.0":
            raise ValueError("unsupported schema_version; The Hand requires Watchman-authorized v2 requests")
        for field in ("authorization_book_receipt_id", "capability", "instrument"):
            if not isinstance(wire[field], str) or not wire[field]:
                raise ValueError(f"{field} is required")
        if not isinstance(wire["decision_id"], str) or not wire["decision_id"].startswith("DEC-"):
            raise ValueError("invalid decision_id")
        if not isinstance(wire["governance_id"], str) or not wire["governance_id"]:
            raise ValueError("invalid governance_id")
        if not isinstance(wire["idempotency_key"], str) or not re.fullmatch(r"[a-f0-9]{64}", wire["idempotency_key"]):
            raise ValueError("invalid idempotency_key")

        try:
            side = OrderSide(wire["side"])
            quantity = Decimal(str(wire["quantity"]))
            expires_at = datetime.fromisoformat(str(wire["expires_at"]).replace("Z", "+00:00"))
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise ValueError("invalid typed contract value") from exc

        if quantity <= 0 or not quantity.is_finite():
            raise ValueError("quantity must be positive and finite")
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("authorization expiry must be timezone-aware")

        return cls(
            schema_version="2.0",
            authorization_book_receipt_id=str(wire["authorization_book_receipt_id"]),
            capability=str(wire["capability"]),
            idempotency_key=str(wire["idempotency_key"]),
            instrument=str(wire["instrument"]),
            side=side,
            quantity=quantity,
            decision_id=str(wire["decision_id"]),
            governance_id=str(wire["governance_id"]),
            expires_at=expires_at,
        )

    def fingerprint(self) -> str:
        material = {
            "schema_version": self.schema_version,
            "authorization_book_receipt_id": self.authorization_book_receipt_id,
            "capability": self.capability,
            "idempotency_key": self.idempotency_key,
            "instrument": self.instrument,
            "side": self.side.value,
            "quantity": format(self.quantity, "f"),
            "decision_id": self.decision_id,
            "governance_id": self.governance_id,
            "expires_at": self.expires_at.isoformat(),
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    schema_version: str
    receipt_id: str
    authorization_book_receipt_id: str
    governance_id: str
    capability: str
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
            "authorization_book_receipt_id": self.authorization_book_receipt_id,
            "governance_id": self.governance_id,
            "capability": self.capability,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "venue_order_id": self.venue_order_id,
            "executed_quantity": None if self.executed_quantity is None else format(self.executed_quantity, "f"),
            "average_price": None if self.average_price is None else format(self.average_price, "f"),
            "executed_at": self.executed_at.isoformat(),
            "message": self.message,
        }
