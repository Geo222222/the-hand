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
    ReferencePrice,
    WatchmanAuthorizedAction,
    compute_authorization_content_hash,
)


NOW = datetime(2026, 9, 3, 20, 0, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def authorization() -> WatchmanAuthorizedAction:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": "WATCH-AUTH-PLAN-001",
        "authorization_book_receipt_id": "BOOK-WATCH-PLAN-001",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": "watchman-signature/WATCH-AUTH-PLAN-001",
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
        "idempotency_key": "a" * 64,
        "permitted_capability_ids": ["CAP-SPOT"],
        "permitted_provider_families": ["SYNTHETIC"],
        "watchman_policy_version": "watchman-economic-v1",
    }
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return WatchmanAuthorizedAction.from_wire(wire)


def capability(**updates: object) -> HandCapability:
    values = {
        "schema_version": "1.0",
        "capability_id": "CAP-SPOT",
        "capability_version": "1",
        "provider_family": "SYNTHETIC",
        "provider_adapter": "synthetic-spot",
        "provider_adapter_version": "1",
        "environment": CapabilityEnvironment.DRY_RUN,
        "capability_kind": CapabilityKind.ORDER_SUBMIT,
        "supported_action_classes": (CapitalActionClass.RISK_INCREASING,),
        "supported_economic_paths": ("SPOT_EXPOSURE_CHANGE",),
        "supported_instrument_families": ("SPOT",),
        "provider_native_unit_model": ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        "required_permission_scope": ("orders:create",),
        "permissions": CapabilityPermissions(can_trade=True),
        "qualification_status": CapabilityQualification.SYNTHETIC_QUALIFIED,
        "idempotency_semantics": IdempotencySemantics.HAND_ENFORCED,
        "limits": (),
        "provenance_ref": "synthetic://capability",
        "provenance_version": "1",
        "provenance_hash": digest("capability"),
    }
    values.update(updates)
    return HandCapability(**values)


def metadata(**updates: object) -> ProviderInstrumentMetadata:
    values = {
        "schema_version": "1.0",
        "provider_family": "SYNTHETIC",
        "provider_instrument_id": "BTC-USD",
        "canonical_economic_root": "BTC",
        "asset_class": AssetClass.CRYPTO,
        "instrument_family": InstrumentFamily.SPOT,
        "base_asset": "BTC",
        "quote_asset": "USD",
        "settlement_asset": "USD",
        "native_quantity_unit": ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        "native_unit_label": "BTC",
        "contract_type": ContractType.NOT_APPLICABLE,
        "contract_multiplier": None,
        "contract_value_convention": ContractValueConvention.NOT_APPLICABLE,
        "price_unit": "USD_PER_BTC",
        "tick_size": Decimal("0.01"),
        "quantity_step": Decimal("0.0001"),
        "minimum_quantity": Decimal("0.0001"),
        "minimum_notional": Decimal("1"),
        "quantity_precision": 4,
        "price_precision": 2,
        "lot_rule": "STEP_SIZE",
        "margin_denomination": None,
        "metadata_version": "1",
        "source_ref": "synthetic://BTC-USD",
        "provenance_hash": digest("metadata"),
        "known_at": NOW - timedelta(seconds=1),
        "effective_at": NOW - timedelta(seconds=1),
        "valid_until": NOW + timedelta(minutes=10),
    }
    values.update(updates)
    return ProviderInstrumentMetadata(**values)


def price(value: str = "50000", **updates: object) -> ReferencePrice:
    values = {
        "value": Decimal(value),
        "unit": "USD_PER_BTC",
        "source_ref": "synthetic://price/BTC-USD",
        "known_at": NOW - timedelta(milliseconds=100),
        "valid_until": NOW + timedelta(seconds=30),
    }
    values.update(updates)
    return ReferencePrice(**values)


def test_exact_spot_translation_produces_content_addressed_plan() -> None:
    result = ProviderExecutionPlanner().plan_exact(
        authorization(), capability(), metadata(), reference_price=price(), now=NOW
    )
    assert result.status is PlanStatus.TRANSLATABLE
    assert result.plan is not None
    assert result.plan.native_quantity == Decimal("0.2")
    assert result.plan.translated_economic_notional == Decimal("10000.0")
    assert result.plan.translation_error == Decimal("0.0")
    assert result.plan.plan_content_hash == result.plan.compute_content_hash()


def test_same_inputs_produce_same_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(authorization(), capability(), metadata(), reference_price=price(), now=NOW)
    second = planner.plan_exact(authorization(), capability(), metadata(), reference_price=price(), now=NOW)
    assert first.plan is not None and second.plan is not None
    assert first.plan.plan_content_hash == second.plan.plan_content_hash


def test_reference_price_change_changes_native_plan_and_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(authorization(), capability(), metadata(), reference_price=price("50000"), now=NOW)
    second = planner.plan_exact(authorization(), capability(), metadata(), reference_price=price("40000"), now=NOW)
    assert first.plan is not None and second.plan is not None
    assert first.plan.native_quantity == Decimal("0.2")
    assert second.plan.native_quantity == Decimal("0.25")
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_metadata_or_capability_version_change_changes_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(authorization(), capability(), metadata(), reference_price=price(), now=NOW)
    changed_metadata = planner.plan_exact(
        authorization(), capability(), metadata(metadata_version="2"), reference_price=price(), now=NOW
    )
    changed_capability = planner.plan_exact(
        authorization(), capability(capability_version="2"), metadata(), reference_price=price(), now=NOW
    )
    assert first.plan and changed_metadata.plan and changed_capability.plan
    assert first.plan.plan_content_hash != changed_metadata.plan.plan_content_hash
    assert first.plan.plan_content_hash != changed_capability.plan.plan_content_hash


def test_declared_but_unqualified_capability_cannot_produce_plan() -> None:
    result = ProviderExecutionPlanner().plan_exact(
        authorization(),
        capability(qualification_status=CapabilityQualification.DECLARED),
        metadata(),
        reference_price=price(),
        now=NOW,
    )
    assert result.status is PlanStatus.CAPABILITY_NOT_QUALIFIED
    assert result.plan is None


def test_stale_reference_price_cannot_produce_plan() -> None:
    result = ProviderExecutionPlanner().plan_exact(
        authorization(),
        capability(),
        metadata(),
        reference_price=price(valid_until=NOW),
        now=NOW,
    )
    assert result.status is PlanStatus.REFERENCE_PRICE_STALE
    assert result.plan is None


def test_non_step_aligned_translation_requires_explicit_quantization_policy() -> None:
    result = ProviderExecutionPlanner().plan_exact(
        authorization(),
        capability(),
        metadata(quantity_step=Decimal("0.03")),
        reference_price=price(),
        now=NOW,
    )
    assert result.status is PlanStatus.EXACT_QUANTIZATION_REQUIRED
    assert result.plan is None
