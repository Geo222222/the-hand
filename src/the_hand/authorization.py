from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from .capability import CapitalActionClass, HandCapability
from .verification import BookEvidenceSource, WatchmanKeyRegistry


class EconomicDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"


class AuthorizationIntakeError(RuntimeError):
    pass


class MalformedWatchmanAuthorization(AuthorizationIntakeError):
    pass


class UntrustedWatchmanAuthorization(AuthorizationIntakeError):
    pass


class EconomicAuthorizationNotYetValid(AuthorizationIntakeError):
    pass


class EconomicAuthorizationExpired(AuthorizationIntakeError):
    pass


class AuthorizationLineageMismatch(AuthorizationIntakeError):
    pass


class AuthorizationCapabilityMismatch(AuthorizationIntakeError):
    pass


class AuthorizationAmountMismatch(AuthorizationIntakeError):
    pass


class AuthorizationReplayConflict(AuthorizationIntakeError):
    pass


_REQUIRED_FIELDS = {
    "schema_version",
    "authorization_id",
    "authorization_book_receipt_id",
    "issuer",
    "issuer_key_id",
    "signature_ref",
    "authorization_content_hash",
    "capital_structure_id",
    "benjamin_decision_receipt_id",
    "benjamin_decision_id",
    "benjamin_decision_hash",
    "candidate_economic_path_id",
    "candidate_economic_path_hash",
    "watchman_pre_action_assessment_id",
    "watchman_pre_action_assessment_hash",
    "watchman_capital_envelope_id",
    "watchman_capital_envelope_hash",
    "responsibility_ref",
    "responsibility_version",
    "action_class",
    "economic_root",
    "instrument_intent",
    "economic_path_type",
    "economic_direction",
    "economic_currency",
    "authorized_economic_amount",
    "authorized_minimum",
    "authorized_maximum",
    "maximum_capital_commitment",
    "issued_at",
    "valid_from",
    "expires_at",
    "idempotency_key",
    "permitted_capability_ids",
    "permitted_provider_families",
    "watchman_policy_version",
}

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

_HASH_FIELDS = (
    "benjamin_decision_hash",
    "candidate_economic_path_hash",
    "watchman_pre_action_assessment_hash",
    "watchman_capital_envelope_hash",
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return result


def _positive_decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a decimal") from exc
    if result <= 0 or not result.is_finite():
        raise ValueError(f"{field} must be positive and finite")
    return result


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


def compute_authorization_content_hash(wire: Mapping[str, object]) -> str:
    """Hash the complete authorization content except the self-referential hash field."""

    material = {key: value for key, value in wire.items() if key != "authorization_content_hash"}
    return hashlib.sha256(_canonical_json(material)).hexdigest()


@dataclass(frozen=True)
class WatchmanAuthorizedAction:
    """Economic authority already decided by Benjamin and governed by Watchman.

    This object contains no provider-native order quantity. It is authority in
    economic terms only; The Hand owns any later provider translation.
    """

    schema_version: str
    authorization_id: str
    authorization_book_receipt_id: str
    issuer: str
    issuer_key_id: str
    signature_ref: str
    authorization_content_hash: str
    capital_structure_id: str
    benjamin_decision_receipt_id: str
    benjamin_decision_id: str
    benjamin_decision_hash: str
    candidate_economic_path_id: str
    candidate_economic_path_hash: str
    watchman_pre_action_assessment_id: str
    watchman_pre_action_assessment_hash: str
    watchman_capital_envelope_id: str
    watchman_capital_envelope_hash: str
    responsibility_ref: str
    responsibility_version: str
    action_class: CapitalActionClass
    economic_root: str
    instrument_intent: str
    economic_path_type: str
    economic_direction: EconomicDirection
    economic_currency: str
    authorized_economic_amount: Decimal
    authorized_minimum: Decimal
    authorized_maximum: Decimal
    maximum_capital_commitment: Decimal
    issued_at: datetime
    valid_from: datetime
    expires_at: datetime
    idempotency_key: str
    permitted_capability_ids: tuple[str, ...]
    permitted_provider_families: tuple[str, ...]
    watchman_policy_version: str

    @classmethod
    def from_wire(cls, wire: Mapping[str, object]) -> "WatchmanAuthorizedAction":
        if set(wire) != _REQUIRED_FIELDS:
            missing = sorted(_REQUIRED_FIELDS - set(wire))
            extra = sorted(set(wire) - _REQUIRED_FIELDS)
            raise ValueError(f"authorization fields mismatch; missing={missing}, extra={extra}")
        if wire.get("schema_version") != "1.0":
            raise ValueError("unsupported WatchmanAuthorizedAction schema_version")
        if wire.get("issuer") != "Watchman":
            raise ValueError("issuer must be Watchman")

        string_fields = (
            "authorization_id",
            "authorization_book_receipt_id",
            "issuer_key_id",
            "signature_ref",
            "capital_structure_id",
            "benjamin_decision_receipt_id",
            "benjamin_decision_id",
            "candidate_economic_path_id",
            "watchman_pre_action_assessment_id",
            "watchman_capital_envelope_id",
            "responsibility_ref",
            "responsibility_version",
            "economic_root",
            "instrument_intent",
            "economic_path_type",
            "economic_currency",
            "watchman_policy_version",
        )
        for field in string_fields:
            if not isinstance(wire[field], str) or not str(wire[field]).strip():
                raise ValueError(f"{field} is required")
        for field in _HASH_FIELDS:
            _sha256(wire[field], field)
        content_hash = _sha256(wire["authorization_content_hash"], "authorization_content_hash")
        expected_hash = compute_authorization_content_hash(wire)
        if content_hash != expected_hash:
            raise ValueError("authorization_content_hash does not match authorization content")
        if not isinstance(wire["idempotency_key"], str) or not re.fullmatch(
            r"[a-f0-9]{64}", str(wire["idempotency_key"])
        ):
            raise ValueError("invalid idempotency_key")

        capabilities = wire["permitted_capability_ids"]
        providers = wire["permitted_provider_families"]
        if not isinstance(capabilities, list) or not capabilities or not all(
            isinstance(value, str) and value for value in capabilities
        ):
            raise ValueError("permitted_capability_ids must be a non-empty string list")
        if not isinstance(providers, list) or not providers or not all(
            isinstance(value, str) and value for value in providers
        ):
            raise ValueError("permitted_provider_families must be a non-empty string list")
        if len(set(capabilities)) != len(capabilities) or capabilities != sorted(capabilities):
            raise ValueError("permitted_capability_ids must be unique and sorted")
        if len(set(providers)) != len(providers) or providers != sorted(providers):
            raise ValueError("permitted_provider_families must be unique and sorted")

        issued_at = _timestamp(wire["issued_at"], "issued_at")
        valid_from = _timestamp(wire["valid_from"], "valid_from")
        expires_at = _timestamp(wire["expires_at"], "expires_at")
        if valid_from < issued_at:
            raise ValueError("valid_from cannot precede issued_at")
        if expires_at <= valid_from:
            raise ValueError("expires_at must follow valid_from")

        amount = _positive_decimal(wire["authorized_economic_amount"], "authorized_economic_amount")
        minimum = _positive_decimal(wire["authorized_minimum"], "authorized_minimum")
        maximum = _positive_decimal(wire["authorized_maximum"], "authorized_maximum")
        commitment = _positive_decimal(wire["maximum_capital_commitment"], "maximum_capital_commitment")
        if not minimum <= amount <= maximum:
            raise ValueError("authorized_economic_amount must be inside Watchman bounds")
        if maximum > commitment:
            raise ValueError("authorized maximum exceeds maximum capital commitment")

        return cls(
            schema_version="1.0",
            authorization_id=str(wire["authorization_id"]),
            authorization_book_receipt_id=str(wire["authorization_book_receipt_id"]),
            issuer="Watchman",
            issuer_key_id=str(wire["issuer_key_id"]),
            signature_ref=str(wire["signature_ref"]),
            authorization_content_hash=content_hash,
            capital_structure_id=str(wire["capital_structure_id"]),
            benjamin_decision_receipt_id=str(wire["benjamin_decision_receipt_id"]),
            benjamin_decision_id=str(wire["benjamin_decision_id"]),
            benjamin_decision_hash=str(wire["benjamin_decision_hash"]),
            candidate_economic_path_id=str(wire["candidate_economic_path_id"]),
            candidate_economic_path_hash=str(wire["candidate_economic_path_hash"]),
            watchman_pre_action_assessment_id=str(wire["watchman_pre_action_assessment_id"]),
            watchman_pre_action_assessment_hash=str(wire["watchman_pre_action_assessment_hash"]),
            watchman_capital_envelope_id=str(wire["watchman_capital_envelope_id"]),
            watchman_capital_envelope_hash=str(wire["watchman_capital_envelope_hash"]),
            responsibility_ref=str(wire["responsibility_ref"]),
            responsibility_version=str(wire["responsibility_version"]),
            action_class=CapitalActionClass(str(wire["action_class"])),
            economic_root=str(wire["economic_root"]),
            instrument_intent=str(wire["instrument_intent"]),
            economic_path_type=str(wire["economic_path_type"]),
            economic_direction=EconomicDirection(str(wire["economic_direction"])),
            economic_currency=str(wire["economic_currency"]),
            authorized_economic_amount=amount,
            authorized_minimum=minimum,
            authorized_maximum=maximum,
            maximum_capital_commitment=commitment,
            issued_at=issued_at,
            valid_from=valid_from,
            expires_at=expires_at,
            idempotency_key=str(wire["idempotency_key"]),
            permitted_capability_ids=tuple(capabilities),
            permitted_provider_families=tuple(providers),
            watchman_policy_version=str(wire["watchman_policy_version"]),
        )

    def to_wire(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "authorization_id": self.authorization_id,
            "authorization_book_receipt_id": self.authorization_book_receipt_id,
            "issuer": self.issuer,
            "issuer_key_id": self.issuer_key_id,
            "signature_ref": self.signature_ref,
            "authorization_content_hash": self.authorization_content_hash,
            "capital_structure_id": self.capital_structure_id,
            "benjamin_decision_receipt_id": self.benjamin_decision_receipt_id,
            "benjamin_decision_id": self.benjamin_decision_id,
            "benjamin_decision_hash": self.benjamin_decision_hash,
            "candidate_economic_path_id": self.candidate_economic_path_id,
            "candidate_economic_path_hash": self.candidate_economic_path_hash,
            "watchman_pre_action_assessment_id": self.watchman_pre_action_assessment_id,
            "watchman_pre_action_assessment_hash": self.watchman_pre_action_assessment_hash,
            "watchman_capital_envelope_id": self.watchman_capital_envelope_id,
            "watchman_capital_envelope_hash": self.watchman_capital_envelope_hash,
            "responsibility_ref": self.responsibility_ref,
            "responsibility_version": self.responsibility_version,
            "action_class": self.action_class.value,
            "economic_root": self.economic_root,
            "instrument_intent": self.instrument_intent,
            "economic_path_type": self.economic_path_type,
            "economic_direction": self.economic_direction.value,
            "economic_currency": self.economic_currency,
            "authorized_economic_amount": format(self.authorized_economic_amount, "f"),
            "authorized_minimum": format(self.authorized_minimum, "f"),
            "authorized_maximum": format(self.authorized_maximum, "f"),
            "maximum_capital_commitment": format(self.maximum_capital_commitment, "f"),
            "issued_at": self.issued_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "idempotency_key": self.idempotency_key,
            "permitted_capability_ids": list(self.permitted_capability_ids),
            "permitted_provider_families": list(self.permitted_provider_families),
            "watchman_policy_version": self.watchman_policy_version,
        }


@dataclass(frozen=True)
class AuthorizationExpectation:
    capital_structure_id: str
    candidate_economic_path_id: str
    candidate_economic_path_hash: str
    action_class: CapitalActionClass
    economic_root: str
    instrument_intent: str
    economic_path_type: str
    authorized_economic_amount: Decimal


@dataclass(frozen=True)
class VerifiedWatchmanAuthorizedAction:
    action: WatchmanAuthorizedAction
    correlation_id: str
    sequence: int
    entry_hash: str
    producer_key_id: str


class WatchmanEconomicAuthorizationVerifier:
    """Verify the target economic authorization against committed Watchman evidence."""

    def __init__(self, source: BookEvidenceSource, keys: WatchmanKeyRegistry) -> None:
        self._source = source
        self._keys = keys

    def verify(self, action: WatchmanAuthorizedAction) -> VerifiedWatchmanAuthorizedAction | None:
        try:
            evidence = self._source.get_committed(action.authorization_book_receipt_id)
            if evidence is None or evidence.receipt_id != action.authorization_book_receipt_id:
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
            if envelope.get("producer_key_id") != action.issuer_key_id:
                return None
            if envelope.get("event_type") != "WATCHMAN.AUTHORIZATION":
                return None
            if envelope.get("evidence_class") != "CONSTITUTIONAL":
                return None
            if envelope.get("subject_id") != action.authorization_id:
                return None
            if envelope.get("causation_receipt_id") != action.benjamin_decision_receipt_id:
                return None

            public_key = self._keys.get(action.issuer_key_id)
            if public_key is None:
                return None
            signature = base64.b64decode(str(envelope.get("signature", "")), validate=True)
            signing_body = {key: value for key, value in envelope.items() if key != "signature"}
            public_key.verify(signature, _canonical_json(signing_body))

            if hashlib.sha256(evidence.payload).hexdigest() != str(envelope.get("payload_digest", "")).lower():
                return None
            payload = json.loads(evidence.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                return None
            parsed = WatchmanAuthorizedAction.from_wire(payload)
            if parsed != action:
                return None

            valid_from = _timestamp(envelope.get("valid_from"), "valid_from")
            valid_until = _timestamp(envelope.get("valid_until"), "valid_until")
            occurred_at = _timestamp(envelope.get("occurred_at"), "occurred_at")
            known_at = _timestamp(envelope.get("known_at"), "known_at")
            produced_at = _timestamp(envelope.get("produced_at"), "produced_at")
            if valid_from != action.valid_from or valid_until != action.expires_at:
                return None
            if occurred_at != action.issued_at:
                return None
            if known_at < occurred_at or produced_at < known_at or evidence.recorded_at < produced_at:
                return None
            correlation_id = envelope.get("correlation_id")
            if not isinstance(correlation_id, str) or not correlation_id:
                return None
            return VerifiedWatchmanAuthorizedAction(
                action=action,
                correlation_id=correlation_id,
                sequence=evidence.sequence,
                entry_hash=evidence.entry_hash,
                producer_key_id=action.issuer_key_id,
            )
        except (
            InvalidSignature,
            ValueError,
            TypeError,
            KeyError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return None


class WatchmanAuthorizationIntake:
    """Fail-closed authority intake. It verifies authority but never executes it."""

    def __init__(self, verifier: WatchmanEconomicAuthorizationVerifier) -> None:
        self._verifier = verifier
        self._records: dict[str, tuple[str, VerifiedWatchmanAuthorizedAction]] = {}

    def accept(
        self,
        wire: Mapping[str, object],
        *,
        capability: HandCapability,
        expected: AuthorizationExpectation,
        now: datetime | None = None,
    ) -> VerifiedWatchmanAuthorizedAction:
        try:
            action = WatchmanAuthorizedAction.from_wire(wire)
        except ValueError as exc:
            raise MalformedWatchmanAuthorization(str(exc)) from exc

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise MalformedWatchmanAuthorization("authorization intake clock must be timezone-aware")
        if current_time < action.valid_from:
            raise EconomicAuthorizationNotYetValid("Watchman authorization is not yet valid")
        if current_time >= action.expires_at:
            raise EconomicAuthorizationExpired("Watchman authorization has expired")

        existing = self._records.get(action.idempotency_key)
        if existing is not None:
            existing_hash, proof = existing
            if existing_hash != action.authorization_content_hash:
                raise AuthorizationReplayConflict(
                    "idempotency key reused with materially different Watchman authority"
                )
            return proof

        proof = self._verifier.verify(action)
        if proof is None:
            raise UntrustedWatchmanAuthorization(
                "no exact trusted committed WATCHMAN.AUTHORIZATION evidence matches this action"
            )

        if (
            action.capital_structure_id != expected.capital_structure_id
            or action.candidate_economic_path_id != expected.candidate_economic_path_id
            or action.candidate_economic_path_hash != expected.candidate_economic_path_hash
            or action.action_class is not expected.action_class
            or action.economic_root != expected.economic_root
            or action.instrument_intent != expected.instrument_intent
            or action.economic_path_type != expected.economic_path_type
        ):
            raise AuthorizationLineageMismatch("authorization lineage or economic intent does not match")
        if action.authorized_economic_amount != expected.authorized_economic_amount:
            raise AuthorizationAmountMismatch("economic amount differs from the governed authorization")

        if capability.capability_id not in action.permitted_capability_ids:
            raise AuthorizationCapabilityMismatch("capability is not permitted by Watchman")
        if capability.provider_family not in action.permitted_provider_families:
            raise AuthorizationCapabilityMismatch("provider family is not permitted by Watchman")
        if action.action_class not in capability.supported_action_classes:
            raise AuthorizationCapabilityMismatch("capability does not support the authorized action class")
        if action.economic_path_type not in capability.supported_economic_paths:
            raise AuthorizationCapabilityMismatch("capability does not support the authorized economic path")

        self._records[action.idempotency_key] = (action.authorization_content_hash, proof)
        return proof
