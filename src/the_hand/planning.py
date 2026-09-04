from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum

from .authorization import WatchmanAuthorizedAction
from .capability import CapabilityQualification, HandCapability, ProviderNativeUnitModel
from .units import ContractValueConvention, ProviderInstrumentMetadata


class PlanStatus(str, Enum):
    TRANSLATABLE = "TRANSLATABLE"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"
    CAPABILITY_NOT_QUALIFIED = "CAPABILITY_NOT_QUALIFIED"
    AUTHORIZATION_EXPIRED = "AUTHORIZATION_EXPIRED"
    AUTHORIZATION_NOT_YET_VALID = "AUTHORIZATION_NOT_YET_VALID"
    UNIT_METADATA_UNAVAILABLE = "UNIT_METADATA_UNAVAILABLE"
    REFERENCE_PRICE_STALE = "REFERENCE_PRICE_STALE"
    EXACT_QUANTIZATION_REQUIRED = "EXACT_QUANTIZATION_REQUIRED"
    NATIVE_MINIMUM_EXCEEDS_AUTHORITY = "NATIVE_MINIMUM_EXCEEDS_AUTHORITY"
    QUANTIZATION_OUTSIDE_TOLERANCE = "QUANTIZATION_OUTSIDE_TOLERANCE"
    TRANSLATION_DIRECTION_CHANGED = "TRANSLATION_DIRECTION_CHANGED"


class QuantizationRule(str, Enum):
    EXACT = "EXACT"
    DOWN = "DOWN"
    NEAREST = "NEAREST"


@dataclass(frozen=True)
class TranslationPolicy:
    policy_id: str
    version: str
    quantization_rule: QuantizationRule
    max_absolute_error: Decimal
    max_relative_error: Decimal
    allow_lower_quantity: bool
    allow_upward_translation: bool

    def __post_init__(self) -> None:
        if not self.policy_id or not self.version:
            raise ValueError("translation policy id and version are required")
        for field, value in (
            ("max_absolute_error", self.max_absolute_error),
            ("max_relative_error", self.max_relative_error),
        ):
            if value < 0 or not value.is_finite():
                raise ValueError(f"{field} must be finite and non-negative")

    @classmethod
    def exact_only(cls) -> "TranslationPolicy":
        return cls(
            policy_id="HAND.EXACT_ONLY",
            version="1",
            quantization_rule=QuantizationRule.EXACT,
            max_absolute_error=Decimal("0"),
            max_relative_error=Decimal("0"),
            allow_lower_quantity=False,
            allow_upward_translation=False,
        )

    def to_wire(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "quantization_rule": self.quantization_rule.value,
            "max_absolute_error": format(self.max_absolute_error, "f"),
            "max_relative_error": format(self.max_relative_error, "f"),
            "allow_lower_quantity": self.allow_lower_quantity,
            "allow_upward_translation": self.allow_upward_translation,
        }

    def content_hash(self) -> str:
        canonical = json.dumps(
            self.to_wire(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class ReferencePrice:
    value: Decimal
    unit: str
    source_ref: str
    known_at: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        if self.value <= 0 or not self.value.is_finite():
            raise ValueError("reference price must be positive and finite")
        if not self.unit or not self.source_ref:
            raise ValueError("reference price unit and source_ref are required")
        for field, value in (("known_at", self.known_at), ("valid_until", self.valid_until)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"reference price {field} must be timezone-aware")
        if self.valid_until <= self.known_at:
            raise ValueError("reference price valid_until must follow known_at")

    def to_wire(self) -> dict[str, str]:
        return {
            "value": format(self.value, "f"),
            "unit": self.unit,
            "source_ref": self.source_ref,
            "known_at": self.known_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
        }

    def content_hash(self) -> str:
        canonical = json.dumps(
            self.to_wire(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class ProviderExecutionPlan:
    schema_version: str
    source_watchman_authorization_id: str
    source_watchman_authorization_hash: str
    candidate_economic_path_id: str
    candidate_economic_path_hash: str
    capability_id: str
    capability_version: str
    capability_hash: str
    provider_family: str
    provider_instrument_id: str
    economic_root: str
    action_class: str
    action: str
    economic_amount_authorized: Decimal
    authorized_maximum: Decimal
    native_quantity: Decimal
    native_unit_type: ProviderNativeUnitModel
    rounding_rule: str
    reference_price: Decimal | None
    reference_price_hash: str | None
    translated_economic_notional: Decimal
    translation_error: Decimal
    translation_policy_id: str
    translation_policy_version: str
    translation_policy_hash: str
    provider_constraints: tuple[tuple[str, str], ...]
    idempotency_key: str
    adapter_planner_version: str
    known_at: datetime
    valid_until: datetime
    metadata_hash: str
    exact_input_hashes: tuple[str, ...]
    plan_content_hash: str

    @classmethod
    def create(cls, **values: object) -> "ProviderExecutionPlan":
        plan = cls(plan_content_hash="", **values)
        return replace(plan, plan_content_hash=plan.compute_content_hash())

    def to_wire(self, *, include_hash: bool = True) -> dict[str, object]:
        wire: dict[str, object] = {
            "schema_version": self.schema_version,
            "source_watchman_authorization_id": self.source_watchman_authorization_id,
            "source_watchman_authorization_hash": self.source_watchman_authorization_hash,
            "candidate_economic_path_id": self.candidate_economic_path_id,
            "candidate_economic_path_hash": self.candidate_economic_path_hash,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "capability_hash": self.capability_hash,
            "provider_family": self.provider_family,
            "provider_instrument_id": self.provider_instrument_id,
            "economic_root": self.economic_root,
            "action_class": self.action_class,
            "action": self.action,
            "economic_amount_authorized": format(self.economic_amount_authorized, "f"),
            "authorized_maximum": format(self.authorized_maximum, "f"),
            "native_quantity": format(self.native_quantity, "f"),
            "native_unit_type": self.native_unit_type.value,
            "rounding_rule": self.rounding_rule,
            "reference_price": None if self.reference_price is None else format(self.reference_price, "f"),
            "reference_price_hash": self.reference_price_hash,
            "translated_economic_notional": format(self.translated_economic_notional, "f"),
            "translation_error": format(self.translation_error, "f"),
            "translation_policy_id": self.translation_policy_id,
            "translation_policy_version": self.translation_policy_version,
            "translation_policy_hash": self.translation_policy_hash,
            "provider_constraints": {key: value for key, value in self.provider_constraints},
            "idempotency_key": self.idempotency_key,
            "adapter_planner_version": self.adapter_planner_version,
            "known_at": self.known_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "metadata_hash": self.metadata_hash,
            "exact_input_hashes": list(self.exact_input_hashes),
        }
        if include_hash:
            wire["plan_content_hash"] = self.plan_content_hash
        return wire

    def compute_content_hash(self) -> str:
        canonical = json.dumps(
            self.to_wire(include_hash=False),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class PlanResult:
    status: PlanStatus
    plan: ProviderExecutionPlan | None = None
    reason: str | None = None


class ProviderExecutionPlanner:
    """Deterministic provider planner. It returns plans or typed failures, never effects."""

    def __init__(self, *, planner_version: str = "hand-provider-planner-v1") -> None:
        if not planner_version:
            raise ValueError("planner_version is required")
        self.planner_version = planner_version

    def plan_exact(
        self,
        authorization: WatchmanAuthorizedAction,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        *,
        reference_price: ReferencePrice | None,
        now: datetime,
    ) -> PlanResult:
        return self.plan(
            authorization,
            capability,
            metadata,
            reference_price=reference_price,
            policy=TranslationPolicy.exact_only(),
            now=now,
        )

    def plan(
        self,
        authorization: WatchmanAuthorizedAction,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        *,
        reference_price: ReferencePrice | None,
        policy: TranslationPolicy,
        now: datetime,
    ) -> PlanResult:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("planning clock must be timezone-aware")
        if now < authorization.valid_from:
            return PlanResult(PlanStatus.AUTHORIZATION_NOT_YET_VALID, reason="authorization not yet valid")
        if now >= authorization.expires_at:
            return PlanResult(PlanStatus.AUTHORIZATION_EXPIRED, reason="authorization expired")
        if capability.qualification_status not in (
            CapabilityQualification.SYNTHETIC_QUALIFIED,
            CapabilityQualification.SHADOW_QUALIFIED,
            CapabilityQualification.LIVE_QUALIFIED,
        ):
            return PlanResult(
                PlanStatus.CAPABILITY_NOT_QUALIFIED,
                reason="capability has not reached a planning-qualified lifecycle state",
            )
        if (
            capability.capability_id not in authorization.permitted_capability_ids
            or capability.provider_family not in authorization.permitted_provider_families
            or authorization.action_class not in capability.supported_action_classes
            or authorization.economic_path_type not in capability.supported_economic_paths
        ):
            return PlanResult(
                PlanStatus.CAPABILITY_NOT_QUALIFIED,
                reason="capability is outside Watchman authorization or action semantics",
            )
        if (
            metadata.provider_family != capability.provider_family
            or metadata.native_quantity_unit is not capability.provider_native_unit_model
            or metadata.canonical_economic_root != authorization.economic_root
            or metadata.instrument_family.value not in capability.supported_instrument_families
        ):
            return PlanResult(
                PlanStatus.UNSUPPORTED_INSTRUMENT,
                reason="capability and provider instrument metadata do not describe the same mechanics",
            )
        if now < metadata.effective_at or now >= metadata.valid_until or metadata.known_at > now:
            return PlanResult(
                PlanStatus.UNIT_METADATA_UNAVAILABLE,
                reason="provider instrument metadata is not valid at the planning time",
            )

        unit = metadata.native_quantity_unit
        amount = authorization.authorized_economic_amount
        price_value: Decimal | None = None
        price_hash: str | None = None
        price_valid_until: datetime | None = None
        if unit in (
            ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
            ProviderNativeUnitModel.LINEAR_CONTRACT,
        ):
            if reference_price is None or reference_price.known_at > now or now >= reference_price.valid_until:
                return PlanResult(
                    PlanStatus.REFERENCE_PRICE_STALE,
                    reason="fresh reference price is required for this declared unit model",
                )
            if reference_price.unit != metadata.price_unit:
                return PlanResult(
                    PlanStatus.UNSUPPORTED_INSTRUMENT,
                    reason="reference price unit does not match provider metadata",
                )
            price_value = reference_price.value
            price_hash = reference_price.content_hash()
            price_valid_until = reference_price.valid_until

        raw_quantity, raw_translated, error = self._translate_raw(
            amount, unit, metadata, price_value
        )
        if error is not None:
            return error

        quantized, quantization_error = self._quantize(
            raw_quantity, metadata.quantity_step, policy
        )
        if quantization_error is not None:
            return quantization_error
        assert quantized is not None

        translated, translation_error = self._translated_notional(
            quantized, unit, metadata, price_value
        )
        if translation_error is not None:
            return translation_error
        assert translated is not None

        if quantized < 0:
            return PlanResult(
                PlanStatus.TRANSLATION_DIRECTION_CHANGED,
                reason="provider-native quantity must never be negative",
            )
        if quantized % metadata.quantity_step != 0:
            return PlanResult(
                PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                reason="provider-native quantity does not satisfy declared quantity step",
            )
        if quantized < metadata.minimum_quantity or translated < metadata.minimum_notional:
            return PlanResult(
                PlanStatus.NATIVE_MINIMUM_EXCEEDS_AUTHORITY,
                reason="provider minimums cannot represent the governed economic amount",
            )
        if translated > authorization.authorized_maximum or translated > authorization.maximum_capital_commitment:
            return PlanResult(
                PlanStatus.NATIVE_MINIMUM_EXCEEDS_AUTHORITY,
                reason="translated notional would exceed Watchman maximum capital authority",
            )
        if translated < authorization.authorized_minimum:
            return PlanResult(
                PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                reason="translated notional falls below Watchman's authorized economic range",
            )
        if translated > amount and not policy.allow_upward_translation:
            if policy.allow_lower_quantity:
                lower = self._floor_to_step(raw_quantity, metadata.quantity_step)
                if lower != quantized:
                    translated_lower, lower_error = self._translated_notional(
                        lower, unit, metadata, price_value
                    )
                    if lower_error is None and translated_lower is not None:
                        quantized = lower
                        translated = translated_lower
            if translated > amount:
                return PlanResult(
                    PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                    reason="translation policy forbids upward economic translation",
                )

        error_value = translated - amount
        absolute_error = abs(error_value)
        relative_error = absolute_error / amount
        if (
            absolute_error > policy.max_absolute_error
            or relative_error > policy.max_relative_error
        ):
            return PlanResult(
                PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                reason=(
                    "translation error exceeds explicit policy: "
                    f"absolute={absolute_error}, relative={relative_error}"
                ),
            )
        if authorization.action_class.value not in [value.value for value in capability.supported_action_classes]:
            return PlanResult(
                PlanStatus.TRANSLATION_DIRECTION_CHANGED,
                reason="action class changed across translation boundary",
            )

        capability_hash = capability.content_hash()
        metadata_hash = metadata.content_hash()
        policy_hash = policy.content_hash()
        input_hashes = [
            f"authorization:{authorization.authorization_content_hash}",
            f"capability:{capability_hash}",
            f"metadata:{metadata_hash}",
            f"translation_policy:{policy_hash}",
        ]
        if price_hash is not None:
            input_hashes.append(f"reference_price:{price_hash}")
        input_hashes = sorted(input_hashes)
        valid_until = min(
            value
            for value in (
                authorization.expires_at,
                metadata.valid_until,
                price_valid_until,
            )
            if value is not None
        )
        constraints = tuple(
            sorted(
                (
                    ("lot_rule", metadata.lot_rule),
                    ("minimum_notional", format(metadata.minimum_notional, "f")),
                    ("minimum_quantity", format(metadata.minimum_quantity, "f")),
                    ("quantity_step", format(metadata.quantity_step, "f")),
                    ("tick_size", format(metadata.tick_size, "f")),
                )
            )
        )
        plan = ProviderExecutionPlan.create(
            schema_version="1.0",
            source_watchman_authorization_id=authorization.authorization_id,
            source_watchman_authorization_hash=authorization.authorization_content_hash,
            candidate_economic_path_id=authorization.candidate_economic_path_id,
            candidate_economic_path_hash=authorization.candidate_economic_path_hash,
            capability_id=capability.capability_id,
            capability_version=capability.capability_version,
            capability_hash=capability_hash,
            provider_family=metadata.provider_family,
            provider_instrument_id=metadata.provider_instrument_id,
            economic_root=authorization.economic_root,
            action_class=authorization.action_class.value,
            action=authorization.economic_direction.value,
            economic_amount_authorized=amount,
            authorized_maximum=authorization.authorized_maximum,
            native_quantity=quantized,
            native_unit_type=unit,
            rounding_rule=policy.quantization_rule.value,
            reference_price=price_value,
            reference_price_hash=price_hash,
            translated_economic_notional=translated,
            translation_error=error_value,
            translation_policy_id=policy.policy_id,
            translation_policy_version=policy.version,
            translation_policy_hash=policy_hash,
            provider_constraints=constraints,
            idempotency_key=authorization.idempotency_key,
            adapter_planner_version=self.planner_version,
            known_at=now,
            valid_until=valid_until,
            metadata_hash=metadata_hash,
            exact_input_hashes=tuple(input_hashes),
        )
        return PlanResult(PlanStatus.TRANSLATABLE, plan=plan)

    def _translate_raw(
        self,
        amount: Decimal,
        unit: ProviderNativeUnitModel,
        metadata: ProviderInstrumentMetadata,
        price: Decimal | None,
    ) -> tuple[Decimal, Decimal | None, PlanResult | None]:
        if unit is ProviderNativeUnitModel.BASE_ASSET_QUANTITY:
            if price is None:
                return Decimal("0"), None, PlanResult(
                    PlanStatus.REFERENCE_PRICE_STALE, reason="reference price required"
                )
            raw = amount / price
            return raw, raw * price, None
        if unit is ProviderNativeUnitModel.QUOTE_NOTIONAL:
            return amount, amount, None
        if unit is ProviderNativeUnitModel.LINEAR_CONTRACT:
            if (
                price is None
                or metadata.contract_multiplier is None
                or metadata.contract_value_convention
                is not ContractValueConvention.BASE_ASSET_PER_CONTRACT
            ):
                return Decimal("0"), None, PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE,
                    reason="linear contract metadata lacks declared value semantics",
                )
            raw = amount / (metadata.contract_multiplier * price)
            return raw, raw * metadata.contract_multiplier * price, None
        if unit is ProviderNativeUnitModel.INVERSE_CONTRACT:
            if (
                metadata.contract_multiplier is None
                or metadata.contract_value_convention
                is not ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT
            ):
                return Decimal("0"), None, PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE,
                    reason="inverse contract metadata lacks declared value semantics",
                )
            raw = amount / metadata.contract_multiplier
            return raw, raw * metadata.contract_multiplier, None
        return Decimal("0"), None, PlanResult(
            PlanStatus.UNSUPPORTED_INSTRUMENT, reason="unsupported native unit model"
        )

    def _translated_notional(
        self,
        quantity: Decimal,
        unit: ProviderNativeUnitModel,
        metadata: ProviderInstrumentMetadata,
        price: Decimal | None,
    ) -> tuple[Decimal | None, PlanResult | None]:
        if unit is ProviderNativeUnitModel.BASE_ASSET_QUANTITY:
            if price is None:
                return None, PlanResult(PlanStatus.REFERENCE_PRICE_STALE, reason="reference price required")
            return quantity * price, None
        if unit is ProviderNativeUnitModel.QUOTE_NOTIONAL:
            return quantity, None
        if unit is ProviderNativeUnitModel.LINEAR_CONTRACT:
            if price is None or metadata.contract_multiplier is None:
                return None, PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE, reason="linear multiplier/price unavailable"
                )
            return quantity * metadata.contract_multiplier * price, None
        if unit is ProviderNativeUnitModel.INVERSE_CONTRACT:
            if metadata.contract_multiplier is None:
                return None, PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE, reason="inverse multiplier unavailable"
                )
            return quantity * metadata.contract_multiplier, None
        return None, PlanResult(PlanStatus.UNSUPPORTED_INSTRUMENT, reason="unsupported unit model")

    def _quantize(
        self, raw: Decimal, step: Decimal, policy: TranslationPolicy
    ) -> tuple[Decimal | None, PlanResult | None]:
        aligned = raw % step == 0
        if policy.quantization_rule is QuantizationRule.EXACT:
            if not aligned:
                return None, PlanResult(
                    PlanStatus.EXACT_QUANTIZATION_REQUIRED,
                    reason="raw provider quantity is not exactly aligned to the declared quantity step",
                )
            return raw, None
        if policy.quantization_rule is QuantizationRule.DOWN:
            quantized = self._floor_to_step(raw, step)
            if quantized != raw and not policy.allow_lower_quantity:
                return None, PlanResult(
                    PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                    reason="policy does not permit lowering provider quantity",
                )
            return quantized, None
        if policy.quantization_rule is QuantizationRule.NEAREST:
            units = (raw / step).to_integral_value(rounding=ROUND_HALF_UP)
            candidate = units * step
            if candidate > raw and not policy.allow_upward_translation:
                if policy.allow_lower_quantity:
                    candidate = self._floor_to_step(raw, step)
                else:
                    return None, PlanResult(
                        PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
                        reason="nearest quantity rounds upward but policy forbids upward translation",
                    )
            return candidate, None
        return None, PlanResult(
            PlanStatus.QUANTIZATION_OUTSIDE_TOLERANCE,
            reason="unsupported quantization policy",
        )

    @staticmethod
    def _floor_to_step(raw: Decimal, step: Decimal) -> Decimal:
        units = (raw / step).to_integral_value(rounding=ROUND_FLOOR)
        return units * step
