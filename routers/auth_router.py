from fastapi import APIRouter

from auth import Auth0Service, AuthHandler

# ── Dependency wiring ─────────────────────────────────────────────────────────
_auth_service = Auth0Service()
_auth_handler = AuthHandler(service=_auth_service)

router = APIRouter(prefix="/auth", tags=["Auth"])

router.add_api_route(
    "/token",
    _auth_handler.get_token,
    methods=["POST"],
    summary="Get Auth0 access token",
    description="""
Exchange your Auth0 **username + password** for a Bearer token
using the Resource Owner Password flow.

Once you have the token:
1. Copy the `access_token` value
2. Click **Authorize 🔒** at the top of this page
3. Paste the token into the **BearerAuth** field

**Test users:**

| User | Role | Permissions |
|---|---|---|
| `user-admin@acme.test` | Admin | read, write, edit, delete |
| `user-editor@acme.test` | Editor | read, edit |
| `user-viewer@acme.test` | Viewer | read only |
| `user-manager@acme.test` | Manager | read, write, edit |

Password for all: `!@#$Qwer1234`
""",
)
