"""The Hand: exact, authorization-gated execution boundary."""

from .adapter import DryRunAdapter, VenueAdapter, VenueResult
from .domain import ExecutionReceipt, ExecutionRequest, ExecutionStatus, OrderSide
from .engine import (
    AuthorizationExpired,
    ContractError,
    ExecutionEngine,
    HandError,
    IdempotencyConflict,
    LiveExecutionDisabled,
    UntrustedAuthorization,
)
from .verification import AuthorizationVerifier, DenyAllVerifier

__all__ = [
    "AuthorizationExpired",
    "AuthorizationVerifier",
    "ContractError",
    "DenyAllVerifier",
    "DryRunAdapter",
    "ExecutionEngine",
    "ExecutionReceipt",
    "ExecutionRequest",
    "ExecutionStatus",
    "HandError",
    "IdempotencyConflict",
    "LiveExecutionDisabled",
    "OrderSide",
    "UntrustedAuthorization",
    "VenueAdapter",
    "VenueResult",
]
