from __future__ import annotations

from abc import ABC, abstractmethod

from dto.auth import TokenRequest, TokenResponse


class AuthServiceInterface(ABC):

    @abstractmethod
    def get_token(self, body: TokenRequest) -> TokenResponse:
        """Exchange username + password for an Auth0 access token."""
        ...

    @abstractmethod
    def decode_token(self, token: str) -> dict:
        """Validate a JWT and return its decoded payload."""
        ...

    @abstractmethod
    def require_permission(self, permission: str):
        """
        Return a FastAPI dependency that enforces a specific permission claim.
        Raises HTTP 403 if the token does not contain the required permission.
        """
        ...
