from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.auth.config import auth_settings
from src.auth.router import router as auth_router
from src.channels.config import channels_settings
from src.channels.router import router as channels_router
from src.channels.service import discover_table_keys, TABLES
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    discover_table_keys()
    yield


app = FastAPI(
    title=settings.APP_TITLE,
    description="""
Browse, create, update, and delete channel items stored in DynamoDB.

**Auth:** All endpoints require a valid Auth0 Bearer token.
Use the **Authorize 🔒** button and log in with your Auth0 username/password.

| Permission | Endpoints |
|---|---|
| `read:channel` | GET /channels, GET /channels/{id} |
| `write:channel` | POST /channels |
| `edit:channel` | PUT /channels/{id}, PATCH /channels/{id} |
| `delete:channel` | DELETE /channels/{id} |

**Current active table(s):** """ + ", ".join(f"`{t}`" for t in TABLES) + """

**Swagger UI:** `http://localhost:8000/docs`
**ReDoc:** `http://localhost:8000/redoc`
""",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": auth_settings.AUTH0_CLIENT_ID,
        "appName": settings.APP_TITLE,
        "scopes": "openid profile email",
        "usePkceWithAuthorizationCodeGrant": False,
    },
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(channels_router)


# ── Meta endpoints ────────────────────────────────────────────────────────────


@app.get("/tables", summary="List available DynamoDB tables", tags=["Meta"])
def list_tables():
    """Returns the list of DynamoDB tables this API manages."""
    return {"tables": TABLES}


@app.get("/health", summary="Health check", tags=["Meta"])
def health():
    return {"status": "ok"}
