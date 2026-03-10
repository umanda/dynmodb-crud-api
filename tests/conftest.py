import pytest
from fastapi.testclient import TestClient

import src.main as main_module
import src.auth.service as auth_service
from src.auth.constants import (
    PERMISSION_DELETE_CHANNEL,
    PERMISSION_EDIT_CHANNEL,
    PERMISSION_READ_CHANNEL,
    PERMISSION_WRITE_CHANNEL,
)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Prevent startup from reaching DynamoDB during tests.
    monkeypatch.setattr(main_module, "discover_table_keys", lambda: None)

    # Default user has all permissions so protected endpoints can be tested.
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        lambda _token: {
            "sub": "test-user",
            "email": "user-admin@acme.test",
            "permissions": [
                PERMISSION_READ_CHANNEL,
                PERMISSION_WRITE_CHANNEL,
                PERMISSION_EDIT_CHANNEL,
                PERMISSION_DELETE_CHANNEL,
            ],
        },
    )

    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
