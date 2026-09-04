from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from the_hand import (
    AssetClass,
    CapitalActionClass,
    CapabilityEnvironment,
    CapabilityKind,
    CapabilityPermissions,
    CapabilityQualification,
    ContractType,
    ContractValueConvention,
    DurablePlanReplayStore,
    EconomicDirection,
    HandBookEvidencePublisher,
    HandBookOutbox,
    HandBookSigner,
    HandCapability,
    IdempotencySemantics,
    InstrumentFamily,
    InstrumentQualification,
    InstrumentQualificationRegistry,
    PlanReplayConflict,
    PlanStatus,
    ProviderExecutionPlanner,
    ProviderInstrumentMetadata,
    ProviderNativeUnitModel,
    QualificationScope,
    QualifiedProviderExecutionPlanner,
    QuantizationRule,
    ReferencePrice,
    ReplaySafeProviderExecutionPlanner,
    TranslationPolicy,
    VerifiedWatchmanAuthorizedAction,
    WatchmanAuthorizedAction,
    compute_authorization_content_hash,
    execution_plan_draft,
)


NOW = datetime(2026, 9, 3, 22, 0, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def authorization_wire(**updates: object) -> dict[str, object]:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": "WATCH-AUTH-REPLAY-001",
        "authorization_book_receipt_id": "BOOK-WATCH-REPLAY-001",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": "watchman-signature/WATCH-AUTH-REPLAY-001",
        "authorization_content_hash": "0" * 64,
        "capital_structure_id": "CAPSTRUCT-REPLAY-001",
        "benjamin_decision_receipt_id": "BOOK-BEN-REPLAY-001",
        "benjamin_decision_id": "DEC-REPLAY-001",
        "benjamin_decision_hash": digest("decision-replay"),
        "candidate_economic_path_id": "PATH-REPLAY-001",
        "candidate_economic_path_hash": digest("path-replay"),
        "watchman_pre_action_assessment_id": "ASSESS-REPLAY-001",
        "watchman_pre_action_assessment_hash": digest("assessment-replay"),
        "watchman_capital_envelope_id": "ENV-REPLAY-001",
        "watchman_capital_envelope_hash": digest("envelope-replay"),
        "responsibility_ref": "RESP-REPLAY-001",
        "responsibility_version": "1",
        "action_class": CapitalActionClass.RISK_INCREASING.value,
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
    wire.update(updates)
    wire["authorization_content_hash"] = "0" * 64
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return wire


def authorization(**updates: object) -> WatchmanAuthorizedAction:
    return WatchmanAuthorizedAction.from_wire(authorization_wire(**updates))


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
        "provenance_ref": "synthetic://capability/spot",
        "provenance_version": "1",
        "provenance_hash": digest("capability-spot"),
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
        "source_ref": "synthetic://metadata/BTC-USD",
        "provenance_hash": digest("metadata-spot"),
        "known_at": NOW - timedelta(seconds=1),
        "effective_at": NOW - timedelta(seconds=1),
        "valid_until": NOW + timedelta(minutes=10),
    }
    values.update(updates)
    return ProviderInstrumentMetadata(**values)


def price(**updates: object) -> ReferencePrice:
    values = {
        "value": Decimal("50000"),
        "unit": "USD_PER_BTC",
        "source_ref": "synthetic://price/BTC-USD/1",
        "known_at": NOW - timedelta(milliseconds=100),
        "valid_until": NOW + timedelta(seconds=30),
    }
    values.update(updates)
    return ReferencePrice(**values)


def exact_policy(**updates: object) -> TranslationPolicy:
    values = {
        "policy_id": "HAND.EXACT_ONLY",
        "version": "1",
        "quantization_rule": QuantizationRule.EXACT,
        "max_absolute_error": Decimal("0"),
        "max_relative_error": Decimal("0"),
        "allow_lower_quantity": False,
        "allow_upward_translation": False,
    }
    values.update(updates)
    return TranslationPolicy(**values)


def qualified_planner(cap: HandCapability, meta: ProviderInstrumentMetadata) -> QualifiedProviderExecutionPlanner:
    qualification = InstrumentQualification.bind(
        qualification_id="QUAL-REPLAY-001",
        qualification_version="1",
        scope=QualificationScope.SYNTHETIC_MECHANISM,
        capability=cap,
        metadata=meta,
        provenance_ref="synthetic://qualification/replay",
        provenance_hash=digest("qualification-replay"),
    )
    registry = InstrumentQualificationRegistry([qualification])
    return QualifiedProviderExecutionPlanner(registry)


def replay_planner(root: Path, cap: HandCapability, meta: ProviderInstrumentMetadata) -> ReplaySafeProviderExecutionPlanner:
    return ReplaySafeProviderExecutionPlanner(
        qualified_planner(cap, meta), DurablePlanReplayStore(root)
    )


def verified(action: WatchmanAuthorizedAction) -> VerifiedWatchmanAuthorizedAction:
    return VerifiedWatchmanAuthorizedAction(
        action=action,
        correlation_id="LIFE-REPLAY-001",
        sequence=17,
        entry_hash=digest("book-entry-replay"),
        producer_key_id="watchman-k1",
    )


def test_same_immutable_inputs_ignore_invocation_clock_for_plan_and_evidence() -> None:
    planner = ProviderExecutionPlanner()
    action = authorization()
    cap = capability()
    meta = metadata()
    ref = price()
    policy = exact_policy()

    first = planner.plan(action, cap, meta, reference_price=ref, policy=policy, now=NOW)
    second = planner.plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=policy,
        now=NOW + timedelta(seconds=5),
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.to_wire() == second.plan.to_wire()
    assert first.plan.plan_content_hash == second.plan.plan_content_hash
    assert first.plan.native_quantity == second.plan.native_quantity
    assert first.plan.translation_error == second.plan.translation_error
    assert first.plan.known_at == ref.known_at

    first_evidence = execution_plan_draft(first.plan, authorization=verified(action))
    second_evidence = execution_plan_draft(second.plan, authorization=verified(action))
    assert first_evidence.payload == second_evidence.payload
    assert first_evidence == second_evidence


def test_restart_reconstructs_same_plan_without_duplicate_semantic_record(tmp_path: Path) -> None:
    action = authorization()
    cap = capability()
    meta = metadata()
    ref = price()
    policy = exact_policy()

    first_boundary = replay_planner(tmp_path, cap, meta)
    first = first_boundary.plan(
        action, cap, meta, reference_price=ref, policy=policy, now=NOW
    )
    assert first.plan is not None

    restarted_boundary = replay_planner(tmp_path, cap, meta)
    second = restarted_boundary.plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=policy,
        now=NOW + timedelta(seconds=1),
    )
    assert second.plan is not None
    assert second.plan.to_wire() == first.plan.to_wire()
    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1


def test_conflicting_idempotency_key_with_different_price_evidence_fails_closed(tmp_path: Path) -> None:
    action = authorization()
    cap = capability()
    meta = metadata()
    subject = replay_planner(tmp_path, cap, meta)
    subject.plan(
        action,
        cap,
        meta,
        reference_price=price(),
        policy=exact_policy(),
        now=NOW,
    )
    with pytest.raises(PlanReplayConflict):
        subject.plan(
            action,
            cap,
            meta,
            reference_price=price(source_ref="synthetic://price/BTC-USD/2"),
            policy=exact_policy(),
            now=NOW + timedelta(seconds=1),
        )


def test_changed_watchman_authorization_changes_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(
        authorization(), capability(), metadata(), reference_price=price(), now=NOW
    )
    second = planner.plan_exact(
        authorization(
            authorization_id="WATCH-AUTH-REPLAY-002",
            authorization_book_receipt_id="BOOK-WATCH-REPLAY-002",
            idempotency_key="b" * 64,
        ),
        capability(),
        metadata(),
        reference_price=price(),
        now=NOW,
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_changed_candidate_economic_path_changes_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(
        authorization(), capability(), metadata(), reference_price=price(), now=NOW
    )
    second = planner.plan_exact(
        authorization(
            candidate_economic_path_id="PATH-REPLAY-002",
            candidate_economic_path_hash=digest("path-replay-2"),
            idempotency_key="c" * 64,
        ),
        capability(),
        metadata(),
        reference_price=price(),
        now=NOW,
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_changed_capability_version_or_hash_changes_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(
        authorization(), capability(), metadata(), reference_price=price(), now=NOW
    )
    second = planner.plan_exact(
        authorization(),
        capability(
            capability_version="2",
            provider_adapter_version="2",
            provenance_hash=digest("capability-spot-v2"),
        ),
        metadata(),
        reference_price=price(),
        now=NOW,
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.capability_hash != second.plan.capability_hash
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def linear_capability() -> HandCapability:
    return capability(
        capability_id="CAP-LINEAR",
        provider_adapter="synthetic-linear",
        supported_economic_paths=("LINEAR_EXPOSURE_CHANGE",),
        supported_instrument_families=("DERIVATIVE",),
        provider_native_unit_model=ProviderNativeUnitModel.LINEAR_CONTRACT,
        provenance_hash=digest("capability-linear"),
    )


def linear_metadata(multiplier: str) -> ProviderInstrumentMetadata:
    return metadata(
        provider_instrument_id="BTC-USD-LINEAR",
        instrument_family=InstrumentFamily.DERIVATIVE,
        settlement_asset="USD",
        native_quantity_unit=ProviderNativeUnitModel.LINEAR_CONTRACT,
        native_unit_label="CONTRACT",
        contract_type=ContractType.LINEAR,
        contract_multiplier=Decimal(multiplier),
        contract_value_convention=ContractValueConvention.BASE_ASSET_PER_CONTRACT,
        quantity_step=Decimal("1"),
        minimum_quantity=Decimal("1"),
        quantity_precision=0,
        lot_rule="WHOLE_CONTRACT",
        metadata_version="linear-1",
        source_ref="synthetic://metadata/BTC-USD-LINEAR",
        provenance_hash=digest("metadata-linear"),
    )


def linear_authorization() -> WatchmanAuthorizedAction:
    return authorization(
        instrument_intent="BTC/USD LINEAR DERIVATIVE EXPOSURE",
        economic_path_type="LINEAR_EXPOSURE_CHANGE",
        permitted_capability_ids=["CAP-LINEAR"],
        idempotency_key="d" * 64,
    )


def test_changed_contract_multiplier_changes_native_quantity_and_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    action = linear_authorization()
    cap = linear_capability()
    first = planner.plan_exact(
        action, cap, linear_metadata("0.001"), reference_price=price(), now=NOW
    )
    second = planner.plan_exact(
        action, cap, linear_metadata("0.002"), reference_price=price(), now=NOW
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.native_quantity == Decimal("200")
    assert second.plan.native_quantity == Decimal("100")
    assert first.plan.metadata_hash != second.plan.metadata_hash
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_changed_reference_price_evidence_changes_identity_even_when_value_is_same() -> None:
    planner = ProviderExecutionPlanner()
    first = planner.plan_exact(
        authorization(), capability(), metadata(), reference_price=price(), now=NOW
    )
    second = planner.plan_exact(
        authorization(),
        capability(),
        metadata(),
        reference_price=price(source_ref="synthetic://price/BTC-USD/other-evidence"),
        now=NOW,
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.native_quantity == second.plan.native_quantity
    assert first.plan.reference_price_hash != second.plan.reference_price_hash
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_changed_translation_policy_version_changes_plan_identity() -> None:
    planner = ProviderExecutionPlanner()
    action = authorization()
    cap = capability()
    meta = metadata()
    ref = price()
    first = planner.plan(
        action, cap, meta, reference_price=ref, policy=exact_policy(), now=NOW
    )
    second = planner.plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=exact_policy(version="2"),
        now=NOW,
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.translation_policy_hash != second.plan.translation_policy_hash
    assert first.plan.plan_content_hash != second.plan.plan_content_hash


def test_replay_record_cannot_resurrect_stale_or_expired_inputs(tmp_path: Path) -> None:
    action = authorization()
    cap = capability()
    meta = metadata()
    ref = price()
    policy = exact_policy()
    subject = replay_planner(tmp_path, cap, meta)

    original = subject.plan(
        action, cap, meta, reference_price=ref, policy=policy, now=NOW
    )
    assert original.plan is not None

    stale = replay_planner(tmp_path, cap, meta).plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=policy,
        now=NOW + timedelta(seconds=31),
    )
    assert stale.status is PlanStatus.REFERENCE_PRICE_STALE
    assert stale.plan is None

    expired = replay_planner(tmp_path, cap, meta).plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=policy,
        now=action.expires_at,
    )
    assert expired.status is PlanStatus.AUTHORIZATION_EXPIRED
    assert expired.plan is None


def test_execution_plan_evidence_and_book_receipt_are_idempotent_after_reconstruction(tmp_path: Path) -> None:
    action = authorization()
    cap = capability()
    meta = metadata()
    ref = price()
    policy = exact_policy()
    first = ProviderExecutionPlanner().plan(
        action, cap, meta, reference_price=ref, policy=policy, now=NOW
    )
    second = ProviderExecutionPlanner().plan(
        action,
        cap,
        meta,
        reference_price=ref,
        policy=policy,
        now=NOW + timedelta(seconds=2),
    )
    assert first.plan is not None and second.plan is not None

    first_draft = execution_plan_draft(first.plan, authorization=verified(action))
    second_draft = execution_plan_draft(second.plan, authorization=verified(action))
    assert first_draft == second_draft

    signer = HandBookSigner(key_id="hand-test-k1", private_key=Ed25519PrivateKey.generate())
    outbox = HandBookOutbox(tmp_path / "book")
    publisher = HandBookEvidencePublisher(signer, outbox)
    first_receipt = publisher.publish(first_draft)
    second_receipt = publisher.publish(second_draft)
    assert first_receipt == second_receipt
    assert outbox.pending_receipt_ids() == (first_receipt,)


def test_replay_boundary_has_no_execution_or_submission_authority(tmp_path: Path) -> None:
    cap = capability()
    meta = metadata()
    boundary = replay_planner(tmp_path, cap, meta)
    result = boundary.plan(
        authorization(),
        cap,
        meta,
        reference_price=price(),
        policy=exact_policy(),
        now=NOW,
    )
    assert result.plan is not None
    assert not hasattr(boundary, "execute")
    assert not hasattr(boundary, "submit")


@pytest.mark.parametrize(
    "forbidden",
    [
        "quantity",
        "native_quantity",
        "contract_count",
        "lot_size",
        "step_size",
        "provider_order_parameters",
    ],
)
def test_provider_native_fields_cannot_enter_watchman_economic_authority(forbidden: str) -> None:
    wire = authorization_wire()
    wire[forbidden] = "1"
    with pytest.raises(ValueError, match="authorization fields mismatch"):
        WatchmanAuthorizedAction.from_wire(wire)


def test_watchman_authority_exposes_only_candidate_path_identity_not_provider_mechanics() -> None:
    fields = set(WatchmanAuthorizedAction.__dataclass_fields__)
    provider_native = {
        "quantity",
        "native_quantity",
        "contract_count",
        "lot_size",
        "step_size",
        "provider_order_parameters",
    }
    assert fields.isdisjoint(provider_native)
    assert {name for name in fields if name.startswith("candidate_economic_path_")} == {
        "candidate_economic_path_id",
        "candidate_economic_path_hash",
    }
