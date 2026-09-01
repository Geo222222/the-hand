from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import ExecutionRequest


@dataclass(frozen=True, slots=True)
class AuthorizationProof:
    """Proof context returned after independently verifying Benjamin evidence in The Book."""

    book_receipt_id: str
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.book_receipt_id or not self.correlation_id:
            raise ValueError("Book authorization receipt and correlation_id are required")


class AuthorizationVerifier(Protocol):
    """Resolve a request to trusted BENJAMIN.AUTHORIZATION evidence, or deny it."""

    def verify(self, request: ExecutionRequest) -> AuthorizationProof | None: ...


class DenyAllVerifier:
    """Safe default: nothing executes until a Book-aware verifier is explicitly configured."""

    def verify(self, request: ExecutionRequest) -> AuthorizationProof | None:
        return None
