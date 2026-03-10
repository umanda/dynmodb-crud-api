from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import (
    AUTH0_ALGORITHMS,
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_DOMAIN,
    AUTH0_REALM,
)
from dto.auth import TokenRequest, TokenResponse
from auth.interfaces import AuthServiceInterface

# ── Module-level singletons ───────────────────────────────────────────────────
_http_bearer = HTTPBearer()
_jwks_cache: dict = {}

TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
JWKS_URL  = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"


class Auth0Service(AuthServiceInterface):
    """
    Concrete Auth0 implementation.

    Responsibilities:
      - Fetch and cache Auth0 JWKS public keys
      - Validate RS256 JWTs (signature, audience, issuer, expiry)
      - Exchange username/password for an access token (Resource Owner Password flow)
      - Provide FastAPI-injectable permission guards
    """

    # ── JWKS cache ────────────────────────────────────────────────────────────

    def _get_jwks(self) -> dict:
        global _jwks_cache
        if not _jwks_cache:
            resp = httpx.get(JWKS_URL, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
        return _jwks_cache

    # ── Token decode / validation ─────────────────────────────────────────────

    def decode_token(self, token: str) -> dict:
        try:
            jwks = self._get_jwks()
            header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key.get("kid") == header.get("kid"):
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n":   key["n"],
                        "e":   key["e"],
                    }
                    break

            if not rsa_key:
                raise HTTPException(status_code=401, detail="No matching public key found.")

            return jwt.decode(
                token,
                rsa_key,
                algorithms=AUTH0_ALGORITHMS,
                audience=AUTH0_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
        except JWTError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Token validation failed: {exc}")

    # ── FastAPI dependency: extract & validate bearer token ───────────────────

    def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(_http_bearer),
    ) -> dict:
        """Inject as a FastAPI dependency to decode the Bearer token."""
        return self.decode_token(credentials.credentials)

    # ── FastAPI dependency factory: permission guard ──────────────────────────

    def require_permission(self, permission: str):
        """
        Returns a FastAPI dependency that enforces a specific permission.

        Usage in router:
            dependencies=[Depends(auth_service.require_permission("read:channel"))]
        """
        def _guard(user: dict = Depends(self.get_current_user)) -> dict:
            granted: list = user.get("permissions", [])
            if permission not in granted:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied. Required: '{permission}'. Granted: {granted}",
                )
            return user

        # Give each guard a unique name so FastAPI registers them separately
        _guard.__name__ = f"require_{permission.replace(':', '_')}"
        return _guard

    # ── Token endpoint logic ──────────────────────────────────────────────────

    def get_token(self, body: TokenRequest) -> TokenResponse:
        """Call Auth0 Resource Owner Password flow and return the access token."""
        resp = httpx.post(
            TOKEN_URL,
            json={
                "grant_type": "password",
                "username": body.username,
                "password": body.password,
                "realm": AUTH0_REALM,
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "audience": AUTH0_AUDIENCE,
                "scope": "openid profile email",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error_description", resp.text)
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        data = resp.json()
        return TokenResponse(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 86400),
            scope=data.get("scope", ""),
        )
