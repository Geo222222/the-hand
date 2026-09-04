from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from the_hand import (
    AssetClass,
    CapitalActionClass,
    CapabilityEnvironment,
    CapabilityKind,
    CapabilityPermissions,
    CapabilityQualification,
    ContractType,
    ContractValueConvention,
    EconomicDirection,
    HandCapability,
    IdempotencySemantics,
    InstrumentFamily,
    PlanStatus,
    ProviderExecutionPlanner,
    ProviderInstrumentMetadata,
    ProviderNativeUnitModel,
    QuantizationRule,
    ReferencePrice,
    TranslationPolicy,
    WatchmanAuthorizedAction,
    compute_authorization_content_hash,
)


NOW = datetime(2026, 9, 3, 20, 0, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def authorization(**updates: object) -> WatchmanAuthorizedAction:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": "WATCH-AUTH-SAFE-001",
        "authorization_book_receipt_id": "BOOK-WATCH-SAFE-001",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": "watchman-signature/WATCH-AUTH-SAFE-001",
        "authorization_content_hash": "0" * 64,
        "capital_structure_id": "CAPSTRUCT-001",
        "benjamin_decision_receipt_id": "BOOK-BEN-001",
        "benjamin_decision_id": "DEC-001",
        "benjamin_decision_hash": digest("decision"),
        "candidate_economic_path_id": "PATH-001",
        "candidate_economic_path_hash": digest("path"),
        "watchman_pre_action_assessment_id": "ASSESS-001",
        "watchman_pre_action_assessment_hash": digest("assessment"),
        "watchman_capital_envelope_id": "ENV-001",
        "watchman_capital_envelope_hash": digest("envelope"),
        "responsibility_ref": "RESP-001",
        "responsibility_version": "1",
        "action_class": "RISK_INCREASING",
        "economic_root": "BTC",
        "instrument_intent": "BTC/USD SPOT EXPOSURE",
        "economic_path_type": "SPOT_EXPOSURE_CHANGE",
        "economic_direction": EconomicDirection.INCREASE.value,
        "economic_currency": "USD",
        "authorized_economic_amount": "10000",
        "authorized_minimum": "9900",
        "authorized_maximum": "10100",
        "maximum_capital_commitment": "10100",
        "issued_at": (NOW - timedelta(seconds=2)).isoformat(),
        "valid_from": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "idempotency_key": "c" * 64,
        "permitted_capability_ids": ["CAP-SPOT"],
        "permitted_provider_families": ["SYNTHETIC"],
        "watchman_policy_version": "watchman-economic-v1",
    }
    wire.update(updates)
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return WatchmanAuthorizedAction.from_wire(wire)


def capability() -> HandCapability:
    return HandCapability(
        schema_version="1.0",
        capability_id="CAP-SPOT",
        capability_version="1",
        provider_family="SYNTHETIC",
        provider_adapter="synthetic-spot",
        provider_adapter_version="1",
        environment=CapabilityEnvironment.DRY_RUN,
        capability_kind=CapabilityKind.ORDER_SUBMIT,
        supported_action_classes=(CapitalActionClass.RISK_INCREASING,),
        supported_economic_paths=("SPOT_EXPOSURE_CHANGE",),
        supported_instrument_families=("SPOT",),
        provider_native_unit_model=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        required_permission_scope=("orders:create",),
        permissions=CapabilityPermissions(can_trade=True),
        qualification_status=CapabilityQualification.SYNTHETIC_QUALIFIED,
        idempotency_semantics=IdempotencySemantics.HAND_ENFORCED,
        limits=(),
        provenance_ref="synthetic://capability",
        provenance_version="1",
        provenance_hash=digest("capability"),
    )


def metadata(*, step: str = "0.00007", valid_until: datetime | None = None) -> ProviderInstrumentMetadata:
    return ProviderInstrumentMetadata(
        schema_version="1.0",
        provider_family="SYNTHETIC",
        provider_instrument_id="BTC-USD",
        canonical_economic_root="BTC",
        asset_class=AssetClass.CRYPTO,
        instrument_family=InstrumentFamily.SPOT,
        base_asset="BTC",
        quote_asset="USD",
        settlement_asset="USD",
        native_quantity_unit=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        native_unit_label="BTC",
        contract_type=ContractType.NOT_APPLICABLE,
        contract_multiplier=None,
        contract_value_convention=ContractValueConvention.NOT_APPLICABLE,
        price_unit="USD_PER_BTC",
        tick_size=Decimal("0.01"),
        quantity_step=Decimal(step),
        minimum_quantity=Decimal(step),
        minimum_notional=Decimal("1"),
        quantity_precision=8,
        price_precision=2,
        lot_rule="STEP_SIZE",
        margin_denomination=None,
        metadata_version="1",
        source_ref="synthetic://BTC-USD",
        provenance_hash=digest("metadata"),
        known_at=NOW - timedelta(seconds=1),
        effective_at=NOW - timedelta(seconds=1),
        valid_until=valid_until or NOW + timedelta(minutes=10),
    )


def price() -> ReferencePrice:
    return ReferencePrice(
        value=Decimal("50000"),
        unit="USD_PER_BTC",
        source_ref="synthetic://price/BTC-USD",
        known_at=NOW - timedelta(milliseconds=100),
        valid_until=NOW + timedelta(seconds=30),
    )


def policy(
    *,
    rule: QuantizationRule = QuantizationRule.DOWN,
    abs_error: str = "1",
    rel_error: str = "0.001",
    allow_lower: bool = True,
    allow_upward: bool = False,
    version: str = "1",
) -> TranslationPolicy:
    return TranslationPolicy(
        policy_id="HAND.SYNTHETIC_TOLERANCE",
        version=version,
        quantization_rule=rule,
        max_absolute_error=Decimal(abs_error),
        max_relative_error=Decimal(rel_error),
        allow_lower_quantity=allow_lower,
        allow_upward_translation=allow_upward,
    )


def test_downward_quantization_is_allowed_only_by_explicit_policy() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(), capability(), metadata(), reference_price=price(), policy=policy(), now=NOW
    )
    assert result.status is PlanStatus.TRANSLATABLE
    assert result.plan is not None
    assert result.plan.native_quantity == Decimal("0.19999")
    assert result.plan.translated_economic_notional == Decimal("9999.50000")
    assert result.plan.translation_error == Decimal("-0.50000")
    assert result.plan.translation_policy_id == "HAND.SYNTHETIC_TOLERANCE"


def test_quantization_error_outside_explicit_policy_fails_closed() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(),
        capability(),
        metadata(),
        reference_price=price(),
        policy=policy(abs_error="0.1"),
        now=NOW,
    )
    assert result.status is PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE
    assert result.plan is None
    assert "absolute=" in str(result.reason)


def test_policy_cannot_round_up_when_upward_translation_is_forbidden() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(),
        capability(),
        metadata(step="0.007"),
        reference_price=price(),
        policy=policy(rule=QuantizationRule.NEAREST, abs_error="200", rel_error="0.02", allow_lower=False),
        now=NOW,
    )
    assert result.status is PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE
    assert result.plan is None


def test_upward_quantization_can_never_exceed_watchman_maximum() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(),
        capability(),
        metadata(step="0.007"),
        reference_price=price(),
        policy=policy(
            rule=QuantizationRule.NEAREST,
            abs_error="200",
            rel_error="0.02",
            allow_lower=False,
            allow_upward=True,
        ),
        now=NOW,
    )
    assert result.status is PlanStatus.NATIVE_MINIMUM_EXCEEDS_AUTHORITY
    assert result.plan is None


def test_lower_translation_must_remain_inside_watchman_authorized_range() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(authorized_minimum="9999.9"),
        capability(),
        metadata(),
        reference_price=price(),
        policy=policy(abs_error="1", rel_error="0.001"),
        now=NOW,
    )
    assert result.status is PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE
    assert result.plan is None


def test_translation_policy_is_part_of_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan(
        authorization(), capability(), metadata(), reference_price=price(), policy=policy(version="1"), now=NOW
    )
    second = planner.plan(
        authorization(), capability(), metadata(), reference_price=price(), policy=policy(version="2"), now=NOW
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.translation_policy_hash != second.plan.translation_policy_hash
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_expired_authorization_and_stale_metadata_never_translate() -> None:
    expired = authorization(
        issued_at=(NOW - timedelta(minutes=10)).isoformat(),
        valid_from=(NOW - timedelta(minutes=9)).isoformat(),
        expires_at=(NOW - timedelta(seconds=1)).isoformat(),
    )
    assert ProviderExecutionPlanner().plan(
        expired, capability(), metadata(), reference_price=price(), policy=policy(), now=NOW
    ).status is PlanStatus.AUTHORIZATION_EXPIRED

    stale_metadata = metadata(valid_until=NOW)
    assert ProviderExecutionPlanner().plan(
        authorization(), capability(), stale_metadata, reference_price=price(), policy=policy(), now=NOW
    ).status is PlanStatus.UNIT_METADATA_UNAVAILABLE


def test_native_quantity_always_satisfies_declared_step() -> None:
    result = ProviderExecutionPlanner().plan(
        authorization(), capability(), metadata(), reference_price=price(), policy=policy(), now=NOW
    )
    assert result.plan is not None
    assert result.plan.native_quantity >= 0
    assert result.plan.native_quantity % metadata().quantity_step == 0
    assert result.plan.action_class == CapitalActionClass.RISK_INCREASING.value
    assert result.plan.action == EconomicDirection.INCREASE.value
