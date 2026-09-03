from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class CapitalActionClass(str, Enum):
    """Versioned Hand-side bridge for Watchman's capital action classes."""

    RISK_INCREASING = "RISK_INCREASING"
    RISK_NEUTRAL = "RISK_NEUTRAL"
    RISK_REDUCING = "RISK_REDUCING"
    EMERGENCY_PROTECTIVE = "EMERGENCY_PROTECTIVE"


class CapabilityEnvironment(str, Enum):
    TEST = "TEST"
    DRY_RUN = "DRY_RUN"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class CapabilityQualification(str, Enum):
    DECLARED = "DECLARED"
    SYNTHETIC_QUALIFIED = "SYNTHETIC_QUALIFIED"
    SHADOW_QUALIFIED = "SHADOW_QUALIFIED"
    LIVE_QUALIFIED = "LIVE_QUALIFIED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class CapabilityKind(str, Enum):
    READ = "READ"
    ORDER_SUBMIT = "ORDER_SUBMIT"
    ORDER_CANCEL = "ORDER_CANCEL"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"
    SIGNING = "SIGNING"
    OTHER_DECLARED = "OTHER_DECLARED"


class ProviderNativeUnitModel(str, Enum):
    BASE_ASSET_QUANTITY = "BASE_ASSET_QUANTITY"
    QUOTE_NOTIONAL = "QUOTE_NOTIONAL"
    LINEAR_CONTRACT = "LINEAR_CONTRACT"
    INVERSE_CONTRACT = "INVERSE_CONTRACT"
    OTHER_DECLARED = "OTHER_DECLARED"


class IdempotencySemantics(str, Enum):
    HAND_ENFORCED = "HAND_ENFORCED"
    PROVIDER_NATIVE = "PROVIDER_NATIVE"
    HAND_AND_PROVIDER = "HAND_AND_PROVIDER"
    READ_ONLY_NOT_APPLICABLE = "READ_ONLY_NOT_APPLICABLE"


@dataclass(frozen=True)
class CapabilityPermissions:
    can_read: bool = False
    can_trade: bool = False
    can_cancel: bool = False
    can_transfer: bool = False
    can_withdraw: bool = False
    can_sign: bool = False

    def to_wire(self) -> dict[str, bool]:
        return {
            "can_read": self.can_read,
            "can_trade": self.can_trade,
            "can_cancel": self.can_cancel,
            "can_transfer": self.can_transfer,
            "can_withdraw": self.can_withdraw,
            "can_sign": self.can_sign,
        }


@dataclass(frozen=True)
class HandCapability:
    """Technical capability declaration. This object is never execution authority."""

    schema_version: str
    capability_id: str
    capability_version: str
    provider_family: str
    provider_adapter: str
    provider_adapter_version: str
    environment: CapabilityEnvironment
    capability_kind: CapabilityKind
    supported_action_classes: tuple[CapitalActionClass, ...]
    supported_economic_paths: tuple[str, ...]
    supported_instrument_families: tuple[str, ...]
    provider_native_unit_model: ProviderNativeUnitModel
    required_permission_scope: tuple[str, ...]
    permissions: CapabilityPermissions
    qualification_status: CapabilityQualification
    idempotency_semantics: IdempotencySemantics
    limits: tuple[tuple[str, str], ...]
    provenance_ref: str
    provenance_version: str
    provenance_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported HandCapability schema_version")
        required = {
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "provider_family": self.provider_family,
            "provider_adapter": self.provider_adapter,
            "provider_adapter_version": self.provider_adapter_version,
            "provenance_ref": self.provenance_ref,
            "provenance_version": self.provenance_version,
        }
        for name, value in required.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        if len(self.provenance_hash) != 64:
            raise ValueError("provenance_hash must be SHA-256 hex")
        try:
            int(self.provenance_hash, 16)
        except ValueError as exc:
            raise ValueError("provenance_hash must be SHA-256 hex") from exc
        if not self.supported_action_classes:
            raise ValueError("at least one supported action class is required")
        if not self.supported_economic_paths:
            raise ValueError("at least one supported economic path is required")
        if not self.supported_instrument_families:
            raise ValueError("at least one supported instrument family is required")
        if len(set(self.required_permission_scope)) != len(self.required_permission_scope):
            raise ValueError("required permission scopes must be unique")
        limit_names = [name for name, _ in self.limits]
        if limit_names != sorted(limit_names) or len(set(limit_names)) != len(limit_names):
            raise ValueError("capability limits must have unique sorted names")
        for name, value in self.limits:
            if not name or not value:
                raise ValueError("capability limits require non-empty names and values")

    @property
    def live_capital_qualified(self) -> bool:
        return (
            self.environment is CapabilityEnvironment.LIVE
            and self.qualification_status is CapabilityQualification.LIVE_QUALIFIED
        )

    def to_wire(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "provider_family": self.provider_family,
            "provider_adapter": self.provider_adapter,
            "provider_adapter_version": self.provider_adapter_version,
            "environment": self.environment.value,
            "capability_kind": self.capability_kind.value,
            "supported_action_classes": [value.value for value in self.supported_action_classes],
            "supported_economic_paths": list(self.supported_economic_paths),
            "supported_instrument_families": list(self.supported_instrument_families),
            "provider_native_unit_model": self.provider_native_unit_model.value,
            "required_permission_scope": list(self.required_permission_scope),
            "permissions": self.permissions.to_wire(),
            "qualification_status": self.qualification_status.value,
            "idempotency_semantics": self.idempotency_semantics.value,
            "limits": {name: value for name, value in self.limits},
            "provenance_ref": self.provenance_ref,
            "provenance_version": self.provenance_version,
            "provenance_hash": self.provenance_hash,
        }

    def content_hash(self) -> str:
        canonical = json.dumps(
            self.to_wire(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class CapabilityConflict(RuntimeError):
    pass


class CapabilityRegistry:
    """In-memory durable-contract registry semantics; registration never grants authority."""

    def __init__(self, capabilities: Iterable[HandCapability] = ()) -> None:
        self._capabilities: dict[str, HandCapability] = {}
        for capability in capabilities:
            self.register(capability)

    def register(self, capability: HandCapability) -> HandCapability:
        existing = self._capabilities.get(capability.capability_id)
        if existing is not None:
            if existing.content_hash() != capability.content_hash():
                raise CapabilityConflict(
                    "capability_id already registered with materially different content"
                )
            return existing
        self._capabilities[capability.capability_id] = capability
        return capability

    def resolve(self, capability_id: str) -> Optional[HandCapability]:
        return self._capabilities.get(capability_id)

    def all(self) -> tuple[HandCapability, ...]:
        return tuple(self._capabilities[key] for key in sorted(self._capabilities))
