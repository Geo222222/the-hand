from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
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
    """Deterministic exact-only v1 planner. It never invokes a provider adapter."""

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

        if unit is ProviderNativeUnitModel.BASE_ASSET_QUANTITY:
            assert price_value is not None
            raw_quantity = amount / price_value
            translated = raw_quantity * price_value
        elif unit is ProviderNativeUnitModel.QUOTE_NOTIONAL:
            raw_quantity = amount
            translated = raw_quantity
        elif unit is ProviderNativeUnitModel.LINEAR_CONTRACT:
            assert price_value is not None
            if (
                metadata.contract_multiplier is None
                or metadata.contract_value_convention
                is not ContractValueConvention.BASE_ASSET_PER_CONTRACT
            ):
                return PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE,
                    reason="linear contract metadata lacks its declared value semantics",
                )
            raw_quantity = amount / (metadata.contract_multiplier * price_value)
            translated = raw_quantity * metadata.contract_multiplier * price_value
        elif unit is ProviderNativeUnitModel.INVERSE_CONTRACT:
            if (
                metadata.contract_multiplier is None
                or metadata.contract_value_convention
                is not ContractValueConvention.QUOTE_CURRENCY_PER_CONTRACT
            ):
                return PlanResult(
                    PlanStatus.UNIT_METADATA_UNAVAILABLE,
                    reason="inverse contract metadata lacks its declared value semantics",
                )
            raw_quantity = amount / metadata.contract_multiplier
            translated = raw_quantity * metadata.contract_multiplier
        else:
            return PlanResult(PlanStatus.UNSUPPORTED_INSTRUMENT, reason="unsupported native unit model")

        step = metadata.quantity_step
        if raw_quantity % step != 0:
            return PlanResult(
                PlanStatus.EXACT_QUANTIZATION_REQUIRED,
                reason="raw provider quantity is not exactly aligned to the declared quantity step",
            )
        if raw_quantity < metadata.minimum_quantity or translated < metadata.minimum_notional:
            return PlanResult(
                PlanStatus.NATIVE_MINIMUM_EXCEEDS_AUTHORITY,
                reason="provider minimums cannot represent the governed economic amount",
            )
        if translated > authorization.authorized_maximum:
            return PlanResult(
                PlanStatus.NATIVE_MINIMUM_EXCEEDS_AUTHORITY,
                reason="translated notional would exceed Watchman maximum",
            )

        capability_hash = capability.content_hash()
        metadata_hash = metadata.content_hash()
        input_hashes = [
            f"authorization:{authorization.authorization_content_hash}",
            f"capability:{capability_hash}",
            f"metadata:{metadata_hash}",
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
            native_quantity=raw_quantity,
            native_unit_type=unit,
            rounding_rule="EXACT_ONLY",
            reference_price=price_value,
            reference_price_hash=price_hash,
            translated_economic_notional=translated,
            translation_error=translated - amount,
            provider_constraints=constraints,
            idempotency_key=authorization.idempotency_key,
            adapter_planner_version=self.planner_version,
            known_at=now,
            valid_until=valid_until,
            metadata_hash=metadata_hash,
            exact_input_hashes=tuple(input_hashes),
        )
        return PlanResult(PlanStatus.TRANSLATABLE, plan=plan)
