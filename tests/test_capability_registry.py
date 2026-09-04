from __future__ import annotations

import hashlib

import pytest

from the_hand import (
    CapitalActionClass,
    CapabilityConflict,
    CapabilityEnvironment,
    CapabilityKind,
    CapabilityPermissions,
    CapabilityQualification,
    CapabilityRegistry,
    HandCapability,
    IdempotencySemantics,
    ProviderNativeUnitModel,
)


def capability(**updates: object) -> HandCapability:
    values = {
        "schema_version": "1.0",
        "capability_id": "CAP-COINBASE-SPOT-ORDER-DRYRUN",
        "capability_version": "1",
        "provider_family": "COINBASE",
        "provider_adapter": "coinbase-order-adapter",
        "provider_adapter_version": "0.0-not-live",
        "environment": CapabilityEnvironment.DRY_RUN,
        "capability_kind": CapabilityKind.ORDER_SUBMIT,
        "supported_action_classes": (
            CapitalActionClass.RISK_INCREASING,
            CapitalActionClass.RISK_NEUTRAL,
            CapitalActionClass.RISK_REDUCING,
            CapitalActionClass.EMERGENCY_PROTECTIVE,
        ),
        "supported_economic_paths": ("SPOT_EXPOSURE_CHANGE",),
        "supported_instrument_families": ("SPOT",),
        "provider_native_unit_model": ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        "required_permission_scope": ("orders:create",),
        "permissions": CapabilityPermissions(can_trade=True),
        "qualification_status": CapabilityQualification.DECLARED,
        "idempotency_semantics": IdempotencySemantics.HAND_ENFORCED,
        "limits": (("max_native_quantity", "1.0"),),
        "provenance_ref": "repo://the-hand/adapters/coinbase",
        "provenance_version": "unimplemented",
        "provenance_hash": hashlib.sha256(b"synthetic capability provenance").hexdigest(),
    }
    values.update(updates)
    return HandCapability(**values)


def test_capability_exists_without_authority_or_live_qualification() -> None:
    subject = capability()
    assert subject.permissions.can_trade is True
    assert subject.environment is CapabilityEnvironment.DRY_RUN
    assert subject.qualification_status is CapabilityQualification.DECLARED
    assert subject.live_capital_qualified is False


def test_live_environment_alone_does_not_mean_live_capital_qualified() -> None:
    subject = capability(environment=CapabilityEnvironment.LIVE)
    assert subject.live_capital_qualified is False


def test_capability_hash_changes_with_material_version_or_limits() -> None:
    first = capability()
    assert first.content_hash() == capability().content_hash()
    assert first.content_hash() != capability(capability_version="2").content_hash()
    assert first.content_hash() != capability(limits=(("max_native_quantity", "2.0"),)).content_hash()


def test_registry_allows_exact_replay_but_rejects_id_redefinition() -> None:
    subject = CapabilityRegistry()
    first = subject.register(capability())
    assert subject.register(capability()) is first
    with pytest.raises(CapabilityConflict):
        subject.register(capability(provider_adapter_version="different"))


def test_capital_action_bridge_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        CapitalActionClass("RISKY_BECAUSE_CALLER_SAYS_SO")


def test_capability_limits_require_canonical_order() -> None:
    with pytest.raises(ValueError, match="sorted"):
        capability(limits=(("z", "1"), ("a", "2")))
