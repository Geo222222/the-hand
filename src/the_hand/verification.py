from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .domain import ExecutionRequest, OrderSide


_ENVELOPE_FIELDS = {
    "schema_version",
    "receipt_id",
    "producer",
    "producer_key_id",
    "event_type",
    "evidence_class",
    "subject_id",
    "occurred_at",
    "payload_digest",
    "payload_ref",
    "correlation_id",
    "causation_receipt_id",
    "privacy_class",
    "visibility_scope",
    "evidence_receipt_ids",
    "source_event_at",
    "known_at",
    "produced_at",
    "valid_from",
    "valid_until",
    "signature",
}

_WATCHMAN_PAYLOAD_FIELDS = {
    "schema_version",
    "governance_id",
    "decision_receipt_id",
    "decision_id",
    "result",
    "policy_version",
    "checks",
    "capability_constraints",
    "evaluated_at",
    "expires_at",
}

_CONSTRAINT_FIELDS = {"capability", "instrument", "side", "quantity", "idempotency_key"}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp is required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return result


@dataclass(frozen=True, slots=True)
class CommittedBookEvidence:
    """A single committed Big Book entry returned by a trusted read boundary."""

    receipt_id: str
    sequence: int
    entry_hash: str
    recorded_at: datetime
    envelope: Mapping[str, Any]
    payload: bytes

    def __post_init__(self) -> None:
        if not self.receipt_id or self.sequence < 0:
            raise ValueError("committed Book evidence requires receipt_id and non-negative sequence")
        if len(self.entry_hash) != 64:
            raise ValueError("entry_hash must be SHA-256 hex")
        try:
            int(self.entry_hash, 16)
        except ValueError as exc:
            raise ValueError("entry_hash must be SHA-256 hex") from exc
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")


class BookEvidenceSource(Protocol):
    """Read-only source that returns only entries already committed by Big Book."""

    def get_committed(self, receipt_id: str) -> CommittedBookEvidence | None: ...


class WatchmanKeyRegistry:
    """Hand-local trust store containing public Watchman verification keys only."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PublicKey] = {}

    def register(self, *, key_id: str, public_key_b64: str) -> None:
        if not key_id or key_id in self._keys:
            raise ValueError("Watchman key_id must be unique and non-empty")
        try:
            raw = base64.b64decode(public_key_b64, validate=True)
            self._keys[key_id] = Ed25519PublicKey.from_public_bytes(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid Watchman Ed25519 public key") from exc

    def get(self, key_id: str) -> Ed25519PublicKey | None:
        return self._keys.get(key_id)


@dataclass(frozen=True, slots=True)
class AuthorizationProof:
    """Verified Watchman authority bound to one exact executable capability."""

    book_receipt_id: str
    correlation_id: str
    governance_id: str
    decision_receipt_id: str
    decision_id: str
    capability: str
    instrument: str
    side: OrderSide
    quantity: Decimal
    idempotency_key: str
    evaluated_at: datetime
    valid_until: datetime
    sequence: int
    entry_hash: str
    producer_key_id: str

    def matches(self, request: ExecutionRequest) -> bool:
        return (
            self.book_receipt_id == request.authorization_book_receipt_id
            and self.governance_id == request.governance_id
            and self.decision_id == request.decision_id
            and self.capability == request.capability
            and self.instrument == request.instrument
            and self.side is request.side
            and self.quantity == request.quantity
            and self.idempotency_key == request.idempotency_key
            and self.valid_until == request.expires_at
        )


class AuthorizationVerifier(Protocol):
    """Resolve a request to valid WATCHMAN.AUTHORIZATION evidence, or deny it."""

    def verify(self, request: ExecutionRequest) -> AuthorizationProof | None: ...


class WatchmanAuthorizationVerifier:
    """Verify the signed Watchman authorization committed in The Book.

    The Big Book read boundary establishes that a receipt is committed. The Hand
    independently verifies Watchman's Ed25519 signature, payload digest, typed
    authorization semantics, and exact capability/request equality.
    """

    def __init__(self, source: BookEvidenceSource, keys: WatchmanKeyRegistry) -> None:
        self._source = source
        self._keys = keys

    def verify(self, request: ExecutionRequest) -> AuthorizationProof | None:
        try:
            evidence = self._source.get_committed(request.authorization_book_receipt_id)
            if evidence is None or evidence.receipt_id != request.authorization_book_receipt_id:
                return None
            envelope = dict(evidence.envelope)
            if set(envelope) != _ENVELOPE_FIELDS:
                return None
            if envelope.get("schema_version") != "2.0":
                return None
            if envelope.get("receipt_id") != evidence.receipt_id:
                return None
            if envelope.get("producer") != "Watchman":
                return None
            if envelope.get("event_type") != "WATCHMAN.AUTHORIZATION":
                return None
            if envelope.get("evidence_class") != "CONSTITUTIONAL":
                return None
            if envelope.get("subject_id") != request.governance_id:
                return None
            key_id = str(envelope.get("producer_key_id", ""))
            public_key = self._keys.get(key_id)
            if public_key is None:
                return None

            signature = base64.b64decode(str(envelope.get("signature", "")), validate=True)
            signing_body = {key: value for key, value in envelope.items() if key != "signature"}
            public_key.verify(signature, _canonical_json(signing_body))

            payload_digest = hashlib.sha256(evidence.payload).hexdigest()
            if payload_digest != str(envelope.get("payload_digest", "")).lower():
                return None
            payload = json.loads(evidence.payload.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != _WATCHMAN_PAYLOAD_FIELDS:
                return None
            if payload.get("schema_version") != "1.0" or payload.get("result") != "AUTHORIZE":
                return None
            if payload.get("governance_id") != request.governance_id:
                return None
            if payload.get("decision_id") != request.decision_id:
                return None
            decision_receipt_id = payload.get("decision_receipt_id")
            if not isinstance(decision_receipt_id, str) or not decision_receipt_id:
                return None
            if envelope.get("causation_receipt_id") != decision_receipt_id:
                return None
            correlation_id = envelope.get("correlation_id")
            if not isinstance(correlation_id, str) or not correlation_id:
                return None

            checks = payload.get("checks")
            if not isinstance(checks, list) or not checks:
                return None
            for check in checks:
                if (
                    not isinstance(check, dict)
                    or set(check) != {"check_id", "status", "reason"}
                    or not isinstance(check.get("check_id"), str)
                    or not check.get("check_id")
                    or check.get("status") != "PASS"
                    or not isinstance(check.get("reason"), str)
                    or not check.get("reason")
                ):
                    return None

            constraints = payload.get("capability_constraints")
            if not isinstance(constraints, dict) or set(constraints) != _CONSTRAINT_FIELDS:
                return None
            if constraints.get("capability") != request.capability:
                return None
            if constraints.get("instrument") != request.instrument:
                return None
            if constraints.get("side") != request.side.value:
                return None
            if constraints.get("idempotency_key") != request.idempotency_key:
                return None
            try:
                quantity = Decimal(str(constraints.get("quantity")))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError("invalid Watchman quantity") from exc
            if quantity != request.quantity or quantity <= 0 or not quantity.is_finite():
                return None

            evaluated_at = _timestamp(payload.get("evaluated_at"))
            expires_at = _timestamp(payload.get("expires_at"))
            occurred_at = _timestamp(envelope.get("occurred_at"))
            known_at = _timestamp(envelope.get("known_at"))
            produced_at = _timestamp(envelope.get("produced_at"))
            valid_until = _timestamp(envelope.get("valid_until"))
            if evaluated_at != occurred_at or evaluated_at != known_at:
                return None
            if expires_at != valid_until or expires_at != request.expires_at:
                return None
            if produced_at < known_at or evidence.recorded_at < produced_at:
                return None

            proof = AuthorizationProof(
                book_receipt_id=evidence.receipt_id,
                correlation_id=correlation_id,
                governance_id=str(payload["governance_id"]),
                decision_receipt_id=decision_receipt_id,
                decision_id=str(payload["decision_id"]),
                capability=str(constraints["capability"]),
                instrument=str(constraints["instrument"]),
                side=OrderSide(str(constraints["side"])),
                quantity=quantity,
                idempotency_key=str(constraints["idempotency_key"]),
                evaluated_at=evaluated_at,
                valid_until=expires_at,
                sequence=evidence.sequence,
                entry_hash=evidence.entry_hash,
                producer_key_id=key_id,
            )
            return proof if proof.matches(request) else None
        except (
            InvalidSignature,
            ValueError,
            TypeError,
            KeyError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return None


class DenyAllVerifier:
    """Safe default: nothing executes until a Watchman-aware verifier is configured."""

    def verify(self, request: ExecutionRequest) -> AuthorizationProof | None:
        return None
