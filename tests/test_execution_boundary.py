from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from the_hand import (
    AuthorizationExpired,
    AuthorizationNotYetValid,
    AuthorizationProof,
    ContractError,
    EvidencePublicationError,
    ExecutionEngine,
    ExecutionStatus,
    IdempotencyConflict,
    LiveExecutionDisabled,
    OrderSide,
    UntrustedAuthorization,
    VenueResult,
)


NOW = datetime(2026, 9, 2, 19, 0, tzinfo=timezone.utc)


def wire(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "2.0",
        "authorization_book_receipt_id": "BOOK-WATCH-001",
        "capability": "ORDER_EXECUTION",
        "idempotency_key": "a" * 64,
        "instrument": "TEST-ASSET",
        "side": "BUY",
        "quantity": "2.5",
        "decision_id": "DEC-001",
        "governance_id": "RSK-001",
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
    }
    value.update(updates)
    return value


def proof(**updates: object) -> AuthorizationProof:
    values = {
        "book_receipt_id": "BOOK-WATCH-001",
        "correlation_id": "LIFE-001",
        "governance_id": "RSK-001",
        "decision_receipt_id": "BOOK-BEN-001",
        "decision_id": "DEC-001",
        "capability": "ORDER_EXECUTION",
        "instrument": "TEST-ASSET",
        "side": OrderSide.BUY,
        "quantity": Decimal("2.5"),
        "idempotency_key": "a" * 64,
        "evaluated_at": NOW - timedelta(seconds=1),
        "valid_until": NOW + timedelta(minutes=5),
        "sequence": 2,
        "entry_hash": "b" * 64,
        "producer_key_id": "watchman-k1",
    }
    values.update(updates)
    return AuthorizationProof(**values)


class AllowVerifier:
    def __init__(self, authorization: AuthorizationProof | None = None) -> None:
        self.authorization = authorization or proof()

    def verify(self, request):
        return self.authorization


class DenyVerifier:
    def verify(self, request):
        return None


class RecordingPublisher:
    def __init__(self) -> None:
        self.drafts = []

    def publish(self, draft):
        self.drafts.append(draft)
        return f"BOOK-HAND-{len(self.drafts):03d}"


class FailingPublisher:
    def publish(self, draft):
        raise RuntimeError("book unavailable")


class CountingAdapter:
    mode = "DRY_RUN"

    def __init__(self) -> None:
        self.calls = 0
        self.last_request = None

    def execute_exact(self, request) -> VenueResult:
        self.calls += 1
        self.last_request = request
        return VenueResult(status=ExecutionStatus.DRY_RUN, message="test dry run")


class FakeLiveAdapter(CountingAdapter):
    mode = "LIVE"


def engine(adapter=None, verifier=None, publisher=None):
    return ExecutionEngine(
        adapter or CountingAdapter(),
        verifier or AllowVerifier(),
        publisher or RecordingPublisher(),
    )


def test_legacy_benjamin_authorization_wire_is_rejected_before_adapter_call() -> None:
    adapter = CountingAdapter()
    legacy = {
        "schema_version": "1.0",
        "authorization_id": "AUTH-001",
        "idempotency_key": "a" * 64,
        "fund_id": "FIRSTFRUITS",
        "instrument": "TEST-ASSET",
        "side": "BUY",
        "quantity": "2.5",
        "decision_id": "DEC-001",
        "risk_id": "RSK-001",
        "issued_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
    }
    with pytest.raises(ContractError):
        engine(adapter=adapter).execute(legacy, now=NOW)
    assert adapter.calls == 0


def test_untrusted_watchman_authorization_is_denied_before_adapter_call() -> None:
    adapter = CountingAdapter()
    with pytest.raises(UntrustedAuthorization):
        engine(adapter=adapter, verifier=DenyVerifier()).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_mismatched_watchman_constraints_are_denied_before_adapter_call() -> None:
    adapter = CountingAdapter()
    with pytest.raises(UntrustedAuthorization):
        engine(
            adapter=adapter,
            verifier=AllowVerifier(proof(quantity=Decimal("3"))),
        ).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_execution_before_watchman_evaluation_is_denied() -> None:
    adapter = CountingAdapter()
    future_evaluation = NOW + timedelta(seconds=1)
    auth = proof(evaluated_at=future_evaluation)
    with pytest.raises(AuthorizationNotYetValid):
        engine(adapter=adapter, verifier=AllowVerifier(auth)).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_expired_watchman_authorization_is_never_executed() -> None:
    adapter = CountingAdapter()
    expiry = NOW - timedelta(seconds=1)
    auth = proof(valid_until=expiry)
    with pytest.raises(AuthorizationExpired):
        engine(adapter=adapter, verifier=AllowVerifier(auth)).execute(
            wire(expires_at=expiry.isoformat()),
            now=NOW,
        )
    assert adapter.calls == 0


def test_exact_watchman_instruction_reaches_adapter_and_hand_proof_is_recorded() -> None:
    adapter = CountingAdapter()
    publisher = RecordingPublisher()
    record = engine(adapter=adapter, publisher=publisher).execute(wire(), now=NOW)

    assert adapter.calls == 1
    assert adapter.last_request.instrument == "TEST-ASSET"
    assert adapter.last_request.side is OrderSide.BUY
    assert adapter.last_request.quantity == Decimal("2.5")
    assert record.receipt.status is ExecutionStatus.DRY_RUN
    assert record.receipt.authorization_book_receipt_id == "BOOK-WATCH-001"
    assert record.receipt.instrument == "TEST-ASSET"
    assert record.receipt.side is OrderSide.BUY
    assert record.receipt.requested_quantity == Decimal("2.5")
    assert record.evidence_receipt_id == "BOOK-HAND-001"

    draft = publisher.drafts[0]
    assert draft.event_type == "HAND.EXECUTION"
    assert draft.privacy_class == "CONFIDENTIAL_EVIDENCE"
    assert draft.visibility_scope == (
        "HAND_EXECUTION",
        "BENJAMIN_RECONCILIATION",
        "BENJAMIN_AUDITOR",
    )
    assert "PUBLIC" not in draft.visibility_scope
    assert draft.causation_receipt_id == "BOOK-WATCH-001"
    assert draft.evidence_receipt_ids == ("BOOK-BEN-001",)
    assert draft.correlation_id == "LIFE-001"
    assert draft.occurred_at == NOW
    assert draft.known_at == NOW
    assert draft.produced_at == NOW


def test_duplicate_idempotency_key_returns_same_record_without_second_action_or_proof() -> None:
    adapter = CountingAdapter()
    publisher = RecordingPublisher()
    subject = engine(adapter=adapter, publisher=publisher)
    first = subject.execute(wire(), now=NOW)
    second = subject.execute(wire(), now=NOW + timedelta(seconds=1))
    assert first == second
    assert adapter.calls == 1
    assert len(publisher.drafts) == 1


def test_idempotency_key_conflict_is_rejected() -> None:
    adapter = CountingAdapter()
    subject = engine(adapter=adapter)
    subject.execute(wire(), now=NOW)
    with pytest.raises(IdempotencyConflict):
        subject.execute(wire(quantity="3"), now=NOW)
    assert adapter.calls == 1


def test_contract_rejects_extra_fields_instead_of_inferring_intent() -> None:
    adapter = CountingAdapter()
    with pytest.raises(ContractError):
        engine(adapter=adapter).execute(wire(thesis="buy because momentum"), now=NOW)
    assert adapter.calls == 0


def test_h2_rejects_live_adapter_even_with_valid_watchman_authority() -> None:
    adapter = FakeLiveAdapter()
    with pytest.raises(LiveExecutionDisabled):
        engine(adapter=adapter).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_hand_evidence_persistence_failure_is_explicit_and_record_is_not_cached() -> None:
    adapter = CountingAdapter()
    subject = engine(adapter=adapter, publisher=FailingPublisher())
    with pytest.raises(EvidencePublicationError):
        subject.execute(wire(), now=NOW)
    assert adapter.calls == 1
