from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth import service as auth_service
from src.auth.exceptions import PermissionDeniedError

_http_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_http_bearer),
) -> dict:
    """FastAPI dependency — decodes & validates the Bearer token."""
    return auth_service.decode_token(credentials.credentials)


def require_permission(permission: str):
    """
    Returns a FastAPI dependency that enforces a specific Auth0 permission.

    Usage:
        @router.get("/channels", dependencies=[Depends(require_permission("read:channel"))])
    """

    def _check(user: dict = Depends(get_current_user)):
        granted: list = user.get("permissions", [])
        if permission not in granted:
            raise PermissionDeniedError(required=permission, granted=granted)
        return user

    _check.__name__ = f"require_{permission.replace(':', '_')}"
    return _check
