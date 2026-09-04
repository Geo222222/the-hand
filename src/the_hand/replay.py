from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .authorization import WatchmanAuthorizedAction
from .capability import HandCapability
from .planning import PlanResult, ProviderExecutionPlan, ReferencePrice, TranslationPolicy
from .units import ProviderInstrumentMetadata


class PlanReplayConflict(RuntimeError):
    """The same idempotency key was reused for materially different plan inputs."""


@dataclass(frozen=True)
class PlanReplayRecord:
    schema_version: str
    idempotency_key: str
    immutable_input_hash: str
    plan_content_hash: str

    def to_wire(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "idempotency_key": self.idempotency_key,
            "immutable_input_hash": self.immutable_input_hash,
            "plan_content_hash": self.plan_content_hash,
        }


class PlanTranslator(Protocol):
    """Provider-neutral planning surface. It may translate, but never execute."""

    def plan(
        self,
        authorization: WatchmanAuthorizedAction,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        *,
        reference_price: ReferencePrice | None,
        policy: TranslationPolicy,
        now: object,
    ) -> PlanResult: ...


def _atomic_json(path: Path, value: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


class DurablePlanReplayStore:
    """Durable idempotency binding for content-addressed provider plans.

    The store never supplies a cached plan. Callers must reconstruct the plan
    from the current immutable authorization/metadata/price/policy inputs first.
    This keeps expiry and freshness checks live on every replay while preserving
    the semantic binding of an idempotency key across process restarts.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, idempotency_key: str) -> Path:
        return self.root / f"{idempotency_key}.json"

    def bind(self, plan: ProviderExecutionPlan) -> PlanReplayRecord:
        record = PlanReplayRecord(
            schema_version="1.0",
            idempotency_key=plan.idempotency_key,
            immutable_input_hash=plan.immutable_input_hash(),
            plan_content_hash=plan.plan_content_hash,
        )
        path = self._path(plan.idempotency_key)
        if path.is_file():
            try:
                existing_wire = json.loads(path.read_text(encoding="utf-8"))
                existing = PlanReplayRecord(**existing_wire)
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise PlanReplayConflict("stored plan replay record is malformed") from exc
            if existing != record:
                raise PlanReplayConflict(
                    "idempotency key already belongs to materially different immutable plan inputs"
                )
            return existing
        _atomic_json(path, record.to_wire())
        return record


class ReplaySafeProviderExecutionPlanner:
    """Canonical H1H planning boundary: reconstruct, validate, then bind replay identity.

    The wrapped planner is always invoked first. A prior replay record therefore
    cannot resurrect expired Watchman authority, stale metadata, or a stale
    reference price. Successful plans are bound durably by idempotency key.
    No adapter or provider mutation surface exists here.
    """

    def __init__(self, planner: PlanTranslator, replay_store: DurablePlanReplayStore) -> None:
        self._planner = planner
        self._replay_store = replay_store

    def plan(
        self,
        authorization: WatchmanAuthorizedAction,
        capability: HandCapability,
        metadata: ProviderInstrumentMetadata,
        *,
        reference_price: ReferencePrice | None,
        policy: TranslationPolicy,
        now: object,
    ) -> PlanResult:
        result = self._planner.plan(
            authorization,
            capability,
            metadata,
            reference_price=reference_price,
            policy=policy,
            now=now,
        )
        if result.plan is not None:
            self._replay_store.bind(result.plan)
        return result
