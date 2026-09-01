from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from the_hand import (
    AuthorizationExpired,
    AuthorizationProof,
    ContractError,
    EvidencePublicationError,
    ExecutionEngine,
    ExecutionStatus,
    IdempotencyConflict,
    LiveExecutionDisabled,
    UntrustedAuthorization,
    VenueResult,
)


NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def wire(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
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
    value.update(updates)
    return value


class AllowVerifier:
    def verify(self, request):
        return AuthorizationProof(book_receipt_id="BOOK-AUTH-001", correlation_id="LIFE-001")


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


def test_untrusted_authorization_is_denied_before_adapter_call() -> None:
    adapter = CountingAdapter()
    with pytest.raises(UntrustedAuthorization):
        engine(adapter=adapter, verifier=DenyVerifier()).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_expired_authorization_is_never_executed() -> None:
    adapter = CountingAdapter()
    with pytest.raises(AuthorizationExpired):
        engine(adapter=adapter).execute(
            wire(
                issued_at=(NOW - timedelta(minutes=2)).isoformat(),
                expires_at=(NOW - timedelta(seconds=1)).isoformat(),
            ),
            now=NOW,
        )
    assert adapter.calls == 0


def test_exact_instruction_reaches_adapter_and_execution_is_recorded_in_book() -> None:
    adapter = CountingAdapter()
    publisher = RecordingPublisher()
    record = engine(adapter=adapter, publisher=publisher).execute(wire(), now=NOW)

    assert adapter.calls == 1
    assert adapter.last_request.instrument == "TEST-ASSET"
    assert adapter.last_request.side.value == "BUY"
    assert adapter.last_request.quantity == Decimal("2.5")
    assert record.receipt.status is ExecutionStatus.DRY_RUN
    assert record.book_receipt_id == "BOOK-HAND-001"
    assert publisher.drafts[0].event_type == "HAND.EXECUTION"
    assert publisher.drafts[0].causation_receipt_id == "BOOK-AUTH-001"
    assert publisher.drafts[0].correlation_id == "LIFE-001"


def test_duplicate_idempotency_key_returns_same_record_without_second_action_or_receipt() -> None:
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


def test_h1_rejects_live_adapter() -> None:
    adapter = FakeLiveAdapter()
    with pytest.raises(LiveExecutionDisabled):
        engine(adapter=adapter).execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_book_publication_failure_is_explicit_and_record_is_not_cached() -> None:
    adapter = CountingAdapter()
    subject = engine(adapter=adapter, publisher=FailingPublisher())
    with pytest.raises(EvidencePublicationError):
        subject.execute(wire(), now=NOW)
    assert adapter.calls == 1
