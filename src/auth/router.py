from fastapi import APIRouter, HTTPException

from src.auth import service as auth_service
from src.auth.schemas import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Get Auth0 access token (Resource Owner Password flow)",
    description="""
Exchange Auth0 username + password for a Bearer token.

The token is returned as `access_token`. Copy it and click **Authorize 🔒**
above, then paste it into the **BearerAuth** field to authenticate all other endpoints.

**Test users:**

| User | Role | Permissions |
|---|---|---|
| `user-admin@acme.test` | Admin | read, write, edit, delete |
| `user-editor@acme.test` | Editor | read, edit |
| `user-viewer@acme.test` | Viewer | read |
| `user-manager@acme.test` | Manager | read, write, edit |

Password for all: `!@#$Qwer1234`
""",
)
def get_token(body: TokenRequest):
    result = auth_service.request_auth0_token(body.username, body.password)
    resp = result["body"]

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
