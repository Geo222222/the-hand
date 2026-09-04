from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from the_hand import (
    CapitalActionClass,
    EconomicDirection,
    ProviderExecutionPlan,
    ProviderNativeUnitModel,
    VerifiedWatchmanAuthorizedAction,
    WatchmanAuthorizedAction,
    compute_authorization_content_hash,
)
from the_hand.evidence import execution_plan_draft


NOW = datetime(2026, 9, 3, 21, 0, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def authorization() -> WatchmanAuthorizedAction:
    wire: dict[str, object] = {
        "schema_version": "1.0",
        "authorization_id": "WATCH-AUTH-EVIDENCE-001",
        "authorization_book_receipt_id": "BOOK-WATCH-EVIDENCE-001",
        "issuer": "Watchman",
        "issuer_key_id": "watchman-k1",
        "signature_ref": "watchman-signature/WATCH-AUTH-EVIDENCE-001",
        "authorization_content_hash": "0" * 64,
        "capital_structure_id": "CAPSTRUCT-EVIDENCE-001",
        "benjamin_decision_receipt_id": "BOOK-BEN-EVIDENCE-001",
        "benjamin_decision_id": "DEC-EVIDENCE-001",
        "benjamin_decision_hash": digest("decision"),
        "candidate_economic_path_id": "PATH-EVIDENCE-001",
        "candidate_economic_path_hash": digest("path"),
        "watchman_pre_action_assessment_id": "ASSESS-EVIDENCE-001",
        "watchman_pre_action_assessment_hash": digest("assessment"),
        "watchman_capital_envelope_id": "ENV-EVIDENCE-001",
        "watchman_capital_envelope_hash": digest("envelope"),
        "responsibility_ref": "RESP-EVIDENCE-001",
        "responsibility_version": "1",
        "action_class": CapitalActionClass.RISK_INCREASING.value,
        "economic_root": "BTC",
        "instrument_intent": "BTC/USD SPOT EXPOSURE",
        "economic_path_type": "SPOT_EXPOSURE_CHANGE",
        "economic_direction": EconomicDirection.INCREASE.value,
        "economic_currency": "USD",
        "authorized_economic_amount": "10000",
        "authorized_minimum": "9990",
        "authorized_maximum": "10100",
        "maximum_capital_commitment": "10100",
        "issued_at": (NOW - timedelta(seconds=2)).isoformat(),
        "valid_from": (NOW - timedelta(seconds=1)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "idempotency_key": "e" * 64,
        "permitted_capability_ids": ["CAP-SPOT-EVIDENCE"],
        "permitted_provider_families": ["SYNTHETIC"],
        "watchman_policy_version": "watchman-economic-v1",
    }
    wire["authorization_content_hash"] = compute_authorization_content_hash(wire)
    return WatchmanAuthorizedAction.from_wire(wire)


def verified() -> VerifiedWatchmanAuthorizedAction:
    action = authorization()
    return VerifiedWatchmanAuthorizedAction(
        action=action,
        correlation_id="LIFE-EVIDENCE-001",
        sequence=11,
        entry_hash=digest("book-entry"),
        producer_key_id="watchman-k1",
    )


def plan() -> ProviderExecutionPlan:
    action = authorization()
    return ProviderExecutionPlan.create(
        schema_version="1.0",
        source_watchman_authorization_id=action.authorization_id,
        source_watchman_authorization_hash=action.authorization_content_hash,
        candidate_economic_path_id=action.candidate_economic_path_id,
        candidate_economic_path_hash=action.candidate_economic_path_hash,
        capability_id="CAP-SPOT-EVIDENCE",
        capability_version="1",
        capability_hash=digest("capability"),
        provider_family="SYNTHETIC",
        provider_instrument_id="BTC-USD",
        economic_root="BTC",
        action_class=CapitalActionClass.RISK_INCREASING.value,
        action=EconomicDirection.INCREASE.value,
        economic_amount_authorized=Decimal("10000"),
        authorized_maximum=Decimal("10100"),
        native_quantity=Decimal("0.2"),
        native_unit_type=ProviderNativeUnitModel.BASE_ASSET_QUANTITY,
        rounding_rule="EXACT",
        reference_price=Decimal("50000"),
        reference_price_hash=digest("reference-price"),
        translated_economic_notional=Decimal("10000"),
        translation_error=Decimal("0"),
        translation_policy_id="HAND.EXACT_ONLY",
        translation_policy_version="1",
        translation_policy_hash=digest("translation-policy"),
        provider_constraints=(
            ("minimum_notional", "1"),
            ("minimum_quantity", "0.0001"),
            ("quantity_step", "0.0001"),
            ("tick_size", "0.01"),
        ),
        idempotency_key=action.idempotency_key,
        adapter_planner_version="hand-provider-planner-v1",
        known_at=NOW,
        valid_until=NOW + timedelta(seconds=30),
        metadata_hash=digest("metadata"),
        exact_input_hashes=(
            f"authorization:{action.authorization_content_hash}",
            f"capability:{digest('capability')}",
            f"metadata:{digest('metadata')}",
            f"reference_price:{digest('reference-price')}",
            f"translation_policy:{digest('translation-policy')}",
        ),
    )


def test_execution_plan_evidence_proves_only_the_plan_stage() -> None:
    subject = execution_plan_draft(plan(), authorization=verified())
    assert subject.event_type == "HAND.EXECUTION_PLAN"
    assert subject.event_type not in {
        "HAND.EXECUTION_SUBMITTED",
        "HAND.EXECUTION_ACCEPTED",
        "HAND.EXECUTION_FILLED",
        "HAND.SETTLEMENT",
        "HAND.RECONCILIATION",
    }
    assert subject.causation_receipt_id == "BOOK-WATCH-EVIDENCE-001"
    assert subject.evidence_receipt_ids == ("BOOK-BEN-EVIDENCE-001",)
    assert subject.correlation_id == "LIFE-EVIDENCE-001"
    assert subject.privacy_class == "CONFIDENTIAL_EVIDENCE"
    assert "PUBLIC" not in subject.visibility_scope


def test_execution_plan_payload_contains_minimum_mechanical_lineage() -> None:
    subject = execution_plan_draft(plan(), authorization=verified())
    payload = json.loads(subject.payload.decode("utf-8"))
    assert payload["source_watchman_authorization_id"] == "WATCH-AUTH-EVIDENCE-001"
    assert payload["capability_id"] == "CAP-SPOT-EVIDENCE"
    assert payload["provider_family"] == "SYNTHETIC"
    assert payload["provider_instrument_id"] == "BTC-USD"
    assert payload["economic_amount_authorized"] == "10000"
    assert payload["native_quantity"] == "0.2"
    assert payload["native_unit_type"] == "BASE_ASSET_QUANTITY"
    assert payload["metadata_hash"] == digest("metadata")
    assert payload["translation_policy_id"] == "HAND.EXACT_ONLY"
    assert payload["translation_error"] == "0"
    assert payload["adapter_planner_version"] == "hand-provider-planner-v1"
    assert payload["plan_content_hash"] == subject.subject_id


def test_execution_plan_evidence_does_not_contain_secret_or_credential_fields() -> None:
    payload = json.loads(execution_plan_draft(plan(), authorization=verified()).payload.decode("utf-8"))
    serialized_keys = " ".join(str(key).lower() for key in payload.keys())
    for forbidden in (
        "api_key",
        "access_token",
        "private_key",
        "credential",
        "withdrawal_secret",
        "signing_material",
    ):
        assert forbidden not in serialized_keys


def test_execution_plan_evidence_rejects_mismatched_watchman_lineage() -> None:
    original = plan()
    mismatched = ProviderExecutionPlan.create(
        **{
            key: value
            for key, value in original.__dict__.items()
            if key != "plan_content_hash"
        }
        | {"source_watchman_authorization_id": "WATCH-AUTH-OTHER"}
    )
    with pytest.raises(ValueError, match="authorization identity"):
        execution_plan_draft(mismatched, authorization=verified())
