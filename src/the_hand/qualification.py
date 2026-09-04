from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .capability import HandCapability
from .planning import PlanResult, PlanStatus, ProviderExecutionPlanner, ReferencePrice, TranslationPolicy
from .authorization import WatchmanAuthorizedAction
from .units import ProviderInstrumentMetadata
from datetime import datetime


class QualificationScope(str, Enum):
    SYNTHETIC_MECHANISM = "SYNTHETIC_MECHANISM"
    SHADOW_MECHANISM = "SHADOW_MECHANISM"
    LIVE_MECHANISM = "LIVE_MECHANISM"


@dataclass(frozen=True)
class InstrumentQualification:
    """Evidence that one exact capability/metadata pair passed a declared qualification scope.

    Synthetic qualification proves only deterministic mechanism behavior. It is
    not provider availability, fill quality, profitability, or live-capital authority.
    """

    schema_version: str
    qualification_id: str
    qualification_version: str
    scope: QualificationScope
    capability_id: str
    capability_version: str
    capability_hash: str
    provider_family: str
    provider_instrument_id: str
    metadata_hash: str
    provenance_ref: str
    provenance_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported InstrumentQualification schema_version")
        for field, value in (
            ("qualification_id", self.qualification_id),
            ("qualification_version", self.qualification_version),
            ("capability_id", self.capability_id),
            ("capability_version", self.capability_version),
            ("provider_family", self.provider_family),
            ("provider_instrument_id", self.provider_instrument_id),
            ("provenance_ref", self.provenance_ref),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field} is required")
        for field, value in (
            ("capability_hash", self.capability_hash),
            ("metadata_hash", self.metadata_hash),
            ("provenance_hash", self.provenance_hash),
        ):
            if not re.fullmatch(r"[a-f0-9]{64}", value):
                raise ValueError(f"{field} must be lowercase SHA-256 hex")

    @classmethod
    def bind(
        cls,
        *,
        qualification_id: str,
        qualification_version: str,
        scope: QualificationScope,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        provenance_ref: str,
        provenance_hash: str,
    ) -> "InstrumentQualification":
        if capability.provider_family != metadata.provider_family:
            raise ValueError("capability and metadata provider families differ")
        return cls(
            schema_version="1.0",
            qualification_id=qualification_id,
            qualification_version=qualification_version,
            scope=scope,
            capability_id=capability.capability_id,
            capability_version=capability.capability_version,
            capability_hash=capability.content_hash(),
            provider_family=metadata.provider_family,
            provider_instrument_id=metadata.provider_instrument_id,
            metadata_hash=metadata.content_hash(),
            provenance_ref=provenance_ref,
            provenance_hash=provenance_hash,
        )

    def matches(self, capability: HandCapability, metadata: ProviderInstrumentMetadata) -> bool:
        return (
            self.capability_id == capability.capability_id
            and self.capability_version == capability.capability_version
            and self.capability_hash == capability.content_hash()
            and self.provider_family == metadata.provider_family
            and self.provider_instrument_id == metadata.provider_instrument_id
            and self.metadata_hash == metadata.content_hash()
        )

    def to_wire(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "qualification_id": self.qualification_id,
            "qualification_version": self.qualification_version,
            "scope": self.scope.value,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "capability_hash": self.capability_hash,
            "provider_family": self.provider_family,
            "provider_instrument_id": self.provider_instrument_id,
            "metadata_hash": self.metadata_hash,
            "provenance_ref": self.provenance_ref,
            "provenance_hash": self.provenance_hash,
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


class QualificationConflict(RuntimeError):
    pass


class InstrumentQualificationRegistry:
    """Registry of exact capability/metadata qualification bindings."""

    def __init__(self, qualifications: Iterable[InstrumentQualification] = ()) -> None:
        self._by_id: dict[str, InstrumentQualification] = {}
        for qualification in qualifications:
            self.register(qualification)

    def register(self, qualification: InstrumentQualification) -> InstrumentQualification:
        existing = self._by_id.get(qualification.qualification_id)
        if existing is not None:
            if existing.content_hash() != qualification.content_hash():
                raise QualificationConflict(
                    "qualification_id already belongs to materially different qualification content"
                )
            return existing
        self._by_id[qualification.qualification_id] = qualification
        return qualification

    def resolve(
        self,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        *,
        required_scope: QualificationScope,
    ) -> InstrumentQualification | None:
        for qualification in self._by_id.values():
            if qualification.scope is required_scope and qualification.matches(capability, metadata):
                return qualification
        return None


class QualifiedProviderExecutionPlanner:
    """Planning gate requiring exact mechanism qualification before translation."""

    def __init__(
        self,
        registry: InstrumentQualificationRegistry,
        *,
        required_scope: QualificationScope = QualificationScope.SYNTHETIC_MECHANISM,
        planner: ProviderExecutionPlanner | None = None,
    ) -> None:
        self._registry = registry
        self._required_scope = required_scope
        self._planner = planner or ProviderExecutionPlanner()

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
        qualification = self._registry.resolve(
            capability, metadata, required_scope=self._required_scope
        )
        if qualification is None:
            return PlanResult(
                PlanStatus.UNIT_METADATA_UNAVAILABLE,
                reason=(
                    "capability/provider metadata pair has not earned the required exact "
                    f"{self._required_scope.value} qualification"
                ),
            )
        return self._planner.plan(
            authorization,
            capability,
            metadata,
            reference_price=reference_price,
            policy=policy,
            now=now,
        )
