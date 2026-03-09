# Best Practices for Contributors

This document outlines the coding conventions and architectural decisions for this project.
It is based on the [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
guide by Zhanymkanov, inspired by Netflix's Dispatch project.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Module Layout](#module-layout)
- [Routing & Controllers](#routing--controllers)
- [Pydantic Schemas](#pydantic-schemas)
- [Service Layer](#service-layer)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Exceptions](#exceptions)
- [Sync vs Async Routes](#sync-vs-async-routes)
- [Cross-Module Imports](#cross-module-imports)
- [Code Style & Linting](#code-style--linting)
- [Docker](#docker)
- [Testing](#testing)
- [Commit Messages](#commit-messages)

---

## Project Structure

All application code lives under `src/`. Each domain (e.g., `auth`, `channels`) is its own
Python package with a consistent set of files:

```
src/
├── main.py            # App factory, lifespan hooks, router registration
├── config.py          # Global BaseSettings
├── database.py        # DynamoDB resource factory
├── exceptions.py      # Global exception base classes
├── auth/              # Authentication domain
│   ├── router.py
│   ├── schemas.py
│   ├── service.py
│   ├── dependencies.py
│   ├── config.py
│   ├── constants.py
│   └── exceptions.py
└── channels/          # Channel CRUD domain
    ├── router.py
    ├── schemas.py
    ├── service.py
    ├── dependencies.py
    ├── config.py
    ├── constants.py
    ├── exceptions.py
    └── utils.py
```

### Adding a new domain

1. Create a new package under `src/` (e.g., `src/reports/`).
2. Add the standard files: `router.py`, `schemas.py`, `service.py`, etc.
3. Register the router in `src/main.py` via `app.include_router(...)`.

---

## Module Layout

Each module file has a clear responsibility:

| File | Responsibility |
|---|---|
| `router.py` | Thin endpoint definitions. Validates input, calls service, returns response. |
| `schemas.py` | Pydantic models for request bodies and responses. |
| `service.py` | Core business logic and data access (DynamoDB operations). |
| `dependencies.py` | FastAPI `Depends()` callables — auth guards, query validators, etc. |
| `config.py` | Domain-specific `BaseSettings` subclass for env vars. |
| `constants.py` | Module constants — permission names, field mappings, error codes. |
| `exceptions.py` | Domain-specific exception classes (subclass global exceptions). |
| `utils.py` | Pure helper functions — data normalization, formatting. No business logic. |

---

## Routing & Controllers

- **Routers are thin.** They parse input, delegate to `service.py`, and return the result.
- **No business logic in routers.** Validation beyond Pydantic goes in `dependencies.py`.
- **Use `tags` and `summary` on every endpoint** for clean Swagger docs.
- **Use `response_model` and `status_code`** where appropriate.

```python
# Good — thin route
@router.get("/channels/{channel_code}")
def get_channel(channel_code: str):
    return channel_service.get_channel(channel_code)

# Bad — business logic in route
@router.get("/channels/{channel_code}")
def get_channel(channel_code: str):
    dynamo = boto3.resource("dynamodb")
    tbl = dynamo.Table("MyTable")
    resp = tbl.get_item(Key={"id": channel_code})
    ...
```

---

## Pydantic Schemas

- **Use Pydantic extensively** for validation — field constraints, regex patterns, custom validators.
- **Separate request and response schemas** when they differ.
- **Use `Field(...)` with examples** for better Swagger documentation.

```python
class ChannelWrite(BaseModel):
    ChannelCode: str = Field(..., min_length=1)
    URLs: List[str]

    @field_validator("URLs")
    @classmethod
    def urls_not_empty(cls, v):
        if not v:
            raise ValueError("URLs must contain at least one entry.")
        return v
```

---

## Service Layer

- **All DynamoDB interactions live in `service.py`.**
- Keep service functions focused — one function per operation.
- Raise domain-specific exceptions (from `exceptions.py`), not raw `HTTPException`.

```python
# Good
def get_channel(channel_code: str) -> dict:
    ...
    raise ChannelNotFoundError(channel_code)

# Bad
def get_channel(channel_code: str) -> dict:
    ...
    raise HTTPException(status_code=404, detail="Not found")
```

---

## Dependencies

- **Use `Depends()` for reusable validation** — auth checks, table validation, etc.
- **Chain dependencies** to avoid duplication (`require_permission` wraps `get_current_user`).
- Dependencies are cached per-request — calling the same dependency multiple times in one
  request only executes it once.

```python
def require_permission(permission: str):
    def _check(user: dict = Depends(get_current_user)):
        if permission not in user.get("permissions", []):
            raise PermissionDeniedError(...)
        return user
    return _check
```

---

## Configuration

- **Decouple settings per domain** using separate `BaseSettings` subclasses.
- **Never hardcode secrets** — use environment variables.
- Each config file instantiates a singleton: `auth_settings = AuthConfig()`.
- Global settings live in `src/config.py`; domain settings in `src/<domain>/config.py`.

```python
# src/auth/config.py
class AuthConfig(BaseSettings):
    AUTH0_DOMAIN: str = "dev-example.us.auth0.com"
    AUTH0_AUDIENCE: str = "https://api.example.test"
    model_config = {"env_file": ".env", "extra": "ignore"}

auth_settings = AuthConfig()
```

---

## Exceptions

- **Global base exceptions** live in `src/exceptions.py` (`NotFoundError`, `ConflictError`, etc.).
- **Domain exceptions** extend these bases and live in `src/<domain>/exceptions.py`.
- This gives you meaningful, self-documenting error classes throughout the codebase.

```python
# src/channels/exceptions.py
class ChannelNotFoundError(NotFoundError):
    def __init__(self, channel_code: str):
        super().__init__(detail=f"Channel '{channel_code}' not found.")
```

---

## Sync vs Async Routes

This project uses **sync routes** because `boto3` is a synchronous SDK. FastAPI automatically
runs sync routes in a threadpool, so they do **not** block the event loop.

**Rules:**

1. If using a sync library (like `boto3`), define the route as `def` (sync).
2. **Never** use `async def` with blocking I/O — this blocks the entire event loop.
3. If you add an async dependency (e.g., `httpx.AsyncClient`), use `async def` routes.

```python
# Good — sync route → FastAPI offloads to threadpool
@router.get("/channels")
def list_channels():
    return channel_service.list_channels()

# Bad — async route with blocking call
@router.get("/channels")
async def list_channels():
    return channel_service.list_channels()  # blocks event loop!
```

---

## Cross-Module Imports

When importing from another domain, use explicit module-level imports:

```python
from src.auth import constants as auth_constants
from src.auth.dependencies import require_permission
from src.channels import service as channel_service
```

**Never use `from src.auth import *`.**

---

## Code Style & Linting

- Use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.
- Prefer type hints on all function signatures.
- Use `snake_case` for functions and variables, `PascalCase` for classes.
- Keep lines under 120 characters.

```bash
# Lint and auto-fix
ruff check --fix src/

# Format
ruff format src/
```

---

## Docker

- The `Dockerfile` copies `src/` and runs `uvicorn src.main:app`.
- `docker-compose.yml` mounts `./src` for live-reload during development.
- All configuration is via environment variables — no secrets in the image.

```bash
# Build and run
docker compose up --build

# Background
docker compose up --build -d
```

---

## Testing

- Tests live in `tests/` mirroring the `src/` structure (`tests/auth/`, `tests/channels/`).
- Use `pytest` as the test runner.
- Prefer `httpx.AsyncClient` with `ASGITransport` for integration tests against the FastAPI app.
- Set up async test client from day one to avoid event loop issues.

```python
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
```

---

## Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject> <jira ticket id(s)>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`,
`ci`, `release`, `deps`

**Examples:**

```
feat(channels): add batch delete endpoint PROJ-123
fix(auth): handle expired JWKS cache
refactor(channels): extract normalize_item to utils
docs: update contributor best practices
```

Keep each line under 72 characters.

---

## References

- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) — primary inspiration for this project's structure
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [boto3 DynamoDB Reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
