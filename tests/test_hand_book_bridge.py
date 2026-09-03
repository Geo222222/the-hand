import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from the_hand import (
    ACKNOWLEDGED,
    PENDING,
    EvidenceDraft,
    HandBookError,
    HandBookEvidencePublisher,
    HandBookOutbox,
    HandBookSigner,
    HandOutboxConflict,
    load_hand_book_signer_from_env,
)


NOW = datetime(2026, 9, 2, 20, 30, tzinfo=timezone.utc)


def private_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(raw).decode("ascii")


def draft(payload: bytes = b'{"execution":"dry-run"}') -> EvidenceDraft:
    return EvidenceDraft(
        event_type="HAND.EXECUTION",
        evidence_class="ECONOMIC",
        privacy_class="CONFIDENTIAL_EVIDENCE",
        visibility_scope=("HAND_EXECUTION",),
        subject_id="EXE-001",
        payload=payload,
        payload_ref="vault://hand/executions/EXE-001",
        correlation_id="LIFE-001",
        causation_receipt_id="BOOK-WATCH-001",
        evidence_receipt_ids=("BOOK-BEN-001",),
        source_event_at=NOW,
        occurred_at=NOW,
        known_at=NOW,
        produced_at=NOW,
        valid_from=None,
        valid_until=None,
    )


class FailingTransport:
    def append_idempotent(self, *, envelope, payload):
        raise ConnectionError("Book unavailable")


class AcceptingTransport:
    def append_idempotent(self, *, envelope, payload):
        return {
            "receipt_id": envelope["receipt_id"],
            "sequence": 3,
            "entry_hash": "c" * 64,
            "recorded_at": NOW.isoformat(),
            "accepted": True,
            "duplicate_replay": False,
        }


def test_hand_identity_owns_only_hand_namespace() -> None:
    signer = HandBookSigner(key_id="hand-k1", private_key=Ed25519PrivateKey.generate())
    identity = signer.public_identity
    assert identity.producer == "The Hand"
    assert identity.allowed_event_prefixes == ("HAND.",)

    forged = draft()
    object.__setattr__(forged, "event_type", "WATCHMAN.AUTHORIZATION")
    with pytest.raises(HandBookError):
        signer.sign_draft(receipt_id="BOOK-FORGED", draft=forged)


def test_hand_loader_requires_hand_runtime_key() -> None:
    with pytest.raises(HandBookError, match="HAND_BOOK_KEY_ID"):
        load_hand_book_signer_from_env({})


def test_hand_loader_rejects_watchman_key_reuse() -> None:
    shared = private_key_b64(Ed25519PrivateKey.generate())
    with pytest.raises(HandBookError, match="WATCHMAN"):
        load_hand_book_signer_from_env(
            {
                "HAND_BOOK_KEY_ID": "hand-k1",
                "HAND_BOOK_ED25519_PRIVATE_KEY_B64": shared,
                "WATCHMAN_BOOK_KEY_ID": "watchman-k1",
                "WATCHMAN_BOOK_ED25519_PRIVATE_KEY_B64": shared,
            }
        )


def test_publisher_persists_exact_signed_hand_evidence_before_delivery(tmp_path: Path) -> None:
    signer = HandBookSigner(key_id="hand-k1", private_key=Ed25519PrivateKey.generate())
    outbox = HandBookOutbox(tmp_path)
    receipt_id = HandBookEvidencePublisher(signer, outbox).publish(draft())
    assert receipt_id == "BOOK-EXE-001"
    record_path = outbox.pending_dir / "BOOK-EXE-001.json"
    assert record_path.is_file()
    record = __import__("json").loads(record_path.read_text(encoding="utf-8"))
    assert record["state"] == PENDING
    assert record["producer"] == "The Hand"
    assert record["event_prefix"] == "HAND."
    assert record["envelope"]["event_type"] == "HAND.EXECUTION"
    assert record["envelope"]["causation_receipt_id"] == "BOOK-WATCH-001"
    assert record["envelope"]["evidence_receipt_ids"] == ["BOOK-BEN-001"]


def test_hand_outbox_retries_exact_evidence_then_acknowledges(tmp_path: Path) -> None:
    signer = HandBookSigner(key_id="hand-k1", private_key=Ed25519PrivateKey.generate())
    outbox = HandBookOutbox(tmp_path)
    HandBookEvidencePublisher(signer, outbox).publish(draft())

    pending = __import__("json").loads((outbox.pending_dir / "BOOK-EXE-001.json").read_text(encoding="utf-8"))
    envelope_digest = pending["envelope_digest"]
    payload_digest = pending["payload_digest"]

    failed = outbox.deliver_one("BOOK-EXE-001", FailingTransport())
    assert failed["state"] == PENDING
    assert failed["attempt_count"] == 1
    assert failed["envelope_digest"] == envelope_digest
    assert failed["payload_digest"] == payload_digest

    accepted = outbox.deliver_one("BOOK-EXE-001", AcceptingTransport())
    assert accepted["state"] == ACKNOWLEDGED
    assert accepted["attempt_count"] == 2
    assert accepted["envelope_digest"] == envelope_digest
    assert accepted["payload_digest"] == payload_digest
    assert accepted["book_receipt"]["sequence"] == 3


def test_hand_receipt_id_cannot_change_meaning(tmp_path: Path) -> None:
    signer = HandBookSigner(key_id="hand-k1", private_key=Ed25519PrivateKey.generate())
    outbox = HandBookOutbox(tmp_path)
    publisher = HandBookEvidencePublisher(signer, outbox)
    publisher.publish(draft(b"first"))
    with pytest.raises(HandOutboxConflict):
        publisher.publish(draft(b"second"))


def test_hand_envelope_payload_digest_is_exact() -> None:
    signer = HandBookSigner(key_id="hand-k1", private_key=Ed25519PrivateKey.generate())
    subject = draft()
    envelope = signer.sign_draft(receipt_id="BOOK-EXE-001", draft=subject)
    assert envelope["payload_digest"] == hashlib.sha256(subject.payload).hexdigest()
