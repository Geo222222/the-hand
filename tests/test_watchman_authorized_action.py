from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from the_hand import (
    AuthorizationAmountMismatch,
    AuthorizationCapabilityMismatch,
    AuthorizationExpectation,
    AuthorizationLineageMismatch,
    AuthorizationReplayConflict,
    CapitalActionClass,
    CapabilityEnvironment,
    CapabilityKind,
    CapabilityPermissions,
    CapabilityQualification,
    EconomicAuthorizationExpired,
    EconomicAuthorizationNotYetValid,
    HandCapability,
    IdempotencySemantics,
    MalformedWatchmanAuthorization,
    ProviderNativeUnitModel,
    UntrustedWatchmanAuthorization,
    WatchmanAuthorizationIntake,
    WatchmanEconomicAuthorizationVerifier,
    WatchmanKeyRegistry,
    compute_authorization_content_hash,
)
from the_hand.verification import CommittedBookEvidence


NOW = datetime(2026, 9, 3, 20, 0, tzinfo=timezone.utc)
ISSUED = NOW - timedelta(seconds=2)
VALID_FROM = NOW - timedelta(seconds=1)
EXPIRES = NOW + timedelta(minutes=5)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def authorization_wire(**updates: object) -> dict[str, object]:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": "WATCH-AUTH-001",
        "authorization_book_receipt_id": "BOOK-WATCH-AUTH-001",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": "watchman-signature/WATCH-AUTH-001",
        "authorization_content_hash": "0" * 64,
        "capital_structure_id": "CAPSTRUCT-FIRSTFRUITS-001",
        "benjamin_decision_receipt_id": "BOOK-BEN-DEC-001",
        "benjamin_decision_id": "DEC-001",
        "benjamin_decision_hash": digest("decision"),
        "candidate_economic_path_id": "PATH-001",
        "candidate_economic_path_hash": digest("path"),
        "watchman_pre_action_assessment_id": "ASSESS-001",
        "watchman_pre_action_assessment_hash": digest("assessment"),
        "watchman_capital_envelope_id": "ENV-001",
        "watchman_capital_envelope_hash": digest("envelope"),
        "responsibility_ref": "RESP-FIRSTFRUITS",
        "responsibility_version": "1",
        "action_class": "RISK_INCREASING",
        "economic_root": "BTC",
        "instrument_intent": "BTC/USD SPOT EXPOSURE",
        "economic_path_type": "SPOT_EXPOSURE_CHANGE",
        "economic_direction": "INCREASE",
        "economic_currency": "USD",
        "authorized_economic_amount": "10000",
        "authorized_minimum": "9900",
        "authorized_maximum": "10100",
        "maximum_capital_commitment": "10100",
        "issued_at": ISSUED.isoformat(),
        "valid_from": VALID_FROM.isoformat(),
        "expires_at": EXPIRES.isoformat(),
        "idempotency_key": "a" * 64,
        "permitted_capability_ids": ["CAP-SPOT-DRYRUN"],
        "permitted_provider_families": ["COINBASE"],
        "watchman_policy_version": "watchman-economic-v1",
    }
    wire.update(updates)
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return wire


def capability(**updates: object) -> HandCapability:
    values = {
        "schema_version": "1.0",
        "capability_id": "CAP-SPOT-DRYRUN",
        "capability_version": "1",
        "provider_family": "COINBASE",
        "provider_adapter": "synthetic-spot-adapter",
        "provider_adapter_version": "1",
        "environment": CapabilityEnvironment.DRY_RUN,
        "capability_kind": CapabilityKind.ORDER_SUBMIT,
        "supported_action_classes": (CapitalActionClass.RISK_INCREASING,),
        "supported_economic_paths": ("SPOT_EXPOSURE_CHANGE",),
        "supported_instrument_families": ("SPOT",),
        "provider_native_unit_model": ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        "required_permission_scope": ("orders:create",),
        "permissions": CapabilityPermissions(can_trade=True),
        "qualification_status": CapabilityQualification.DECLARED,
        "idempotency_semantics": IdempotencySemantics.HAND_ENFORCED,
        "limits": (),
        "provenance_ref": "synthetic://capability",
        "provenance_version": "1",
        "provenance_hash": digest("capability"),
    }
    values.update(updates)
    return HandCapability(**values)


def expectation(**updates: object) -> AuthorizationExpectation:
    values = {
        "capital_structure_id": "CAPSTRUCT-FIRSTFRUITS-001",
        "candidate_economic_path_id": "PATH-001",
        "candidate_economic_path_hash": digest("path"),
        "action_class": CapitalActionClass.RISK_INCREASING,
        "economic_root": "BTC",
        "instrument_intent": "BTC/USD SPOT EXPOSURE",
        "economic_path_type": "SPOT_EXPOSURE_CHANGE",
        "authorized_economic_amount": Decimal("10000"),
    }
    values.update(updates)
    return AuthorizationExpectation(**values)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def committed(key: Ed25519PrivateKey, wire: dict[str, object], *, tamper_signature: bool = False):
    payload = canonical(wire)
    envelope = {
        "schema_version": "2.0",
        "receipt_id": wire["authorization_book_receipt_id"],
        "producer": "Watchman",
        "producer_key_id": wire["issuer_key_id"],
        "event_type": "WATCHMAN.AUTHORIZATION",
        "evidence_class": "CONSTITUTIONAL",
        "subject_id": wire["authorization_id"],
        "occurred_at": wire["issued_at"],
        "payload_digest": hashlib.sha256(payload).hexdigest(),
        "payload_ref": "vault://watchman/authorizations/WATCH-AUTH-001",
        "correlation_id": "LIFE-001",
        "causation_receipt_id": wire["benjamin_decision_receipt_id"],
        "privacy_class": "CONFIDENTIAL_EVIDENCE",
        "visibility_scope": ["WATCHMAN_AUTHORITY", "HAND_VERIFIER"],
        "evidence_receipt_ids": [wire["benjamin_decision_receipt_id"]],
        "source_event_at": wire["issued_at"],
        "known_at": wire["issued_at"],
        "produced_at": wire["issued_at"],
        "valid_from": wire["valid_from"],
        "valid_until": wire["expires_at"],
    }
    signature = key.sign(canonical(envelope))
    if tamper_signature:
        signature = b"x" * 64
    signed = {**envelope, "signature": base64.b64encode(signature).decode("ascii")}
    return CommittedBookEvidence(
        receipt_id=str(wire["authorization_book_receipt_id"]),
        sequence=7,
        entry_hash=digest("book-entry"),
        recorded_at=ISSUED + timedelta(milliseconds=1),
        envelope=signed,
        payload=payload,
    )


class Source:
    def __init__(self, evidence: CommittedBookEvidence | None) -> None:
        self.evidence = evidence

    def get_committed(self, receipt_id: str):
        if self.evidence is None or self.evidence.receipt_id != receipt_id:
            return None
        return self.evidence


def intake(wire: dict[str, object], *, evidence: CommittedBookEvidence | None = None):
    key = Ed25519PrivateKey.generate()
    if evidence is None:
        evidence = committed(key, wire)
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    keys = WatchmanKeyRegistry()
    keys.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    return WatchmanAuthorizationIntake(WatchmanEconomicAuthorizationVerifier(Source(evidence), keys)), key


def subject(wire: dict[str, object] | None = None):
    wire = authorization_wire() if wire is None else wire
    key = Ed25519PrivateKey.generate()
    evidence = committed(key, wire)
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    keys = WatchmanKeyRegistry()
    keys.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    return WatchmanAuthorizationIntake(WatchmanEconomicAuthorizationVerifier(Source(evidence), keys))


def test_exact_committed_watchman_economic_authorization_is_accepted() -> None:
    wire = authorization_wire()
    proof = subject(wire).accept(wire, capability=capability(), expected=expectation(), now=NOW)
    assert proof.action.authorization_id == "WATCH-AUTH-001"
    assert proof.action.authorized_economic_amount == Decimal("10000")
    assert proof.action.permitted_capability_ids == ("CAP-SPOT-DRYRUN",)


def test_authorized_boolean_cannot_replace_watchman_authority() -> None:
    wire = authorization_wire()
    wire["authorized"] = True
    with pytest.raises(MalformedWatchmanAuthorization):
        subject(authorization_wire()).accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_provider_native_quantity_cannot_be_supplied_as_economic_intent() -> None:
    wire = authorization_wire()
    wire["quantity"] = "0.15"
    with pytest.raises(MalformedWatchmanAuthorization):
        subject(authorization_wire()).accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_expired_authorization_is_rejected() -> None:
    wire = authorization_wire(
        issued_at=(NOW - timedelta(minutes=10)).isoformat(),
        valid_from=(NOW - timedelta(minutes=9)).isoformat(),
        expires_at=(NOW - timedelta(seconds=1)).isoformat(),
    )
    with pytest.raises(EconomicAuthorizationExpired):
        subject(wire).accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_future_authorization_is_rejected() -> None:
    wire = authorization_wire(
        issued_at=NOW.isoformat(),
        valid_from=(NOW + timedelta(seconds=1)).isoformat(),
        expires_at=(NOW + timedelta(minutes=5)).isoformat(),
    )
    with pytest.raises(EconomicAuthorizationNotYetValid):
        subject(wire).accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_amount_outside_watchman_bounds_is_malformed() -> None:
    wire = authorization_wire(authorized_economic_amount="10200")
    with pytest.raises(MalformedWatchmanAuthorization, match="inside Watchman bounds"):
        subject(authorization_wire()).accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_expected_amount_cannot_differ_from_authorized_amount() -> None:
    wire = authorization_wire()
    with pytest.raises(AuthorizationAmountMismatch):
        subject(wire).accept(
            wire,
            capability=capability(),
            expected=expectation(authorized_economic_amount=Decimal("9999")),
            now=NOW,
        )


def test_capital_structure_and_candidate_path_mismatches_fail_closed() -> None:
    wire = authorization_wire()
    with pytest.raises(AuthorizationLineageMismatch):
        subject(wire).accept(
            wire,
            capability=capability(),
            expected=expectation(capital_structure_id="CAPSTRUCT-OTHER"),
            now=NOW,
        )
    with pytest.raises(AuthorizationLineageMismatch):
        subject(wire).accept(
            wire,
            capability=capability(),
            expected=expectation(candidate_economic_path_hash=digest("other-path")),
            now=NOW,
        )


def test_action_class_mismatch_fails_closed() -> None:
    wire = authorization_wire()
    with pytest.raises(AuthorizationLineageMismatch):
        subject(wire).accept(
            wire,
            capability=capability(),
            expected=expectation(action_class=CapitalActionClass.RISK_REDUCING),
            now=NOW,
        )


def test_provider_and_capability_selection_must_be_watchman_permitted() -> None:
    wire = authorization_wire()
    with pytest.raises(AuthorizationCapabilityMismatch):
        subject(wire).accept(
            wire,
            capability=capability(capability_id="CAP-OTHER"),
            expected=expectation(),
            now=NOW,
        )
    with pytest.raises(AuthorizationCapabilityMismatch):
        subject(wire).accept(
            wire,
            capability=capability(provider_family="KRAKEN"),
            expected=expectation(),
            now=NOW,
        )


def test_unsupported_capital_action_class_is_rejected() -> None:
    wire = authorization_wire()
    with pytest.raises(AuthorizationCapabilityMismatch):
        subject(wire).accept(
            wire,
            capability=capability(supported_action_classes=(CapitalActionClass.RISK_REDUCING,)),
            expected=expectation(),
            now=NOW,
        )


def test_missing_watchman_authorization_fails_closed() -> None:
    wire = authorization_wire()
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    keys = WatchmanKeyRegistry()
    keys.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    subject_without_evidence = WatchmanAuthorizationIntake(
        WatchmanEconomicAuthorizationVerifier(Source(None), keys)
    )
    with pytest.raises(UntrustedWatchmanAuthorization):
        subject_without_evidence.accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_tampered_watchman_signature_fails_closed() -> None:
    wire = authorization_wire()
    key = Ed25519PrivateKey.generate()
    evidence = committed(key, wire, tamper_signature=True)
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    keys = WatchmanKeyRegistry()
    keys.register(key_id="watchman-k1", public_key_b64=base64.b64encode(public).decode("ascii"))
    tampered = WatchmanAuthorizationIntake(WatchmanEconomicAuthorizationVerifier(Source(evidence), keys))
    with pytest.raises(UntrustedWatchmanAuthorization):
        tampered.accept(wire, capability=capability(), expected=expectation(), now=NOW)


def test_exact_idempotent_authority_replay_returns_same_proof() -> None:
    wire = authorization_wire()
    handler = subject(wire)
    first = handler.accept(wire, capability=capability(), expected=expectation(), now=NOW)
    second = handler.accept(wire, capability=capability(), expected=expectation(), now=NOW)
    assert first is second


def test_same_idempotency_key_with_different_authority_is_rejected() -> None:
    wire = authorization_wire()
    handler = subject(wire)
    handler.accept(wire, capability=capability(), expected=expectation(), now=NOW)
    changed = authorization_wire(authorized_economic_amount="9999")
    with pytest.raises(AuthorizationReplayConflict):
        handler.accept(
            changed,
            capability=capability(),
            expected=expectation(authorized_economic_amount=Decimal("9999")),
            now=NOW,
        )
