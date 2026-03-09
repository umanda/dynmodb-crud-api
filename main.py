from fastapi import FastAPI

from config import ACTIVE_TABLES, AUTH0_CLIENT_ID
from routers import auth_router, channel_router

app = FastAPI(
    title="DynamoDB Channel API",
    description="""
Browse, create, update, and delete channel items stored in DynamoDB.

**Authentication:** All channel endpoints require a valid Auth0 Bearer token.

Use **`POST /auth/token`** to get your token, then click **Authorize 🔒** and paste it.

| Permission | Endpoints |
|---|---|
| `read:channel` | GET /channels, GET /channels/{{id}} |
| `write:channel` | POST /channels |
| `edit:channel` | PUT /channels/{{id}}, PATCH /channels/{{id}} |
| `delete:channel` | DELETE /channels/{{id}} |

**Current active tables:** {tables}

> To switch to production tables, update `ACTIVE_TABLES` in `config/settings.py`.
""".format(tables=", ".join(f"`{t}`" for t in ACTIVE_TABLES)),
    version="2.1.0",
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": AUTH0_CLIENT_ID,
        "appName": "DynamoDB Channel API",
        "scopes": "openid profile email",
    },
)

app.include_router(auth_router)
app.include_router(channel_router)


@app.get("/tables", tags=["Meta"], summary="List available DynamoDB tables")
def list_tables():
    """Returns the list of DynamoDB tables this API manages."""
    return {"tables": ACTIVE_TABLES}


@app.get("/health", tags=["Meta"], summary="Health check")
def health():
    return {"status": "ok"}
