from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from the_hand import (
    AssetClass,
    ContractType,
    ContractValueConvention,
    InstrumentFamily,
    ProviderInstrumentMetadata,
    ProviderNativeUnitModel,
)


NOW = datetime(2026, 9, 3, 20, 0, tzinfo=timezone.utc)


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
        "quantity_step": Decimal("0.000001"),
        "minimum_quantity": Decimal("0.00001"),
        "minimum_notional": Decimal("1"),
        "quantity_precision": 6,
        "price_precision": 2,
        "lot_rule": "STEP_SIZE",
        "margin_denomination": None,
        "metadata_version": "synthetic-v1",
        "source_ref": "synthetic://instrument/BTC-USD",
        "provenance_hash": hashlib.sha256(b"spot metadata").hexdigest(),
        "known_at": NOW - timedelta(seconds=1),
        "effective_at": NOW - timedelta(seconds=1),
        "valid_until": NOW + timedelta(hours=1),
    }
    values.update(updates)
    return ProviderInstrumentMetadata(**values)


def test_spot_base_quantity_metadata_is_explicit_and_hashable() -> None:
    subject = metadata()
    assert subject.native_quantity_unit is ProviderNativeUnitModel.BASE_ASSET_QUANTITY
    assert subject.contract_multiplier is None
    assert subject.content_hash() == metadata().content_hash()
    assert subject.content_hash() != metadata(quantity_step=Decimal("0.00001")).content_hash()


def test_spot_quote_notional_is_a_distinct_native_unit_model() -> None:
    subject = metadata(
        native_quantity_unit=ProviderNativeUnitModel.QUOTE_NOTIONAL,
        native_unit_label="USD",
        quantity_step=Decimal("0.01"),
        minimum_quantity=Decimal("1"),
    )
    assert subject.native_quantity_unit is ProviderNativeUnitModel.QUOTE_NOTIONAL
    assert subject.native_unit_label == "USD"


def test_linear_contract_requires_explicit_multiplier_and_base_value_convention() -> None:
    subject = metadata(
        provider_instrument_id="BTC-LINEAR-PERP",
        instrument_family=InstrumentFamily.DERIVATIVE,
        native_quantity_unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
        native_unit_label="CONTRACT",
        contract_type=ContractType.LINEAR,
        contract_multiplier=Decimal("0.001"),
        contract_value_convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        quantity_step=Decimal("1"),
        minimum_quantity=Decimal("1"),
        lot_rule="INTEGER_CONTRACTS",
        margin_denomination="USD",
    )
    assert subject.contract_multiplier == Decimal("0.001")
    with pytest.raises(ValueError, match="contract_multiplier"):
        metadata(
            instrument_family=InstrumentFamily.DERIVATIVE,
            native_quantity_unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
            contract_type=ContractType.LINEAR,
            contract_multiplier=None,
            contract_value_convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        )


def test_inverse_contract_is_not_linear_metadata() -> None:
    subject = metadata(
        provider_instrument_id="BTC-INVERSE-PERP",
        instrument_family=InstrumentFamily.DERIVATIVE,
        native_quantity_unit=ProviderNativeUnitModel.INVERSE_CONTRACT,
        native_unit_label="CONTRACT",
        contract_type=ContractType.INVERSE,
        contract_multiplier=Decimal("100"),
        contract_value_convention=ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT,
        quantity_step=Decimal("1"),
        minimum_quantity=Decimal("1"),
        lot_rule="INTEGER_CONTRACTS",
        margin_denomination="BTC",
    )
    assert subject.contract_type is ContractType.INVERSE
    assert subject.contract_value_convention is ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT
    with pytest.raises(ValueError, match="quote-currency-per-contract"):
        metadata(
            instrument_family=InstrumentFamily.DERIVATIVE,
            native_quantity_unit=ProviderNativeUnitModel.INVERSE_CONTRACT,
            contract_type=ContractType.INVERSE,
            contract_multiplier=Decimal("100"),
            contract_value_convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        )


def test_spot_metadata_rejects_contract_formula_fields() -> None:
    with pytest.raises(ValueError, match="contract multiplier"):
        metadata(contract_multiplier=Decimal("1"))


def test_metadata_validity_and_provenance_are_part_of_identity() -> None:
    first = metadata()
    assert first.content_hash() != metadata(metadata_version="synthetic-v2").content_hash()
    assert first.content_hash() != metadata(valid_until=NOW + timedelta(hours=2)).content_hash()
    with pytest.raises(ValueError, match="valid_until"):
        metadata(valid_until=NOW - timedelta(minutes=1))
