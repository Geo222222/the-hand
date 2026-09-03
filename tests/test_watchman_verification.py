from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from the_hand import (
    CommittedBookEvidence,
    ExecutionRequest,
    WatchmanAuthorizationVerifier,
    WatchmanKeyRegistry,
)


NOW = datetime(2026, 9, 2, 20, 0, tzinfo=timezone.utc)
EVALUATED = NOW - timedelta(seconds=1)
EXPIRES = NOW + timedelta(minutes=5)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def request(**updates: object) -> ExecutionRequest:
    wire: dict[str, object] = {
        "schema_version": "2.0",
        "authorization_book_receipt_id": "BOOK-WATCH-001",
        "capability": "ORDER_EXECUTION",
        "idempotency_key": "a" * 64,
        "instrument": "BTC-USD",
        "side": "BUY",
        "quantity": "0.01",
        "decision_id": "DEC-001",
        "governance_id": "RSK-001",
        "expires_at": EXPIRES.isoformat(),
    }
    wire.update(updates)
    return ExecutionRequest.from_wire(wire)


def payload(*, result: str = "AUTHORIZE", quantity: str = "0.01") -> bytes:
    authorized = result == "AUTHORIZE"
    return canonical(
        {
            "schema_version": "1.0",
            "governance_id": "RSK-001",
            "decision_receipt_id": "BOOK-BEN-001",
            "decision_id": "DEC-001",
            "result": result,
            "policy_version": "watchman-b0-v1",
            "checks": [
                {
                    "check_id": "B0_POLICY_PASS" if authorized else "ORDER_QUANTITY_LIMIT_EXCEEDED",
                    "status": "PASS" if authorized else "BLOCK",
                    "reason": "B0_POLICY_PASS" if authorized else "ORDER_QUANTITY_LIMIT_EXCEEDED",
                }
            ],
            "capability_constraints": (
                {
                    "capability": "ORDER_EXECUTION",
                    "instrument": "BTC-USD",
                    "side": "BUY",
                    "quantity": quantity,
                    "idempotency_key": "a" * 64,
                }
                if authorized
                else None
            ),
            "evaluated_at": EVALUATED.isoformat(),
            "expires_at": EXPIRES.isoformat() if authorized else None,
        }
    )


def signed_evidence(
    key: Ed25519PrivateKey,
    *,
    event_type: str = "WATCHMAN.AUTHORIZATION",
    body_payload: bytes | None = None,
    key_id: str = "watchman-k1",
) -> CommittedBookEvidence:
    body_payload = payload() if body_payload is None else body_payload
    envelope = {
        "schema_version": "2.0",
        "receipt_id": "BOOK-WATCH-001",
        "producer": "Watchman",
        "producer_key_id": key_id,
        "event_type": event_type,
        "evidence_class": "CONSTITUTIONAL",
        "subject_id": "RSK-001",
        "occurred_at": EVALUATED.isoformat(),
        "payload_digest": hashlib.sha256(body_payload).hexdigest(),
        "payload_ref": "vault://watchman/governance/RSK-001",
        "correlation_id": "LIFE-001",
        "causation_receipt_id": "BOOK-BEN-001",
        "privacy_class": "CONFIDENTIAL_EVIDENCE",
        "visibility_scope": ["WATCHMAN_AUTHORITY", "HAND_VERIFIER", "BENJAMIN_AUDITOR"],
        "evidence_receipt_ids": [],
        "source_event_at": (EVALUATED - timedelta(milliseconds=10)).isoformat(),
        "known_at": EVALUATED.isoformat(),
        "produced_at": EVALUATED.isoformat(),
        "valid_from": EVALUATED.isoformat() if event_type == "WATCHMAN.AUTHORIZATION" else None,
        "valid_until": EXPIRES.isoformat() if event_type == "WATCHMAN.AUTHORIZATION" else None,
    }
    signature = key.sign(canonical(envelope))
    signed = {**envelope, "signature": base64.b64encode(signature).decode("ascii")}
    return CommittedBookEvidence(
        receipt_id="BOOK-WATCH-001",
        sequence=2,
        entry_hash="b" * 64,
        recorded_at=EVALUATED + timedelta(milliseconds=1),
        envelope=signed,
        payload=body_payload,
    )


class Source:
    def __init__(self, evidence: CommittedBookEvidence | None) -> None:
        self.evidence = evidence

    def get_committed(self, receipt_id: str):
        if self.evidence is None or self.evidence.receipt_id != receipt_id:
            return None
        return self.evidence


def verifier(evidence: CommittedBookEvidence, key: Ed25519PrivateKey) -> WatchmanAuthorizationVerifier:
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    registry = WatchmanKeyRegistry()
    registry.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    return WatchmanAuthorizationVerifier(Source(evidence), registry)


def test_exact_committed_watchman_authorization_verifies() -> None:
    key = Ed25519PrivateKey.generate()
    proof = verifier(signed_evidence(key), key).verify(request())
    assert proof is not None
    assert proof.book_receipt_id == "BOOK-WATCH-001"
    assert proof.decision_receipt_id == "BOOK-BEN-001"
    assert proof.quantity == Decimal("0.01")
    assert proof.capability == "ORDER_EXECUTION"
    assert proof.valid_until == EXPIRES


def test_watchman_block_is_not_execution_authority() -> None:
    key = Ed25519PrivateKey.generate()
    evidence = signed_evidence(key, event_type="WATCHMAN.BLOCK", body_payload=payload(result="BLOCK"))
    assert verifier(evidence, key).verify(request()) is None


def test_tampered_watchman_signature_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    evidence = signed_evidence(key)
    tampered = dict(evidence.envelope)
    tampered["signature"] = base64.b64encode(b"x" * 64).decode("ascii")
    changed = CommittedBookEvidence(
        receipt_id=evidence.receipt_id,
        sequence=evidence.sequence,
        entry_hash=evidence.entry_hash,
        recorded_at=evidence.recorded_at,
        envelope=tampered,
        payload=evidence.payload,
    )
    assert verifier(changed, key).verify(request()) is None


def test_unknown_watchman_key_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    evidence = signed_evidence(key, key_id="untrusted-k1")
    assert verifier(evidence, key).verify(request()) is None


def test_tampered_payload_digest_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    evidence = signed_evidence(key)
    changed = CommittedBookEvidence(
        receipt_id=evidence.receipt_id,
        sequence=evidence.sequence,
        entry_hash=evidence.entry_hash,
        recorded_at=evidence.recorded_at,
        envelope=evidence.envelope,
        payload=payload(quantity="0.02"),
    )
    assert verifier(changed, key).verify(request()) is None


def test_request_cannot_expand_watchman_quantity() -> None:
    key = Ed25519PrivateKey.generate()
    evidence = signed_evidence(key)
    expanded = request(quantity="0.02")
    assert verifier(evidence, key).verify(expanded) is None


def test_request_cannot_change_instrument_side_or_idempotency_key() -> None:
    key = Ed25519PrivateKey.generate()
    subject = verifier(signed_evidence(key), key)
    assert subject.verify(request(instrument="ETH-USD")) is None
    assert subject.verify(request(side="SELL")) is None
    assert subject.verify(request(idempotency_key="c" * 64)) is None


def test_request_expiry_must_equal_signed_watchman_expiry() -> None:
    key = Ed25519PrivateKey.generate()
    mismatched = request(expires_at=(EXPIRES + timedelta(seconds=1)).isoformat())
    assert verifier(signed_evidence(key), key).verify(mismatched) is None


def test_missing_book_receipt_fails_closed() -> None:
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    registry = WatchmanKeyRegistry()
    registry.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    assert WatchmanAuthorizationVerifier(Source(None), registry).verify(request()) is None
