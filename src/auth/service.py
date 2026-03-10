import httpx
from jose import jwt, JWTError

from src.auth.config import auth_settings
from src.auth.constants import AUTH0_ALGORITHMS
from src.auth.exceptions import InvalidTokenError, PublicKeyNotFoundError, TokenValidationError

# Cache JWKS so we don't fetch on every request
_jwks_cache: dict = {}


def _extract_email_claim(payload: dict) -> str | None:
    """Return email from standard or custom Auth0 access-token claims."""
    direct_email = payload.get("email")
    if direct_email:
        return direct_email

    legacy_custom = payload.get("user-email")
    if legacy_custom:
        return legacy_custom

    for key, value in payload.items():
        if isinstance(key, str) and key.lower().endswith("/email") and value:
            return str(value)
    return None


def get_jwks() -> dict:
    """Fetch and cache the Auth0 JWKS key set."""
    global _jwks_cache
    if not _jwks_cache:
        resp = httpx.get(auth_settings.jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def decode_token(token: str) -> dict:
    """Validate a JWT against the Auth0 JWKS and return its payload."""
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise PublicKeyNotFoundError()

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=AUTH0_ALGORITHMS,
            audience=auth_settings.AUTH0_AUDIENCE,
            issuer=auth_settings.issuer,
        )
        email = _extract_email_claim(payload)
        if email:
            payload["email"] = email
        return payload
    except JWTError as e:
        raise InvalidTokenError(detail=f"Invalid token: {e}")
    except (PublicKeyNotFoundError, InvalidTokenError):
        raise
    except Exception as e:
        raise TokenValidationError(detail=f"Token validation failed: {e}")


def request_auth0_token(username: str, password: str) -> dict:
    """Exchange username + password for an Auth0 access token (ROPC flow)."""
    resp = httpx.post(
        auth_settings.token_url,
        json={
            "grant_type": "password",
            "username": username,
            "password": password,
            "realm": auth_settings.AUTH0_REALM,
            "client_id": auth_settings.AUTH0_CLIENT_ID,
            "client_secret": auth_settings.AUTH0_CLIENT_SECRET,
            "audience": auth_settings.AUTH0_AUDIENCE,
            "scope": "openid profile email",
        },
        timeout=15,
    )
    return {"status_code": resp.status_code, "body": resp}
