from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .evidence import EvidenceDraft, EvidencePublisher


PENDING = "PENDING"
ACKNOWLEDGED = "ACKNOWLEDGED"
QUARANTINED = "QUARANTINED"


class HandBookError(RuntimeError):
    pass


class HandOutboxConflict(HandBookError):
    pass


@dataclass(frozen=True)
class HandPublicIdentity:
    producer: str
    key_id: str
    public_key_b64: str
    allowed_event_prefixes: tuple[str, ...]

    def wire(self) -> dict[str, object]:
        return {
            "producer": self.producer,
            "key_id": self.key_id,
            "public_key_b64": self.public_key_b64,
            "allowed_event_prefixes": list(self.allowed_event_prefixes),
        }


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class HandBookSigner:
    PRODUCER = "The Hand"
    PREFIX = "HAND."

    def __init__(self, *, key_id: str, private_key: Ed25519PrivateKey) -> None:
        if not key_id:
            raise HandBookError("HAND_BOOK_KEY_ID is required")
        self.key_id = key_id
        self._private_key = private_key

    @classmethod
    def from_private_key_b64(cls, *, key_id: str, private_key_b64: str) -> "HandBookSigner":
        try:
            raw = base64.b64decode(private_key_b64, validate=True)
            private_key = Ed25519PrivateKey.from_private_bytes(raw)
        except (ValueError, TypeError) as exc:
            raise HandBookError("invalid Hand Ed25519 private key material") from exc
        return cls(key_id=key_id, private_key=private_key)

    @property
    def public_identity(self) -> HandPublicIdentity:
        public_bytes = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return HandPublicIdentity(
            producer=self.PRODUCER,
            key_id=self.key_id,
            public_key_b64=base64.b64encode(public_bytes).decode("ascii"),
            allowed_event_prefixes=(self.PREFIX,),
        )

    def sign_draft(self, *, receipt_id: str, draft: EvidenceDraft) -> dict[str, object]:
        if not receipt_id:
            raise HandBookError("receipt_id is required")
        if not draft.event_type.startswith(self.PREFIX):
            raise HandBookError("The Hand signer may emit only HAND.* evidence")
        payload_digest = hashlib.sha256(draft.payload).hexdigest()
        body: dict[str, object] = {
            "schema_version": "2.0",
            "receipt_id": receipt_id,
            "producer": self.PRODUCER,
            "producer_key_id": self.key_id,
            "event_type": draft.event_type,
            "evidence_class": draft.evidence_class,
            "subject_id": draft.subject_id,
            "occurred_at": draft.occurred_at.isoformat(),
            "payload_digest": payload_digest,
            "payload_ref": draft.payload_ref,
            "correlation_id": draft.correlation_id,
            "causation_receipt_id": draft.causation_receipt_id,
            "privacy_class": draft.privacy_class,
            "visibility_scope": list(draft.visibility_scope),
            "evidence_receipt_ids": list(draft.evidence_receipt_ids),
            "source_event_at": draft.source_event_at.isoformat() if draft.source_event_at else None,
            "known_at": draft.known_at.isoformat(),
            "produced_at": draft.produced_at.isoformat(),
            "valid_from": draft.valid_from.isoformat() if draft.valid_from else None,
            "valid_until": draft.valid_until.isoformat() if draft.valid_until else None,
        }
        signature = self._private_key.sign(canonical_json(body))
        return {**body, "signature": base64.b64encode(signature).decode("ascii")}


def load_hand_book_signer_from_env(env: Mapping[str, str] | None = None) -> HandBookSigner:
    source = os.environ if env is None else env
    key_id = source.get("HAND_BOOK_KEY_ID", "")
    private_key_b64 = source.get("HAND_BOOK_ED25519_PRIVATE_KEY_B64", "")
    if not key_id or not private_key_b64:
        raise HandBookError(
            "Hand Book signing is unavailable: HAND_BOOK_KEY_ID and "
            "HAND_BOOK_ED25519_PRIVATE_KEY_B64 are required"
        )
    for organ in ("WATCHMAN", "BENJAMIN", "ZLJ"):
        other_key_id = source.get(f"{organ}_BOOK_KEY_ID")
        other_private = source.get(f"{organ}_BOOK_ED25519_PRIVATE_KEY_B64")
        if other_key_id and other_key_id == key_id:
            raise HandBookError(f"The Hand and {organ} must use different Book key IDs")
        if other_private and other_private == private_key_b64:
            raise HandBookError(f"The Hand and {organ} must use different Book private keys")
    return HandBookSigner.from_private_key_b64(key_id=key_id, private_key_b64=private_key_b64)


class HandBookTransport(Protocol):
    def append_idempotent(self, *, envelope: Mapping[str, Any], payload: bytes) -> Mapping[str, Any]: ...


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(value), handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HandBookError("outbox record must be a JSON object")
    return value


class HandBookOutbox:
    """Durable exact-evidence outbox for HAND.* only."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.pending_dir = self.root / "pending"
        self.acknowledged_dir = self.root / "acknowledged"
        self.quarantined_dir = self.root / "quarantined"

    def _path(self, state: str, receipt_id: str) -> Path:
        directory = {
            PENDING: self.pending_dir,
            ACKNOWLEDGED: self.acknowledged_dir,
            QUARANTINED: self.quarantined_dir,
        }[state]
        return directory / f"{receipt_id}.json"

    def _find(self, receipt_id: str) -> Path | None:
        for state in (PENDING, ACKNOWLEDGED, QUARANTINED):
            path = self._path(state, receipt_id)
            if path.is_file():
                return path
        return None

    def enqueue(self, *, envelope: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
        receipt_id = str(envelope.get("receipt_id", ""))
        event_type = str(envelope.get("event_type", ""))
        if not receipt_id:
            raise HandBookError("receipt_id is required")
        if envelope.get("producer") != "The Hand" or not event_type.startswith("HAND."):
            raise HandBookError("Hand outbox accepts only The Hand / HAND.* evidence")
        payload_digest = hashlib.sha256(payload).hexdigest()
        if payload_digest != str(envelope.get("payload_digest", "")).lower():
            raise HandBookError("payload digest differs from signed Hand envelope")
        envelope_digest = hashlib.sha256(canonical_json(dict(envelope))).hexdigest()
        existing_path = self._find(receipt_id)
        if existing_path is not None:
            existing = _read(existing_path)
            if existing.get("payload_digest") != payload_digest or existing.get("envelope_digest") != envelope_digest:
                raise HandOutboxConflict("receipt_id already belongs to different Hand evidence")
            return existing
        record: dict[str, Any] = {
            "schema_version": 1,
            "receipt_id": receipt_id,
            "producer": "The Hand",
            "event_prefix": "HAND.",
            "state": PENDING,
            "envelope": dict(envelope),
            "envelope_digest": envelope_digest,
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "payload_digest": payload_digest,
            "attempt_count": 0,
            "last_error": None,
            "book_receipt": None,
        }
        _atomic_json(self._path(PENDING, receipt_id), record)
        return record

    def pending_receipt_ids(self) -> tuple[str, ...]:
        if not self.pending_dir.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self.pending_dir.glob("*.json")))

    def deliver_one(self, receipt_id: str, transport: HandBookTransport) -> dict[str, Any]:
        path = self._path(PENDING, receipt_id)
        if not path.is_file():
            existing = self._find(receipt_id)
            if existing is None:
                raise KeyError(receipt_id)
            return _read(existing)
        record = _read(path)
        envelope = record["envelope"]
        payload = base64.b64decode(str(record["payload_b64"]), validate=True)
        if hashlib.sha256(payload).hexdigest() != record.get("payload_digest"):
            return self.quarantine(receipt_id, "stored payload digest mismatch")
        if hashlib.sha256(canonical_json(envelope)).hexdigest() != record.get("envelope_digest"):
            return self.quarantine(receipt_id, "stored envelope digest mismatch")
        record["attempt_count"] = int(record.get("attempt_count", 0)) + 1
        record["last_error"] = None
        _atomic_json(path, record)
        try:
            response = dict(transport.append_idempotent(envelope=envelope, payload=payload))
        except Exception as exc:
            record = _read(path)
            record["last_error"] = f"{type(exc).__name__}: {exc}"
            _atomic_json(path, record)
            return record
        if response.get("receipt_id") != receipt_id or response.get("accepted") is not True:
            return self.quarantine(receipt_id, "Book returned invalid Hand acceptance")
        record = _read(path)
        record["state"] = ACKNOWLEDGED
        record["book_receipt"] = response
        acknowledged = self._path(ACKNOWLEDGED, receipt_id)
        _atomic_json(acknowledged, record)
        path.unlink()
        return record

    def quarantine(self, receipt_id: str, reason: str) -> dict[str, Any]:
        path = self._path(PENDING, receipt_id)
        if not path.is_file():
            existing = self._find(receipt_id)
            if existing is None:
                raise KeyError(receipt_id)
            return _read(existing)
        record = _read(path)
        record["state"] = QUARANTINED
        record["last_error"] = reason
        quarantine_path = self._path(QUARANTINED, receipt_id)
        _atomic_json(quarantine_path, record)
        path.unlink()
        return record


class HandBookEvidencePublisher(EvidencePublisher):
    """Persist exact signed HAND.* evidence before any delivery attempt."""

    def __init__(self, signer: HandBookSigner, outbox: HandBookOutbox) -> None:
        self._signer = signer
        self._outbox = outbox

    def publish(self, draft: EvidenceDraft) -> str:
        receipt_id = f"BOOK-{draft.subject_id}"
        envelope = self._signer.sign_draft(receipt_id=receipt_id, draft=draft)
        self._outbox.enqueue(envelope=envelope, payload=draft.payload)
        return receipt_id
