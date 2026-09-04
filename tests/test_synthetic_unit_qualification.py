from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

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
    InstrumentQualification,
    InstrumentQualificationRegistry,
    PlanStatus,
    ProviderInstrumentMetadata,
    ProviderNativeUnitModel,
    QualificationScope,
    QualifiedProviderExecutionPlanner,
    ReferencePrice,
    TranslationPolicy,
    WatchmanAuthorizedAction,
    compute_authorization_content_hash,
)


NOW = datetime(2026, 9, 3, 20, 30, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def authorization(
    *,
    capability_id: str,
    path: str,
    amount: str = "10000",
    minimum: str = "9900",
    maximum: str = "10100",
    idempotency_key: str = "d" * 64,
) -> WatchmanAuthorizedAction:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": f"WATCH-{capability_id}",
        "authorization_book_receipt_id": f"BOOK-WATCH-{capability_id}",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": f"watchman-signature/{capability_id}",
        "authorization_content_hash": "0" * 64,
        "capital_structure_id": "CAPSTRUCT-SYNTHETIC-001",
        "benjamin_decision_receipt_id": "BOOK-BEN-SYNTHETIC-001",
        "benjamin_decision_id": "DEC-SYNTHETIC-001",
        "benjamin_decision_hash": digest("decision"),
        "candidate_economic_path_id": f"PATH-{capability_id}",
        "candidate_economic_path_hash": digest(f"path-{capability_id}"),
        "watchman_pre_action_assessment_id": "ASSESS-SYNTHETIC-001",
        "watchman_pre_action_assessment_hash": digest("assessment"),
        "watchman_capital_envelope_id": "ENV-SYNTHETIC-001",
        "watchman_capital_envelope_hash": digest("envelope"),
        "responsibility_ref": "RESP-SYNTHETIC-001",
        "responsibility_version": "1",
        "action_class": CapitalActionClass.RISK_INCREASING.value,
        "economic_root": "BTC",
        "instrument_intent": f"SYNTHETIC {path}",
        "economic_path_type": path,
        "economic_direction": EconomicDirection.INCREASE.value,
        "economic_currency": "USD",
        "authorized_economic_amount": amount,
        "authorized_minimum": minimum,
        "authorized_maximum": maximum,
        "maximum_capital_commitment": maximum,
        "issued_at": (NOW - timedelta(seconds=2)).isoformat(),
        "valid_from": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "idempotency_key": idempotency_key,
        "permitted_capability_ids": [capability_id],
        "permitted_provider_families": ["SYNTHETIC"],
        "watchman_policy_version": "watchman-synthetic-v1",
    }
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return WatchmanAuthorizedAction.from_wire(wire)


def capability(
    *,
    capability_id: str,
    path: str,
    family: InstrumentFamily,
    unit: ProviderNativeUnitModel,
) -> HandCapability:
    return HandCapability(
        schema_version="1.0",
        capability_id=capability_id,
        capability_version="1",
        provider_family="SYNTHETIC",
        provider_adapter=f"synthetic-{capability_id.lower()}",
        provider_adapter_version="1",
        environment=CapabilityEnvironment.DRY_RUN,
        capability_kind=CapabilityKind.ORDER_SUBMIT,
        supported_action_classes=(CapitalActionClass.RISK_INCREASING,),
        supported_economic_paths=(path,),
        supported_instrument_families=(family.value,),
        provider_native_unit_model=unit,
        required_permission_scope=("synthetic:orders:create",),
        permissions=CapabilityPermissions(can_trade=True),
        qualification_status=CapabilityQualification.SYNTHETIC_QUALIFIED,
        idempotency_semantics=IdempotencySemantics.HAND_ENFORCED,
        limits=(),
        provenance_ref=f"synthetic://capability/{capability_id}",
        provenance_version="1",
        provenance_hash=digest(f"capability-{capability_id}"),
    )


def metadata(
    *,
    instrument: str,
    family: InstrumentFamily,
    unit: ProviderNativeUnitModel,
    contract_type: ContractType,
    multiplier: Decimal | None,
    convention: ContractValueConvention,
    quantity_step: Decimal,
    margin: str | None = None,
) -> ProviderInstrumentMetadata:
    return ProviderInstrumentMetadata(
        schema_version="1.0",
        provider_family="SYNTHETIC",
        provider_instrument_id=instrument,
        canonical_economic_root="BTC",
        asset_class=AssetClass.CRYPTO,
        instrument_family=family,
        base_asset="BTC",
        quote_asset="USD",
        settlement_asset="USD" if contract_type is not ContractType.INVERSE else "BTC",
        native_quantity_unit=unit,
        native_unit_label="BTC" if unit is ProviderNativeUnitModel.BASE_ASSET_QUANTITY else "CONTRACT",
        contract_type=contract_type,
        contract_multiplier=multiplier,
        contract_value_convention=convention,
        price_unit="USD_PER_BTC",
        tick_size=Decimal("0.01"),
        quantity_step=quantity_step,
        minimum_quantity=quantity_step,
        minimum_notional=Decimal("1"),
        quantity_precision=8,
        price_precision=2,
        lot_rule="STEP_SIZE" if family is InstrumentFamily.SPOT else "INTEGER_CONTRACTS",
        margin_denomination=margin,
        metadata_version="synthetic-v1",
        source_ref=f"synthetic://metadata/{instrument}",
        provenance_hash=digest(f"metadata-{instrument}-{multiplier}"),
        known_at=NOW - timedelta(seconds=1),
        effective_at=NOW - timedelta(seconds=1),
        valid_until=NOW + timedelta(minutes=10),
    )


def reference_price() -> ReferencePrice:
    return ReferencePrice(
        value=Decimal("50000"),
        unit="USD_PER_BTC",
        source_ref="synthetic://price/BTC-USD",
        known_at=NOW - timedelta(milliseconds=100),
        valid_until=NOW + timedelta(seconds=30),
    )


def qualified_planner(
    cap: HandCapability,
    meta: ProviderInstrumentMetadata,
    *,
    required_scope: QualificationScope = QualificationScope.SYNTHETIC_MECHANISM,
) -> QualifiedProviderExecutionPlanner:
    binding = InstrumentQualification.bind(
        qualification_id=f"QUAL-{cap.capability_id}",
        qualification_version="1",
        scope=QualificationScope.SYNTHETIC_MECHANISM,
        capability=cap,
        metadata=meta,
        provenance_ref="synthetic://qualification-suite/h1f",
        provenance_hash=digest(f"qualification-{cap.capability_id}-{meta.content_hash()}"),
    )
    registry = InstrumentQualificationRegistry((binding,))
    return QualifiedProviderExecutionPlanner(registry, required_scope=required_scope)


def test_spot_quote_economic_notional_translates_to_base_asset_quantity() -> None:
    cap = capability(
        capability_id="CAP-SPOT-BASE",
        path="SPOT_EXPOSURE_CHANGE",
        family=InstrumentFamily.SPOT,
        unit=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
    )
    meta = metadata(
        instrument="BTC-USD",
        family=InstrumentFamily.SPOT,
        unit=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        contract_type=ContractType.NOT_APPLICABLE,
        multiplier=None,
        convention=ContractValueConvention.NOT_APPLICABLE,
        quantity_step=Decimal("0.0001"),
    )
    result = qualified_planner(cap, meta).plan(
        authorization(capability_id=cap.capability_id, path="SPOT_EXPOSURE_CHANGE"),
        cap,
        meta,
        reference_price=reference_price(),
        policy=TranslationPolicy.exact_only(),
        now=NOW,
    )
    assert result.status is PlanStatus.TRANSLATABLE
    assert result.plan is not None
    assert result.plan.native_quantity == Decimal("0.2")
    assert result.plan.native_unit_type is ProviderNativeUnitModel.BASE_ASSET_QUANTITY
    assert result.plan.translated_economic_notional == Decimal("10000.0")


def test_linear_derivative_uses_declared_contract_multiplier_times_price() -> None:
    cap = capability(
        capability_id="CAP-LINEAR",
        path="LINEAR_DERIVATIVE_EXPOSURE",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
    )
    meta = metadata(
        instrument="BTC-LINEAR-SYNTH",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
        contract_type=ContractType.LINEAR,
        multiplier=Decimal("0.001"),
        convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        quantity_step=Decimal("1"),
        margin="USD",
    )
    result = qualified_planner(cap, meta).plan(
        authorization(capability_id=cap.capability_id, path="LINEAR_DERIVATIVE_EXPOSURE"),
        cap,
        meta,
        reference_price=reference_price(),
        policy=TranslationPolicy.exact_only(),
        now=NOW,
    )
    assert result.status is PlanStatus.TRANSLATABLE
    assert result.plan is not None
    assert result.plan.native_quantity == Decimal("2E+2")
    assert result.plan.translated_economic_notional == Decimal("10000.000")


def test_inverse_derivative_is_not_passed_through_linear_formula() -> None:
    cap = capability(
        capability_id="CAP-INVERSE",
        path="INVERSE_DERIVATIVE_EXPOSURE",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.INVERSE_CONTRACT,
    )
    meta = metadata(
        instrument="BTC-INVERSE-SYNTH",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.INVERSE_CONTRACT,
        contract_type=ContractType.INVERSE,
        multiplier=Decimal("100"),
        convention=ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT,
        quantity_step=Decimal("1"),
        margin="BTC",
    )
    result = qualified_planner(cap, meta).plan(
        authorization(capability_id=cap.capability_id, path="INVERSE_DERIVATIVE_EXPOSURE"),
        cap,
        meta,
        reference_price=reference_price(),
        policy=TranslationPolicy.exact_only(),
        now=NOW,
    )
    assert result.status is PlanStatus.TRANSLATABLE
    assert result.plan is not None
    assert result.plan.native_quantity == Decimal("100")
    assert result.plan.reference_price is None
    assert result.plan.native_quantity != Decimal("10000") / (Decimal("100") * Decimal("50000"))


def test_changed_contract_multiplier_invalidates_exact_metadata_qualification() -> None:
    cap = capability(
        capability_id="CAP-LINEAR",
        path="LINEAR_DERIVATIVE_EXPOSURE",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
    )
    qualified_meta = metadata(
        instrument="BTC-LINEAR-SYNTH",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
        contract_type=ContractType.LINEAR,
        multiplier=Decimal("0.001"),
        convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        quantity_step=Decimal("1"),
        margin="USD",
    )
    planner = qualified_planner(cap, qualified_meta)
    changed_multiplier = metadata(
        instrument="BTC-LINEAR-SYNTH",
        family=InstrumentFamily.DERIVATIVE,
        unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
        contract_type=ContractType.LINEAR,
        multiplier=Decimal("0.002"),
        convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        quantity_step=Decimal("1"),
        margin="USD",
    )
    result = planner.plan(
        authorization(capability_id=cap.capability_id, path="LINEAR_DERIVATIVE_EXPOSURE"),
        cap,
        changed_multiplier,
        reference_price=reference_price(),
        policy=TranslationPolicy.exact_only(),
        now=NOW,
    )
    assert result.status is PlanStatus.UNIT_METADATA_UNAVAILABLE
    assert result.plan is None
    assert "has not earned" in str(result.reason)


def test_missing_derivative_multiplier_fails_closed_at_metadata_boundary() -> None:
    with pytest.raises(ValueError, match="contract_multiplier"):
        metadata(
            instrument="BTC-LINEAR-SYNTH",
            family=InstrumentFamily.DERIVATIVE,
            unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
            contract_type=ContractType.LINEAR,
            multiplier=None,
            convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
            quantity_step=Decimal("1"),
            margin="USD",
        )


def test_unsupported_unit_model_fails_closed_at_metadata_boundary() -> None:
    with pytest.raises(ValueError, match="unsupported provider native unit model"):
        metadata(
            instrument="BTC-UNKNOWN-SYNTH",
            family=InstrumentFamily.DERIVATIVE,
            unit=ProviderNativeUnitModel.OTHER_DECLARED,
            contract_type=ContractType.NOT_APPLICABLE,
            multiplier=None,
            convention=ContractValueConvention.NOT_APPLICABLE,
            quantity_step=Decimal("1"),
        )


def test_synthetic_qualification_does_not_satisfy_live_mechanism_scope() -> None:
    cap = capability(
        capability_id="CAP-SPOT-BASE",
        path="SPOT_EXPOSURE_CHANGE",
        family=InstrumentFamily.SPOT,
        unit=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
    )
    meta = metadata(
        instrument="BTC-USD",
        family=InstrumentFamily.SPOT,
        unit=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        contract_type=ContractType.NOT_APPLICABLE,
        multiplier=None,
        convention=ContractValueConvention.NOT_APPLICABLE,
        quantity_step=Decimal("0.0001"),
    )
    result = qualified_planner(
        cap, meta, required_scope=QualificationScope.LIVE_MECHANISM
    ).plan(
        authorization(capability_id=cap.capability_id, path="SPOT_EXPOSURE_CHANGE"),
        cap,
        meta,
        reference_price=reference_price(),
        policy=TranslationPolicy.exact_only(),
        now=NOW,
    )
    assert result.status is PlanStatus.UNIT_METADATA_UNAVAILABLE
    assert result.plan is None
