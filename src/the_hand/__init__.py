"""The Hand: exact, authorization-gated execution boundary."""

from .adapter import DryRunAdapter, VenueAdapter, VenueResult
from .domain import ExecutionReceipt, ExecutionRequest, ExecutionStatus, OrderSide
from .engine import (
    AuthorizationExpired,
    ContractError,
    EvidencePublicationError,
    ExecutionEngine,
    HandError,
    IdempotencyConflict,
    LiveExecutionDisabled,
    RecordedExecution,
    UntrustedAuthorization,
)
from .evidence import EvidenceDraft, EvidencePublisher
from .verification import AuthorizationProof, AuthorizationVerifier, DenyAllVerifier

__all__ = [
    "AuthorizationExpired",
    "AuthorizationProof",
    "AuthorizationVerifier",
    "ContractError",
    "DenyAllVerifier",
    "DryRunAdapter",
    "EvidenceDraft",
    "EvidencePublicationError",
    "EvidencePublisher",
    "ExecutionEngine",
    "ExecutionReceipt",
    "ExecutionRequest",
    "ExecutionStatus",
    "HandError",
    "IdempotencyConflict",
    "LiveExecutionDisabled",
    "OrderSide",
    "RecordedExecution",
    "UntrustedAuthorization",
    "VenueAdapter",
    "VenueResult",
]
