from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .capability import ProviderNativeUnitModel


class AssetClass(str, Enum):
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    FX = "FX"
    COMMODITY = "COMMODITY"
    OTHER = "OTHER"


class InstrumentFamily(str, Enum):
    SPOT = "SPOT"
    DERIVATIVE = "DERIVATIVE"


class ContractType(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    LINEAR = "LINEAR"
    INVERSE = "INVERSE"


class ContractValueConvention(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BASE_ASSET_PER_CONTRACT = "BASE_ASSET_PER_CONTRACT"
    QUOTE_CURRENCY_PER_CONTRACT = "QUOTE_CURRENCY_PER_CONTRACT"


def _positive(value: Decimal | None, field: str, *, required: bool = True) -> Decimal | None:
    if value is None:
        if required:
            raise ValueError(f"{field} is required")
        return None
    if value <= 0 or not value.is_finite():
        raise ValueError(f"{field} must be positive and finite")
    return value


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True)
class ProviderInstrumentMetadata:
    """Provider-declared unit semantics. Metadata describes mechanics, never authority."""

    schema_version: str
    provider_family: str
    provider_instrument_id: str
    canonical_economic_root: str
    asset_class: AssetClass
    instrument_family: InstrumentFamily
    base_asset: str
    quote_asset: str
    settlement_asset: str
    native_quantity_unit: ProviderNativeUnitModel
    native_unit_label: str
    contract_type: ContractType
    contract_multiplier: Decimal | None
    contract_value_convention: ContractValueConvention
    price_unit: str
    tick_size: Decimal
    quantity_step: Decimal
    minimum_quantity: Decimal
    minimum_notional: Decimal
    quantity_precision: int
    price_precision: int
    lot_rule: str
    margin_denomination: str | None
    metadata_version: str
    source_ref: str
    provenance_hash: str
    known_at: datetime
    effective_at: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported ProviderInstrumentMetadata schema_version")
        for field, value in (
            ("provider_family", self.provider_family),
            ("provider_instrument_id", self.provider_instrument_id),
            ("canonical_economic_root", self.canonical_economic_root),
            ("base_asset", self.base_asset),
            ("quote_asset", self.quote_asset),
            ("settlement_asset", self.settlement_asset),
            ("native_unit_label", self.native_unit_label),
            ("price_unit", self.price_unit),
            ("lot_rule", self.lot_rule),
            ("metadata_version", self.metadata_version),
            ("source_ref", self.source_ref),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field} is required")
        if not re.fullmatch(r"[a-f0-9]{64}", self.provenance_hash):
            raise ValueError("provenance_hash must be lowercase SHA-256 hex")
        for field, value in (
            ("tick_size", self.tick_size),
            ("quantity_step", self.quantity_step),
            ("minimum_quantity", self.minimum_quantity),
            ("minimum_notional", self.minimum_notional),
        ):
            _positive(value, field)
        if self.quantity_precision < 0 or self.price_precision < 0:
            raise ValueError("precision values must be non-negative")
        for field, value in (
            ("known_at", self.known_at),
            ("effective_at", self.effective_at),
            ("valid_until", self.valid_until),
        ):
            _aware(value, field)
        if self.valid_until <= self.effective_at:
            raise ValueError("valid_until must follow effective_at")

        if self.native_quantity_unit in (
            ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
            ProviderNativeUnitModel.QUOTE_NOTIONAL,
        ):
            if self.instrument_family is not InstrumentFamily.SPOT:
                raise ValueError("spot native unit models require SPOT instrument family")
            if self.contract_type is not ContractType.NOT_APPLICABLE:
                raise ValueError("spot metadata cannot declare derivative contract type")
            if self.contract_multiplier is not None:
                raise ValueError("spot metadata cannot declare a contract multiplier")
            if self.contract_value_convention is not ContractValueConvention.NOT_APPLICABLE:
                raise ValueError("spot metadata cannot declare contract value convention")
        elif self.native_quantity_unit is ProviderNativeUnitModel.LINEAR_CONTRACT:
            if self.instrument_family is not InstrumentFamily.DERIVATIVE:
                raise ValueError("linear contracts require DERIVATIVE instrument family")
            if self.contract_type is not ContractType.LINEAR:
                raise ValueError("linear unit model requires LINEAR contract type")
            _positive(self.contract_multiplier, "contract_multiplier")
            if self.contract_value_convention is not ContractValueConvention.BASE_ASSET_PER_CONTRACT:
                raise ValueError(
                    "linear contract semantics require an explicitly declared base-asset-per-contract convention"
                )
        elif self.native_quantity_unit is ProviderNativeUnitModel.INVERSE_CONTRACT:
            if self.instrument_family is not InstrumentFamily.DERIVATIVE:
                raise ValueError("inverse contracts require DERIVATIVE instrument family")
            if self.contract_type is not ContractType.INVERSE:
                raise ValueError("inverse unit model requires INVERSE contract type")
            _positive(self.contract_multiplier, "contract_multiplier")
            if self.contract_value_convention is not ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT:
                raise ValueError(
                    "inverse contract semantics require an explicitly declared quote-currency-per-contract convention"
                )
        else:
            raise ValueError("unsupported provider native unit model for v1 metadata")

    def to_wire(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider_family": self.provider_family,
            "provider_instrument_id": self.provider_instrument_id,
            "canonical_economic_root": self.canonical_economic_root,
            "asset_class": self.asset_class.value,
            "instrument_family": self.instrument_family.value,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "settlement_asset": self.settlement_asset,
            "native_quantity_unit": self.native_quantity_unit.value,
            "native_unit_label": self.native_unit_label,
            "contract_type": self.contract_type.value,
            "contract_multiplier": (
                None if self.contract_multiplier is None else format(self.contract_multiplier, "f")
            ),
            "contract_value_convention": self.contract_value_convention.value,
            "price_unit": self.price_unit,
            "tick_size": format(self.tick_size, "f"),
            "quantity_step": format(self.quantity_step, "f"),
            "minimum_quantity": format(self.minimum_quantity, "f"),
            "minimum_notional": format(self.minimum_notional, "f"),
            "quantity_precision": self.quantity_precision,
            "price_precision": self.price_precision,
            "lot_rule": self.lot_rule,
            "margin_denomination": self.margin_denomination,
            "metadata_version": self.metadata_version,
            "source_ref": self.source_ref,
            "provenance_hash": self.provenance_hash,
            "known_at": self.known_at.isoformat(),
            "effective_at": self.effective_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
        }

    def content_hash(self) -> str:
        canonical = json.dumps(
            self.to_wire(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
