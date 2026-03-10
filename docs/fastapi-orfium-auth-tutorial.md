# Tutorial: Add fastapi-orfium-auth to This API

This guide shows how to integrate `fastapi-orfium-auth` into this project while keeping the current endpoint design.

Important context:
- This package was designed around Orfium SSO Facade conventions.
- Your app currently validates Auth0 tokens directly in `src/auth/service.py`.
- Integration can work, but should be done behind a feature flag so rollback is easy.

---

## 1. What will change

Current flow:
- `src/auth/dependencies.py` reads Bearer token with FastAPI `HTTPBearer`.
- `src/auth/service.py` fetches JWKS and validates JWT.
- `require_permission` checks `permissions` claim.

Target flow:
- `src/auth/dependencies.py` uses `fastapi_orfium_auth.JWTBearer` as dependency.
- Permission checks are delegated to that package.
- Existing routes can stay unchanged if `require_permission(...)` keeps same function signature.

---

## 2. Install dependency

Add package to requirements:

```txt
# requirements.txt
fastapi-orfium-auth==5.0.1
```

Rebuild:

```bash
docker compose build
docker compose up -d
```

---

## 3. Add feature flag and auth settings

Update `src/auth/config.py`:

```python
from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    AUTH0_DOMAIN: str = "dev-umanda.us.auth0.com"
    AUTH0_AUDIENCE: str = "https://api.acme.test"
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""
    AUTH0_REALM: str = "Username-Password-Authentication"

    # New: opt-in switch for package migration
    AUTH_USE_ORFIUM_AUTH: bool = False

    # New: package configuration
    AUTH_SSO_FACADE_DOMAIN: str = "https://dev-umanda.us.auth0.com"
    AUTH_SSO_ALGORITHM: str = "RS256"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def issuer(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/"
```

And in `.env`:

```env
AUTH_USE_ORFIUM_AUTH=true
AUTH_SSO_FACADE_DOMAIN=https://dev-umanda.us.auth0.com
AUTH_SSO_ALGORITHM=RS256
```

---

## 4. Replace dependency internals (keep same API)

Update `src/auth/dependencies.py` so routes do not need changes.

```python
from typing import Any

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth import service as auth_service
from src.auth.config import auth_settings
from src.auth.exceptions import PermissionDeniedError

_http_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_http_bearer),
) -> dict[str, Any]:
    return auth_service.decode_token(credentials.credentials)


def _legacy_require_permission(permission: str):
    def _check(user: dict = Depends(get_current_user)):
        granted: list = user.get("permissions", [])
        if permission not in granted:
            raise PermissionDeniedError(required=permission, granted=granted)
        return user

    _check.__name__ = f"require_{permission.replace(':', '_')}"
    return _check


def _orfium_require_permission(permission: str):
    from fastapi_orfium_auth.jwt_bearer import JWTBearer

    bearer = JWTBearer(
        sso_facade_domain=auth_settings.AUTH_SSO_FACADE_DOMAIN,
        algorithm=auth_settings.AUTH_SSO_ALGORITHM,
        audience=auth_settings.AUTH0_AUDIENCE,
        issuer=auth_settings.issuer,
        allowed_permissions=[permission],
        auto_error=True,
        use_caching=True,
    )

    async def _check(user=Depends(bearer)):
        # Keep return shape compatible with legacy code.
        return {
            "sub": user.user_id,
            "org_id": user.org_id,
            "permissions": user.permissions,
        }

    _check.__name__ = f"require_{permission.replace(':', '_')}"
    return _check


def require_permission(permission: str):
    if auth_settings.AUTH_USE_ORFIUM_AUTH:
        return _orfium_require_permission(permission)
    return _legacy_require_permission(permission)
```

Why this design:
- `src/channels/router.py` remains unchanged.
- You can toggle old/new behavior via environment variable.
- Rollback is immediate by setting `AUTH_USE_ORFIUM_AUTH=false`.

---

## 5. Keep or remove legacy validator

During migration, keep `src/auth/service.py` as fallback.
After successful rollout, you may remove legacy token decode logic if no longer needed.

Recommended migration sequence:
1. Deploy with flag off (no behavior change).
2. Turn flag on in staging.
3. Test permissions and claim shape.
4. Roll to production.

---

## 6. Test checklist

Use real Auth0 token and verify:

1. Missing token returns 401.
2. Invalid token returns 401.
3. Valid token without required permission returns 403.
4. Valid token with required permission returns 200.
5. All channel routes keep existing authorization behavior.

Manual checks in Swagger:
1. Call `/auth/token` to get token (if still enabled).
2. Authorize in `/docs`.
3. Hit `GET /channels`, `POST /channels`, `DELETE /channels/{channel_code}` with different users.

---

## 7. Known compatibility risks

1. Package expects Orfium SSO Facade style integration; pure Auth0 tenants may behave differently depending on JWKS endpoint expectations.
2. Claim mapping includes `org_id` or `auth_org_id`; your current app mainly uses `permissions`.
3. If your environment does not expose expected SSO paths, token verification may fail.

If this happens, keep legacy mode enabled and continue using current Auth0 validation.

---

## 8. Rollback plan

Rollback is config-only:

```env
AUTH_USE_ORFIUM_AUTH=false
```

Then redeploy/restart API.

No route-level code rollback required if you used the feature-flag wrapper above.

---

## 9. Recommendation for this repo

Use this package only if your team wants standardization across services.
For pure Auth0 API validation, your current direct JWT approach is simpler and already correct.

If needed, improve the current approach with:
- JWKS refresh on unknown `kid`
- cache TTL and periodic refresh
- stricter claim validation for `azp` / `scope` rules
