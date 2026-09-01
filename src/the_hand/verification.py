from __future__ import annotations

from typing import Protocol

from .domain import ExecutionRequest


class AuthorizationVerifier(Protocol):
    """Trust boundary for proving an authorization originated from Benjamin."""

    def verify(self, request: ExecutionRequest) -> bool: ...


class DenyAllVerifier:
    """Safe default: nothing executes until a verifier is explicitly configured."""

    def verify(self, request: ExecutionRequest) -> bool:
        return False
