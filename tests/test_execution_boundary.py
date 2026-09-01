from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from the_hand import (
    AuthorizationExpired,
    ContractError,
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
    def verify(self, request: object) -> bool:
        return True


class DenyVerifier:
    def verify(self, request: object) -> bool:
        return False


class CountingAdapter:
    mode = "DRY_RUN"

    def __init__(self) -> None:
        self.calls = 0
        self.last_request = None

    def execute_exact(self, request: object) -> VenueResult:
        self.calls += 1
        self.last_request = request
        return VenueResult(status=ExecutionStatus.DRY_RUN, message="test dry run")


class FakeLiveAdapter(CountingAdapter):
    mode = "LIVE"


def test_untrusted_authorization_is_denied_before_adapter_call() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, DenyVerifier())
    with pytest.raises(UntrustedAuthorization):
        engine.execute(wire(), now=NOW)
    assert adapter.calls == 0


def test_expired_authorization_is_never_executed() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    expired = wire(
        issued_at=(NOW - timedelta(minutes=10)).isoformat(),
        expires_at=(NOW - timedelta(seconds=1)).isoformat(),
    )
    with pytest.raises(AuthorizationExpired):
        engine.execute(expired, now=NOW)
    assert adapter.calls == 0


def test_exact_instruction_reaches_adapter_unchanged() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    receipt = engine.execute(wire(), now=NOW)
    assert adapter.calls == 1
    assert adapter.last_request.instrument == "TEST-ASSET"
    assert adapter.last_request.side.value == "BUY"
    assert adapter.last_request.quantity == Decimal("2.5")
    assert receipt.status is ExecutionStatus.DRY_RUN


def test_duplicate_idempotency_key_returns_same_receipt_without_second_action() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    first = engine.execute(wire(), now=NOW)
    second = engine.execute(wire(), now=NOW + timedelta(seconds=1))
    assert first == second
    assert adapter.calls == 1


def test_idempotency_key_conflict_is_rejected() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    engine.execute(wire(), now=NOW)
    with pytest.raises(IdempotencyConflict):
        engine.execute(wire(quantity="3"), now=NOW)
    assert adapter.calls == 1


def test_contract_rejects_extra_fields_instead_of_inferring_intent() -> None:
    adapter = CountingAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    with pytest.raises(ContractError):
        engine.execute(wire(thesis="buy because momentum"), now=NOW)
    assert adapter.calls == 0


def test_h0_rejects_live_adapter() -> None:
    adapter = FakeLiveAdapter()
    engine = ExecutionEngine(adapter, AllowVerifier())
    with pytest.raises(LiveExecutionDisabled):
        engine.execute(wire(), now=NOW)
    assert adapter.calls == 0
